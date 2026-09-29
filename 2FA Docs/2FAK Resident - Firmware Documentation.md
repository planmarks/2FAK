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
- **algorithms:** ES256 (`-7`).
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
- `ed25519-sk` is **not** supported (no Ed25519/EdDSA in the firmware); use `ecdsa-sk`.

Full sysadmin workflow (resident enroll/export, ProxyJump bastions, Ansible
`authorized_keys`, SSH-CA integration, PIN tiering, Windows/PuTTY, backup enrollment, and
the `2FAK-ssh-enroll` helper) is documented in `2FAK Resident - Hardware SSH Key Guide.md`.

## Attestation

- Packed / `basic_full` attestation, muru.global batch attestation key + certificate on
  production units (injected by `provision_attestation.py`); metadata statement embeds the
  muru Root CA. Not FIDO Certified; conformance is a self-test result; not (yet) in the FIDO
  Metadata Service.

## Secure firmware update, production lockdown, and hardware root

These are identical to the non-resident variant:

- **Signed USB update:** the verifying (production) bootloader accepts only muru-signed
  firmware (ECDSA P-256 over the app region); the dev bootloader accepts unsigned firmware;
  anti-rollback enforces version-not-older.
- **Production lockdown:** RDP-2 permanently disables the debug port; signed USB updates still
  work afterwards; production images are built without `SOLO_HACKER`.
- **Hardware root of trust:** on units with a provisioned ATECC608B the FIDO master secret is
  derived inside the secure element, with a transparent software fallback if the chip is
  absent, unprovisioned, or fails.

(See `2FAK Non-Resident - Firmware Documentation.md` for the detailed description of these
shared subsystems.)

## Build (reference)

- `RESIDENT=1 FIDO23=1 bash build.sh` selects the passkey behaviour and advertises `FIDO_2_3`
  (default for this variant).
- `VERIFY_BOOT=1` produces the production image (`all-verifying.hex`); `VERIFY_BOOT=0`
  produces the dev image (`all-dev.hex`).
- Toolchain: arm-none-eabi-gcc + make from the STM32CubeIDE bundle. Flash region use is
  roughly one third of the 256 KB device.
