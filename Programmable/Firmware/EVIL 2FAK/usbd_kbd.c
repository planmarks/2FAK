/* 2FAK USB business-card demo - HID boot keyboard class */
#include "usbd_kbd.h"
#include "usbd_ctlreq.h"
#include "usbd_core.h"

static uint8_t USBD_KBD_Init(USBD_HandleTypeDef *pdev, uint8_t cfgidx);
static uint8_t USBD_KBD_DeInit(USBD_HandleTypeDef *pdev, uint8_t cfgidx);
static uint8_t USBD_KBD_Setup(USBD_HandleTypeDef *pdev, USBD_SetupReqTypedef *req);
static uint8_t *USBD_KBD_GetCfgDesc(uint16_t *length);
static uint8_t *USBD_KBD_GetDeviceQualifierDesc(uint16_t *length);
static uint8_t USBD_KBD_DataIn(USBD_HandleTypeDef *pdev, uint8_t epnum);

USBD_ClassTypeDef USBD_KBD = {
  USBD_KBD_Init,
  USBD_KBD_DeInit,
  USBD_KBD_Setup,
  NULL,               /* EP0_TxSent */
  NULL,               /* EP0_RxReady */
  USBD_KBD_DataIn,    /* DataIn */
  NULL,               /* DataOut */
  NULL,               /* SOF */
  NULL,
  NULL,
  USBD_KBD_GetCfgDesc,
  USBD_KBD_GetCfgDesc,
  USBD_KBD_GetCfgDesc,
  USBD_KBD_GetDeviceQualifierDesc,
};

/* Configuration descriptor: config + interface(HID boot keyboard) + HID desc + IN endpoint */
__ALIGN_BEGIN static uint8_t USBD_KBD_CfgDesc[34] __ALIGN_END = {
  0x09, USB_DESC_TYPE_CONFIGURATION,
  34, 0x00,          /* wTotalLength */
  0x01,              /* bNumInterfaces */
  0x01,              /* bConfigurationValue */
  0x00,              /* iConfiguration */
  0xA0,              /* bmAttributes: bus powered + remote wakeup */
  0x32,              /* MaxPower 100 mA */

  /* Interface */
  0x09, USB_DESC_TYPE_INTERFACE,
  0x00,              /* bInterfaceNumber */
  0x00,              /* bAlternateSetting */
  0x01,              /* bNumEndpoints */
  0x03,              /* bInterfaceClass: HID */
  0x01,              /* bInterfaceSubClass: Boot */
  0x01,              /* bInterfaceProtocol: Keyboard */
  0x00,              /* iInterface */

  /* HID descriptor */
  0x09, HID_DESCRIPTOR_TYPE,
  0x11, 0x01,        /* bcdHID 1.11 */
  0x00,              /* bCountryCode */
  0x01,              /* bNumDescriptors */
  HID_REPORT_DESC,   /* bDescriptorType: Report */
  KBD_REPORT_DESC_SIZE, 0x00,

  /* Endpoint IN */
  0x07, USB_DESC_TYPE_ENDPOINT,
  KBD_EPIN_ADDR,     /* bEndpointAddress */
  0x03,              /* bmAttributes: Interrupt */
  KBD_EPIN_SIZE, 0x00,
  0x0A,              /* bInterval: 10 ms */
};

/* HID class descriptor returned for GET_DESCRIPTOR(HID) */
__ALIGN_BEGIN static uint8_t USBD_KBD_HIDDesc[9] __ALIGN_END = {
  0x09, HID_DESCRIPTOR_TYPE,
  0x11, 0x01,
  0x00,
  0x01,
  HID_REPORT_DESC,
  KBD_REPORT_DESC_SIZE, 0x00,
};

__ALIGN_BEGIN static uint8_t USBD_KBD_DeviceQualifierDesc[USB_LEN_DEV_QUALIFIER_DESC] __ALIGN_END = {
  USB_LEN_DEV_QUALIFIER_DESC, USB_DESC_TYPE_DEVICE_QUALIFIER,
  0x00, 0x02, 0x00, 0x00, 0x00, 0x40, 0x01, 0x00,
};

/* Standard boot-keyboard report descriptor (63 bytes) */
__ALIGN_BEGIN static uint8_t USBD_KBD_ReportDesc[KBD_REPORT_DESC_SIZE] __ALIGN_END = {
  0x05, 0x01,        /* Usage Page (Generic Desktop) */
  0x09, 0x06,        /* Usage (Keyboard) */
  0xA1, 0x01,        /* Collection (Application) */
  0x05, 0x07,        /*   Usage Page (Key Codes) */
  0x19, 0xE0,        /*   Usage Minimum (224) */
  0x29, 0xE7,        /*   Usage Maximum (231) */
  0x15, 0x00,        /*   Logical Minimum (0) */
  0x25, 0x01,        /*   Logical Maximum (1) */
  0x75, 0x01,        /*   Report Size (1) */
  0x95, 0x08,        /*   Report Count (8) */
  0x81, 0x02,        /*   Input (Data,Var,Abs) ; modifier byte */
  0x95, 0x01,        /*   Report Count (1) */
  0x75, 0x08,        /*   Report Size (8) */
  0x81, 0x01,        /*   Input (Const) ; reserved byte */
  0x95, 0x05,        /*   Report Count (5) */
  0x75, 0x01,        /*   Report Size (1) */
  0x05, 0x08,        /*   Usage Page (LEDs) */
  0x19, 0x01,        /*   Usage Minimum (1) */
  0x29, 0x05,        /*   Usage Maximum (5) */
  0x91, 0x02,        /*   Output (Data,Var,Abs) ; LED report */
  0x95, 0x01,        /*   Report Count (1) */
  0x75, 0x03,        /*   Report Size (3) */
  0x91, 0x01,        /*   Output (Const) ; LED padding */
  0x95, 0x06,        /*   Report Count (6) */
  0x75, 0x08,        /*   Report Size (8) */
  0x15, 0x00,        /*   Logical Minimum (0) */
  0x25, 0x65,        /*   Logical Maximum (101) */
  0x05, 0x07,        /*   Usage Page (Key Codes) */
  0x19, 0x00,        /*   Usage Minimum (0) */
  0x29, 0x65,        /*   Usage Maximum (101) */
  0x81, 0x00,        /*   Input (Data,Array) ; keycodes */
  0xC0               /* End Collection */
};

static USBD_KBD_HandleTypeDef kbd_handle;

static uint8_t USBD_KBD_Init(USBD_HandleTypeDef *pdev, uint8_t cfgidx) {
  (void)cfgidx;
  USBD_LL_OpenEP(pdev, KBD_EPIN_ADDR, USBD_EP_TYPE_INTR, KBD_EPIN_SIZE);
  pdev->ep_in[KBD_EPIN_ADDR & 0xFU].is_used = 1U;
  pdev->pClassData = &kbd_handle;
  kbd_handle.state = KBD_IDLE;
  return USBD_OK;
}

static uint8_t USBD_KBD_DeInit(USBD_HandleTypeDef *pdev, uint8_t cfgidx) {
  (void)cfgidx;
  USBD_LL_CloseEP(pdev, KBD_EPIN_ADDR);
  pdev->ep_in[KBD_EPIN_ADDR & 0xFU].is_used = 0U;
  return USBD_OK;
}

static uint8_t USBD_KBD_Setup(USBD_HandleTypeDef *pdev, USBD_SetupReqTypedef *req) {
  USBD_KBD_HandleTypeDef *h = (USBD_KBD_HandleTypeDef *)pdev->pClassData;
  uint16_t len = 0U;
  uint8_t *pbuf = NULL;
  uint16_t status_info = 0U;
  USBD_StatusTypeDef ret = USBD_OK;

  switch (req->bmRequest & USB_REQ_TYPE_MASK) {
  case USB_REQ_TYPE_CLASS:
    switch (req->bRequest) {
    case HID_REQ_SET_PROTOCOL: h->Protocol = (uint8_t)(req->wValue); break;
    case HID_REQ_GET_PROTOCOL: USBD_CtlSendData(pdev, (uint8_t *)&h->Protocol, 1U); break;
    case HID_REQ_SET_IDLE:     h->IdleState = (uint8_t)(req->wValue >> 8); break;
    case HID_REQ_GET_IDLE:     USBD_CtlSendData(pdev, (uint8_t *)&h->IdleState, 1U); break;
    default: USBD_CtlError(pdev, req); ret = USBD_FAIL; break;
    }
    break;
  case USB_REQ_TYPE_STANDARD:
    switch (req->bRequest) {
    case USB_REQ_GET_STATUS:
      if (pdev->dev_state == USBD_STATE_CONFIGURED) USBD_CtlSendData(pdev, (uint8_t *)&status_info, 2U);
      else { USBD_CtlError(pdev, req); ret = USBD_FAIL; }
      break;
    case USB_REQ_GET_DESCRIPTOR:
      if ((req->wValue >> 8) == HID_REPORT_DESC) {
        len = MIN(KBD_REPORT_DESC_SIZE, req->wLength);
        pbuf = USBD_KBD_ReportDesc;
      } else if ((req->wValue >> 8) == HID_DESCRIPTOR_TYPE) {
        len = MIN(sizeof(USBD_KBD_HIDDesc), req->wLength);
        pbuf = USBD_KBD_HIDDesc;
      } else { USBD_CtlError(pdev, req); ret = USBD_FAIL; break; }
      USBD_CtlSendData(pdev, pbuf, len);
      break;
    case USB_REQ_GET_INTERFACE:
      if (pdev->dev_state == USBD_STATE_CONFIGURED) USBD_CtlSendData(pdev, (uint8_t *)&h->AltSetting, 1U);
      else { USBD_CtlError(pdev, req); ret = USBD_FAIL; }
      break;
    case USB_REQ_SET_INTERFACE:
      if (pdev->dev_state == USBD_STATE_CONFIGURED) h->AltSetting = (uint8_t)(req->wValue);
      else { USBD_CtlError(pdev, req); ret = USBD_FAIL; }
      break;
    default: USBD_CtlError(pdev, req); ret = USBD_FAIL; break;
    }
    break;
  default: USBD_CtlError(pdev, req); ret = USBD_FAIL; break;
  }
  return ret;
}

static uint8_t USBD_KBD_DataIn(USBD_HandleTypeDef *pdev, uint8_t epnum) {
  (void)epnum;
  ((USBD_KBD_HandleTypeDef *)pdev->pClassData)->state = KBD_IDLE;
  return USBD_OK;
}

static uint8_t *USBD_KBD_GetCfgDesc(uint16_t *length) {
  *length = sizeof(USBD_KBD_CfgDesc);
  return USBD_KBD_CfgDesc;
}

static uint8_t *USBD_KBD_GetDeviceQualifierDesc(uint16_t *length) {
  *length = sizeof(USBD_KBD_DeviceQualifierDesc);
  return USBD_KBD_DeviceQualifierDesc;
}

uint8_t USBD_KBD_IsIdle(USBD_HandleTypeDef *pdev) {
  USBD_KBD_HandleTypeDef *h = (USBD_KBD_HandleTypeDef *)pdev->pClassData;
  if (h == NULL) return 0;
  return (h->state == KBD_IDLE);
}

uint8_t USBD_KBD_SendReport(USBD_HandleTypeDef *pdev, uint8_t *report8) {
  USBD_KBD_HandleTypeDef *h = (USBD_KBD_HandleTypeDef *)pdev->pClassData;
  if (pdev->dev_state != USBD_STATE_CONFIGURED) return USBD_FAIL;
  if (h == NULL) return USBD_FAIL;
  h->state = KBD_BUSY;
  USBD_LL_Transmit(pdev, KBD_EPIN_ADDR, report8, KBD_EPIN_SIZE);
  return USBD_OK;
}
