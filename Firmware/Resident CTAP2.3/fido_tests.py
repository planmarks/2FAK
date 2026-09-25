"""
2FA Key - extended CTAP test runner.

Covers the checks that fido_diag.py does not:
  rk        - residentKey-required negative test (must be refused)
  credprot  - credProtect extension functional test (set level, read it back)
  hmac      - hmac-secret functional test (salt round trip, determinism)
  u2f       - CTAP1 / U2F legacy register + authenticate
  pinretry  - PIN retry counter decrement and lockout  (DESTRUCTIVE: consumes retries)

Run from an ELEVATED terminal.  Needs: python -m pip install fido2
(fido2 pulls in the 'cryptography' package, which this script also uses.)

Usage:
  python fido_tests.py                 # runs the safe tests: rk, credprot, hmac, u2f
  python fido_tests.py rk credprot     # run only the named tests
  python fido_tests.py pinretry        # run the destructive PIN-retry test on its own
  python fido_tests.py all             # safe tests + pinretry

Notes:
  - The create-based tests (rk, credprot, hmac) need a key with NO PIN set, because
    makeCredential requires PIN proof once a PIN exists. If a PIN is set, reset first
    with fido_reset.py, or run only u2f / pinretry.
  - Touch the key when it blinks. Several tests need more than one touch.
"""
import sys, os, hashlib, hmac as hmaclib

from fido2.hid import CtapHidDevice
from fido2.ctap import CtapError
from fido2.ctap2 import Ctap2
from fido2.ctap2.pin import ClientPin, PinProtocolV1, PinProtocolV2
from fido2.ctap1 import Ctap1

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

RP = {"id": "muru.test", "name": "muru test"}
USER = {"id": b"\x01\x02\x03\x04\x05\x06\x07\x08", "name": "tester", "displayName": "Tester"}
PARAMS = [{"type": "public-key", "alg": -7}]

GREEN = "PASS"; RED = "FAIL"; SKIP = "SKIP"


def get_device():
    devs = list(CtapHidDevice.list_devices())
    if not devs:
        print("No FIDO HID device. Elevate the terminal and plug the key in.")
        sys.exit(1)
    dev = devs[0]
    print("product:", getattr(dev, "product_name", "?"),
          "| serial:", getattr(dev, "serial_number", "?"))
    return dev


def pin_is_set(ctap):
    return bool(ctap.get_info().options.get("clientPin"))


# ---------- rk negative ----------
def test_rk(dev):
    print("\n== rk: residentKey-required must be refused ==")
    ctap = Ctap2(dev)
    if pin_is_set(ctap):
        print(SKIP, "- a PIN is set; reset first (makeCredential needs PIN proof).")
        return None
    print(">> TOUCH the key...")
    try:
        ctap.make_credential(os.urandom(32), RP, USER, PARAMS, options={"rk": True})
        print(RED, "- device accepted a resident credential (should have refused)")
        return False
    except CtapError as e:
        if e.code == CtapError.ERR.UNSUPPORTED_OPTION:
            print(GREEN, "- refused with CTAP2_ERR_UNSUPPORTED_OPTION (0x2b)")
            return True
        print(RED, "- refused, but with 0x%02x (%s)" % (e.code, e.code))
        return False


# ---------- credProtect ----------
def test_credprotect(dev):
    print("\n== credprot: credProtect level is honoured ==")
    ctap = Ctap2(dev)
    if pin_is_set(ctap):
        print(SKIP, "- a PIN is set; reset first.")
        return None
    ok = True
    for level in (1, 2):
        print(">> TOUCH the key (credProtect=%d)..." % level)
        try:
            att = ctap.make_credential(os.urandom(32), RP, USER, PARAMS,
                                       extensions={"credProtect": level})
            got = att.auth_data.extensions.get("credProtect") if att.auth_data.extensions else None
            if got == level:
                print(GREEN, "- level %d echoed back in authData extensions" % level)
            else:
                print(RED, "- requested %d, got %r" % (level, got)); ok = False
        except CtapError as e:
            print(RED, "- error 0x%02x (%s)" % (e.code, e.code)); ok = False
    return ok


# ---------- hmac-secret ----------
def _aes_cbc(key, data, decrypt=False):
    c = Cipher(algorithms.AES(key), modes.CBC(b"\x00" * 16))
    op = c.decryptor() if decrypt else c.encryptor()
    return op.update(data) + op.finalize()


def _shared_secret(ctap):
    # getKeyAgreement (PIN protocol 1, subcommand 2)
    resp = ctap.client_pin(1, 2)
    peer = resp[1]
    peer_x = int.from_bytes(peer[-2], "big")
    peer_y = int.from_bytes(peer[-3], "big")
    peer_pub = ec.EllipticCurvePublicNumbers(peer_x, peer_y, ec.SECP256R1()).public_key()
    priv = ec.generate_private_key(ec.SECP256R1())
    z = priv.exchange(ec.ECDH(), peer_pub)
    secret = hashlib.sha256(z).digest()
    n = priv.public_key().public_numbers()
    my_cose = {1: 2, 3: -25, -1: 1,
               -2: n.x.to_bytes(32, "big"), -3: n.y.to_bytes(32, "big")}
    return secret, my_cose


def _hmac_get(ctap, cred_id, secret, my_cose, salt):
    salt_enc = _aes_cbc(secret, salt)
    salt_auth = hmaclib.new(secret, salt_enc, hashlib.sha256).digest()[:16]
    ext = {"hmac-secret": {1: my_cose, 2: salt_enc, 3: salt_auth}}
    assertion = ctap.get_assertion(
        RP["id"], os.urandom(32),
        allow_list=[{"type": "public-key", "id": cred_id}],
        extensions=ext)
    out_enc = assertion.auth_data.extensions["hmac-secret"]
    return _aes_cbc(secret, out_enc, decrypt=True)


def test_hmac(dev):
    print("\n== hmac: hmac-secret salt round trip ==")
    ctap = Ctap2(dev)
    if "hmac-secret" not in (ctap.get_info().extensions or []):
        print(RED, "- hmac-secret not advertised"); return False
    if pin_is_set(ctap):
        print(SKIP, "- a PIN is set; reset first.")
        return None
    print(">> TOUCH the key (create hmac-secret credential)...")
    try:
        att = ctap.make_credential(os.urandom(32), RP, USER, PARAMS,
                                   extensions={"hmac-secret": True})
    except CtapError as e:
        print(RED, "- makeCredential error 0x%02x (%s)" % (e.code, e.code)); return False
    if not (att.auth_data.extensions or {}).get("hmac-secret"):
        print(RED, "- credential not created with hmac-secret"); return False
    cred_id = att.auth_data.credential_data.credential_id

    salt_a = b"\xA1" * 32
    salt_b = b"\xB2" * 32
    secret, my_cose = _shared_secret(ctap)
    print(">> TOUCH the key (assertion 1, salt A)...")
    out_a1 = _hmac_get(ctap, cred_id, secret, my_cose, salt_a)
    secret, my_cose = _shared_secret(ctap)
    print(">> TOUCH the key (assertion 2, salt A again)...")
    out_a2 = _hmac_get(ctap, cred_id, secret, my_cose, salt_a)
    secret, my_cose = _shared_secret(ctap)
    print(">> TOUCH the key (assertion 3, salt B)...")
    out_b = _hmac_get(ctap, cred_id, secret, my_cose, salt_b)

    ok = True
    if len(out_a1) != 32:
        print(RED, "- output not 32 bytes"); ok = False
    if out_a1 != out_a2:
        print(RED, "- same salt gave different outputs (not deterministic)"); ok = False
    else:
        print(GREEN, "- same salt -> same 32-byte output (deterministic)")
    if out_a1 == out_b:
        print(RED, "- different salts gave the same output"); ok = False
    else:
        print(GREEN, "- different salt -> different output")
    return ok


# ---------- U2F / CTAP1 ----------
def test_u2f(dev):
    print("\n== u2f: CTAP1 / U2F legacy register + authenticate ==")
    # U2F is a build option (off by default to save flash). If not advertised, skip.
    if "U2F_V2" not in (Ctap2(dev).get_info().versions or []):
        print(SKIP, "- U2F not built in (default build; rebuild with U2F=1 to include it)")
        return None
    try:
        c1 = Ctap1(dev)
        ver = c1.get_version()
        print("   version:", ver)
        app = hashlib.sha256(b"https://muru.test").digest()
        chal = hashlib.sha256(b"challenge").digest()
        print(">> TOUCH the key (U2F register)...")
        reg = c1.register(chal, app)
        reg.verify(app, chal)
        print(">> TOUCH the key (U2F authenticate)...")
        auth = c1.authenticate(chal, app, reg.key_handle)
        auth.verify(app, chal, reg.public_key)
        print(GREEN, "- U2F register + authenticate verified")
        return True
    except CtapError as e:
        print(RED, "- CTAP error 0x%02x (%s)" % (e.code, e.code)); return False
    except Exception as e:
        print(RED, "- %r" % e); return False


# ---------- PIN retry (destructive) ----------
def test_pinretry(dev):
    print("\n== pinretry: retry counter decrement and lockout (DESTRUCTIVE) ==")
    ctap = Ctap2(dev)
    cp = ClientPin(ctap, PinProtocolV1())   # device supports PIN protocol 1 only
    test_pin = "246810"
    if not pin_is_set(ctap):
        print("   no PIN set; setting a temporary test PIN:", test_pin)
        cp.set_pin(test_pin)
    else:
        print("   a PIN is already set. This test will spend retries with WRONG guesses")
        print("   and may block the key (needs a factory reset afterwards).")
    if input('   Type "RETRY" to proceed: ').strip() != "RETRY":
        print(SKIP); return None

    def retries():
        r = cp.get_pin_retries()
        return r[0] if isinstance(r, (tuple, list)) else r

    print("   retries before:", retries())
    seen_lock = False
    for i in range(1, 9):
        try:
            cp.get_pin_token("00000000")   # deliberately wrong
            print(RED, "- wrong PIN was accepted"); return False
        except CtapError as e:
            left = None
            try: left = retries()
            except CtapError: left = "?"
            print("   attempt %d: 0x%02x (%s), retries left: %s" % (i, e.code, e.code, left))
            if e.code == CtapError.ERR.PIN_AUTH_BLOCKED:   # 0x34, per power-cycle
                print(GREEN, "- PIN_AUTH_BLOCKED after repeated wrong attempts (unplug/replug to continue)")
                seen_lock = True; break
            if e.code == CtapError.ERR.PIN_BLOCKED:        # 0x32, needs factory reset
                print(GREEN, "- PIN_BLOCKED: key must be factory reset")
                seen_lock = True; break
    if not seen_lock:
        print(RED, "- did not observe a lockout")
    print("   >>> Run fido_reset.py to clear the PIN/lockout when done.")
    return seen_lock


# ---------- PIN/UV Auth Protocol 2 end to end ----------
def test_pin2(dev):
    print("\n== pin2: PIN/UV Auth Protocol 2 (set PIN, token, makeCredential, getAssertion) ==")
    ctap = Ctap2(dev)
    protos = ctap.get_info().pin_uv_protocols or []
    print("   advertised pinUvAuthProtocols:", list(protos))
    if 2 not in protos:
        print(RED, "- protocol 2 not advertised"); return False
    if pin_is_set(ctap):
        print(SKIP, "- a PIN is set; reset first (this test sets its own PIN).")
        return None

    PIN = "246810"
    cp = ClientPin(ctap, PinProtocolV2())
    proto = PinProtocolV2()
    try:
        cp.set_pin(PIN)
        print(GREEN, "- set_pin (protocol 2) OK")
        token = cp.get_pin_token(PIN)
        print(GREEN, "- get_pin_token (protocol 2) OK")
    except CtapError as e:
        print(RED, "- ClientPIN v2 error 0x%02x (%s)" % (e.code, e.code)); return False

    ok = True
    # makeCredential with a protocol-2 pinUvAuthParam
    cdh = os.urandom(32)
    param = proto.authenticate(token, cdh)
    print(">> TOUCH the key (makeCredential, protocol 2)...")
    try:
        att = ctap.make_credential(cdh, RP, USER, PARAMS, pin_uv_param=param, pin_uv_protocol=2)
        uv = att.auth_data.flags & 0x04
        print(GREEN if uv else RED, "- makeCredential OK, UV flag %s" % ("set" if uv else "NOT set"))
        ok = ok and bool(uv)
    except CtapError as e:
        print(RED, "- makeCredential error 0x%02x (%s)" % (e.code, e.code)); return False

    # getAssertion with a protocol-2 pinUvAuthParam
    cred_id = att.auth_data.credential_data.credential_id
    cdh2 = os.urandom(32)
    param2 = proto.authenticate(token, cdh2)
    print(">> TOUCH the key (getAssertion, protocol 2)...")
    try:
        assertion = ctap.get_assertion(RP["id"], cdh2,
                                       allow_list=[{"type": "public-key", "id": cred_id}],
                                       pin_uv_param=param2, pin_uv_protocol=2)
        uv = assertion.auth_data.flags & 0x04
        print(GREEN if uv else RED, "- getAssertion OK, UV flag %s" % ("set" if uv else "NOT set"))
        ok = ok and bool(uv)
    except CtapError as e:
        print(RED, "- getAssertion error 0x%02x (%s)" % (e.code, e.code)); return False

    print("   >>> Run fido_reset.py to clear the test PIN when done.")
    return ok


# ---------- pinUvAuthToken permissions model (getPinUvAuthTokenUsingPinWithPermissions) ----------
def test_pin2perm(dev):
    print("\n== pin2perm: pinUvAuthToken permissions + RP binding (subcommand 0x09) ==")
    ctap = Ctap2(dev)
    info = ctap.get_info()
    if not info.options.get("pinUvAuthToken"):
        print(RED, "- pinUvAuthToken option not advertised"); return False
    if pin_is_set(ctap):
        print(SKIP, "- a PIN is set; reset first (this test sets its own PIN).")
        return None

    PIN = "246810"
    PERM = ClientPin.PERMISSION
    proto = PinProtocolV2()
    cp = ClientPin(ctap, PinProtocolV2())
    try:
        cp.set_pin(PIN)
    except CtapError as e:
        print(RED, "- set_pin error 0x%02x" % e.code); return False

    ok = True

    # 1) token with mc+ga bound to muru.test: MC then GA must work
    try:
        tok = cp.get_pin_token(PIN, PERM.MAKE_CREDENTIAL | PERM.GET_ASSERTION, RP["id"])
        print(GREEN, "- getPinUvAuthTokenUsingPinWithPermissions (mc|ga, rp=%s) OK" % RP["id"])
    except CtapError as e:
        print(RED, "- subcmd 0x09 error 0x%02x (%s)" % (e.code, e.code)); return False
    cdh = os.urandom(32)
    print(">> TOUCH the key (makeCredential, bound token)...")
    try:
        att = ctap.make_credential(cdh, RP, USER, PARAMS,
                                   pin_uv_param=proto.authenticate(tok, cdh), pin_uv_protocol=2)
        print(GREEN, "- makeCredential accepted (mc permission, rp match)")
    except CtapError as e:
        print(RED, "- makeCredential should have worked, got 0x%02x" % e.code); return False
    cred_id = att.auth_data.credential_data.credential_id

    # 2) negative: token WITHOUT mc permission -> makeCredential must be refused
    try:
        tok_ga = cp.get_pin_token(PIN, PERM.GET_ASSERTION, RP["id"])
        cdh = os.urandom(32)
        print(">> TOUCH the key (makeCredential with GA-only token, expect refusal)...")
        ctap.make_credential(cdh, RP, USER, PARAMS,
                             pin_uv_param=proto.authenticate(tok_ga, cdh), pin_uv_protocol=2)
        print(RED, "- makeCredential accepted a GA-only token (should refuse)"); ok = False
    except CtapError as e:
        print(GREEN, "- GA-only token refused for makeCredential (0x%02x %s)" % (e.code, e.code))

    # 3) negative: token bound to a DIFFERENT rp -> getAssertion for RP must be refused
    try:
        tok_other = cp.get_pin_token(PIN, PERM.GET_ASSERTION, "other.example")
        cdh = os.urandom(32)
        print(">> TOUCH the key (getAssertion with wrong-rp token, expect refusal)...")
        ctap.get_assertion(RP["id"], cdh, allow_list=[{"type": "public-key", "id": cred_id}],
                           pin_uv_param=proto.authenticate(tok_other, cdh), pin_uv_protocol=2)
        print(RED, "- getAssertion accepted a token bound to another RP (should refuse)"); ok = False
    except CtapError as e:
        print(GREEN, "- wrong-RP token refused for getAssertion (0x%02x %s)" % (e.code, e.code))

    # 4) negative: request an unsupported permission (credentialMgmt) -> must be refused
    try:
        cp.get_pin_token(PIN, PERM.CREDENTIAL_MGMT, RP["id"])
        print(RED, "- credentialMgmt permission was granted (should refuse)"); ok = False
    except CtapError as e:
        print(GREEN, "- unsupported permission refused at token issue (0x%02x %s)" % (e.code, e.code))

    print("   >>> Run fido_reset.py to clear the test PIN when done.")
    return ok


TESTS = {
    "rk": test_rk, "credprot": test_credprotect, "hmac": test_hmac,
    "u2f": test_u2f, "pin2": test_pin2, "pin2perm": test_pin2perm, "pinretry": test_pinretry,
}
SAFE = ["rk", "credprot", "hmac", "u2f"]


def main():
    args = [a.lower() for a in sys.argv[1:]]
    if not args:
        order = SAFE
    elif args == ["all"]:
        order = SAFE + ["pin2", "pin2perm", "pinretry"]
    else:
        order = [a for a in args if a in TESTS]
        if not order:
            print("Unknown test(s). Choose from:", ", ".join(TESTS), "or 'all'."); sys.exit(1)

    dev = get_device()
    results = {}
    for name in order:
        results[name] = TESTS[name](dev)

    print("\n== summary ==")
    for name in order:
        r = results[name]
        print("  %-9s %s" % (name, GREEN if r is True else (SKIP if r is None else RED)))


if __name__ == "__main__":
    main()
