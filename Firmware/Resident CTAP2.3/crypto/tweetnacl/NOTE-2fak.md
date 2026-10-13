# TweetNaCl (vendored) - provenance & review status

Vendored for the Ed25519 (`ed25519-sk`, COSE -8) feature in the Resident firmware.

- **Source:** https://raw.githubusercontent.com/sbp/tweetnacl-tools/master/tweetnacl.{c,h}
  (a mirror of the canonical TweetNaCl from https://tweetnacl.cr.yp.to/).
- **Files:** `tweetnacl.c` (16637 B), `tweetnacl.h` (20014 B).
- **SHA-256:**
  - tweetnacl.c `02e65bc3013ff2168983365e55906bc783c4c7e0a60d8100f17bb303a17175c4`
  - tweetnacl.h `43f29ad721d9927b747b0100ab4160c119e7bb180c7c98a66e4bf79d31244287`
- **License:** TweetNaCl is public domain.
- **Authenticity check (done):** the `.c` matches canonical TweetNaCl - `#define sv static void`,
  `typedef i64 gf[16]`, the Ed25519 constants `D/D2/X/Y/I`, and `sigma = "expand 32-byte k"` are
  the reference values. The 20 KB header is the normal generated all-primitives `tweetnacl.h`.

## What 2FAK uses from it

Only Ed25519: `crypto_sign_ed25519_tweet_keypair` (seed-based via an injected `randombytes`) and
`crypto_sign_ed25519_tweet` (deterministic signing), plus their internal SHA-512. All other NaCl
primitives are dropped at link time by `-ffunction-sections` + `-Wl,--gc-sections`.

The firmware must provide exactly one `randombytes()` (seed injection for keygen; Ed25519 signing
is deterministic and does not call it).

## REVIEW STATUS: pending owner sign-off

This is third-party code downloaded from the internet and integrated into a security product.
Before shipping: have a maintainer review/diff it against the canonical TweetNaCl release and
confirm the SHA-256s above. Build wiring and the `crypto_ed25519_*` wrappers were paused pending
that sign-off (see `../../ED25519_PLAN.md`).
