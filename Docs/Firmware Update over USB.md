# 2FAK firmware update over USB (signed, no programmer)

This is the post-sale update path. After a unit is flashed once via SWD with an
`all-*.hex` image (which includes the matching bootloader), further updates are pushed
**over USB** with `Tools/updater/2fak_update.py` — no SWD programmer needed. This is what
lets us close SWD later (RDP-2) and still ship updates.

## Two bootloader flavours

Built by `Firmware/<variant>/build.sh` via the `VERIFY_BOOT` switch:

| Build | Command | Bootloader | USB updates accept |
|---|---|---|---|
| **Dev** | `VERIFY_BOOT=0 bash build.sh` | non-verifying | any (unsigned) firmware |
| **Production** | `VERIFY_BOOT=1 bash build.sh` | verifying | only firmware signed with the muru bootloader key |

Outputs (in `prebuilt/`): `all-dev.hex` and `all-verifying.hex` (full flashable images for
the initial SWD flash), plus `solo.hex` (the app alone, used for USB updates).

## The production signing key

- Generated once by `keys/make_bootloader_key.py` into `secrets/bootloader/bootloader-prod.pem`.
- **Private key = the root of update trust. Never commit it; back it up securely offline.**
  If it is lost, no future signed updates can be produced for units in the field. If it
  leaks, an attacker can sign malicious firmware for those units.
- The public half is embedded in `targets/stm32l432/bootloader/pubkey_bootloader.c`
  (PAGES==128 production branch) and compiled into the verifying bootloader.

## Updating a unit

1. **Initial flash (once, via SWD)** with STM32CubeProgrammer:
   - dev unit: flash `prebuilt/all-dev.hex`
   - production unit: flash `prebuilt/all-verifying.hex`
   (For production, also run `provision_attestation.py` first if the unit needs the muru
   attestation, exactly as today.)

2. **Later updates (over USB)** with the app image `solo.hex` from a newer build:
   ```bash
   # Dev unit (unsigned):
   python Tools/updater/2fak_update.py program "Firmware/Resident CTAP2.3/prebuilt/solo.hex"

   # Production unit (signed with the key):
   python Tools/updater/2fak_update.py program "Firmware/Resident CTAP2.3/prebuilt/solo.hex" \
          --key secrets/bootloader/bootloader-prod.pem
   ```
   The tool: enters the bootloader (the device blinks — **touch the button**), streams the
   app, sends the signature (production) or nothing (dev), and the device reboots into the
   new firmware. `info` shows the current mode; `sign` produces a detached signature so the
   key can live on a separate secure machine from the flashing station.

3. **Version rule:** the verifying bootloader only accepts firmware whose version is
   **>= the current** version (anti-rollback). Bump `VER` in `build.sh` for real updates;
   re-flashing the same version is allowed (useful for testing).

## First-time validation (do this on a sacrificial unit, SWD still open)

Because SWD is still open at this stage, a bad update is always recoverable by re-flashing
over SWD — which is exactly why we build and prove this path *before* the RDP-2 lockdown.

1. Build both flavours: `VERIFY_BOOT=0 FIDO23=1 bash build.sh` and
   `VERIFY_BOOT=1 FIDO23=1 bash build.sh`.
2. SWD-flash `all-verifying.hex`. Confirm the key still works (FIDO login / conformance).
3. `python Tools/updater/2fak_update.py info` → expect "APPLICATION mode".
4. `program solo.hex` **without** `--key` → expect it to be **refused** at BootDone
   (proves the verifying bootloader rejects unsigned firmware).
5. `program solo.hex --key secrets/bootloader/bootloader-prod.pem` → touch when it blinks →
   expect "Firmware accepted; rebooting". Confirm the key still works afterwards.
6. Repeat 3-5 on an `all-dev.hex` unit; there the unsigned `program` should **succeed**.

Report what happens at each step; the USB transport (enter-bootloader, streaming,
re-enumeration) is the part that can only be verified on hardware. The signing itself is
already verified in software (the tool's signature validates against the embedded key).
