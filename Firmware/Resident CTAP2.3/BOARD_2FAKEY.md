# 2FA Key — board port of the Nitrokey FIDO2 firmware

This is the **Nitrokey FIDO2 firmware** (a maintained fork of SoloKeys Solo 1),
with a small board bring‑up applied for the *2FA Key* hardware
(STM32L442KCU6, USB‑A blade, button on PA0, single LED on PB3).

Source cloned from <https://github.com/Nitrokey/nitrokey-fido2-firmware> (branch
`master`) with submodules. The firmware runs on the **STM32L442KC** unchanged —
it is register‑compatible with the L432KC the code targets (L442 = L432 + AES).

---

## What was changed for this board

Only two functional changes were needed — the rest of the reference config already
matches this hardware (crystal‑less HSI48+CRS clock, active‑low button read, SPI on
PA5/6/7 not PB3):

| File | Change | Why |
|------|--------|-----|
| `targets/stm32l432/src/app.h` | `HWREV` default `3 → 2` | `HWREV ≤ 2` maps the user‑presence button to **PA0** (SW1). HWREV 3 uses PB1. |
| `targets/stm32l432/Makefile` | `HWREV ?= 3 → 2` | same, for targets that pass `-DHWREV`. (`all-hacker` passes no `-DHWREV`, so the `app.h` default also matters — both are set.) |
| `targets/stm32l432/src/led.c` | `led_rgb()` drives **PB3 GPIO** on/off instead of TIM2 RGB PWM | this board has a single LED (D1) on PB3, not an RGB LED on PA1/2/3. |
| `targets/stm32l432/src/init.c` | `init_gpio()` configures **PB3** as push‑pull output | drive the status LED. |

Things that did **not** need changing (verified in source):
- **Button polarity** — `device.c` already reads the button active‑low
  (`0 == (port & pin)`), matching SW1→GND with the R3 pull‑up. *(The earlier
  `FIRMWARE_PORTING.md` guessed an inversion was needed — it is not.)*
- **USB clock** — `init.c` already does crystal‑less HSI48 + CRS synced to USB.
- **Touch sensor** — auto‑detected via PB1; PB1 is unconnected on this board, so it
  reads "no touch" and falls back to the physical PA0 button automatically.
- **NFC / ATECC** — no NFC chip; SPI (PA5/6/7) and the AMS probe simply find nothing
  and NFC stays disabled → USB‑only. The ATECC (U2) is unused by this firmware.
  *(Note: the debug UART uses PB6/PB7, which are your I²C pins to the unused ATECC —
  harmless, since the firmware never talks to the ATECC.)*

See `git diff` in this folder for the exact patch.

---

## Cross‑platform: Windows, macOS, Linux

Nothing extra is needed in firmware — this builds a **standard FIDO2/U2F USB‑HID
authenticator** (FIDO HID usage page `0xF1D0`). That interface is recognized
natively by:

- **Windows 10/11** — via the built‑in WebAuthn API (browsers/Windows Hello). No driver.
- **macOS** — native (Safari/Chrome/Firefox WebAuthn).
- **Linux** — native in browsers.

The only host‑side extra is **Linux udev rules** so CLI tools (`nitropy`/`solo`) can
access the raw device without root (browsers don't need this). Create
`/etc/udev/rules.d/70-2fakey.rules`:

```
# Nitrokey FIDO2 / Solo (SoloKeys) — allow non-root access
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="20a0", TAG+="uaccess"
KERNEL=="hidraw*", ATTRS{idVendor}=="20a0", TAG+="uaccess", MODE="0660"
```

then `sudo udevadm control --reload && sudo udevadm trigger`.

---

## Build

**Already built:** ready-to-flash images are in **`prebuilt/`** (`bootloader.hex`,
`solo.hex`, plus `.elf`/`.bin`), built unlocked (`FLASH_ROP=0`, `HWREV=2` → PA0,
`AES256=1`). App ≈ 59 KB flash / 30 KB RAM, bootloader ≈ 15 KB — fits the 256 KB part.

### Rebuild on Windows (Git Bash) — one command
The toolchain bundled with **STM32CubeIDE** (`arm-none-eabi-gcc` + `make`) is used;
no separate install needed. From Git Bash:
```bash
./build.sh
```
`build.sh` copies the tree to a space-free dir (the "2FA Key" path breaks GCC/Make),
puts the CubeIDE gcc/make on PATH, adds a `python3` shim, passes the version
explicitly (the native `make`'s `$(shell)` can't run under `sh`), builds, and copies
the results into `prebuilt/`.

### Manual equivalent (if you prefer)
```bash
# from a space-free copy of this repo, with CubeIDE gcc+make on PATH:
cd targets/stm32l432
V="VERSION=5.0.0 VERSION_FULL=5.0.0 VERSION_FULL_RAW=5.0.0.nitrokey \
VERSION_MAJ=5 VERSION_MIN=0 VERSION_PAT=0 SOLO_VERSION_FULL=5.0.0 SOLO_VERSION=5.0.0 \
SOLO_VERSION_MAJ=5 SOLO_VERSION_MIN=0 SOLO_VERSION_PAT=0 PAGESHR=256kB"
make cbor $V
make bootloader-nonverifying $V     # -> bootloader.hex
make all-hacker $V                  # -> solo.hex  (FLASH_ROP=0, unlocked)
```

### On WSL/Linux (clean, no workarounds)
On a real Linux env the stock flow works without the version overrides:
`sudo apt install gcc-arm-none-eabi make python3`, tag the repo
(`git tag -a 5.0.0.nitrokey -m x`), then `make cbor && make bootloader-nonverifying
&& make all-hacker`. The Docker path (`make docker-build-all`) also works there.

Both `bootloader.hex` and `solo.hex` are unlocked (no readout protection, SWD stays
open). Avoid the `--lock`/release merge until the device is final.

---

## Flash (first time, over SWD)

> **Flashing the raw `bootloader.hex` + `solo.hex` over SWD is NOT enough** — two
> flash markers that the Solo bootloader/tooling normally set are missing, so use the
> merged **`prebuilt/all.hex`** instead (full erase, flash it, reset):
> `STM32_Programmer_CLI -c port=SWD -e all -d all.hex -v -rst`
>
> `all.hex` = bootloader + app + the two fixes:
> 1. **Auth word @ `0x08035FF8` = `0x00000000`.** The bootloader only jumps to the app
>    when `is_authorized_to_boot()` sees this word == 0 (`AUTH_WORD_ADDR`). A raw SWD
>    flash leaves it `0xFFFFFFFF`, so the device stays in the **bootloader** — it still
>    shows up as a "fido" HID device but doesn't answer CTAP2, giving *"can't read your
>    security key."* (Normally the bootloader zeroes this itself when the app is
>    installed *through* it via `solo/nitropy program bootloader`.)
> 2. **Attestation key @ `0x08038800`** (the hacker key). Without a valid key here the
>    firmware's `device_migrate()` self-provisions a blank `0xFF` signing key and
>    MakeCredential fails. `all.hex` seeds the hacker key so migration installs the
>    matching hacker cert on first boot.
>
> After flashing, `fido_diag.py` (elevated) should report product **"Nitrokey FIDO2"**
> (not "…Bootloader") and a successful MakeCredential on button press.

Blank chip → use the ST‑Link (STLINK‑V3MINIE + TC2030‑CTX‑NL‑STDC14) path:

1. Power the board via its USB blade.
2. Hold the Tag‑Connect on J2.
3. In **STM32CubeProgrammer** (ST‑LINK / SWD): **Erase full chip**, then flash
   **both** `bootloader.hex` and `solo.hex` (base `0x08000000`), verify.

> ⚠️ Do **not** enable RDP/flash lock (no `--lock`, `FLASH_ROP=0`) yet — keep SWD
> open while bringing the board up. RDP2 is irreversible and kills SWD *and* DFU.

### After the first flash — update over USB (no ST‑Link)
The Solo/Nitrokey bootloader accepts USB updates: hold the button (PA0) while
plugging in to enter bootloader mode, then:
```bash
pip3 install nitropy         # or solo-python
nitropy fido2 util program bootloader solo.hex   # newer builds: nitropy start update
```

---

## Test

1. `chrome://webauthn` or <https://webauthn.io> → register + authenticate. Confirm
   the LED lights and that nothing completes until you press SW1 (user presence).
2. **Google**: Account → Security → 2‑Step Verification → security keys → add.
   Self‑built keys are accepted. ✅
3. **Microsoft**: personal accounts accept it; **Entra/M365 work tenants may reject**
   it where attestation is enforced (your key is self‑attested / not in the FIDO
   metadata service). See `../FIRMWARE_PORTING.md` §7 for details.

---

## Notes / possible refinements

- **LED behavior** is basic on/off (any non‑zero "color" → on). The reference
  "breathing" heartbeat therefore shows as steady/blink on a single LED; tune
  `led_rgb()` or the heartbeat in `device.c` if you want a specific pattern.
- **Button EXTI** (`init.c`) wakes on the PA0 rising edge (release). Presence is
  polled, so this is only relevant for sleep/wake; switch to falling edge if you add
  low‑power sleep.
- **Custom AAGUID / attestation**: the dev build uses a default self‑attestation
  identity. Set your own AAGUID if you want the key individually identifiable.
