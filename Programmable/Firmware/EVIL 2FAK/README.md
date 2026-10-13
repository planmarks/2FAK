# EVIL 2FAK — USB business-card demo firmware

A **standalone USB‑HID keyboard** firmware for the 2FAK hardware (STM32L442KCU6),
used to **demonstrate the device's capabilities on your own laptop during meetings**.

On **button press (SW1 / PA0)** it "types" the sequence to open a URL in the default
browser and blinks the status **LED (D1 / PB3)** while doing so. Nothing runs on
plug‑in; every action is a deliberate, operator‑initiated button press. This is a
consent‑based demo (like a QR business card), **for your own device only** — not a
covert/auto‑run payload.

- **Opens:** `https://instagram.com/papathought`
- **USB name:** `2FAK Business Card` (manufacturer `muru.global`)
- **Host target:** Windows (`Win`+`R` → type URL → `Enter`). See below to change.

> This firmware is **separate** from the real 2FAK security key. It runs standalone
> at flash base `0x08000000` (no bootloader). Flashing it **replaces** the FIDO2
> firmware; reflash the product image (`../firmware/prebuilt/all.hex`) to restore the
> security key.

## Build
From Git Bash (uses the STM32CubeIDE‑bundled gcc/make; handles the space in the path):
```bash
./build.sh
```
Output: `prebuilt/2fak_card.hex` (+ `.bin`/`.elf`). ~9 KB flash.

## Flash (STM32CubeProgrammer, SWD)
```bash
STM32_Programmer_CLI -c port=SWD -e all -d prebuilt/2fak_card.hex -v -rst
```
Then unplug the ST‑Link and insert the USB blade into a port. The LED gives a short
heartbeat blink every ~1.5 s. Press SW1 to open the link.

## Restore the real 2FAK security key
```bash
STM32_Programmer_CLI -c port=SWD -e all -d ../firmware/prebuilt/all.hex -v -rst
```

## Customize
- **URL:** `TARGET_URL` in `main.c`.
- **macOS demo:** replace the `Win`+`R` step in `open_url()` with `Cmd`+`Space`
  (Spotlight): `tap(MOD_LGUI, 0x2C)` won't do it — use GUI+Space via a space keycode;
  simplest is to send `LGUI`+`space` then type the URL + Enter. Ask if you want a
  macOS build variant.
- **Product/USB name:** `USBD_PRODUCT` / `USBD_MANUFACTURER` in `usbd_desc.c`.

## Files
- `main.c` — clock, GPIO, USB start, button→type logic, keystroke map
- `usbd_kbd.c/.h` — HID boot‑keyboard class (report descriptor, IN endpoint)
- `usbd_desc.c/.h` — device/string descriptors (VID `0x1209`, PID `0x2FAC`)
- `usbd_conf.c/.h` — USB low‑level (PCD) glue, keyboard‑only
- `linker.ld` — standalone image at `0x08000000`
- `shared/` — reused STM32 USB core + HAL PCD + LL drivers + startup (from the 2FAK tree)
