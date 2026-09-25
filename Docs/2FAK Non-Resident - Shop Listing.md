# 2FAK Security Key (Second-Factor Edition)

## Short description

2FAK is an open-source USB security key for two-factor authentication. It works with
the FIDO2/WebAuthn sign-in used by many major online services. It is built around an
STM32 microcontroller with a dedicated secure element, and it is designed as a hardware
second factor that you add on top of your normal password.

> **Two firmware editions.** This listing is the **Second-Factor Edition** (CTAP2.0/2.1,
> non-resident). A **Passkey Edition** (CTAP2.3, on-key discoverable credentials for
> passwordless sign-in) is also available on the same hardware. Both use signed USB
> firmware updates and the same production security lockdown; a unit can be moved between
> editions with a signed update.

## Long description

2FAK is a small USB key that helps protect your online accounts. After you enter your
username and password, you insert the key and touch the button to complete sign-in. The
private keys used for authentication are created and used on the device itself. They are
not shared with the websites you log in to, and the device does not phone home.

This is the Second-Factor Edition. It creates non-discoverable credentials only, which
means it acts as an extra security step on top of your password. It does not store a
list of your accounts on the key and does not act as a stand-alone passwordless login
("passkey"). Each website keeps the reference to its own credential and supplies it back
to the key at sign-in.

The design is open source, so the hardware and firmware can be reviewed by anyone. On
supported units, an on-board secure element (Microchip ATECC608B) holds a device root
key that is generated on the device and cannot be read back out of the chip. Per-account
keys are derived from that root.

### Key points

- USB-A security key for two-factor authentication.
- Compatible with FIDO2/WebAuthn and U2F sign-in flows in common browsers and operating
  systems, with no extra driver needed.
- Second factor only: creates non-discoverable credentials, reports `rk = false`, and
  declines requests to store resident/discoverable credentials.
- Physical touch button confirms that a person approved each sign-in (user presence).
- Optional device PIN (FIDO Client PIN) can be set for user verification.
- Private keys are created and kept on the device. They are not exported.
- On supported units, a secure element (ATECC608B) provides a hardware-protected device
  root; per-account keys are derived from it.
- Open-source firmware and hardware.
- Unlimited number of accounts, because no per-account data is stored on the key.

### Typical sign-in flow

1. Enter your username and password on the website.
2. Insert 2FAK when the site asks for your security key.
3. If you set a device PIN, enter it.
4. Touch the button to confirm.
5. You are signed in.

### What is in the box

- 1 x 2FAK security key.

### Technical specifications

- Controller: STMicroelectronics STM32L442 (Arm Cortex-M4).
- Secure element: Microchip ATECC608B (present on the board; used for the device root on
  provisioned units).
- Interface: USB Full-Speed (USB-A), HID transport (CTAPHID). No driver required.
- Protocols: FIDO2 (CTAP2) and U2F (CTAP1).
- Controls: one touch button, one status LED.
- Power: bus powered. No battery.

### Compatibility

2FAK uses the standard FIDO2/WebAuthn and U2F interfaces. It works with services and
browsers that support hardware security keys over USB, on common desktop operating
systems. Please check that the specific service you want to protect supports USB
security keys, since support is decided by each service.

### Data protection

2FAK is designed with data minimisation in mind. It does not collect personal data, it
does not store your account names on the key, and it does not send data to us or to any
third party. Authentication keys stay on the device.

### Guarantee and compliance

This product is sold within the EU. The statutory legal guarantee of conformity applies
as required by EU consumer law. This is a low-voltage, USB bus-powered device with no
radio transmitter. RoHS and REACH obligations are handled by the manufacturer.

### Please note

- This device is a security aid. No single security product can guarantee protection
  against every possible attack. Use it together with good account practices.
- If you set a device PIN and forget it, the PIN cannot be recovered. You would need to
  perform a factory reset, which invalidates existing credentials, and then register the
  key again with each service.
- Because this edition creates non-discoverable credentials, it is intended as a second
  factor and not as a stand-alone passwordless login.
