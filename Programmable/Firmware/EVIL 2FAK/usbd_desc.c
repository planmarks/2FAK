/* 2FAK USB business-card demo - device & string descriptors */
#include "usbd_core.h"
#include "usbd_desc.h"
#include "usbd_conf.h"

#define USBD_VID            0x1209      /* pid.codes community VID (demo use) */
#define USBD_PID            0x2FAC
#define USBD_LANGID_STRING  0x0409      /* English (US) */
#define USBD_MANUFACTURER   "papathought"
#define USBD_PRODUCT        "2FAK Business Card"
#define USBD_SERIAL         "2FAK-DEMO-0001"

static uint8_t *KBD_DeviceDescriptor(USBD_SpeedTypeDef speed, uint16_t *length);
static uint8_t *KBD_LangIDStrDescriptor(USBD_SpeedTypeDef speed, uint16_t *length);
static uint8_t *KBD_ManufacturerStrDescriptor(USBD_SpeedTypeDef speed, uint16_t *length);
static uint8_t *KBD_ProductStrDescriptor(USBD_SpeedTypeDef speed, uint16_t *length);
static uint8_t *KBD_SerialStrDescriptor(USBD_SpeedTypeDef speed, uint16_t *length);

USBD_DescriptorsTypeDef KBD_Desc = {
  KBD_DeviceDescriptor,
  KBD_LangIDStrDescriptor,
  KBD_ManufacturerStrDescriptor,
  KBD_ProductStrDescriptor,
  KBD_SerialStrDescriptor,
};

__ALIGN_BEGIN static const uint8_t USBD_DeviceDesc[USB_LEN_DEV_DESC] __ALIGN_END = {
  0x12,                       /* bLength */
  USB_DESC_TYPE_DEVICE,       /* bDescriptorType */
  0x00, 0x02,                 /* bcdUSB 2.00 */
  0x00,                       /* bDeviceClass (per interface) */
  0x00,                       /* bDeviceSubClass */
  0x00,                       /* bDeviceProtocol */
  USB_MAX_EP0_SIZE,           /* bMaxPacketSize0 */
  LOBYTE(USBD_VID), HIBYTE(USBD_VID),
  LOBYTE(USBD_PID), HIBYTE(USBD_PID),
  0x00, 0x01,                 /* bcdDevice 1.0 */
  USBD_IDX_MFC_STR,           /* iManufacturer */
  USBD_IDX_PRODUCT_STR,       /* iProduct */
  USBD_IDX_SERIAL_STR,        /* iSerialNumber */
  USBD_MAX_NUM_CONFIGURATION  /* bNumConfigurations */
};

__ALIGN_BEGIN static const uint8_t USBD_LangIDDesc[USB_LEN_LANGID_STR_DESC] __ALIGN_END = {
  USB_LEN_LANGID_STR_DESC,
  USB_DESC_TYPE_STRING,
  LOBYTE(USBD_LANGID_STRING), HIBYTE(USBD_LANGID_STRING),
};

__ALIGN_BEGIN static uint8_t USBD_StrDesc[USBD_MAX_STR_DESC_SIZ] __ALIGN_END;

static uint8_t *KBD_DeviceDescriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
  (void)speed; *length = sizeof(USBD_DeviceDesc); return (uint8_t *)USBD_DeviceDesc;
}
static uint8_t *KBD_LangIDStrDescriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
  (void)speed; *length = sizeof(USBD_LangIDDesc); return (uint8_t *)USBD_LangIDDesc;
}
static uint8_t *KBD_ManufacturerStrDescriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
  (void)speed; USBD_GetString((uint8_t *)USBD_MANUFACTURER, USBD_StrDesc, sizeof(USBD_StrDesc), length); return USBD_StrDesc;
}
static uint8_t *KBD_ProductStrDescriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
  (void)speed; USBD_GetString((uint8_t *)USBD_PRODUCT, USBD_StrDesc, sizeof(USBD_StrDesc), length); return USBD_StrDesc;
}
static uint8_t *KBD_SerialStrDescriptor(USBD_SpeedTypeDef speed, uint16_t *length) {
  (void)speed; USBD_GetString((uint8_t *)USBD_SERIAL, USBD_StrDesc, sizeof(USBD_StrDesc), length); return USBD_StrDesc;
}
