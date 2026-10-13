/* 2FAK Mouse Jiggler - USB device library config */
#ifndef __USBD_CONF_H
#define __USBD_CONF_H

#include "stm32l4xx_hal.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define USBD_MAX_NUM_INTERFACES               1
#define USBD_MAX_NUM_CONFIGURATION            1
#define USBD_MAX_STR_DESC_SIZ                 64
#define USBD_SELF_POWERED                     0
#define USBD_DEBUG_LEVEL                      0

/* Mouse HID interrupt IN endpoint */
#define MOUSE_EPIN_ADDR                       0x81U
#define MOUSE_EPIN_SIZE                       0x04U   /* 4-byte report: buttons, dx, dy, wheel */

#endif
