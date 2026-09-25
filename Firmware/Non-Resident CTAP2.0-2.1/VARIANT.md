# Non-resident (server-side) variant

This copy of the 2FA firmware is the **second-factor-only** product. It does not store
discoverable credentials (passkeys) on the device.

## What changed vs BACKUP
- `fido2/ctap.c` getInfo now advertises **`rk: false`** (no discoverable credential
  capability).
- `fido2/ctap.c` makeCredential **refuses** requests that ask for a resident key
  (returns `CTAP2_ERR_UNSUPPORTED_OPTION`), so relying parties fall back to a
  non-resident credential.
- No PIN is forced (unchanged). A pure second factor needs no PIN.

Everything else (identity, AAGUID, attestation provisioning, extensions, SSH,
hmac-secret) is the same as the Phase 1/2 firmware.

## ATECC608B hardware root (secure element)

The board's ATECC608B (I2C1 on PB6/PB7) can hold the FIDO root secret in tamper-
resistant hardware. When engaged, the MCU never stores the root: it asks the chip to
HMAC a per-device flash salt and uses the result as the master secret from which every
credential key is derived. The root key cannot be read out of the chip.

Files: `targets/stm32l432/src/atecc.{c,h}`. Hooks: `device_init()` calls `atecc_init()`
before state load; `crypto_load_master_secret()` re-derives the master from the chip
when it is ready.

**Safe by default / reflashable (RDP0).** `atecc_ready()` returns true only when the
chip is present *and* provisioned (config+data zones locked). On every un-provisioned
unit, or if the chip does not answer, the firmware falls back to the existing software
master secret with **no behaviour change**. So the current populated-but-unused chips
stay dormant and the MCU remains fully reflashable. The debug UART (which shares
PB6/PB7) is only built when `DEBUG_LEVEL > 0`; production builds leave the pins free
for I2C.

### Provisioning (one-time, IRREVERSIBLE) - sacrificial-unit flow

Provisioning is compiled only with `PROVISION=1` (`-DATECC_PROVISION`) and is never
automatic. It is triggered by a **button-gated** vendor command so it cannot fire by
accident. `atecc_provision()` runs these steps and returns the step it failed at
(`ATECC_PROV_*` in `atecc.h`):

1. write root-slot config (`SlotConfig[0]=0x2080`: IsSecret, HMAC-usable, immutable
   after lock; `KeyConfig[0]=0x003C`: non-ECC/generic key, lockable, ReqRandom=0)
2. **read the config back and verify** - if it mismatches, abort here; nothing is
   locked and the chip is still usable
3. lock the config zone *(irreversible)*
4. write a random 32-byte root key in the clear (allowed only while data unlocked)
5. lock the data zone *(irreversible)*
6. run a test derivation (Nonce passthrough + HMAC) and confirm it works

Steps 1-2 fail safe. The config values are set from the ATECC608B datasheet and
cryptoauthlib constants, but whether the HMAC command actually works with this config
can only be confirmed after locking - which is exactly why the first runs go on a
sacrificial unit with a logic analyzer on PB6/PB7.

Procedure:

    # 1. build + flash the provisioning image to a SACRIFICIAL board
    PROVISION=1 bash build.sh          # -> prebuilt/provision/all.hex
    #    flash prebuilt/provision/all.hex, replug
    python atecc_selftest.py           # confirm present:True first
    python atecc_provision.py          # type PROVISION, then TOUCH the key

    # 2. on success, go back to the normal image and check it took
    bash build.sh                      # -> prebuilt/all.hex (no provisioning cmd)
    #    flash prebuilt/all.hex, replug
    python atecc_selftest.py           # expect present:True ready:True kdf_ok:True

The normal image never contains the provisioning command. The I2C address (confirmed
0x60) and wake timing are already validated by the self-test.

### Self-test (confirm the chip is talking before you ever provision)

Vendor command `CTAPHID_ATECC` (0x63) probes the chip read-only and returns 9 bytes:
present, ready, config_locked, data_locked, 4-byte revision, kdf_ok. It never writes
to or locks the chip. It also queues an LED cue: **3 blinks** = present and
provisioned, **2 blinks** = present but not provisioned (normal today), **5 fast
blinks** = not answering.

Run it from an elevated terminal (`pip install fido2`):

    python atecc_selftest.py

Use this on a real board to confirm the I2C address (0x60 vs 0x6A) and wiring are
right *before* trusting the hardware root or attempting provisioning.

## Why
Best fit for non-technical users: password + touch, unlimited accounts, no PIN to
forget, no 50-key limit, no PIN-lockout resets, and nothing about your accounts stored
on the key.

## Test after flashing prebuilt/all.hex
1. `fido2-token -I` shows `options: ... rk: false`.
2. webauthn.io with "discoverable credential: discouraged" registers and logs in.
3. webauthn.io with "discoverable credential: required" should FAIL to register (this
   is correct: the device declines to store a passkey).
4. Google / GitHub: add as a security key (second factor). No PIN prompt.

To restore the full-featured build, flash `../BACKUP/prebuilt/all.hex`.
