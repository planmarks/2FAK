# 2FAK USB business-card demo firmware
PREFIX ?= arm-none-eabi-
CC      = $(PREFIX)gcc
CP      = $(PREFIX)objcopy
SZ      = $(PREFIX)size

TARGET  = 2fak_card

MCU     = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard

DEFS    = -DSTM32L432xx -DUSE_FULL_LL_DRIVER

INCS    = -I. -Ishared/lib -Ishared/lib/usbd -Ishared/cmsis

CFLAGS  = $(MCU) $(DEFS) $(INCS) -Os -g3 -Wall \
          -ffunction-sections -fdata-sections -fno-common

LDFLAGS = $(MCU) -specs=nano.specs -specs=nosys.specs -T linker.ld \
          -Wl,--gc-sections -Wl,-Map=$(TARGET).map -lc -lm

SRCS = \
  main.c \
  usbd_kbd.c \
  usbd_desc.c \
  usbd_conf.c \
  shared/lib/usbd/usbd_core.c \
  shared/lib/usbd/usbd_ctlreq.c \
  shared/lib/usbd/usbd_ioreq.c \
  shared/lib/stm32l4xx_hal_pcd.c \
  shared/lib/stm32l4xx_hal_pcd_ex.c \
  shared/lib/stm32l4xx_ll_usb.c \
  shared/lib/stm32l4xx_ll_rcc.c \
  shared/lib/stm32l4xx_ll_gpio.c \
  shared/lib/stm32l4xx_ll_pwr.c \
  shared/lib/stm32l4xx_ll_utils.c \
  shared/startup_stm32l432xx.s

all: $(TARGET).hex

$(TARGET).elf: $(SRCS) linker.ld
	$(CC) $(CFLAGS) $(SRCS) -o $@ $(LDFLAGS)
	$(SZ) $@

$(TARGET).hex: $(TARGET).elf
	$(CP) -O ihex $< $@
	$(CP) -O binary $< $(TARGET).bin

clean:
	rm -f $(TARGET).elf $(TARGET).hex $(TARGET).bin $(TARGET).map
