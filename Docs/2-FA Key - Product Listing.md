# 2-FA Key

*by muru.global*

## Title
2-FA Key — Hardware Security Key for Phishing-Proof Login (USB-A, FIDO2 / U2F)

## Short description
A small USB key that makes your accounts almost impossible to phish. Plug it in, tap
the button, and you are signed in. No codes to type, no app to open. Works with Google,
Microsoft, GitHub and hundreds of other sites that support security keys and passkeys.

## Long description
Passwords get stolen. Text-message codes can be intercepted. Even authenticator app
codes can be tricked by a fake login page. The 2-FA Key removes that whole problem.

When a site asks for your security key, you plug in the 2-FA Key and touch its button.
In that moment the key proves who you are to the real website using strong
cryptography. The secret that does this never leaves the key, and a fake site cannot
copy it, because the key checks that it is talking to the genuine site. That is what
"phishing-proof" means in practice.

It is built to be simple and to last. The board itself is the USB-A plug, so there is
no cable and no moving connector to wear out. There is nothing to install and nothing
to charge. It works the moment you plug it in.

Highlights:

- **Phishing-proof.** Your login is tied to the real website, so fake pages get nothing.
- **No codes to type.** Plug in, tap the button, done.
- **Your secret stays on the key.** Keys are created and kept inside the chip and are
  never handed out. The key can be locked so they cannot be pulled off it.
- **One key, many accounts.** Use the same key for Google, Microsoft, GitHub, GitLab,
  Dropbox, Cloudflare, Facebook, X, and password managers like Bitwarden and 1Password.
- **Go passwordless.** On sites that support passkeys, sign in with just the key and a tap.
- **No drivers.** Windows, macOS, Linux, Android and ChromeOS recognise it on their own.
- **Open firmware.** The security software is open source, so experts can check it.

Good to know: this key uses open-source firmware with self-attestation. It is a great
fit for personal accounts and for companies that accept standard security keys. Some
strict company systems only allow specific certified brands, so if it is for work,
check with your IT team first. Keep a second key or a backup method in case one is lost.

## Technical specifications

| Item | Detail |
|---|---|
| Standards | FIDO2 / WebAuthn passkeys, FIDO U2F |
| Controller | STM32L442, Arm Cortex-M4, 80 MHz |
| Security | On-chip true random generator, AES hardware, flash read protection; optional secure element |
| Connector | USB-A, built into the board edge (no cable) |
| Speed | USB 2.0 Full-Speed |
| Confirm action | Physical touch button |
| Indicator | Status LED |
| Power | From USB, about 30 mA. No battery |
| Works with | Windows 10/11, macOS, Linux, Android, ChromeOS |
| Size | About 48 x 21 mm |
| In the box | 2-FA Key. A second key is recommended as a backup |

*Rev V1A. Specifications may change.*
