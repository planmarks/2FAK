# 2FAK

Open-source USB security key (FIDO2 / WebAuthn / CTAP) by **muru.global**, built on
an STMicroelectronics STM32L442KCU6 with an optional ATECC608B secure element. The
board *is* the USB-A plug: no cable, no moving connector.

- USB VID/PID: **0x1209 / 0x2FA2** (0x1209 is the pid.codes open-source Vendor ID)
- AAGUID: **c2aa81f8-352d-56e2-c689-2bfdb5a52ccc**
- Firmware lineage: fork of Nitrokey FIDO2 / SoloKeys solo1 (see `NOTICE`)

## Repository layout

```
2FAK/
  Hardware/                     Board design files (schematic, PCB, BOM)
  Firmware/
    Non-Resident CTAP2.0-2.1/   Second-factor authenticator (no discoverable creds)
    Resident CTAP2.3/           Passkey authenticator (discoverable creds + credMgmt)
  Tools/                        Build/flashing/test tooling
  Docs/                         Product and technical documentation
  pidcodes/                     pid.codes PID allocation request (PR content)
  LICENSE  LICENSE-APACHE  LICENSE-MIT  NOTICE
```

## Two firmware variants

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

## Building

Each firmware directory is self-contained. On Windows with the STM32CubeIDE toolchain,
from Git Bash:

```bash
cd "Firmware/Resident CTAP2.3"
bash build.sh                    # production-style build
```

Build switches (environment variables) are documented in `build.sh`. Artifacts land in
`prebuilt/` and are **not** committed (see Secrets, below).

## Security model and secrets

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

## License

Dual-licensed under **Apache-2.0 OR MIT**, at your option. See `LICENSE`, `LICENSE-APACHE`,
`LICENSE-MIT`, and `NOTICE` for third-party attribution.
