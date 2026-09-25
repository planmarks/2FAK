"""
2FA Key - authenticatorReset (clears the PIN AND all credentials).

There is no "reset only the PIN" in FIDO2. Reset removes the PIN and every credential,
and this key also re-rolls its master secret, so anything registered before stops
working. Use only on a test/owned key.

Rules enforced by the standard:
  - the reset must be sent within ~10 seconds of plugging the key in
  - you must physically touch the key to confirm

How to run (elevated terminal, `python -m pip install fido2`):
  1. UNPLUG the key.
  2. PLUG it back in.
  3. Within 10 seconds, run:  python fido_reset.py
  4. TOUCH the key when it blinks.
"""
import sys, ctypes
from fido2.hid import CtapHidDevice
from fido2.ctap2 import Ctap2

try:
    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
except Exception:
    is_admin = None
print("Running as administrator:", is_admin)

devs = list(CtapHidDevice.list_devices())
if not devs:
    print("No FIDO HID device. Elevate the terminal and plug the key in, then re-run.")
    sys.exit(1)

dev = devs[0]
print("product:", getattr(dev, "product_name", "?"),
      "| serial:", getattr(dev, "serial_number", "?"))
print("\n*** This ERASES the PIN and ALL credentials on this key. ***")
if input('Type "RESET" to continue: ').strip() != "RESET":
    print("Aborted.")
    sys.exit(0)

ctap = Ctap2(dev)
print("\n>>> TOUCH THE KEY NOW to confirm the reset...")
try:
    ctap.reset()
    print("\nReset OK. The PIN and all credentials are cleared.")
    print("Run fido_diag.py: options should show clientPin: False again.")
except Exception as e:
    print("\nReset failed:", repr(e))
    print("Most common cause: more than ~10 seconds passed since plug-in.")
    print("Unplug, replug, and run this again within 10 seconds, then touch promptly.")
