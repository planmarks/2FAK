# 2FAK Flashing Station

An operator wizard to flash and test 2FAK units in production, then mint a unique ID with a
QR code and barcode for each unit and record everything in an append-only log.

## Requirements

- **STM32CubeProgrammer** (`STM32_Programmer_CLI.exe`) - bundled with STM32CubeIDE; the tool
  auto-locates it.
- Python 3 with the deps: `pip install -r requirements.txt`
- Built firmware images (run each firmware's `build.sh` for both dev and prod):
  - `Firmware/Non-Resident CTAP2.0-2.1/prebuilt/all-dev.hex` and `all-verifying.hex`
  - `Firmware/Resident CTAP2.3/prebuilt/all-dev.hex` and `all-verifying.hex`
- One or more 2FAK units connected via **ST-Link** (for flashing) and **USB** (for testing),
  e.g. through a USB hub.
- On Windows, run from an **Administrator** terminal (FIDO USB devices are hidden otherwise).

```bash
python station.py
```

## The flow

1. **Start** - shows environment status (programmer, images, code libs).
2. **Detect** - lists connected ST-Link probes.
3. **Select** - one unit: Continue; several: tick the ones to flash.
4. **Assign firmware** - per unit, choose variant (`non-resident` / `resident`) and build
   (`dev` = unsigned USB updates, `prod` = verifying bootloader, signed updates only).
   "Apply to all" fills the table quickly.
5. **Confirm** - review the plan and the warnings.
6. **Flash** - each unit is programmed over SWD (erase + program + verify + reset) with a
   live log. The MCU unique ID is read first and becomes the unit's hardware ID.
7. **Test** - firmware-appropriate USB checks (getInfo versions/options match the variant,
   AAGUID, ES256, ATECC probe, lock status). Skippable.
8. **Test log** - streamed on screen, "Copy log" to clipboard; a per-unit summary is shown.
9. **IDs & codes** - each unit that flashed and passed gets `2FAK-<R|N>-<12 hex>` derived
   from its MCU UID, plus a QR PNG and a Code128 barcode PNG under `codes/`.
10. **Log** - every unit is appended to `logs/flashing_master_log.csv` (device ID, MCU UID,
    variant/build, flash start/finish + result, test start/finish, passed/failed tests, QR
    and barcode generated). The log is **appended, never overwritten**.

## Important notes

- **This tool does not set RDP-2.** Locking (permanent SWD disable) is a separate, final,
  irreversible step done per unit with `Tools/updater/2fak_update.py lock` after the unit is
  fully flashed and tested. Doing it here would prevent re-flashing during bring-up.
- **Multi-unit USB testing** currently assumes the unit under test is the FIDO device
  present; robust simultaneous multi-unit testing needs the firmware to expose the MCU UID as
  the USB serial number (a planned follow-up). Single-unit testing is unambiguous.
- **Logs and codes are runtime output** (git-ignored). Back them up as your production record;
  the QR/barcode export format and size will be finalised later.
- Hardware paths (ST-Link flashing, UID read, USB tests) could not be tested off-bench and
  should be validated on real units; report issues and they will be fixed.
