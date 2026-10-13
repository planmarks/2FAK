# Ed25519 (`ed25519-sk`, COSE alg -8) - implementation plan (Resident firmware)

## STATUS (2026-10): VALIDATED ON HARDWARE

`ed25519-sk` key generation **and** authentication tested working **locally and against
Cloudflare** - this exercises the full path (getInfo `-8`, makeCredential negotiation, OKP COSE
key, Ed25519 signing + the relying party verifying the signature). The build compiles, runs, and
interoperates. Still outstanding: a formal **FIDO conformance-suite re-run + metadata update**
for `-8`, and a maintainer **review of the vendored TweetNaCl** (see `crypto/tweetnacl/NOTE-2fak.md`).

### Original plan (for reference)

Done in-tree (Resident dir only; Non-Resident untouched):
- Vendored TweetNaCl (`crypto/tweetnacl/`, sha256 recorded in NOTE-2fak.md); build-wired in application.mk.
- `crypto.c/.h`: `crypto_ed25519_derive_pubkey` / `crypto_ed25519_sign` (seed = `generate_private_key`,
  injected into TweetNaCl keygen via `randombytes`); guarded `#ifndef IS_BOOTLOADER`.
- `cose_key.h`: OKP/EdDSA/Ed25519 constants. `ctap_add_cose_key`: OKP 4-entry key for EdDSA.
  `ctap_generate_cose_key`: EdDSA case.
- `CredentialId` carries `alg` (funded from `CREDENTIAL_RK_FLASH_PAD` 2->1, so struct size is
  UNCHANGED - no flash realignment). `make_auth_tag` covers `alg` (all call sites updated, incl u2f.c).
- makeCredential sets `id.alg`; getAssertion verifies tag incl alg and signs raw Ed25519 (no DER,
  no pre-hash) for EdDSA creds; credMgmt cose uses `rk.id.alg`; getInfo advertises -7 then -8;
  parser accepts -8.

NOT yet done (cannot run here - no host C compiler, only the ARM cross-toolchain):
- Build on the bench, flash, and functionally test (make an EdDSA cred, verify the OKP key +
  signature with python-fido2 / `cryptography`; `ssh-keygen -t ecdsa-sk` still works; then
  `ssh-keygen -t ed25519-sk -O resident`). Re-run FIDO conformance. Review the vendored TweetNaCl.

---


Grounded in the current code. Same derive-and-wrap model as the P-256 keys; the ATECC roots
the secret, all Ed25519 math runs in the MCU. Attestation stays ES256 (only the *credential*
key becomes Ed25519).

## Key finding: the derivation already fits

- `fido2/crypto.c: generate_private_key()` returns a 32-byte HMAC-SHA256(+AES) value. **Any
  32 bytes is a valid Ed25519 seed**, so no new derivation is needed - feed those 32 bytes to
  Ed25519 keygen.
- `fido2/ctap.c: ctap_generate_cose_key(cose, &id, len, type, COSEAlg)` **already takes the COSE
  alg** (makeCredential passes `credInfo->COSEAlgorithmIdentifier`). The resident path at
  ctap.c:1750 currently hardcodes `COSE_ALG_ES256` - that must pass the credential's real alg.

## Stage 0 - vendor the primitive (do NOT hand-write)

Add a reviewed, compact Ed25519 to `crypto/` (recommend **TweetNaCl** `tweetnacl.c/.h`, public
domain, ~1 file, includes Ed25519 + SHA-512; or orlp/ed25519). Expose two calls used by the
wrappers below:
- keypair-from-seed: 32-byte seed -> 32-byte public key (+ cached expanded key for signing)
- sign: (seed/expanded key, message) -> 64-byte signature
Flash cost ~5-10 KB (budget is ~1/3 of 256 KB used, fine). SHA-512 already exists (cifra
`cf_sha512`); TweetNaCl bundling its own is acceptable, or wire Ed25519 to the existing SHA-512.

## Stage 1 - crypto.c/.h wrappers

Mirror the P-256 helpers:
```c
// crypto.h
void crypto_ed25519_derive_pubkey(uint8_t *data, int len, uint8_t pubkey[32]);
void crypto_ed25519_sign(uint8_t *data, int len,
                         const uint8_t *msg, int msglen, uint8_t sig[64]);
```
Implementations call `generate_private_key(data,len,NULL,0,seed)` to get the 32-byte seed, then
the vendored keypair/sign. Wipe the seed after use.

## Stage 2 - carry the algorithm with the credential

getAssertion must know whether a credential is ES256 or EdDSA.
- **Non-resident:** encode alg in `CredentialId` (fido2/ctap.h:198). Add a `uint8_t alg;` field
  (the `tag` MAC already covers the whole struct, so it stays authenticated). Pre-launch, so the
  credential-ID format change is acceptable (reset clears old creds).
- **Resident:** store alg in the `CTAP_residentKey` record (ctap.h:215; it has spare room) so the
  on-device record is self-describing.
- Map `COSEAlgorithmIdentifier` -> {ES256=-7, EdDSA=-8}; default/reject anything else.

## Stage 3 - makeCredential

- Algorithm negotiation: when scanning `pubKeyCredParams`, accept **-8** as well as -7, honoring
  the RP's order of preference (currently only -7 is matched).
- `ctap_generate_cose_key()`: branch on alg -
  - ES256 (-7): existing EC2 key (kty=2, crv=P-256, x,y).
  - EdDSA (-8): **OKP** COSE key - `kty=1 (OKP)`, `alg=-8`, `crv=6 (Ed25519)`, `x = pubkey[32]`
    (no y). Derive pubkey via `crypto_ed25519_derive_pubkey`.
- Record the chosen alg into the credential ID / RK (Stage 2).

## Stage 4 - getAssertion

- Read the credential's alg (from CredentialId for non-resident, from the RK record for
  resident). Sign authData‖clientDataHash with `crypto_ed25519_sign` for -8, else the ES256 path.
- Assertion signature for EdDSA is the raw 64-byte Ed25519 signature (no DER), per WebAuthn.

## Stage 5 - getInfo

- Add `{alg: -8, type: "public-key"}` to the algorithms array (ctap.c:~416). **Only after Stages
  1-4 work** - never advertise what we can't do.

## Stage 6 - attestation (no change)

Packed / basic_full attestation keeps signing with the muru **ES256** batch key. The attestation
statement's `alg` stays -7; only the credential key is Ed25519. So no attestation changes.

## Stage 7 - test + conformance

- Unit: make an EdDSA credential, verify the OKP COSE key + a signature with a known verifier
  (python-fido2 / cryptography Ed25519).
- Re-run the FIDO conformance suite (new algorithm advertised).
- Confirm `ssh-keygen -t ed25519-sk -O resident` now works end to end.

## Open decisions

1. Vendored primitive: TweetNaCl (default) vs orlp/ed25519 vs another. Constant-time matters.
2. Default algorithm preference when an RP lists both -7 and -8: honor RP order (recommended);
   do not force one.
