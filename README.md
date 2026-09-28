# 2FAK

Open-source USB security key (FIDO2 / WebAuthn / CTAP) by **muru.global**, built on
an STMicroelectronics STM32L442KCU6 with an optional ATECC608B secure element. The
board *is* the USB-A plug: no cable, no moving connector.

- USB VID/PID: **0x1209 / 0x2FA2** (0x1209 is the pid.codes open-source Vendor ID; PID 0x2FA2 is registered to us at pid.codes)
- AAGUID: **c2aa81f8-352d-56e2-c689-2bfdb5a52ccc**
- Firmware lineage: fork of Nitrokey FIDO2 / SoloKeys solo1 (see `NOTICE`)

## Hardware

### Microcontroller

- **Part:** STMicroelectronics STM32L442KCU6 (Arm Cortex-M4F, up to 80 MHz, UFQFPN-32
  package). Register-compatible with the STM32L432.
- **Memory:** 256 KB flash, 64 KB SRAM.
- **On-chip security features:** true random number generator (TRNG), AES-256 hardware
  accelerator, and flash read-out protection (RDP) supported in silicon.
- **Clocking:** crystal-less USB using the internal HSI48 oscillator with the Clock
  Recovery System (CRS); no external crystal is required.

### Secure Element (populated variant)

- **Part:** Microchip ATECC608B, on the I2C1 bus.
- Confirmed on hardware at 7-bit I2C address 0x60, Info revision word 0x00006003 (which
  identifies an ATECC608B).
- Provides tamper-resistant key storage and cryptographic operations. On the units where
  it is fitted, it can hold a device root that cannot be read back out of the chip.
- On boards where it is not fitted, the footprint remains but is unpopulated.

### USB Interface

- USB 2.0 **Full-Speed** (12 Mbit/s) device.
- **USB-A male** contacts integrated into the edge of the PCB (no cable, no moving
  connector).
- Dedicated ESD / TVS protection on the D+, D- and VBUS lines.

### User Interface

- One **tactile push button** (user-presence / control input).
- One **status LED**.

### Power

- **USB bus-powered** from the 5 V supply, regulated on-board to 3.3 V by an LDO.
- Typical current draw about 30 mA. No battery and no battery sensing.

### Debug and Programming

- **SWD** debug/programming interface (SWDIO / SWCLK).
- BOOT0 is available for boot-mode selection.

*Notice: SWD is closed in units sold as 2FAK Authentication Key.*

## Pin Summary

| Function        | Pin         |
|-----------------|-------------|
| Button          | PA0         |
| Status LED      | PB3         |
| USB D- / D+     | PA11 / PA12 |
| SWD (SWDIO/SWCLK)| PA13 / PA14|
| I2C to ATECC (SCL/SDA) | PB6 / PB7 |
| BOOT0           | PH3         |

Note: PB6 / PB7 are shared between the ATECC I2C bus and an optional debug UART. On the
populated (secure-element) boards these pins are used for the I2C bus.

## 2FA Firmware Variants

| | Non-Resident CTAP2.0/2.1 | Resident CTAP2.3 |
|---|---|---|
| Model | Second factor (server-side credentials) | Passkeys (discoverable credentials) |
| Discoverable credentials (rk) | No | Yes |
| Credential Management | No | Yes |
| ClientPIN protocols | 1 | 1 and 2 |
| Extensions | hmac-secret, credProtect | hmac-secret, credProtect, minPinLength |
| Conformance (self-test) | CTAP2.0, CTAP2.1 | CTAP2.0, CTAP2.1, CTAP2.3 |

Conformance results are validated against the **FIDO Alliance Conformance Test Tools
(self-test)** and are recorded per firmware under `Firmware/.../tests/`. Formal FIDO
Certification is a separate submission and is **not** claimed.

### Building

Each firmware directory is self-contained. On Windows with the STM32CubeIDE toolchain,
from Git Bash:

```bash
cd "Firmware/Resident CTAP2.3"
bash build.sh                    # production-style build
```

Build switches (environment variables) are documented in `build.sh`. Artifacts land in
`prebuilt/` and are **not** committed (see Secrets, below).

### Security

Per-credential keys are generated and held in the MCU; the optional device root can be
held in the ATECC608B secure element. Production units enable flash readout protection
(RDP) and a verifying bootloader so firmware cannot be extracted or replaced off a
locked device.

**This is a public repository. It never contains private keys.** The following are
git-ignored and must exist only on the build/flashing machines:

- muru attestation private keys (`keys/2fak/ca_key.pem`, `att_key.pem`, `priv.bin/.hex`)
- the production verifying-bootloader signing key
- any provisioned `*.hex` (a provisioned image embeds the attestation private key)

Public certificates (root CA + leaf), the AAGUID, and the metadata statements are
published on purpose. Release firmware images are distributed via signed GitHub
Releases, not committed to the tree.

### Platform Compatibility

## Other Firmware Options
- Mouse Jiggler firmware (coming soon)
- SSH Key firmware (coming soon)
- HID Injection firmware (coming soon)

## License

Licensed under **Apache-2.0**. See `LICENSE-APACHE` for the full license text and
`NOTICE` for third-party attribution.
