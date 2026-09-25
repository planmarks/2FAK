"""
2FA Key - ATECC608B self-test.

Sends the CTAPHID_ATECC vendor command (0x63) and prints what the secure element
reports. Read-only: it never writes to or locks the chip. Safe to run any time.

Run from an ELEVATED terminal (Windows blocks non-admin HID access to FIDO keys).
Needs: python -m pip install fido2

Also watch the key's LED when you run it:
    3 blinks  = chip present AND provisioned (hardware root in use)
    2 blinks  = chip present but NOT provisioned (software fallback - normal for now)
    5 blinks  = chip not answering (absent or wiring/address issue)
"""
import sys, ctypes
from fido2.hid import CtapHidDevice

CTAPHID_ATECC = 0x80 | 0x63   # TYPE_INIT | 0x63

try:
    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
except Exception:
    is_admin = None
print("Running as administrator:", is_admin)

devs = list(CtapHidDevice.list_devices())
print("FIDO HID devices:", len(devs))
if not devs:
    if is_admin is False:
        print("=> NOT elevated. Open PowerShell as Administrator and re-run.")
    else:
        print("=> No key seen. Plug in the USB blade (ST-Link disconnected) and re-run.")
    sys.exit(1)

dev = devs[0]
print("product:", getattr(dev, "product_name", "?"),
      "| serial:", getattr(dev, "serial_number", "?"))

try:
    resp = dev.call(CTAPHID_ATECC, b"")
except Exception as e:
    print("ATECC self-test command failed:", repr(e))
    print("=> This firmware may predate the self-test, or the command was blocked.")
    sys.exit(2)

if len(resp) < 9:
    print("Unexpected short response:", resp.hex())
    sys.exit(3)

present = resp[0]
ready   = resp[1]
cfg     = resp[2]
dat     = resp[3]
rev     = resp[4:8]
kdf_ok  = resp[8]

print("\n== ATECC608B self-test ==")
print("present (chip answered):", bool(present))
print("revision (Info word)   :", rev.hex() if present else "-")
print("config zone locked     :", bool(cfg))
print("data zone locked       :", bool(dat))
print("provisioned & ready    :", bool(ready), "(hardware root in use)" if ready else "(software fallback)")
if ready:
    print("test KDF succeeded     :", bool(kdf_ok))

print()
if not present:
    print(">>> Chip not talking. Check I2C address (0x60 vs 0x6A in atecc.c), the")
    print(">>> PB6/PB7 wiring, and that this is a DEBUG=0 build (debug UART shares those pins).")
elif not ready:
    print(">>> Chip is alive but not provisioned. This is expected today: the key uses the")
    print(">>> software root and stays fully reflashable. Provision only on a validated unit.")
else:
    print(">>> Hardware root active. The FIDO master secret is derived inside the ATECC.")
