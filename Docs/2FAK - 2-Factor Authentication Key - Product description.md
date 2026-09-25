# 2FAK — 2‑Factor Authentication Key

*by muru.global · Hardware rev. V1A*

---

## Short description

**2FAK is a hardware security key that makes your online accounts phishing‑proof.**
Plug it into any USB‑A port, tap the button to confirm it's really you, and you're
signed in — no codes to copy, no apps to open, nothing for an attacker to steal.
Built on open‑source firmware and the same proven chip used by leading open security
keys, it works with Google, Microsoft, GitHub, and hundreds of other services that
support modern **passkeys / FIDO2 / U2F**.

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
- **One key, hundreds of services.** Works anywhere that supports FIDO2/WebAuthn
  passkeys or U2F security keys — Google, Microsoft accounts, GitHub, GitLab, Dropbox,
  Cloudflare, X/Twitter, Facebook, and popular password managers such as Bitwarden and
  1Password, among many others.
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

## Technical specifications

| | |
|---|---|
| **Security controller** | STMicroelectronics STM32L442KCU6 — Arm® Cortex®‑M4 @ 80 MHz |
| **Memory** | 256 KB flash · 64 KB SRAM |
| **Hardware security** | True random number generator (TRNG) · AES‑256 accelerator · flash readout protection (RDP) |
| **Optional secure element** | ATECC608B footprint (I²C) for hardware key isolation |
| **Protocols** | FIDO2 (CTAP2) / WebAuthn passkeys · FIDO U2F (CTAP1) |
| **Conformance** | Passes FIDO Alliance Conformance Test Tools (self‑test): CTAP2.0, CTAP2.1 and CTAP2.3 authenticator suites, 0 failures. Formal FIDO Certification is a separate step, not yet claimed. |
| **Interface** | USB 2.0 Full‑Speed (12 Mbit/s), USB‑A — integrated PCB‑edge plug (no cable, no connector) |
| **Clocking** | Crystal‑less USB (internal HSI48 + Clock Recovery System) |
| **User interaction** | Tactile "user‑presence" button (touch‑to‑confirm) · status LED |
| **Power** | Bus‑powered from USB 5 V; on‑board 3.3 V LDO; ~30 mA typical |
| **Protection** | Dedicated USB D+/D−/VBUS ESD/TVS array |
| **Operating systems** | Windows 10/11 · macOS · Linux · Android · ChromeOS (native, driver‑free) |
| **Firmware** | Open‑source FIDO2/U2F (Solo 1 / Nitrokey lineage) |
| **Board** | 2‑layer FR4, ground‑poured; ~48 × 21 mm; gold‑plated USB contacts |
| **Programming/debug** | SWD via Tag‑Connect TC2030 footprint (factory/advanced) |

*Specifications for hardware rev. V1A and subject to refinement.*
