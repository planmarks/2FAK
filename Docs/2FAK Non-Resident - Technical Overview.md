# 2FAK Non-Resident - Technical Overview

Internal engineering reference for the second-factor (non-resident) product. This
describes what the hardware and firmware actually do today, not a target specification.

## 1. Summary

2FAK is a USB security key based on an STM32L442 microcontroller with a Microchip
ATECC608B secure element. The firmware is a fork of the Nitrokey FIDO2 firmware, which
itself derives from SoloKeys Solo 1. This variant is configured as a second factor only:
it creates non-discoverable credentials and declines resident/discoverable credential
requests.

## 2. Hardware

- MCU: STM32L442KCU6 (Arm Cortex-M4, UFQFPN-32). Register compatible with STM32L432.
- Secure element: ATECC608B on I2C1. Confirmed on hardware at 7-bit I2C address 0x60,
  Info revision word 00006003 (identifies an ATECC608B).
- USB: Full-Speed device, crystal-less (HSI48 with CRS). USB-A male blade.
- User interface: one button and one status LED.
- Debug/programming: SWD (SWDIO/SWCLK) plus the USB DFU bootloader.
- Power: USB bus powered. No battery, no battery sensing.

Pin summary:

| Function        | Pin        |
|-----------------|------------|
| Button          | PA0        |
| Status LED      | PB3        |
| USB D- / D+     | PA11 / PA12|
| SWD             | PA13 / PA14|
| I2C to ATECC    | PB6 / PB7  |
| BOOT0           | PH3        |

The debug UART would also use PB6/PB7, so it is only compiled at DEBUG_LEVEL > 0.
Production builds (DEBUG_LEVEL 0) leave PB6/PB7 free for the ATECC I2C bus.

## 3. Firmware architecture

- Base: Nitrokey FIDO2 / Solo 1 fork. Bootloader plus application.
- Transport: USB HID with CTAPHID.
- Protocols advertised in authenticatorGetInfo:
  - versions: `FIDO_2_0`, `FIDO_2_1_PRE`, `FIDO_2_1` by default (plus `U2F_V2` only in a
    `U2F=1` build, and `FIDO_2_3` only in a `FIDO23=1` build). Default tops out at
    FIDO_2_1 because the conformance tools test to the highest advertised version.
  - extensions: `credProtect`, `hmac-secret`
  - options: `rk = false`, `up = true`, `plat = false`, `clientPin` (dynamic),
    `pinUvAuthToken = true`
  - pinUvAuthProtocols: `[1, 2]`
  - transports: `["usb"]`
  - maxCredentialCountInList, maxCredentialIdLength, algorithms (`[ES256]`),
    minPINLength (4), firmwareVersion
- Credential model: non-resident only. `authenticatorMakeCredential` returns
  `CTAP2_ERR_UNSUPPORTED_OPTION` if a resident key is requested. No credential storage,
  no account picker.
- CTAP commands present: GetInfo, MakeCredential, GetAssertion, ClientPIN (PIN/UV auth
  protocols 1 and 2, including `getPinUvAuthTokenUsingPinWithPermissions`), Reset, plus
  the Solo vendor commands.
- pinUvAuthToken: 32-byte token, permission bits (makeCredential + getAssertion only),
  optional RP-ID binding, rolling 30s inactivity lifetime, invalidated on power cycle and
  reset. See `fido2/pin_protocol.{c,h}` and the token logic in `fido2/ctap.c`.
- User presence: physical button, handled by the standard user-presence path with LED
  signalling (idle off, waiting blink, accepted solid).
- Client PIN: supported, optional. Standard CTAP retry behaviour (per-boot lockout after
  repeated failures, full block requiring reset when the retry counter reaches zero).
- U2F/CTAP1: present for legacy compatibility.

### Identity and attestation

- USB VID/PID and AAGUID are project placeholders. They are not yet officially allocated
  or registered. See limitations.
- Attestation is packet/self attestation. Development builds seed the well-known Solo
  "hacker" attestation key. A muru.global batch attestation key and certificate can be
  injected at flash time with `provision_attestation.py`. The device is not listed in the
  FIDO Metadata Service (MDS).

## 4. Hardware root of trust (ATECC608B)

On provisioned units the FIDO master secret is derived inside the secure element rather
than held only in MCU flash.

- Driver: `targets/stm32l432/src/atecc.{c,h}`. Raw I2C1, GPIO wake, Atmel CRC16, and the
  Info, Read, Nonce, MAC, Write and Lock commands.
- Root slot: slot 0, configured as a secret, non-ECC key that is not readable and is
  usable by the MAC command (SlotConfig 0x2080, KeyConfig 0x003C).
- Derivation: a per-device flash value is loaded into TempKey with a passthrough Nonce,
  then the MAC command (mode 0x06, PTNONCE_TEMPKEY) computes a 32-byte digest keyed by
  the unreadable root slot key. The result becomes the master secret from which
  per-credential keys are derived. The legacy HMAC command is not used because the
  ATECC608B rejects it (parse error); MAC mode 0x06 was confirmed on hardware.
- Reset semantics: the flash value acts as a salt. Changing or wiping it changes every
  derived key, so an authenticator reset still invalidates old credentials.

### Detect and fall back

`atecc_ready()` returns true only when the chip answers and both its config and data
zones are locked (provisioned). Otherwise the firmware uses the software master secret
with no change in behaviour. If a provisioned chip ever fails to derive, the code also
falls back to the software secret. As a result:

- Units with an unprovisioned or absent chip behave exactly as the software-only build.
- A mis-provisioned chip cannot brick the FIDO function.

### Provisioning (one-time, irreversible)

Provisioning writes the slot config, verifies it before locking, locks the config zone,
writes a random root key, locks the data zone, and runs a self-check. It is compiled
only with `-DATECC_PROVISION` and triggered by a button-gated vendor command, so it
cannot run by accident. See the provisioning section of `VARIANT.md`.

## 5. Build and flash

- Toolchain: arm-none-eabi-gcc and make from the STM32CubeIDE bundle.
- Normal image: `bash build.sh` produces `prebuilt/all.hex` (bootloader plus application
  plus boot authorisation word plus seeded attestation key).
- Provisioning image: `PROVISION=1 bash build.sh` produces `prebuilt/provision/all.hex`,
  which adds the provisioning and diagnostic vendor commands. The normal image does not
  contain them.
- CTAP1/U2F: OFF by default (legacy-only, saves flash). Build with `U2F=1 bash build.sh`
  to include it; that adds `U2F_V2` to getInfo and the CTAPHID_MSG transport. With it off,
  CTAPHID_MSG returns CTAP1_ERR_INVALID_COMMAND.
- PIN enforcement policy: build-time `PIN_POLICY` (default `optional`).
  `PIN_POLICY=requireset bash build.sh` forces a PIN to be set before the first
  credential; `PIN_POLICY=alwaysuv bash build.sh` advertises `alwaysUv` and requires a
  pinUvAuthToken for every makeCredential and getAssertion. Default shipped build is
  `optional` (relying party decides).
- CTAP version advertised: default tops out at `FIDO_2_1`. `FIDO23=1 bash build.sh` also
  advertises `FIDO_2_3` (only once full 2.3 conformance is validated with the FIDO tools).
- Attestation PKI: `keys/make_attestation_ca.py` generates the attestation Root CA and a
  batch leaf cert (AAGUID extension = the device AAGUID). `provision_attestation.py`
  injects the leaf key+cert into all.hex for production attestation. The metadata
  statement is generated by `metadata/make_metadata.py` (embeds the Root CA).
- Flash over SWD with STM32CubeProgrammer, or over the USB DFU bootloader.
- Read-out protection: current builds use RDP level 0 for development and reflashing. An
  RDP level 2 production build and a signature-verifying bootloader are planned for later.

## 6. Security model (short)

- Per-account key pairs are created on the device. Private keys are not exported.
- User presence (touch) is required for registration and authentication.
- Optional Client PIN provides user verification and gates key use.
- On provisioned units, the device root cannot be read out of the secure element.
- The device stores no account list and sends no personal data.

## 7. Current limitations

- `FIDO_2_3` is advertised, but formal FIDO conformance-tool validation has not been run.
  Do not make an external "CTAP 2.3" claim until it passes the conformance tools. The
  `alwaysUv` / `makeCredUvNotRqd` options and the full 2.3 up/uv option matrix are not
  implemented (the core up=touch, uv=pinUvAuthToken behaviour is).
- No PIN is enforced in the default build (`PIN_POLICY=optional`). The `requireset` and
  `alwaysuv` policies exist as build options but are not yet hardware-tested.
- Flash use is ~91% in the default (U2F-off) build, ~93% with `U2F=1`. Roughly 6 KB free
  in the default build.
- USB VID/PID and AAGUID are placeholders and are not officially allocated.
- The device is not FIDO certified and is not listed in the FIDO MDS.
- RDP level 2 and a verifying bootloader are not yet enabled.
- The ATECC hardware root has been validated on one board so far. It should be validated
  across a larger sample before being relied on in volume.
- Protocol 2 and the pinUvAuthToken permissions model are code-complete and need a
  hardware-test pass (`fido_tests.py pin2` and `pin2perm`).
