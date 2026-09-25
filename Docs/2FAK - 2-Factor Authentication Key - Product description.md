# 2FAK — 2‑Factor Authentication Key

*by muru.global · Hardware rev. V1A*

---

## Short description

**2FAK is a hardware security key that makes your online accounts phishing‑proof.**
Plug it into any USB‑A port, tap the button to confirm it's really you, and you're
signed in — no codes to copy, no apps to open, nothing for an attacker to steal.
Built on open‑source firmware and the same proven chip used by leading open security
keys, it works with Google, Microsoft, GitHub, and hundreds of other services that
support modern **passkeys / FIDO2 / WebAuthn**. It ships in two firmware variants: a
classic **second‑factor** build and a **passkey** build (see below).

---

## Long description

Passwords leak. SMS codes get intercepted. Authenticator‑app codes can be phished by
a convincing fake login page. **2FAK removes that entire class of attack.**

2FAK is a small, tough, cable‑free USB key — the circuit board *is* the USB‑A plug, so
there's nothing to wear out or snap off. When a website asks for your security key,
you insert 2FAK and touch its button. Behind that simple tap, the key performs
public‑key cryptography that proves your identity **directly to the real website** and
**only** to the real website. The secret never leaves the key, and a phishing site
literally cannot produce a valid response — because the key checks who it's talking to.

- **Phishing‑resistant by design.** Credentials are cryptographically bound to the
  genuine site. Fake login pages get nothing usable.
- **Nothing to type.** No 6‑digit codes, no time pressure, no copy‑paste. Insert, tap,
  done.
- **Your keys stay on the key.** Private keys are generated and stored inside the
  chip's protected flash and are never exported. After provisioning, the firmware can
  be locked (readout protection) so the secrets can't be extracted even with physical
  access.
- **One key, hundreds of services.** Works anywhere that supports FIDO2/WebAuthn —
  Google, Microsoft accounts, GitHub, GitLab, Dropbox, Cloudflare, X/Twitter, Facebook,
  and popular password managers such as Bitwarden and 1Password, among many others.
- **Field‑updatable, securely.** Firmware can be updated over USB without a programmer.
  Production units only accept firmware digitally signed by muru.global, so an update
  cannot be tampered with.
- **Works everywhere you do.** No drivers, no software to install. Windows, macOS,
  Linux, Android and ChromeOS recognise it natively over USB.
- **Open and auditable.** 2FAK runs maintained open‑source security‑key firmware, so
  its behaviour can be independently reviewed — no black boxes guarding your identity.
- **Standards‑tested.** Validated against the FIDO Alliance Conformance Test Tools
  (self‑test), passing the full CTAP2.0, CTAP2.1 and CTAP2.3 authenticator test suites
  with zero failures. Formal FIDO Certification is a separate submission and is not yet
  claimed.
- **Made to last.** A single‑piece PCB blade with no moving connector, a low‑power
  microcontroller, and ESD‑protected USB lines for everyday pocket‑and‑keyring life.

Use it as your everyday second factor, or go passwordless entirely on services that
support it — signing in with just the key and a touch.

> **Good to know:** 2FAK uses self‑attestation (open‑source firmware). It's ideal for
> personal accounts and organisations that allow standard security keys. Some corporate
> environments enforce *attestation allow‑lists* that only accept specific certified
> models — check with your IT administrator if you're deploying in such a tenant.

---

## Two firmware variants

2FAK ships with a choice of two firmware builds on the **same hardware**. Both are
phishing‑resistant FIDO2 authenticators; they differ in whether credentials are stored
on the key.

**Second‑factor (Non‑Resident, CTAP2.0 / 2.1)**
- Classic security‑key mode: credentials are held by the website (server‑side), not on
  the key, so there is effectively no on‑key credential limit and the footprint is minimal.
- Ideal as a strong second factor on top of your existing sign‑in.
- Passes the FIDO Alliance Conformance Test Tools for CTAP2.0 and CTAP2.1 (self‑test).

**Passkey (Resident, CTAP2.3)**
- Stores discoverable credentials (passkeys) on the key, with on‑device credential
  management, for passwordless sign‑in.
- Passes the FIDO Alliance Conformance Test Tools for CTAP2.0, CTAP2.1 and CTAP2.3
  (self‑test).

Both variants share the same signed USB update mechanism and the same production lockdown
(flash readout protection with the debug port permanently disabled). A unit can be moved
between variants with a signed USB update. Formal FIDO Certification is a separate
submission and is not yet claimed.

---

## Technical specifications

| | |
|---|---|
| **Security controller** | STMicroelectronics STM32L442KCU6 — Arm® Cortex®‑M4 @ 80 MHz |
| **Memory** | 256 KB flash · 64 KB SRAM |
| **Hardware security** | True random number generator (TRNG) · AES‑256 accelerator · flash readout protection level 2 on production units (SWD/debug permanently disabled) |
| **Optional secure element** | ATECC608B footprint (I²C) for hardware key isolation |
| **Protocols** | FIDO2 (CTAP2) / WebAuthn. Two firmware variants: second‑factor (CTAP2.0/2.1) and passkey (CTAP2.3, discoverable credentials + credential management) |
| **Firmware update** | Signed firmware update over USB (no programmer); production units accept only muru.global‑signed images |
| **Conformance** | Passes FIDO Alliance Conformance Test Tools (self‑test): second‑factor build CTAP2.0/2.1; passkey build CTAP2.0/2.1/2.3; 0 failures. Formal FIDO Certification is a separate step, not yet claimed. |
| **Interface** | USB 2.0 Full‑Speed (12 Mbit/s), USB‑A — integrated PCB‑edge plug (no cable, no connector) |
| **Clocking** | Crystal‑less USB (internal HSI48 + Clock Recovery System) |
| **User interaction** | Tactile "user‑presence" button (touch‑to‑confirm) · status LED |
| **Power** | Bus‑powered from USB 5 V; on‑board 3.3 V LDO; ~30 mA typical |
| **Protection** | Dedicated USB D+/D−/VBUS ESD/TVS array |
| **Operating systems** | Windows 10/11 · macOS · Linux · Android · ChromeOS (native, driver‑free) |
| **Firmware** | Open‑source FIDO2 (Solo 1 / Nitrokey lineage); dual Apache‑2.0 OR MIT |
| **Board** | 2‑layer FR4, ground‑poured; ~48 × 21 mm; gold‑plated USB contacts |
| **Programming/debug** | SWD via Tag‑Connect TC2030 footprint (factory only; permanently disabled on production units after RDP‑2 lock). Post‑sale updates are signed‑USB only |

*Specifications for hardware rev. V1A and subject to refinement.*
