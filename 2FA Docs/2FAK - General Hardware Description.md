# 2FAK - General Hardware Description

General description of the 2FAK hardware platform. This document covers the hardware only;
it makes no reference to firmware or firmware behaviour.

## Overview

2FAK is a small open-source USB-A hardware token. The printed circuit board itself forms
the USB-A plug (a single-piece "blade"), so there is no cable and no separate connector to
wear out. It is built around an STMicroelectronics STM32L4 microcontroller and is powered
entirely from the USB port.

The same board is produced in two hardware configurations:

- **With secure element** - the ATECC608B is populated. Used for the pre-programmed
  security-key units.
- **Without secure element** - the ATECC608B footprint is left unpopulated. Used for the
  programmable units.

Both configurations are otherwise identical.

## Microcontroller

- **Part:** STMicroelectronics STM32L442KCU6 (Arm Cortex-M4F, up to 80 MHz, UFQFPN-32
  package). Register-compatible with the STM32L432.
- **Memory:** 256 KB flash, 64 KB SRAM.
- **On-chip security features:** true random number generator (TRNG), AES-256 hardware
  accelerator, and flash read-out protection (RDP) supported in silicon.
- **Clocking:** crystal-less USB using the internal HSI48 oscillator with the Clock
  Recovery System (CRS); no external crystal is required.

## Secure element (populated variant)

- **Part:** Microchip ATECC608B, on the I2C1 bus.
- Confirmed on hardware at 7-bit I2C address 0x60, Info revision word 0x00006003 (which
  identifies an ATECC608B).
- Provides tamper-resistant key storage and cryptographic operations. On the units where
  it is fitted, it can hold a device root that cannot be read back out of the chip.
- On boards where it is not fitted, the footprint remains but is unpopulated.

## USB interface

- USB 2.0 **Full-Speed** (12 Mbit/s) device.
- **USB-A male** contacts integrated into the edge of the PCB (no cable, no moving
  connector).
- Dedicated ESD / TVS protection on the D+, D- and VBUS lines.

## User interface

- One **tactile push button** (user-presence / control input).
- One **status LED**.

## Power

- **USB bus-powered** from the 5 V supply, regulated on-board to 3.3 V by an LDO.
- Typical current draw about 30 mA. No battery and no battery sensing.

## Debug and programming

- **SWD** debug/programming interface (SWDIO / SWCLK), broken out to a Tag-Connect
  TC2030-style footprint for factory and advanced use.
- BOOT0 is available for boot-mode selection.

## Pin summary

| Function        | Pin         |
|-----------------|-------------|
| Button          | PA0         |
| Status LED      | PB3         |
| USB D- / D+     | PA11 / PA12 |
| SWD (SWDIO/SWCLK)| PA13 / PA14|
| I2C to ATECC (SCL/SDA) | PB6 / PB7 |
| BOOT0           | PH3         |

Note: PB6 / PB7 are shared between the ATECC I2C bus and an optional debug UART. On the
populated (secure-element) boards these pins are used for the I2C bus.

## Board

- 2-layer FR4, ground-poured.
- Approximately 48 x 21 mm.
- Gold-plated USB edge contacts.
- Hardware revision V1A.

## Operating conditions

- Works in any standard USB-A port. Driver-free at the hardware level (enumeration and
  behaviour are determined by whatever firmware is loaded, which is out of scope here).

*Hardware revision V1A. Specifications may change.*
