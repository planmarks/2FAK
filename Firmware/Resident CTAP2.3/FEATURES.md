# 2FAK FIDO2 firmware - Phase 1 and 2 changes

This covers the identity and feature work done on the 2FA firmware. No hardware
change and no bootloader or RDP change. This is still the unlocked (RDP 0) build for
testing.

## Phase 1: identity and attestation

### Identity
- **AAGUID** set to the 2FAK product line: `c2aa81f8-352d-56e2-c689-2bfdb5a52ccc`.
  This is the public model id the key reports. It is defined in
  `targets/stm32l432/src/attestation.c` (`global_aaguid`).
- **Manufacturer** string changed from "Nitrokey" to **muru.global**.
- **USB VID/PID** changed to `0x1209 / 0x2FA2` (pid.codes range) so we no longer ship
  under Nitrokey's IDs. These are placeholders for pre-production. Request your own USB
  IDs before mass production.
- **Serial number** is already unique per unit (derived from the STM32 chip UID). No
  change needed. Check with `fido2-token -L` or `-I`.

### Attestation (muru.global batch key and certificate)
A batch attestation key and self-signed certificate were generated for muru.global,
with our AAGUID embedded in the certificate. Files live in `keys/2fak/`:
- `att_cert.pem` / `att_cert.der` - the certificate (public).
- `att_key.pem`, `priv.bin` - the **private** key. These are **gitignored** and must
  never be committed.

How it is used:
- `device_migrate()` was changed so it **respects an already-provisioned attestation
  page** instead of overwriting it. So a factory-injected muru key and cert are used.
- `provision_attestation.py` injects the key and cert into a built `all.hex` at flash
  time (the factory step). The private key goes only into the flashed image, not the
  repo.

```bash
pip install intelhex
python provision_attestation.py prebuilt/all.hex prebuilt/all_provisioned.hex
```

**For testing now:** if you flash the plain `prebuilt/all.hex` (not provisioned), the
key falls back to the public Solo/Nitrokey hacker certificate. The key still works for
registration and login (services that use "none" attestation, like Google, do not care).
Provision the muru cert when you want the key to attest as muru.global, and note that
getting that cert trusted (FIDO metadata service, certification) is a separate paid
process, not code.

## Phase 2: features

### LED language (already correct, now documented)
On this board the single LED gives clear feedback and needs no change:
- **Off** = idle, nothing to do.
- **Blinking** = the key is waiting for your touch (or is busy).
- **Solid on** = your touch was accepted.
- **Fast red-style bursts** = a reset or destructive action is in progress.

This matches how commercial keys behave (off until they need you). We kept the tested
button and presence state machine untouched.

### Extensions (verified enabled)
The firmware advertises and implements both:
- **hmac-secret** - lets the key derive a stable secret for a site or app. This is what
  enables the offline uses below.
- **credProtect** - lets a credential require the PIN before it can be used or listed.

Check on the device:
```bash
fido2-token -I <device>     # look for "extensions: credProtect, hmac-secret"
```

### SSH and Git signing (works today, no firmware change)
FIDO2 keys work as SSH keys with modern OpenSSH:
```bash
ssh-keygen -t ecdsa-sk -O resident -O application=ssh:2fak
# add the printed public key to the server's authorized_keys or GitHub
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ecdsa_sk.pub
git config --global commit.gpgsign true
```
You touch the key to log in or to sign a commit. "resident" stores it on the key so it
can be pulled onto a new computer.

### Offline secrets via hmac-secret
The key can act as a second factor for local encryption:
- **KeePassXC**: Database, Security, add a hardware key (challenge-response).
- **Disk encryption (Linux)**: `systemd-cryptenroll --fido2-device=auto /dev/...`.
- **File encryption**: `age-plugin-fido2-hmac`.

## Test checklist (after flashing)
1. `fido2-token -L` lists the key with the muru.global name and a unique serial.
2. `fido2-token -I` shows AAGUID `c2aa81f8...` and the two extensions.
3. Register and log in on webauthn.io and on Google.
4. Create an `ecdsa-sk` SSH key and log in to a server.
5. LED: off at idle, blinks when a site asks you to touch, solid after you touch.
