# 2FAK Non-Resident - CTAP 2.3 Upgrade Plan

Ordered work plan to move the current firmware (CTAP 2.0 / 2.1-preview, PIN Protocol 1)
to the profile requested in `CTAP_Implementation_Requirements.md` (CTAP 2.3, PIN/UV Auth
Protocol 2, optional PIN enforcement). All items are firmware only. No hardware change is
needed.

Effort is in developer-days for one engineer already familiar with embedded C and FIDO2.
Ranges are estimates, not commitments.

## Constraints to keep in mind

- Flash budget: [DONE] CTAP1/U2F is now a build option, OFF by default (`U2F=1` to
  include it). Default build is ~91% flash (~6 KB free); `U2F=1` is ~93%. Track flash
  after each phase; further relief would come from trimming unused Solo vendor features.
- Sequencing rule: do not advertise `FIDO_2_3` until Protocol 2 and the pinUvAuthToken
  model are in and tested. Advertising 2.3 early makes the device non-conformant.
- The base is Solo 1 (C). Some 2.1/2.3 work was only ever done in Solo 2 (Rust) and
  cannot be copied over, so parts of this are new code.

## Phase 0 - Cleanup and test harness (quick, do first)

Goal: fix the loose ends and get a repeatable test setup before the big changes.

- Set `credentialMgmtPreview` to false / remove it from getInfo (non-resident profile).
- Confirm the non-resident basics on hardware: `fido2-token -I`, webauthn.io round trip
  ("discouraged" should pass, "required" should fail), one PIN set/verify cycle.
- Stand up the FIDO conformance test tools as the acceptance gate for later phases.

Effort: 1 to 2 days.
Depends on: nothing.

## Phase 1 - PIN/UV Auth Protocol 2 and pinUvAuthToken (the main work)

Goal: add Protocol 2 alongside the existing Protocol 1, and add the token model.

Progress:

- [DONE] Protocol primitives module `fido2/pin_protocol.{c,h}` (added to the build,
  compiles). Provides, for protocol 1 and 2:
  - `pin_protocol_shared_secret` - protocol 1 = SHA-256(Z); protocol 2 = HKDF-SHA-256(Z)
    into HMAC-key(32) || AES-key(32).
  - `pin_protocol_encrypt` / `pin_protocol_decrypt` - protocol 1 = AES-256-CBC IV 0;
    protocol 2 = random 16-byte IV prepended, AES-256-CBC with the AES-key.
  - `pin_protocol_verify` - HMAC-SHA-256; 16-byte compare for protocol 1, 32 for 2.
  Protocol 1 paths are byte-for-byte equivalent to the original inline code, so this is
  additive and cannot regress the validated protocol-1 flows.

- [DONE, validated on hardware] Wiring for protocol 2, end to end (fido_tests.py pin2:
  setPIN, getPinToken, makeCredential, getAssertion all pass with UV; protocol-1
  regression suite still green):
  - `pinAuth[16] -> [32]` plus a length field in the makeCredential / getAssertion /
    clientPin structs (`ctap.h`); `ctap_parse.c` now copies the real length via a new
    `parse_var_byte_string` and keeps `pinHashEncSize`.
  - ClientPIN setPIN / changePIN / getPINToken routed through `pin_protocol` by protocol;
    getKeyAgreement is unchanged (protocol-agnostic). Token is returned with a random IV
    under protocol 2.
  - makeCredential / getAssertion pinUvAuthParam verification is protocol-aware
    (`verify_pin_auth(protocol, ...)`).
  - getInfo advertises `pinUvAuthProtocols = [1, 2]` (protocol 1 first, so existing
    clients keep the validated path; protocol 2 is selectable).
  - Builds clean. Flash use rose to ~92% (63.8 KB / 68 KB), so later phases will likely
    need U2F to become a build option.
  - Test with `fido_tests.py pin2` (protocol 2 end to end) and re-run the protocol-1
    suite for regression. Protocol 1 code paths are unchanged in behaviour.

- [DONE, validated on hardware] Follow-on: the pinUvAuthToken permissions model
  (`getPinUvAuthTokenUsingPinWithPermissions`, permission bits mc/ga, RP-ID binding,
  rolling 30s expiry, power-cycle/reset invalidation). getInfo advertises
  `pinUvAuthToken = true`. `fido_tests.py pin2perm`: permission scoping (0x40),
  RP binding (0x33), and unsupported-permission refusal all pass.

Notes: no new crypto beyond `pin_protocol`. Each pass must be hardware-tested for BOTH
protocol 1 (regression) and protocol 2 (new).

Effort: 8 to 15 days.
Depends on: Phase 0.

## Phase 2 - getInfo and command semantics to 2.3, then advertise FIDO_2_3

Goal: bring the reported profile and command behaviour up to 2.3.

- [DONE] getInfo: versions add `FIDO_2_1` and `FIDO_2_3`; `pinUvAuthProtocols = [1, 2]`;
  options add `pinUvAuthToken = true`; new fields `algorithms` ([ES256]), `minPINLength`
  (4), `firmwareVersion`. `transports`, `maxCredentialCountInList` and
  `maxCredentialIdLength` were already present.
- [DONE] MakeCredential / GetAssertion: permission checks via the token model; `up` option
  rejected in makeCredential; correct error codes (PIN_REQUIRED, PIN_TOKEN_EXPIRED,
  UNAUTHORIZED_PERMISSION).
- [PARTIAL] up/uv option matrix: core behaviour (up = touch, uv = pinUvAuthToken) is in;
  `alwaysUv` / `makeCredUvNotRqd` not implemented.
- [DONE] credProtect enforced (levels 1/2 verified in Phase 0); hmac-secret re-verified.
- `FIDO_2_3` is now advertised. Run the FIDO conformance tools before any external "2.3"
  claim - that is the remaining gate for this phase.

Effort: mostly done; remaining is conformance-tool validation and the optional up/uv
options. Depends on: Phase 1.

## Phase 3 - PIN enforcement policy (product decision)

[DONE] Implemented as a build-time switch, `PIN_POLICY`, so the SKU behaviour can change
without code changes. Default is optional.

- `optional` (default): relying party decides via userVerification. Current behaviour.
- `requireset` (`PIN_POLICY=requireset`): a PIN must be set before the first credential;
  makeCredential returns CTAP2_ERR_PIN_REQUIRED when no PIN is set. Not `alwaysUv`, so a
  relying party can still do touch-only getAssertion.
- `alwaysuv` (`PIN_POLICY=alwaysuv`): advertises `alwaysUv = true` and requires a
  pinUvAuthToken for every makeCredential and getAssertion (the requirements-doc flow:
  password, insert, PIN, touch).

All three modes compile. Only `optional` (the shipped default) is hardware-tested;
`requireset` / `alwaysuv` should get a hardware pass before a SKU ships with them.
Still optional: the 2.3 long-touch reset confirmation.

Depends on: Phase 1 (uses the token model to enforce UV).

## Phase 4 - Conformance and interoperability validation

Goal: prove it before release.

- Run the FIDO conformance test tools for the CTAP 2.3 authenticator profile and fix
  findings.
- Interop pass: Chrome, Edge, Firefox, Safari; Windows and macOS security-key management;
  webauthn.io; the main services the product targets.
- Regression pass on the non-resident behaviour and the ATECC hardware-root path.
- Re-check flash usage against budget.

Effort: 4 to 8 days plus iteration.
Depends on: Phases 1 to 3.

## Rough total

About 4 to 6 weeks of focused work for one experienced engineer, plus a buffer for
conformance iteration. Phase 1 is the largest and riskiest part.

## Out of scope here

- FIDO Certification itself (a separate, paid process). The free conformance test tools
  can be used for self-testing without formal certification.
- Official USB VID/PID and AAGUID allocation (needed before public release, tracked
  separately).
- RDP level 2 production build and verifying bootloader (separate hardening track).
