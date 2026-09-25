"""
2FA Key CTAP diagnostic. Run from an ELEVATED terminal (Windows blocks non-admin
HID access to FIDO keys). Needs: python -m pip install fido2
It prints getInfo, then attempts a makeCredential and prints the exact error.
Touch the key (SW1) when prompted.
"""
import secrets, sys, ctypes
from fido2.hid import CtapHidDevice
from fido2.ctap2 import Ctap2

try:
    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
except Exception:
    is_admin = None
print("Running as administrator:", is_admin)

devs = list(CtapHidDevice.list_devices())
print("FIDO HID devices:", len(devs))
if not devs:
    if is_admin is False:
        print("=> NOT elevated. Windows hides FIDO keys from non-admin processes.")
        print("   Close this window. Open PowerShell as Administrator (title must read")
        print("   'Administrator: Windows PowerShell') and run this again.")
    else:
        print("=> Elevated, but no key seen. Make sure the USB blade is plugged into a")
        print("   USB port (ST-Link disconnected) and re-run.")
    sys.exit(1)

dev = devs[0]
print("product:", getattr(dev, "product_name", "?"), "| serial:", getattr(dev, "serial_number", "?"))
ctap = Ctap2(dev)

# --- getInfo ---
try:
    info = ctap.get_info()
    print("\n== getInfo ==")
    print("versions      :", info.versions)
    print("extensions    :", info.extensions)
    print("aaguid        :", info.aaguid.hex())
    print("options       :", info.options)
    print("maxMsgSize    :", info.max_msg_size)
    print("pinUvProtocols:", getattr(info, "pin_uv_protocols", None))
    print("transports    :", getattr(info, "transports", None))
except Exception as e:
    print("GETINFO ERROR:", repr(e))
    sys.exit(2)

# --- makeCredential (this is what fails in the browser) ---
print("\n== makeCredential ==  >> TOUCH THE KEY (SW1) when the LED signals...")
cdh = secrets.token_bytes(32)
rp = {"id": "example.com", "name": "Example"}
user = {"id": b"\x01\x02\x03\x04", "name": "tester", "displayName": "Tester"}
params = [{"type": "public-key", "alg": -7}]  # ES256
try:
    att = ctap.make_credential(cdh, rp, user, params)
    print("MakeCredential OK!")
    print("  fmt      :", att.fmt)
    print("  attStmt  :", list(att.att_stmt.keys()))
    print("  alg      :", att.att_stmt.get("alg"))
    ncred = att.auth_data.credential_data
    print("  cred algo:", ncred.public_key[3] if ncred else "?")
    # Show the attestation leaf cert so we can tell which attestation is active
    # (dev "hacker" cert vs. our muru batch cert from all_attested.hex).
    x5c = att.att_stmt.get("x5c")
    if x5c:
        try:
            from cryptography import x509
            leaf = x509.load_der_x509_certificate(x5c[0])
            print("  x5c subj :", leaf.subject.rfc4514_string())
            print("  x5c issr :", leaf.issuer.rfc4514_string())
            try:
                ext = leaf.extensions.get_extension_for_oid(
                    x509.ObjectIdentifier("1.3.6.1.4.1.45724.1.1.4"))
                print("  x5c aaguid:", ext.value.value[2:].hex())
            except Exception:
                print("  x5c aaguid: (none)")
        except Exception as e:
            print("  x5c parse error:", repr(e))
    print("\n>>> The authenticator itself works. If webauthn.io still fails it's an")
    print(">>> attestation/RP issue, not the device.")
except Exception as e:
    print("MAKECREDENTIAL ERROR:", repr(e))
