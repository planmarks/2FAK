# 2FAK Non-Resident - Firmware Documentation

Documentation of the **non-resident (second-factor)** firmware. This document covers the
firmware only. It is one of two firmware variants built from a single codebase; the passkey
variant is documented in `2FAK Resident - Firmware Documentation.md`.

## Summary

A FIDO2 / WebAuthn security-key firmware configured as a **second factor only**. It creates
non-discoverable (server-side) credentials and declines requests to store resident /
discoverable credentials. It is a fork of the Nitrokey FIDO2 firmware, which derives from
SoloKeys Solo 1, and is built with the `RESIDENT=0` option.

- **Transport:** USB HID (CTAPHID).
- **USB identity:** VID 0x1209 (pid.codes, open-source) / PID 0x2FA2.
- **AAGUID:** c2aa81f8-352d-56e2-c689-2bfdb5a52ccc (self-assigned).
- **Conformance:** passes the FIDO Alliance Conformance Test Tools for CTAP2.0 and CTAP2.1
  (self-test). See `2FAK Non-Resident - FIDO Conformance Readiness.md`.
- **License:** Apache-2.0.

## Protocols advertised (authenticatorGetInfo)

- **versions:** `FIDO_2_0`, `FIDO_2_1_PRE`, `FIDO_2_1` (this variant does not advertise
  `FIDO_2_3`).
- **extensions:** `credProtect`, `hmac-secret`.
- **options:** `rk = false`, `up = true`, `plat = false`, `clientPin` (dynamic, reflects
  whether a PIN is set), `pinUvAuthToken = true`. No `credMgmt`.
- **pinUvAuthProtocols:** `[1, 2]`.
- **transports:** `["usb"]`.
- **algorithms:** ES256 (`-7`).
- **maxCredentialCountInList**, **maxCredentialIdLength**, **minPINLength** (4),
  **firmwareVersion**.

## Credential model

- **Non-resident only.** `authenticatorMakeCredential` returns
  `CTAP2_ERR_UNSUPPORTED_OPTION` when a resident/discoverable credential (`rk = true`) is
  requested. Nothing is stored on the key and there is no account picker; the number of
  accounts is effectively unlimited because credentials live on the relying party.
- Credentials are self-authenticating: the credential ID carries a MAC that the device
  verifies, so per-account key pairs are re-derived on demand and never exported.

## CTAP commands

- `authenticatorGetInfo`, `authenticatorMakeCredential`, `authenticatorGetAssertion`,
  `authenticatorClientPIN`, `authenticatorReset`, plus the Solo/Nitrokey vendor commands
  (bootloader entry, version, lock, ATECC self-test).
- **Client PIN:** PIN/UV auth protocols **1 and 2**, including
  `getPinUvAuthTokenUsingPinWithPermissions`.
- **pinUvAuthToken:** 32-byte token; permission bits limited to makeCredential + getAssertion
  (`mc`, `ga`); optional RP-ID binding; rolling ~30 s inactivity lifetime; invalidated on
  power cycle and on reset. A token presented without the permission an operation needs is
  rejected with `PIN_AUTH_INVALID`.

## Client PIN behaviour

- Optional by default (the relying party decides). A build-time `PIN_POLICY` can change this:
  `optional` (default), `requireset` (a PIN must be set before the first credential), or
  `alwaysuv` (advertise `alwaysUv` and require a pinUvAuthToken on every operation).
- Standard CTAP retry handling: a per-boot lockout after 3 consecutive bad attempts
  (`PIN_AUTH_BLOCKED`, cleared by a power cycle), and a full block when the persistent retry
  counter reaches zero (`PIN_BLOCKED`, cleared only by an authenticatorReset). A reset also
  clears the per-boot lockout.

## User presence

- A physical button press is required for registration and authentication (user presence),
  with LED signalling (idle off, waiting blink, accepted solid).

## Extensions

- **hmac-secret** (protocol 1 and 2 aware).
- **credProtect** (credential-protection levels, packed into the MAC-covered credential ID).

## Attestation

- Packed / `basic_full` attestation.
- Development images seed the well-known Solo "hacker" attestation key. Production units are
  provisioned with the muru.global batch attestation key + certificate (injected at flash
  time by `provision_attestation.py`); the metadata statement embeds the muru Root CA.
- The device uses self-/batch attestation and is not (yet) listed in the FIDO Metadata
  Service. It is not FIDO Certified; conformance is a self-test result.

## Secure firmware update over USB

- **Verifying (production) bootloader:** accepts firmware over USB only if it is signed with
  the muru production bootloader key (ECDSA P-256 over a SHA-256 of the application region).
  The private key never leaves muru; the device verifies the signature itself.
- **Non-verifying (dev) bootloader:** accepts unsigned firmware, for development.
- **Anti-rollback:** the verifying bootloader only accepts firmware whose version is greater
  than or equal to the currently installed version.
- Updates are delivered over USB (no programmer needed), so a unit remains updatable after
  its debug port is closed.

## Production lockdown

- Production units enable **flash read-out protection level 2 (RDP-2)**: the SWD/debug port
  is permanently disabled, so firmware and secrets cannot be read out or the chip reflashed
  over a programmer. Signed USB updates still work after locking, because the bootloader
  remains intact.
- Production images are built without the `SOLO_HACKER` option.

## Hardware root of trust (populated units)

- On units with the ATECC608B fitted and provisioned, the FIDO master secret is derived
  inside the secure element (MAC command, mode 0x06) from an unreadable root key, rather than
  held only in MCU flash. Per-credential keys derive from that master secret.
- If the secure element is absent, unprovisioned, or ever fails to derive, the firmware falls
  back to a software master secret with no change in behaviour, so a missing or mis-provisioned
  chip cannot break the FIDO function.
- An authenticatorReset changes the per-device salt, which invalidates all previously derived
  credentials.

## Build (reference)

- `RESIDENT=0 bash build.sh` selects the non-resident behaviour (default for this variant).
- `VERIFY_BOOT=1` produces the production image (`all-verifying.hex`, verifying bootloader,
  `SOLO_HACKER` off); `VERIFY_BOOT=0` produces the dev image (`all-dev.hex`).
- `U2F=1` optionally compiles the legacy U2F/CTAP1 path (off by default to save flash).
- Toolchain: arm-none-eabi-gcc + make from the STM32CubeIDE bundle. Flash region use is
  roughly one third of the 256 KB device.
