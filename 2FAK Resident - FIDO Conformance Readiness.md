# 2FAK Resident - FIDO Conformance Readiness

Status of the **resident (passkey)** firmware against the FIDO Alliance Conformance Testing
Tools and the Metadata Statement spec (v3.0). For the team.

## STATUS: CTAP2.0, CTAP2.1 and CTAP2.3 authenticator tests PASS

The passkey build (`RESIDENT=1 FIDO23=1`, plus the conformance test image) passes the FIDO
Conformance Tools CTAP2.0, CTAP2.1 **and** CTAP2.3 authenticator suites, together with its
metadata statement. This is **self-test validation, not formal FIDO Certification.**

Results (self-test, all zero failures):

| Suite | Result |
|-------|--------|
| CTAP2.0 | 128 passed / 0 failed |
| CTAP2.1 | 139 passed / 0 failed |
| CTAP2.3 | 180 passed / 0 failed |

The last full run was verified on hardware.

## What the tools check

1. **CTAP2 authenticator conformance** - the device is tested against the CTAP spec up to the
   highest version it advertises in getInfo (`FIDO_2_3` for this build).
2. **Metadata Statement validation** - the statement must be well-formed and its claims
   (versions, options, algorithms, attestation, key protection, AAGUID) must match the
   device's getInfo, and device attestation must chain to the declared
   `attestationRootCertificates`.

Formal certification and Metadata Service (MDS) listing are a separate, paid FIDO process.

## Test modules selected (passkey profile)

Because this build advertises `rk = true` and `credMgmt = true`, the resident-key and
credential-management modules are in scope and are exercised:

- Transports, Generic
- MakeCredential (Request + Response), GetAssertion (Request + Response)
- Reset
- Discoverable Credentials (Resident Key)
- Extensions: HMAC-Secret (incl. strict PUAT2), CredProtect, MinPinLength
- ClientPIN protocol 1 and protocol 2
- Credential Management API (metadata, enumerate RPs, enumerate credentials, update, delete)
- Metadata tests

Not selected / not applicable (not advertised by this SKU): Enterprise Attestation,
Authenticator Config, Biometric Enrollment, Large Blobs.

## Metadata alignment

The metadata statement (`metadata/2fak_metadata.json`) is generated to match the device
getInfo exactly:

- `versions`: `FIDO_2_0`, `FIDO_2_1_PRE`, `FIDO_2_1`, `FIDO_2_3`; `upv` includes `{1,0}`,
  `{1,1}`, `{1,3}`.
- `options`: `rk = true`, `up = true`, `plat = false`, `credMgmt = true`, `clientPin = false`
  (fresh device), `pinUvAuthToken = true`.
- `authenticationAlgorithms`: `secp256r1_ecdsa_sha256_raw`; `attestationTypes`: `basic_full`;
  attestation chains to the muru.global Root CA embedded in the statement.

## Notable fixes made to reach a clean pass

- Advertise `FIDO_2_3` and add `{1,3}` to metadata `upv` for the 2.3 profile.
- Enable resident keys + credential management (rk storage, `credMgmt` option, the `cm`
  pinUvAuthToken permission).
- Implement `updateUserInformation` (credential management 0x07).
- A **deleted discoverable credential must not authenticate** via an allow-list getAssertion:
  discoverable credentials are flagged in the (MAC-covered) credential ID and require a live
  resident record, so a deleted passkey returns `NO_CREDENTIALS`.
- Return `PIN_AUTH_INVALID` (not `UNAUTHORIZED_PERMISSION`) when a *presented* pinUvAuthToken
  lacks the permission an operation needs (mc/ga/cm).
- Clear the per-boot PIN lockout on `authenticatorReset` (the tool resets between modules
  instead of power-cycling).
- Emit a KEEPALIVE before a CANCEL can be observed (HID keepalive/cancel test).

## Test vs production image

Conformance is run with a **conformance build** (`CONFORMANCE=1`) that relaxes two
test-hostile behaviours so the tools can run unattended: user presence is auto-approved after
a short keepalive window, and `authenticatorReset` is allowed at any time (not just within
the first 10 s of power-up). **This image is for testing only and must not ship.** Production
units run the normal image, which requires a real button touch and keeps the reset window.

## Not claimed

- Not FIDO Certified (self-test only).
- Not listed in the FIDO Metadata Service.
- Formal certification / MDS listing is the separate, paid FIDO process, planned for later.

## Reproduce

1. Build the conformance image: `RESIDENT=1 FIDO23=1 CONFORMANCE=1 bash build.sh`, then run
   `provision_attestation.py` so the device presents the muru attestation.
2. Flash the resulting image; load `metadata/2fak_metadata.json` into the tool's metadata
   field.
3. In the FIDO Conformance Tools, select the passkey-profile modules listed above (leave
   Enterprise Attestation, Authenticator Config, Biometric Enrollment and Large Blobs
   unselected).
4. Run each of the CTAP2.0, CTAP2.1 and CTAP2.3 suites.
