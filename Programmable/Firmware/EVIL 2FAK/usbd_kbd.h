/* 2FAK USB business-card demo - HID boot keyboard class */
#ifndef __USBD_KBD_H
#define __USBD_KBD_H

#include "usbd_ioreq.h"
#include "usbd_conf.h"

#define KBD_REPORT_DESC_SIZE   63U
#define HID_DESCRIPTOR_TYPE    0x21U
#define HID_REPORT_DESC        0x22U
#define HID_REQ_SET_PROTOCOL   0x0BU
#define HID_REQ_GET_PROTOCOL   0x03U
#define HID_REQ_SET_IDLE       0x0AU
#define HID_REQ_GET_IDLE       0x02U

typedef enum { KBD_IDLE = 0, KBD_BUSY } KBD_StateTypeDef;

typedef struct {
  uint32_t          Protocol;
  uint32_t          IdleState;
  uint32_t          AltSetting;
  KBD_StateTypeDef  state;
} USBD_KBD_HandleTypeDef;

extern USBD_ClassTypeDef USBD_KBD;

/* Send one 8-byte boot-keyboard report (modifier, reserved, 6 keycodes). */
uint8_t USBD_KBD_SendReport(USBD_HandleTypeDef *pdev, uint8_t *report8);
uint8_t USBD_KBD_IsIdle(USBD_HandleTypeDef *pdev);

#endif
