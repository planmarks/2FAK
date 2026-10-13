# 2FAK Mouse Jiggler

A **standalone USB‑HID mouse** firmware for the 2FAK hardware (STM32L442KCU6). While
the device is plugged into a computer it **nudges the mouse pointer a few pixels and
immediately back, at a random interval between 1 and 23 seconds** — enough to keep the
host awake / show "active" without the cursor drifting. It runs automatically on
plug‑in; no button press needed.

- **USB name:** `2FAK Mouse Jiggler` (manufacturer `papathought`), VID `0x1209` / PID `0x2FAB`
- **Interval:** random **1–23 s** (seeded per‑device from the STM32 unique ID)
- **Motion:** ±3–10 px nudge, then the same amount back (net‑zero drift)
- **LED (D1/PB3):** blinks on each jiggle; slow heartbeat blink every ~2 s otherwise
- **Host:** works on Windows / macOS / Linux — it's a standard boot‑protocol HID mouse, no driver

> This firmware is **separate** from the real 2FAK security key. It runs standalone at
> flash base `0x08000000` (no bootloader). Flashing it **replaces** the FIDO2 firmware;
> reflash the product image (`../firmware/prebuilt/all.hex`) to restore the security key.

## Build
From Git Bash (uses the STM32CubeIDE‑bundled gcc/make; handles the space in the path):
```bash
./build.sh
```
Output: `prebuilt/2fak_jiggler.hex` (+ `.bin`/`.elf`). ~9 KB flash.

Manual equivalent, from a space‑free copy with the CubeIDE gcc+make on PATH:
```bash
make
```

## Flash (STM32CubeProgrammer, SWD)
```bash
STM32_Programmer_CLI -c port=SWD -e all -d prebuilt/2fak_jiggler.hex -v -rst
```
Then unplug the ST‑Link and insert the USB blade into a port. Within 1–23 s the pointer
will twitch and the LED will blink.

## Restore the real 2FAK security key
```bash
STM32_Programmer_CLI -c port=SWD -e all -d ../firmware/prebuilt/all.hex -v -rst
```

## Customize
- **Interval / motion:** `JIGGLE_MIN_S`, `JIGGLE_MAX_S`, `JIGGLE_MIN_PX`, `JIGGLE_SPAN_PX` at the top of `main.c`.
- **USB name / IDs:** `USBD_PRODUCT` / `USBD_MANUFACTURER` / `USBD_PID` in `usbd_desc.c`.
- **Pause button:** `SW1 (PA0)` is configured as an input but unused — a few lines in
  `main.c`'s loop can make it toggle jiggling on/off if you want manual control.

## Files
- `main.c` — clock, GPIO, USB start, PRNG, jiggle loop
- `usbd_mouse.c/.h` — HID mouse class (52‑byte report descriptor, 4‑byte IN report)
- `usbd_desc.c/.h` — device/string descriptors
- `usbd_conf.c/.h` — USB low‑level (PCD) glue
- `linker.ld` — standalone image at `0x08000000`
- `shared/` — reused STM32 USB core + HAL PCD + LL drivers + startup (from the 2FAK tree)
