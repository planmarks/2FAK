/* 2FAK Mouse Jiggler - HID mouse class (report descriptor + IN endpoint) */
#include "usbd_mouse.h"
#include "usbd_ctlreq.h"
#include "usbd_core.h"

static uint8_t USBD_MOUSE_Init(USBD_HandleTypeDef *pdev, uint8_t cfgidx);
static uint8_t USBD_MOUSE_DeInit(USBD_HandleTypeDef *pdev, uint8_t cfgidx);
static uint8_t USBD_MOUSE_Setup(USBD_HandleTypeDef *pdev, USBD_SetupReqTypedef *req);
static uint8_t *USBD_MOUSE_GetCfgDesc(uint16_t *length);
static uint8_t *USBD_MOUSE_GetDeviceQualifierDesc(uint16_t *length);
static uint8_t USBD_MOUSE_DataIn(USBD_HandleTypeDef *pdev, uint8_t epnum);

USBD_ClassTypeDef USBD_MOUSE = {
  USBD_MOUSE_Init,
  USBD_MOUSE_DeInit,
  USBD_MOUSE_Setup,
  NULL,                 /* EP0_TxSent */
  NULL,                 /* EP0_RxReady */
  USBD_MOUSE_DataIn,    /* DataIn */
  NULL,                 /* DataOut */
  NULL,                 /* SOF */
  NULL,
  NULL,
  USBD_MOUSE_GetCfgDesc,
  USBD_MOUSE_GetCfgDesc,
  USBD_MOUSE_GetCfgDesc,
  USBD_MOUSE_GetDeviceQualifierDesc,
};

/* Configuration descriptor: config + interface(HID boot mouse) + HID desc + IN endpoint */
__ALIGN_BEGIN static uint8_t USBD_MOUSE_CfgDesc[34] __ALIGN_END = {
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
  0x02,              /* bInterfaceProtocol: Mouse */
  0x00,              /* iInterface */

  /* HID descriptor */
  0x09, HID_DESCRIPTOR_TYPE,
  0x11, 0x01,        /* bcdHID 1.11 */
  0x00,              /* bCountryCode */
  0x01,              /* bNumDescriptors */
  HID_REPORT_DESC,   /* bDescriptorType: Report */
  MOUSE_REPORT_DESC_SIZE, 0x00,

  /* Endpoint IN */
  0x07, USB_DESC_TYPE_ENDPOINT,
  MOUSE_EPIN_ADDR,   /* bEndpointAddress */
  0x03,              /* bmAttributes: Interrupt */
  MOUSE_EPIN_SIZE, 0x00,
  0x0A,              /* bInterval: 10 ms */
};

/* HID class descriptor returned for GET_DESCRIPTOR(HID) */
__ALIGN_BEGIN static uint8_t USBD_MOUSE_HIDDesc[9] __ALIGN_END = {
  0x09, HID_DESCRIPTOR_TYPE,
  0x11, 0x01,
  0x00,
  0x01,
  HID_REPORT_DESC,
  MOUSE_REPORT_DESC_SIZE, 0x00,
};

__ALIGN_BEGIN static uint8_t USBD_MOUSE_DeviceQualifierDesc[USB_LEN_DEV_QUALIFIER_DESC] __ALIGN_END = {
  USB_LEN_DEV_QUALIFIER_DESC, USB_DESC_TYPE_DEVICE_QUALIFIER,
  0x00, 0x02, 0x00, 0x00, 0x00, 0x40, 0x01, 0x00,
};

/* Standard relative-mouse report descriptor (52 bytes):
 * report = { buttons(3 + 5 pad), X(-127..127), Y(-127..127), Wheel(-127..127) } */
__ALIGN_BEGIN static uint8_t USBD_MOUSE_ReportDesc[MOUSE_REPORT_DESC_SIZE] __ALIGN_END = {
  0x05, 0x01,        /* Usage Page (Generic Desktop) */
  0x09, 0x02,        /* Usage (Mouse) */
  0xA1, 0x01,        /* Collection (Application) */
  0x09, 0x01,        /*   Usage (Pointer) */
  0xA1, 0x00,        /*   Collection (Physical) */
  0x05, 0x09,        /*     Usage Page (Buttons) */
  0x19, 0x01,        /*     Usage Minimum (1) */
  0x29, 0x03,        /*     Usage Maximum (3) */
  0x15, 0x00,        /*     Logical Minimum (0) */
  0x25, 0x01,        /*     Logical Maximum (1) */
  0x95, 0x03,        /*     Report Count (3) */
  0x75, 0x01,        /*     Report Size (1) */
  0x81, 0x02,        /*     Input (Data,Var,Abs) ; 3 buttons */
  0x95, 0x01,        /*     Report Count (1) */
  0x75, 0x05,        /*     Report Size (5) */
  0x81, 0x01,        /*     Input (Const)       ; 5-bit padding */
  0x05, 0x01,        /*     Usage Page (Generic Desktop) */
  0x09, 0x30,        /*     Usage (X) */
  0x09, 0x31,        /*     Usage (Y) */
  0x09, 0x38,        /*     Usage (Wheel) */
  0x15, 0x81,        /*     Logical Minimum (-127) */
  0x25, 0x7F,        /*     Logical Maximum (127) */
  0x75, 0x08,        /*     Report Size (8) */
  0x95, 0x03,        /*     Report Count (3) */
  0x81, 0x06,        /*     Input (Data,Var,Rel) ; X, Y, Wheel */
  0xC0,              /*   End Collection */
  0xC0               /* End Collection */
};

static USBD_MOUSE_HandleTypeDef mouse_handle;

static uint8_t USBD_MOUSE_Init(USBD_HandleTypeDef *pdev, uint8_t cfgidx) {
  (void)cfgidx;
  USBD_LL_OpenEP(pdev, MOUSE_EPIN_ADDR, USBD_EP_TYPE_INTR, MOUSE_EPIN_SIZE);
  pdev->ep_in[MOUSE_EPIN_ADDR & 0xFU].is_used = 1U;
  pdev->pClassData = &mouse_handle;
  mouse_handle.state = MOUSE_IDLE;
  return USBD_OK;
}

static uint8_t USBD_MOUSE_DeInit(USBD_HandleTypeDef *pdev, uint8_t cfgidx) {
  (void)cfgidx;
  USBD_LL_CloseEP(pdev, MOUSE_EPIN_ADDR);
  pdev->ep_in[MOUSE_EPIN_ADDR & 0xFU].is_used = 0U;
  return USBD_OK;
}

static uint8_t USBD_MOUSE_Setup(USBD_HandleTypeDef *pdev, USBD_SetupReqTypedef *req) {
  USBD_MOUSE_HandleTypeDef *h = (USBD_MOUSE_HandleTypeDef *)pdev->pClassData;
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
        len = MIN(MOUSE_REPORT_DESC_SIZE, req->wLength);
        pbuf = USBD_MOUSE_ReportDesc;
      } else if ((req->wValue >> 8) == HID_DESCRIPTOR_TYPE) {
        len = MIN(sizeof(USBD_MOUSE_HIDDesc), req->wLength);
        pbuf = USBD_MOUSE_HIDDesc;
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

static uint8_t USBD_MOUSE_DataIn(USBD_HandleTypeDef *pdev, uint8_t epnum) {
  (void)epnum;
  ((USBD_MOUSE_HandleTypeDef *)pdev->pClassData)->state = MOUSE_IDLE;
  return USBD_OK;
}

static uint8_t *USBD_MOUSE_GetCfgDesc(uint16_t *length) {
  *length = sizeof(USBD_MOUSE_CfgDesc);
  return USBD_MOUSE_CfgDesc;
}

static uint8_t *USBD_MOUSE_GetDeviceQualifierDesc(uint16_t *length) {
  *length = sizeof(USBD_MOUSE_DeviceQualifierDesc);
  return USBD_MOUSE_DeviceQualifierDesc;
}

uint8_t USBD_MOUSE_IsIdle(USBD_HandleTypeDef *pdev) {
  USBD_MOUSE_HandleTypeDef *h = (USBD_MOUSE_HandleTypeDef *)pdev->pClassData;
  if (h == NULL) return 0;
  return (h->state == MOUSE_IDLE);
}

uint8_t USBD_MOUSE_SendReport(USBD_HandleTypeDef *pdev, uint8_t *report4) {
  USBD_MOUSE_HandleTypeDef *h = (USBD_MOUSE_HandleTypeDef *)pdev->pClassData;
  if (pdev->dev_state != USBD_STATE_CONFIGURED) return USBD_FAIL;
  if (h == NULL) return USBD_FAIL;
  h->state = MOUSE_BUSY;
  USBD_LL_Transmit(pdev, MOUSE_EPIN_ADDR, report4, MOUSE_EPIN_SIZE);
  return USBD_OK;
}
