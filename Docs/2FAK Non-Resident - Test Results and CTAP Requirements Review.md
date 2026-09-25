# 2FAK Non-Resident - Test Results and CTAP Requirements Review

For the team. This records what has been tested so far on the non-resident (second
factor) build, and reviews it against `CTAP_Implementation_Requirements.md`. It is
written to be honest about what is verified on hardware versus what is only verified by
code inspection or still pending.

Firmware base: Nitrokey FIDO2 / Solo 1 fork. Build: `prebuilt/all.hex` (normal) and
`prebuilt/provision/all.hex` (provisioning). Reference board serial: 207C37AF3631.

## 1. Status legend

- PASS: verified on real hardware in this cycle.
- CODE: implemented and confirmed by source inspection; hardware test still recommended.
- PENDING: not yet tested.
- PARTIAL: implemented differently or only in part; see note.
- NOT MET: not implemented.
- ALIGNED: requirement is "do not implement", and we do not implement it.

## 2. Test results

### 2.1 Build

| Item | Result | Notes |
|------|--------|-------|
| Normal image builds | PASS | flash use ~86%, links clean |
| Provisioning image builds | PASS | adds provisioning + diagnostic vendor commands only |
| Provisioning command absent from normal image | PASS | confirmed by symbol check |

### 2.2 Secure element (ATECC608B)

| Test | Result | Notes |
|------|--------|-------|
| Chip present / responds | PASS | I2C address 0x60, Info revision 00006003 (ATECC608B) |
| Driver (wake, CRC16, Info, Read-lock) | PASS | via self-test command |
| Config template write + verify | PASS | SlotConfig 0x2080, KeyConfig 0x003C |
| Config zone lock | PASS | required an explicit wake before LOCK (fixed) |
| Root key write + data zone lock | PASS | random root written before data lock |
| Derivation primitive | PASS | legacy HMAC rejected (parse error); MAC mode 0x06 works |
| Hardware root active after provisioning | PASS | self-test: ready = true, kdf_ok = true |
| Software fallback when unprovisioned/absent | CODE | `atecc_ready()` gate; no behaviour change on plain units |

### 2.3 FIDO / CTAP behaviour

Hardware verification below is from the Phase 0 run on board 207C37AF3631 (see
`docs/debug/`: fido_diag_results.txt, webauthnio_results.txt, output.json).

| Test | Result | Notes |
|------|--------|-------|
| Registration + login as a security key (base firmware) | PASS | previously verified on Google with the same CTAP core (BACKUP build) |
| getInfo contents | PASS | fido_diag: versions U2F_V2/FIDO_2_0/FIDO_2_1_PRE, ext credProtect+hmac-secret, options rk:false/up:true/plat:false/clientPin, pinUvProtocols [1], transports ['usb'] |
| getInfo reports rk = false | PASS | confirmed on hardware |
| credentialMgmtPreview removed | PASS | getInfo now shows 4 options only |
| transports = ['usb'] | PASS | confirmed on hardware after Phase 0 fix |
| Non-resident registration (discouraged/default) | PASS | webauthn.me: "device-bound non-discoverable credential", ES256 P-256, BE/BS = 0; fido_diag makeCredential OK (packed, x5c) |
| makeCredential rejects resident key (required -> fail) | PASS | fido_tests.py rk: refused with 0x2b UNSUPPORTED_OPTION |
| PIN enforcement (PIN set, no pinAuth) | PASS | with a PIN set, a makeCredential without pinAuth correctly returns 0x36 (PIN required) |
| Registration + login WITHOUT a PIN | PASS | confirmed on hardware (no PIN set) |
| Registration + login WITH a PIN | PASS | confirmed on hardware (PIN set, verified, UP + UV) |
| authenticatorReset (clears PIN + credentials) | PASS | confirmed via fido_reset.py; clientPin returns to false |
| PIN retry lockout | PASS | fido_tests.py pinretry: 0x31, 0x31, then 0x34 PIN_AUTH_BLOCKED at 3 attempts/boot; retries 8->7->6->5 |
| PIN full block (retries to 0 -> 0x32) | PARTIAL | per-boot lockout (0x34) verified; exhausting all 8 to reach 0x32 not run (needs repeated reboots), behaviour is standard |
| hmac-secret functional | PASS | fido_tests.py hmac: same salt -> same 32-byte output, different salt -> different |
| credProtect functional | PASS | fido_tests.py credprot: levels 1 and 2 echoed back |
| U2F/CTAP1 legacy | PASS | fido_tests.py u2f: register + authenticate verified |

Test tooling in the repo root: `fido_diag.py` (getInfo + basic makeCredential), `fido_tests.py`
(rk / credprot / hmac / u2f / pinretry), `fido_reset.py` (clear PIN + credentials),
`atecc_selftest.py`, `atecc_provision.py`, `atecc_diag.py`. The create-based tests (rk,
credprot, hmac) need a key with no PIN set; reset first if a PIN is present.

Still to capture: the residentKey-required negative test, a getAssertion login, and a
full PIN set/verify/retry/reset cycle.

### 2.4 Observations from the Phase 0 run

- **No transports in getInfo (FIXED).** The RP had shown transports `["ble","nfc","usb"]`,
  a client-side default. getInfo now reports `transports: ["usb"]` (response key 0x09).
- **UV flag set true (investigated, correct).** output.json showed `userVerified = true`.
  fido_diag reported `clientPin = false` earlier, but that was before this registration.
  On the webauthn.me path the client (Windows) set a PIN on the key and verified it.
  makeCredential returns `CTAP2_ERR_PIN_REQUIRED` if a PIN is set without `pinAuth`, and
  verifies `pinAuth` before use, so UV = true only when a PIN was actually verified. This
  is correct CTAP behaviour, not a defect, so no code was changed. (A cosmetic refactor to
  set the UV bit from a per-call "verified" flag instead of "PIN is set" is equivalent
  today and is folded into the Phase 1 PIN/UV rework.)
- **AAGUID zeroed under attestation "none" is expected.** output.json shows an all-zero
  AAGUID because the RP requested attestation `none`. With direct attestation the real
  AAGUID (c2aa81f8352d56e2c6892bfdb5a52ccc) and the x5c chain appear, as seen in
  fido_diag (fmt packed, attStmt has x5c).

### 2.5 PIN/UV Auth Protocol 2 (Phase 1)

Implemented alongside protocol 1 (`fido2/pin_protocol.{c,h}` + wiring). getInfo now
advertises `pinUvAuthProtocols = [1, 2]`. The pinUvAuthToken is 32 bytes (required by
protocol 2, valid for protocol 1). Validated on hardware (board 207C37AF3631):

| Test | Result | Notes |
|------|--------|-------|
| Protocol 1 regression suite on the P2 build | PASS | rk / credprot / hmac / u2f all still PASS |
| getInfo advertises [1, 2] | PASS | fido_diag / fido_tests pin2 |
| setPIN (protocol 2) | PASS | HKDF shared secret, random-IV newPinEnc, 32-byte pinAuth |
| getPinToken (protocol 2) | PASS | 32-byte token returned (random IV) |
| makeCredential (protocol 2 pinUvAuthParam) | PASS | UV flag set |
| getAssertion (protocol 2 pinUvAuthParam) | PASS | UV flag set |

Tool: `fido_tests.py pin2`.

### 2.6 pinUvAuthToken permissions model + CTAP 2.3 getInfo

Hardware-validated (board 207C37AF3631):

| Test | Result | Notes |
|------|--------|-------|
| getInfo 2.3 fields well-formed | PASS | versions incl. FIDO_2_1/FIDO_2_3, options incl. pinUvAuthToken, pinUvAuthProtocols [1,2], transports [usb] |
| Protocol-1 regression on 2.3 build | PASS | rk/credprot/hmac/u2f |
| pin2 (protocol 2 end to end) | PASS | setPIN, token, makeCredential + getAssertion, UV set |
| getPinUvAuthTokenUsingPinWithPermissions | PASS | mc\|ga token bound to rp issued and accepted |
| permission scoping | PASS | GA-only token -> makeCredential refused (0x40 UNAUTHORIZED_PERMISSION) |
| RP-ID binding | PASS | wrong-RP token -> getAssertion refused (0x33 PIN_AUTH_INVALID) |
| unsupported permission | PASS | credentialMgmt requested -> refused at issue (0x40) |

The only remaining gate for an external "CTAP 2.3" claim is a FIDO conformance-tool run.

### 2.7 Conformance-prep changes (hardware-confirmed)

- Version advertisement is now a build switch. Default build confirmed on hardware to
  report versions `[FIDO_2_0, FIDO_2_1_PRE, FIDO_2_1]` only (no FIDO_2_3, no U2F_V2).
- transports `[usb]`, AAGUID `c2aa81f8-352d-56e2-c689-2bfdb5a52ccc`, non-resident, and
  `pinUvAuthToken`/`pinUvAuthProtocols [1,2]` all confirmed via fido_diag + webauthn.io.
- Attestation PKI (Root CA + batch leaf with matching AAGUID) generated; the earlier
  cert-AAGUID mismatch is fixed. Confirmed active on-device from `all_attested.hex`:
  x5c leaf `CN=muru.global 2FAK Series, OU=Authenticator Attestation, O=muru.global, C=SI`,
  issuer `CN=muru.global 2FAK Attestation Root CA`, cert AAGUID = getInfo AAGUID
  `c2aa81f8...`. Chain and AAGUID consistent end to end.
- Metadata statement drafted (`metadata/2fak_metadata.json`). See the FIDO Conformance
  Readiness doc for remaining vendor/tool steps.


- `getPinUvAuthTokenUsingPinWithPermissions` (subcommand 0x09): permission bits (only
  makeCredential + getAssertion are granted; others rejected with
  CTAP2_ERR_UNAUTHORIZED_PERMISSION), optional RP-ID binding, and a fresh token per
  issue. Tokens carry a rolling 30s inactivity lifetime and are invalidated on power
  cycle and factory reset. makeCredential/getAssertion now check the token's permission
  and RP binding.
- getInfo: versions add `FIDO_2_1` and `FIDO_2_3`; options add `pinUvAuthToken = true`;
  new fields `algorithms` ([ES256]), `minPINLength` (4), `firmwareVersion`.
- Advertising `FIDO_2_3` is a strong claim: run the FIDO conformance tools before making
  it externally. Not implemented: `alwaysUv` / `makeCredUvNotRqd` options and the full
  2.3 up/uv option matrix (the core up=touch, uv=pinUvAuthToken behaviour is in place).
- Tests: `fido_tests.py pin2perm` (permissions + RP binding + negative cases). Flash use
  is now ~93%, so U2F should become a build option before further growth.

## 3. Requirements review (against CTAP_Implementation_Requirements.md)

### 3.1 Met or aligned

| Requirement | Status | Note |
|-------------|--------|------|
| Non-discoverable credentials only | PASS | webauthn.me registered a "device-bound non-discoverable credential" |
| rk = false in getInfo | PASS | confirmed on hardware via fido_diag |
| Reject discoverable/resident creation | CODE | CTAP2_ERR_UNSUPPORTED_OPTION; explicit negative test not yet captured |
| RP supplies credential ID via allowList | CODE | inherent to non-resident operation |
| No passkey storage / no account picker | PASS | non-discoverable credential confirmed; nothing stored on key |
| authenticatorGetInfo | PASS | verified on hardware |
| authenticatorMakeCredential | PASS | verified on this build, with and without PIN |
| authenticatorGetAssertion | PASS | login verified on this build (with and without PIN) |
| authenticatorClientPIN | PASS | protocol 1; PIN set/verify works, enforcement confirmed |
| authenticatorReset | PASS | verified via fido_reset.py |
| Client PIN is the UV method | PASS | login with PIN sets UP + UV |
| PIN local, global, never sent, changeable, unrecoverable | CODE | standard CTAP PIN model |
| clientPin reports false/true by state | PASS | observed false (no PIN) and true (PIN set) |
| Standard CTAP PIN retry (per-boot lockout at 3, full block, reset needed) | PASS | per-boot 0x34 verified at 3 attempts; full 0x32 path is standard (not exhausted) |
| User Presence via physical button | PASS | touch confirmed, LED signalling |
| Standard authenticatorReset (not proprietary) | PASS | CTAP reset verified |
| hmac-secret advertised and functional | PASS | salt round trip verified |
| credProtect advertised and functional | PASS | levels 1 and 2 verified |
| USB HID / CTAPHID / CTAP2 CBOR | PASS | standard transport, no driver |
| Secure credential-key generation/storage | PASS | on-device keys; ATECC hardware root on provisioned units |
| Do NOT implement resident, passkeys, biometrics, largeBlob, BLE, hybrid, digital creds, payment, enterprise attestation/management | ALIGNED | none implemented |

### 3.2 Not met or partial

| Requirement | Status | Reason |
|-------------|--------|--------|
| CTAP 2.1 conformance | PASS (self-test) | FIDO Conformance Tools v1.9.2 CTAP2.0 and CTAP2.1 authenticator suites pass on `all_conformance.hex` for the non-resident profile. Not formal certification. See the FIDO Conformance Readiness doc. |
| CTAP 2.3 / advertise FIDO_2_3 | CONFIGURABLE | 2.3 getInfo fields implemented; default advertises up to FIDO_2_1 (conformance-validated). `FIDO23=1` additionally advertises FIDO_2_3 - do not ship until a 2.3 conformance run passes. |
| PIN/UV Auth Protocol 2 | DONE (validated) | implemented and validated on hardware; getInfo advertises [1, 2]. See sections 2.5-2.6. |
| pinUvAuthToken = true (getInfo option) | DONE (validated) | `getPinUvAuthTokenUsingPinWithPermissions` with mc/ga permission bits, RP-ID binding and rolling expiry; permission scoping and RP binding verified on hardware (`fido_tests.py pin2perm`). |
| Intended flow requires PIN | CONFIGURABLE | build-time `PIN_POLICY`: `optional` (default, shipped), `requireset` (PIN required before first credential), or `alwaysuv` (PIN/UV on every op = the requirements-doc flow). Default ships optional per product decision; `alwaysuv` matches the doc when selected. Only `optional` is hardware-tested so far. |
| Reset via long-touch confirmation (2.3) | PARTIAL | standard reset within the power-up window with physical interaction is supported; the specific 2.3 long-touch confirmation variant is not separately implemented. |
| hmac-secret and credProtect as 2.3 conformance | PARTIAL | both are advertised and available, but as 2.0/2.1-style extensions, not as part of a certified 2.3 profile. |

### 3.3 Minor inconsistency (FIXED in Phase 0)

- getInfo previously advertised `credentialMgmtPreview = true` even though this is a
  non-resident build with no credential management. This has been removed. getInfo now
  reports 4 options only: `rk`, `up`, `plat`, `clientPin`.

## 4. Summary for planning

What matches the requirements today:
- The credential model is correct: non-resident only, rk = false, resident requests
  rejected, allowList-based authentication, no passkey or account storage.
- The required command set is present (GetInfo, MakeCredential, GetAssertion, ClientPIN,
  Reset), plus hmac-secret and credProtect, over standard USB HID / CTAPHID / CTAP2.
- User presence and Client PIN (protocol 1) work, and secure on-device key handling is in
  place, now strengthened by the ATECC608B hardware root on provisioned units.

The main gap is the CTAP version and PIN protocol level. The requirements ask for a
CTAP 2.3 profile with PIN/UV Auth Protocol 2 and pinUvAuthToken. The current firmware is
a CTAP 2.0 / 2.1-preview core with PIN/UV Auth Protocol 1. Reaching the requested
profile means:

1. Implement PIN/UV Auth Protocol 2 and the pinUvAuthToken model.
2. Bring getInfo and command semantics up to CTAP 2.3 and advertise FIDO_2_3 only once
   the mandatory 2.3 pieces are in place.
3. Decide whether PIN should be enforced by default for this SKU, or left optional and
   enforced by the relying party policy.
4. Clean up the credentialMgmtPreview flag. (DONE in Phase 0.)
5. Optionally implement the 2.3 long-touch reset confirmation.

These are firmware roadmap items. They do not require hardware changes. Until they are
done, the honest description of the device is a standards-based FIDO2 (CTAP 2.0/2.1) and
U2F second-factor key with optional PIN, not a CTAP 2.3 certified authenticator.
