# 2FA Key — Firmware Porting Guide

Porting the **[Nitrokey FIDO2 firmware](https://github.com/Nitrokey/nitrokey-fido2-firmware)**
(a maintained fork of SoloKeys Solo 1) to this board.

> **Why not write from scratch:** a FIDO2/CTAP2 stack is security‑critical crypto.
> This board was chosen specifically to run proven, audited firmware. We port that
> firmware to the hardware; we do **not** re‑implement the authenticator.

---

## 0. What actually needs changing

Most of the firmware runs unmodified on this board. Only three things differ from
the Solo/Nitrokey reference hardware:

| Area | Reference firmware | This board | Action |
|------|--------------------|------------|--------|
| MCU | STM32L432KC | **STM32L442KC** (L432 + AES, register‑compatible) | none — `stm32l432` target runs as‑is |
| USB clock | crystal‑less HSI48 + CRS | same | **none — already correct** |
| Button | PA0 (HWREV ≤ 2), **active‑high** read | PA0 (SW1), **active‑low** (R3 pull‑up, switch→GND) | force PA0 + **invert polarity** |
| LED | RGB via TIM2 PWM on PA1/PA2/PA3 | **single LED on PB3**, active‑high | replace LED driver |
| NFC/ambient sensor | AMS chip present | none | runtime auto‑disables (USB‑only) |

---

## 1. Prerequisites (WSL / Ubuntu)

```bash
sudo apt update
sudo apt install -y git make python3 python3-pip
# Easiest: Docker-based toolchain (repo ships one). Install Docker in WSL, then no
# need to install arm-none-eabi-gcc yourself.
```

On the Windows side you'll also want **STM32CubeProgrammer** for the first SWD flash.

## 2. Clone

```bash
git clone --recurse-submodules https://github.com/Nitrokey/nitrokey-fido2-firmware
cd nitrokey-fido2-firmware
```

All paths below are under `targets/stm32l432/src/`.

---

## 3. Board patches

> These are against current `master`. Function names are confirmed from the source,
> but line numbers drift — locate by symbol name and adapt.

### 3a. Button → PA0, and invert to active‑low

**`app.h`** — force the button to PA0 regardless of `HWREV` (avoids pulling in other
HWREV‑specific hardware assumptions):

```c
/* --- 2FA Key board: user-presence button SW1 on PA0 --- */
#undef  SOLO_BUTTON_PORT
#undef  SOLO_BUTTON_PIN
#define SOLO_BUTTON_PORT   GPIOA
#define SOLO_BUTTON_PIN    LL_GPIO_PIN_0
```

**`device.c`** — the reference reads the button as *pressed when the pin is HIGH*.
Your SW1 pulls PA0 to **GND** when pressed (idle HIGH via R3), so it's **active‑low**.
Without this change, user‑presence would read as permanently pressed:

```c
static int is_physical_button_pressed(void)
{
    // 2FA Key: SW1 -> GND, PA0 pull-up. Pressed == pin LOW.
    return (LL_GPIO_ReadInputPort(SOLO_BUTTON_PORT) & SOLO_BUTTON_PIN) == 0;
}
```

Also make sure the **touch path is not selected**: `device_init_button()` uses the
TSC touch sensor only if `tsc_sensor_exists()` returns true. With no touch hardware
it falls back to the physical GPIO automatically — verify this on your build (if it
misdetects, hard‑code the physical path).

*(Optional)* the button EXTI is set for rising‑edge wake; your press is a falling
edge. It only matters for wake‑from‑sleep, not presence polling — switch to falling
edge if you use sleep.

### 3b. LED → single GPIO on PB3

**`init.c`** — in the GPIO init function, **add** PB3 as a push‑pull output (and you
can drop the PA1/PA2/PA3 + TIM2 PWM LED setup, since those pins are unused here):

```c
/* 2FA Key: single status LED D1 on PB3, active-high */
LL_GPIO_SetPinMode(GPIOB,  LL_GPIO_PIN_3, LL_GPIO_MODE_OUTPUT);
LL_GPIO_SetPinOutputType(GPIOB, LL_GPIO_PIN_3, LL_GPIO_OUTPUT_PUSHPULL);
LL_GPIO_SetPinPull(GPIOB,  LL_GPIO_PIN_3, LL_GPIO_PULL_NO);
LL_GPIO_ResetOutputPin(GPIOB, LL_GPIO_PIN_3);   // start off
```

> Note: PB3 defaults to JTDO/TRACESWO after reset. You use **SWD** (PA13/PA14) and
> SWO is not wired (J2.6 NC), so re‑purposing PB3 as GPIO is safe — the mode set
> above overrides the default alternate function.

**`led.c`** — replace the RGB/PWM driver with a single on/off LED. Keep the same API
so the rest of the firmware (`heartbeat`, `device_wink`, default‑color calls) works:

```c
#include "stm32l4xx_ll_gpio.h"
#include "app.h"

#define LED_PORT  GPIOB
#define LED_PIN   LL_GPIO_PIN_3

// Single-color LED: on if any RGB channel is non-zero, else off.
void led_rgb(uint32_t hex)
{
    if (hex & 0x00FFFFFF)
        LL_GPIO_SetOutputPin(LED_PORT, LED_PIN);
    else
        LL_GPIO_ResetOutputPin(LED_PORT, LED_PIN);
}

// Neutralize the PWM color demo (was TIM2-based).
void led_test_colors(void) { }
```

Leave `led_blink()`, `led_set_default_color()`, `led_reset_default_color()` as‑is if
they route through `led_rgb()`; if any of them poke `TIM2->CCRx` directly, replace
those bodies with `led_rgb(...)` calls too. The heartbeat pulse becomes a steady/
blinking single LED — expected and fine.

### 3c. Everything else

- **Clock:** `init.c` already does `LL_RCC_HSI48_Enable()` + CRS synced to USB — no change.
- **AES:** the L442's AES block is unused by this firmware; ignore it.
- **NFC/AMS:** no chip on your board; the firmware probes and disables NFC at runtime → USB‑only, which is what you want.

---

## 4. Build

```bash
make docker-build-toolchain     # one-time: builds the ARM toolchain image
make docker-build-all           # builds firmware -> ./builds/*.hex
```

Output hex files land in `./builds/`. You want the combined bootloader+application
image for a first flash (if only separate `bootloader.hex` and firmware hex are
produced, merge them):

```bash
pip3 install solo-python
solo mergehex builds/bootloader*.hex builds/firmware*.hex builds/all.hex
```

---

## 5. First flash — over SWD

Blank chip → use the ST‑Link path we set up (STLINK‑V3MINIE + TC2030‑CTX‑NL‑STDC14):

1. Power the board via its USB blade.
2. Hold the Tag‑Connect on J2.
3. In **STM32CubeProgrammer**: connect via ST‑LINK/SWD → **Erase full chip** →
   flash `builds/all.hex` at base `0x08000000` → verify.

> ⚠️ **Do NOT set RDP Level 2 yet.** RDP2 permanently disables SWD *and* the USB
> bootloader. Only lock it once everything works and firmware is final.

### After the first flash: USB updates without the ST‑Link
The Solo/Nitrokey bootloader you just flashed accepts firmware updates **over USB** —
hold the button (PA0) while plugging in to enter bootloader mode, then:

```bash
solo program bootloader builds/firmware*.hex
```

So the ST‑Link is only needed once.

---

## 6. Test

1. **Basic WebAuthn:** [webauthn.io](https://webauthn.io) or `chrome://webauthn` —
   register + authenticate. Confirm the LED signals and the button gates presence
   (nothing should complete until you press SW1).
2. **Google:** Account → Security → 2‑Step Verification → **Passkeys and security
   keys** → add security key. Self‑built keys are accepted. ✅
3. **Microsoft:** see the caveat below.

---

## 7. Attestation, AAGUID & the Google vs Microsoft reality

A firmware built from source uses a **default/self attestation** identity, and its
**AAGUID is not in the FIDO Alliance metadata service (MDS)**. Consequences:

- **Google / personal Microsoft account:** accept self‑attested keys → works.
- **Microsoft 365 / Entra ID (work tenant):** as of the 2026 passkey‑profile model,
  admins can **enforce attestation** and **restrict AAGUIDs**. A self‑built key will
  be **rejected where attestation is enforced**. It works only on a tenant you
  administer where you disable attestation enforcement (and/or allow‑list your
  AAGUID). Nothing in firmware changes this — it's tenant policy.

*(Optional)* set your own unique AAGUID in the firmware config so your key is
distinguishable; it still won't be MDS‑listed, so treat it as a self‑attested
personal key.

---

## 8. Security caveats (read before relying on it)

- This is a **self‑built, self‑attested, uncertified** authenticator. Fine as a
  personal second factor; not equivalent to a certified commercial key.
- Keep the device **unlocked (no RDP2)** during development. Lock RDP2 only when
  done — and understand it's irreversible.
- Don't modify the crypto/CTAP core. The value of this path is that that code is
  audited upstream; keep your changes confined to board bring‑up (button, LED, pins).

---

## Board reference (for the patches above)

| Signal | Pin | Firmware macro / note |
|--------|-----|-----------------------|
| Button SW1 | PA0 | `SOLO_BUTTON_PORT/PIN`, active‑low |
| LED D1 | PB3 | single GPIO, active‑high |
| USB DM/DP | PA11 / PA12 | via USBLC6 (U1) |
| SWDIO / SWCLK | PA13 / PA14 | Tag‑Connect J2 |
| BOOT0 | PH3 | pull‑down R2 |
| I²C (ATECC, unused) | PB6 / PB7 | leave default |
