#ifndef FIDO2_PR_APP_COMMON_H
#define FIDO2_PR_APP_COMMON_H


/* 2FAK product identity. VID/PID are placeholders (pid.codes range) for pre-production;
   request/allocate your own USB IDs before mass production. */
#define USBD_VID                        0x1209
#define USBD_PID                        0x2FA2
#define USBD_LANGID_STRING              0x409
#define USBD_MANUFACTURER_STRING        "muru.global"
#define USBD_PRODUCT_FS_STRING          SOLO_PRODUCT_NAME
#define USBD_SERIAL_NUM                 "0123456789ABCDEF"

#define APP_EXECS_BOOTLOADER
//#define BUTTON_EXECS_BOOTLOADER


#endif //FIDO2_PR_APP_COMMON_H
