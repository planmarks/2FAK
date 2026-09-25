# 2FAK production lock: RDP-2 / SWD lockdown

This is the final, **irreversible** production step. It sets STM32 readout protection
level 2 (RDP-2), which permanently disables the SWD debug port so firmware and secrets
cannot be read out or the chip reflashed with a programmer. After this, the **only** way
to update a unit is a signed USB firmware update (see `Firmware Update over USB.md`), so
the verifying bootloader must already be in place and proven before locking.

## How it works

The lock is driven by the firmware, not the programmer:

1. A persistent flag (`SOLO_FLAG_LOCKED`) lives in the attestation page's `device_settings`.
2. On every boot, `flash_option_bytes_init()` checks `solo_is_locked()`. When the flag is
   set (and the build is not a test build), it programs the option byte to **RDP-2**
   (`0xCC`) and triggers an option-byte reload.
3. RDP-2 sticks forever: option bytes can no longer be changed and SWD is dead.

The flag is set at runtime by the vendor command the updater's `lock` subcommand sends, so
you can **test a unit fully, then lock it** — the safe order.

> Do NOT set RDP with the programmer directly. The firmware rewrites the option byte to
> RDP-0 on boot whenever the lock flag is *not* set, so RDP must be driven by the flag.
> Setting RDP-1 out of band would trigger a mass-erase on the next boot.

## Production order (must be this order)

1. SWD-flash the **verifying** image: `prebuilt/all-verifying.hex` (or a provisioned
   `all_provisioned.hex` from `provision_attestation.py` for a real muru-attested unit).
2. Power-cycle; confirm the unit works (FIDO login, `info` shows APPLICATION mode).
3. Prove USB update works: `program solo.hex --key secrets/bootloader/bootloader-prod.pem`.
4. Only when the unit is final and verified, **lock it**:
   ```bash
   python Tools/updater/2fak_update.py lock
   ```
   Confirm the prompt (type `LOCK`), then **unplug and replug**. On that boot the firmware
   programs RDP-2.
5. Verify:
   - `python Tools/updater/2fak_update.py info` -> `RDP: LOCKED (RDP-2, SWD disabled)`.
   - Try to connect with STM32CubeProgrammer over SWD -> it must **fail** (proof SWD is dead).
   - Confirm FIDO still works and a signed USB update still applies (the recovery path).

## Warnings

- **Irreversible.** RDP-2 cannot be undone. No SWD, no debug, no reflash-via-programmer,
  ever, on that chip. There is no mass-erase escape (that only exists for RDP-1 -> 0).
- **Lock last.** Anything you cannot do over a signed USB update (change the bootloader,
  re-provision attestation over SWD, fix a bootloader bug) must be done *before* locking.
- **Use sacrificial units to test this.** The unit you run `lock` on is permanently locked.
- The bootloader must be the final verifying bootloader with our production key before
  locking, because it can never be replaced afterwards.

## First-time validation (sacrificial unit)

1. SWD-flash `prebuilt/all-verifying.hex`; confirm `info` -> APPLICATION mode, unlocked.
2. `program solo.hex --key secrets/bootloader/bootloader-prod.pem` -> succeeds (USB update OK).
3. `lock` -> type `LOCK` -> unplug/replug.
4. `info` -> `LOCKED (RDP-2)`. STM32CubeProgrammer SWD connect -> fails.
5. `program solo.hex --key ...` again -> still succeeds (signed USB update works post-lock).
6. FIDO still works (fido_diag.py). Done: SWD is gone, USB updates remain.
