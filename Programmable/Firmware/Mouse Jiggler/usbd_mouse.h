/* 2FAK Mouse Jiggler - HID mouse class */
#ifndef __USBD_MOUSE_H
#define __USBD_MOUSE_H

#include "usbd_ioreq.h"
#include "usbd_conf.h"

#define MOUSE_REPORT_DESC_SIZE 52U
#define HID_DESCRIPTOR_TYPE    0x21U
#define HID_REPORT_DESC        0x22U
#define HID_REQ_SET_PROTOCOL   0x0BU
#define HID_REQ_GET_PROTOCOL   0x03U
#define HID_REQ_SET_IDLE       0x0AU
#define HID_REQ_GET_IDLE       0x02U

typedef enum { MOUSE_IDLE = 0, MOUSE_BUSY } MOUSE_StateTypeDef;

typedef struct {
  uint32_t            Protocol;
  uint32_t            IdleState;
  uint32_t            AltSetting;
  MOUSE_StateTypeDef  state;
} USBD_MOUSE_HandleTypeDef;

extern USBD_ClassTypeDef USBD_MOUSE;

/* Send one 4-byte mouse report: {buttons, dx, dy, wheel}. */
uint8_t USBD_MOUSE_SendReport(USBD_HandleTypeDef *pdev, uint8_t *report4);
uint8_t USBD_MOUSE_IsIdle(USBD_HandleTypeDef *pdev);

#endif
