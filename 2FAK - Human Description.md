# Human Description

2FAK is a STM32 based USB-A dongle that comes in a programmable and Pre-Programmed versions. Pre-Programmed version of 2FAK comes with a mandatory secure element as well as applied and verified anti-tampering methods. Programmable 2FAK comes without a secure element by default. 2FAK is an open-source device with public hardware and firmware accessible for independant quality and security assessment.

2FAK was developed as an accessible alternative to major 2-Factor Authentication keys that can be purchased at a reasonable cost or assembled manually in places where the device or alternatives are unavailable. 2FAK is built on accessible hardware that is stocked at most major and minor manufacturers and resellers.

## Programmable USB Dongle
Programmable version of 2FAK has open programming pins that can be connected to via STLink programmer. As a programmable device, 2FAK can be used as a DIY 2-Factor Authentication key, a Mouse Jiggler, a DIY HID Injection device and much more. The Programmable 2FAK comes with pre-made firmwares for HID Injections and Mouse Jiggler. Additional project templates and optional 3D printable files are available on project Github. 

## Pre-Programmed 2FA Key
Pre-Programmed version of 2FAK comes with 2 firmware options. One with Non-Resident firmware that doesn't store any keys and a Resident firmware that can store up to 50 keys. Pre-Programmed 2FAK comes with 2-Factor Authentication firmware and a secure lement as means to prevent tampering and hacking. Pre-Programmed units can be purchased in pairs (1 2FAK + 1 Backup 2FAK) as a standard measure to prevent loss of access.

### Non-Resident 2FA Key
Non-Resident 2FAK is a FIDO2 / WebAuthn second factor built to the CTAP2.0 / 2.1 standards
and passes the FIDO Alliance Conformance Tools for CTAP2.0 and CTAP2.1 (self-test; not yet
formally FIDO Certified).

#### Firmware Specifications
- FIDO2 / WebAuthn (CTAP2.0 / 2.1), USB HID transport.
- Second factor only: credentials are held by the website (server-side); nothing is stored
  on the key, so the number of accounts is effectively unlimited.
- Optional device PIN (FIDO Client PIN), PIN/UV auth protocols 1 and 2.
- Extensions: hmac-secret, credProtect.
- Signed firmware updates over USB; production units are read-out protected (RDP-2).
- USB VID/PID 0x1209 / 0x2FA2.

#### Tested Platforms
- Google

### Resident 2FA Key
Resident 2FAK supports the higher FIDO CTAP2.3 standard and passes the FIDO Alliance
Conformance Tools for CTAP2.0, CTAP2.1 and CTAP2.3 (self-test; not yet formally FIDO
Certified). It can be used as a two-factor and passwordless (passkey) sign-in on most
platforms. For enterprise-level security keys, please contact us via e-mail.

#### Firmware Specifications
- FIDO2 / WebAuthn (CTAP2.0 / 2.1 / 2.3), USB HID transport.
- Passkeys: stores up to about 50 discoverable credentials on the key, with on-device
  credential management, for passwordless sign-in. Also works as a second factor.
- Optional device PIN (FIDO Client PIN), PIN/UV auth protocols 1 and 2.
- Extensions: hmac-secret, credProtect.
- Signed firmware updates over USB; production units are read-out protected (RDP-2).
- USB VID/PID 0x1209 / 0x2FA2.

#### Tested Platforms
- GitHub
- Google

Platforms yet to be tested:
1. Microsoft (personal account + Entra ID / work)
2. Apple ID
3. Amazon
4. Facebook / Meta
5. X (Twitter)
6. GitLab
7. Docker Hub
8. AWS (IAM / root)
9. Cloudflare
10. Okta
11. Bitwarden
12. 1Password
13. PayPal
14. Stripe
15. Coinbase
16. Kraken
17. Binance
18. Dropbox
19. Proton (Mail)
20. Fastmail
21. Nextcloud
22. Discord
23. Salesforce

## Custom Solutions
2FAK can be repurposed for use in a wide range of industrial and corporate solutions. Employee authentication keys; License verification keys; Legasy transition adapters and more. For custom solutions, please reach out via e-mail.

## Hardware Specifications
- MCU: STM32L442KCU6 (Arm Cortex-M4, UFQFPN-32). Register compatible with STM32L432.
- Secure element: ATECC608B on I2C1. Confirmed on hardware at 7-bit I2C address 0x60,
  Info revision word 00006003 (identifies an ATECC608B).
- USB: Full-Speed device, crystal-less (HSI48 with CRS). USB-A male blade.
- User interface: one button and one status LED.
- Debug/programming: SWD (SWDIO/SWCLK) plus the USB DFU bootloader.
- Power: USB bus powered. No battery, no battery sensing.

### Pin Summary
| Function        | Pin        |
|-----------------|------------|
| Button          | PA0        |
| Status LED      | PB3        |
| USB D- / D+     | PA11 / PA12|
| SWD             | PA13 / PA14|
| I2C to ATECC    | PB6 / PB7  |
| BOOT0           | PH3        |

### Hardware root of trust (ATECC608B)

On provisioned units the FIDO master secret is derived inside the secure element rather
than held only in MCU flash.

## Technical Specifications

| Item | Detail |
|---|---|
| Standards | FIDO2 / WebAuthn. Two firmware editions: second-factor (CTAP2.0/2.1) and passkey (CTAP2.3) |
| Controller | STM32L442, Arm Cortex-M4, 80 MHz |
| Security | On-chip true random generator, AES hardware, flash read-out protection level 2 on pre-programmed units (debug port disabled); secure element (ATECC608B) on pre-programmed units |
| USB ID | VID 0x1209 (pid.codes) / PID 0x2FA2 |
| Firmware update | Signed firmware update over USB; production units accept only muru.global-signed images |
| Connector | USB-A, built into the board edge (no cable) |
| Speed | USB 2.0 Full-Speed |
| Confirm action | Physical touch button |
| Indicator | Status LED |
| Power | From USB, about 30 mA. No battery |
| Works with | Windows 10/11, macOS, Linux, Android, ChromeOS |
| Size | About 48 x 21 mm |
| In the box | 2-FA Key. A second key is recommended as a backup |