# 2FAK Resident - Firmware Documentation

Documentation of the **resident (passkey)** firmware. This document covers the firmware only.
It is one of two firmware variants built from a single codebase; the second-factor variant is
documented in `2FAK Non-Resident - Firmware Documentation.md`. This variant is the same code
built with `RESIDENT=1` (and `FIDO23=1`).

## Summary

A FIDO2 / WebAuthn security-key firmware that supports **discoverable credentials (passkeys)**
and on-device **credential management**, for passwordless sign-in. It is a fork of the Nitrokey
FIDO2 firmware, which derives from SoloKeys Solo 1.

- **Transport:** USB HID (CTAPHID).
- **USB identity:** VID 0x1209 (pid.codes, open-source) / PID 0x2FA2.
- **AAGUID:** c2aa81f8-352d-56e2-c689-2bfdb5a52ccc (self-assigned).
- **Conformance:** passes the FIDO Alliance Conformance Test Tools for CTAP2.0, CTAP2.1 and
  CTAP2.3 (self-test). See `2FAK Resident - FIDO Conformance Readiness.md`.
- **License:** Apache-2.0.

## Protocols advertised (authenticatorGetInfo)

- **versions:** `FIDO_2_0`, `FIDO_2_1_PRE`, `FIDO_2_1`, `FIDO_2_3`.
- **extensions:** `credProtect`, `hmac-secret`.
- **options:** `rk = true`, `up = true`, `plat = false`, `credMgmt = true`, `clientPin`
  (dynamic), `pinUvAuthToken = true`. Emitted in CTAP2 canonical key order.
- **pinUvAuthProtocols:** `[1, 2]`.
- **transports:** `["usb"]`.
- **algorithms:** ES256 (`-7`) and EdDSA (`-8`, Ed25519), advertised in that preference order.
  > Ed25519 (TweetNaCl) is **validated on hardware**: `ed25519-sk` key generation and
  > authentication were tested working locally and against Cloudflare, which exercises the whole
  > path (getInfo `-8`, makeCredential negotiation, OKP COSE key, Ed25519 signing + verification).
  > A formal FIDO **conformance re-run** (to extend the self-test PASS and metadata to `-8`) is
  > still outstanding. See `ED25519_PLAN.md`.
- **maxCredentialCountInList**, **maxCredentialIdLength**, **minPINLength** (4),
  **firmwareVersion**.

## Credential model

- **Resident / discoverable credentials (passkeys).** `authenticatorMakeCredential` with
  `rk = true` stores the credential on the device so it can be found later by a
  getAssertion with an empty allow-list (passwordless sign-in). Capacity is up to
  approximately **50 resident credentials**.
- Discoverable credentials are flagged inside the (MAC-covered) credential ID. Once a
  discoverable credential is deleted via credential management, a getAssertion that presents
  its credential ID in an allow-list correctly fails with `NO_CREDENTIALS` (a deleted passkey
  cannot be resurrected).
- Non-discoverable (second-factor) credentials also work, exactly as in the non-resident
  variant.
- **Key material.** Each credential's private key (**ES256 or Ed25519**) is derived on demand
  via HMAC from the device master secret plus the credential ID, and exists only transiently in
  RAM - it is never written to flash. The master secret is rooted in the ATECC608B on
  provisioned units (see *Secure element* below). The credential's signature algorithm is
  recorded in the credential ID and is covered by the ID's authentication tag, so it cannot be
  altered without detection.

## CTAP commands

- Everything in the non-resident variant, plus:
- `authenticatorCredentialManagement` (0x0A / preview 0x41): `getCredsMetadata`,
  `enumerateRPs` (Begin/GetNextRP), `enumerateCredentials` (Begin/GetNextCredential),
  `deleteCredential`, and `updateUserInformation`.
- `authenticatorSelection` (0x0B).
- **Client PIN:** PIN/UV auth protocols **1 and 2**, including
  `getPinUvAuthTokenUsingPinWithPermissions`.
- **pinUvAuthToken:** 32-byte token; permission bits makeCredential + getAssertion +
  **credentialManagement** (`mc`, `ga`, `cm`); optional RP-ID binding; rolling ~30 s
  inactivity lifetime; invalidated on power cycle and reset. Credential-management commands
  require a token carrying the `cm` permission; a token without it is rejected with
  `PIN_AUTH_INVALID`.

## Client PIN behaviour

- Same as the non-resident variant: optional by default, with build-time `PIN_POLICY`
  (`optional` / `requireset` / `alwaysuv`). Standard CTAP retry handling (per-boot lockout at
  3 consecutive failures, full block at zero retries; a reset clears both).

## User presence

- A physical button press is required for registration, authentication, and
  `authenticatorSelection`, with LED signalling.

## Extensions

- **hmac-secret** (protocol 1 and 2 aware).
- **credProtect** (credential-protection levels; the level is also reported through
  credential management).

## Hardware SSH keys (OpenSSH)

Because SSH's FIDO key types ride on the standard FIDO2 credential flow, this firmware works
as a hardware-backed SSH key with **no firmware changes**:

- OpenSSH 8.2+ `ecdsa-sk` keys use ES256, which is exactly what this firmware advertises;
  the FIDO application string `ssh:` is treated as an ordinary RP ID (no RP-ID filtering).
- **Resident (portable) SSH keys** (`ssh-keygen -t ecdsa-sk -O resident`) are supported
  because this variant stores discoverable credentials; they can be pulled onto any machine
  with `ssh-keygen -K`. The non-resident variant can only do non-resident `ecdsa-sk` keys.
- `verify-required` maps to the device PIN (Client PIN) plus the touch (user presence).
- Both `ecdsa-sk` (ES256) and `ed25519-sk` (Ed25519) are supported and **tested working
  (local + Cloudflare)**.

Full sysadmin workflow (resident enroll/export, ProxyJump bastions, Ansible
`authorized_keys`, SSH-CA integration, PIN tiering, Windows/PuTTY, backup enrollment, and
the `2FAK-ssh-enroll` helper) is documented in `2FAK Resident - Hardware SSH Key Guide.md`.

## Attestation

- Packed / `basic_full` attestation, muru.global batch attestation key + certificate on
  production units (injected by `provision_attestation.py`); metadata statement embeds the
  muru Root CA. Not FIDO Certified; conformance is a self-test result; not (yet) in the FIDO
  Metadata Service.

## Secure firmware update, production lockdown, and hardware root

These subsystems are shared with the non-resident variant.

- **Signed USB update:** the verifying (production) bootloader accepts only muru-signed
  firmware (ECDSA P-256 over the app region); the dev bootloader accepts unsigned firmware;
  anti-rollback enforces version-not-older. Hardware-verified end to end.
- **Production lockdown (RDP-2):** setting readout-protection level 2 **permanently** disables
  the SWD/debug port (irreversible); signed USB updates still work afterwards; production images
  are built without `SOLO_HACKER`. On the production line this is the "Close Debug" step: the app
  sets a persistent lock flag over USB (`CTAPHID_LOCK`), and the firmware programs RDP-2 on the
  next boot.

### Secure element (ATECC608B) - hardware root of trust

On a provisioned unit the device's **root secret lives inside the ATECC608B and never leaves
it**. The firmware derives its 64-byte master secret from that root via the chip's keyed MAC,
salted with a per-device value in flash that is regenerated on `authenticatorReset` (so a reset
changes every derived key). Per-credential keys (ES256 and Ed25519) are then HMAC-derived from
the master secret on demand and exist only transiently in RAM - **no long-term private key is
written to MCU flash**. This is the derive-and-wrap model: a few key slots cannot hold ~50
passkeys, so one unreadable root plus derivation backs an unlimited number of credentials.

`atecc_ready()` gates the whole path: it returns true **only** when the chip answered **and** is
fully provisioned (config + data zones locked). On any unit where the chip is absent,
un-provisioned, or unresponsive, the firmware falls back to a software master secret with **no
behaviour change** - so the hardware root is dormant until a unit is deliberately provisioned,
and a mis-provisioned chip can never brick FIDO.

Implementation status - **proven on hardware** (board `207C37AF3631`: both zones locked, KDF
verified, hardware root active):

| Component | Status |
|---|---|
| ATECC I2C driver (`atecc.c`) | wake / Atmel CRC16 / command framing |
| Key derivation (`atecc_kdf`) | MAC command, **mode 0x06** - hardware-confirmed via `atecc_diag` |
| Master secret rooted in the chip (`crypto.c`) | `crypto_load_master_secret` -> `atecc_kdf` when `atecc_ready()` |
| Per-credential keys | HMAC-derived from the master secret; **never stored** |
| Provisioning (`atecc_provision`) | fail-safe: writes **and verifies** the slot config BEFORE the two irreversible zone locks |
| CTAPHID triggers | `0x63` self-test, `0x64` provision (button-gated), `0x65` diagnostics |
| Tooling | `atecc_selftest.py`, `atecc_provision.py`, `atecc_diag.py` |
| Safe fallback | `atecc_ready()` false until provisioned+locked -> software root, no behaviour change |

Per-unit provisioning is run during production and is orchestrated by the flashing station
(flash the PROVISION build -> `0x64` with a button touch -> flash the shipping build). The
provisioning/diagnostic commands (`0x64`/`0x65`) are compiled **only** with `PROVISION=1` and are
never present in shipping firmware. Full procedure: `Firmware/Resident CTAP2.3/PROVISIONING.md`.

(See `2FAK Non-Resident - Firmware Documentation.md` for the shared signed-update and lockdown
subsystems.)

## Build (reference)

- `RESIDENT=1 FIDO23=1 bash build.sh` selects the passkey behaviour and advertises `FIDO_2_3`
  (default for this variant).
- `VERIFY_BOOT=1` produces the production image (`all-verifying.hex`); `VERIFY_BOOT=0`
  produces the dev image (`all-dev.hex`).
- Toolchain: arm-none-eabi-gcc + make from the STM32CubeIDE bundle. Flash region use is
  roughly one third of the 256 KB device.
