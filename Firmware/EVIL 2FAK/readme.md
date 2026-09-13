# EVIL 2FAK — USB Educational Development Board

---

## Short description

**EVIL 2FAK is a fully open, reprogrammable STM32L4 development board shaped like a
USB‑A stick.** It's the same hardware as the 2FAK security key — but sold unlocked and
documented for tinkering. Flash your own firmware over SWD with an ST‑Link, and use the
on‑board USB Full‑Speed peripheral, button, LED, and I²C secure‑element footprint to
learn USB device classes, FIDO2/CTAP internals, HID, and embedded security hands‑on.
Ships with example firmware — including a **USB HID "business‑card"** demo that opens a
link on a button press.

---

## Long description

Most "USB gadget" boards are either a bare dev kit with no enclosure story, or a sealed
consumer device you can't touch. **EVIL 2FAK sits in the sweet spot:** a pocketable,
cable‑free USB‑A board built around a capable Cortex‑M4, with the debug port broken out
and nothing locked down.

It's a great platform for:

- **Learning USB from the metal up** — the STM32L442 has native USB 2.0 FS. Build and
  enumerate HID keyboards, composite devices, CDC serial, mass storage, or a raw
  vendor interface, and watch it appear on a host with no drivers.
- **FIDO2 / security‑key R&D** — it runs the open‑source Solo 1 / Nitrokey FIDO2
  firmware unmodified, so you can study CTAP2/WebAuthn, attestation, credential
  storage, and flash readout protection on real silicon.
- **HID / "USB business card" experiments** — the included demo firmware enumerates as
  a keyboard and, on a button press, types a URL to open it in the browser, blinking
  the LED as feedback. A clean, consent‑based example of HID output (great for teaching
  how BadUSB‑class techniques work — and why OSes and layouts matter).
- **General Cortex‑M4 firmware dev** — TRNG, AES‑256, timers, ADC, multiple serial/SPI
  buses and plenty of free GPIO for whatever you bolt on.

**Programming is deliberately frictionless.** The board exposes a **Tag‑Connect TC2030
SWD** footprint — no header to solder. Touch an **ST‑Link** (V2/V3) to it and flash
with STM32CubeProgrammer / OpenOCD / pyOCD, or debug live from STM32CubeIDE. The MCU is
**register‑compatible with the STM32L432**, so the enormous STM32L4 ecosystem, HAL/LL
drivers, and examples apply directly. Because it's shipped unlocked (RDP level 0), you
can reflash it endlessly; the bundled bootloader also supports **USB firmware updates**
(no ST‑Link needed after the first flash).

Open hardware, open firmware, open pins. Break it, reflash it, learn something.

> **Note on the name & intent.** "EVIL" is tongue‑in‑cheek. This is an **educational /
> development** board. Use its HID capabilities only on machines you own or are
> authorised to test. Don't deploy keystroke‑injection payloads against people's
> computers without consent — that's not what this is for.

---

## Technical specifications

| | |
|---|---|
| **MCU** | STM32L442KCU6 — Arm® Cortex®‑M4F @ 80 MHz, UFQFPN‑32 (5×5 mm) |
| **Memory** | 256 KB flash · 64 KB SRAM |
| **Crypto / RNG** | Hardware AES‑256 · true RNG (TRNG) · flash readout protection (RDP 0/1/2) |
| **USB** | USB 2.0 Full‑Speed device (12 Mbit/s), USB‑A PCB‑edge plug, crystal‑less (HSI48 + CRS) |
| **Debug / programming** | **SWD** on Tag‑Connect **TC2030‑NL** footprint (SWDIO, SWCLK, NRST, 3V3, GND) — program via **ST‑Link V2/V3** |
| **Bootloader** | Open‑source Solo/Nitrokey bootloader → USB DFU‑style updates after first SWD flash |
| **User I/O** | 1× tactile button (PA0, active‑low) · 1× LED (PB3, active‑high) |
| **Secure element** | ATECC608B (I²C on PB6/PB7) footprint — populate optionally |
| **Power** | USB 5 V → AP2112K‑3.3 LDO (3.3 V / 600 mA); USBLC6‑2SC6 ESD on D+/D−/VBUS |
| **Board** | 2‑layer FR4, ground pour both sides, ~48 × 21 mm |
| **Toolchain** | arm‑none‑eabi‑gcc + make (or STM32CubeIDE) · STM32Cube HAL/LL |
| **Example firmware** | FIDO2/U2F security key · USB HID "business‑card" (keyboard) |

---

## Pinout & open pins

**Fixed on‑board functions**

| Signal | MCU pin | Notes |
|--------|---------|-------|
| USB D− / D+ | PA11 / PA12 | via USBLC6 ESD, to the USB‑A blade |
| SWDIO / SWCLK | PA13 / PA14 | Tag‑Connect J2 |
| NRST | NRST | Tag‑Connect J2 (+ RC filter) |
| Button (user presence) | PA0 | active‑low, 10 kΩ pull‑up |
| LED | PB3 | active‑high, 330 Ω series |
| I²C SCL / SDA | PB6 / PB7 | 4.7 kΩ pull‑ups, to ATECC608B (U2) |
| BOOT0 | PH3 | 10 kΩ pull‑down (boots from flash) |
| VDDA | PA/analog | filtered via ferrite bead |

**Free / open GPIO** (unused by the reference designs — available for your firmware):

> `PA1 PA2 PA3 PA4 PA5 PA6 PA7 PA8 PA9 PA10 PA15 PB0 PB1 PB4 PB5 PC14 PC15`
> — plus `PB6/PB7` if you leave the ATECC608B unpopulated.

Across those pins the STM32L442 can expose **ADC inputs, USART/LPUART, SPI1, I²C,
TIM/PWM channels, comparators, and low‑power timers** — see the STM32L442 datasheet for
the exact alternate‑function map. On this compact form factor these pins live on the
QFN/passives rather than a 0.1″ header, so bring them out with fine‑pitch rework or a
custom carrier. The **SWD Tag‑Connect pads and the USB port are the primary,
solder‑free interfaces** for day‑to‑day development.

---

## What's in the box / repo

- The board (rev. V1A), or Gerbers/KiCad sources to fabricate your own.
- Example firmware + build scripts (arm‑gcc/make), flashing instructions, and pin docs.
- Requires: an **ST‑Link** (V2 or V3) and a **Tag‑Connect TC2030‑CTX‑NL‑STDC14** cable
  (for STLINK‑V3) to program over SWD.

*Specifications for hardware rev. V1A and subject to refinement.*
