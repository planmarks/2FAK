"""
2FA Key - ATECC608B ONE-TIME provisioning trigger.  *** IRREVERSIBLE ***

Only works on firmware built with PROVISION=1 (prebuilt/provision/all.hex). It sends
the button-gated CTAPHID_ATECC_PROVISION command; you then TOUCH THE KEY to confirm.
On the chip this: writes the root-slot config, verifies it, locks the config zone,
writes a random root key, locks the data zone, and proves the derivation works. After
this the chip can never be reconfigured - use a SACRIFICIAL unit until validated.

Run from an ELEVATED terminal.  Needs: python -m pip install fido2

    python atecc_provision.py

After a successful run, reflash the NORMAL image (prebuilt/all.hex) and replug so the
firmware loads the hardware root, then run atecc_selftest.py (expect ready = True).
"""
import sys, ctypes
from fido2.hid import CtapHidDevice

CTAPHID_ATECC_PROVISION = 0x80 | 0x64

STEP = {
    0: "OK - provisioned and derivation verified",
    1: "COMMS - could not talk to chip, or the button was not pressed in time",
    2: "CFG_WRITE - writing the slot config failed (chip NOT locked, still usable)",
    3: "CFG_VERIFY - config read-back mismatch, aborted (chip NOT locked, still usable)",
    4: "CFG_LOCK - locking the config zone failed",
    5: "KEY_WRITE - writing the root key failed",
    6: "DATA_LOCK - locking the data zone failed",
    7: "KDF - zones locked but the test derivation failed (chip is spent)",
}

try:
    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
except Exception:
    is_admin = None
print("Running as administrator:", is_admin)

devs = list(CtapHidDevice.list_devices())
if not devs:
    print("No FIDO HID device. Elevate the terminal and plug in the key (ST-Link off).")
    sys.exit(1)
dev = devs[0]
print("product:", getattr(dev, "product_name", "?"),
      "| serial:", getattr(dev, "serial_number", "?"))

print("\n*** This PERMANENTLY locks the ATECC608B on this board. Use a sacrificial unit. ***")
if input('Type "PROVISION" to continue: ').strip() != "PROVISION":
    print("Aborted.")
    sys.exit(0)

print("\n>>> TOUCH THE KEY NOW to confirm (you have ~5 seconds)...")
try:
    resp = dev.call(CTAPHID_ATECC_PROVISION, b"")
except Exception as e:
    print("Command failed:", repr(e))
    print("=> Make sure this is the PROVISION build (prebuilt/provision/all.hex).")
    sys.exit(2)

if len(resp) < 4:
    print("Unexpected short response:", resp.hex())
    sys.exit(3)

status, cfg, dat, ready = resp[0], resp[1], resp[2], resp[3]
print("\n== provisioning result ==")
print("status        :", status, "-", STEP.get(status, "unknown"))
print("config locked :", bool(cfg))
print("data locked   :", bool(dat))
print("ready         :", bool(ready))

if status == 0:
    print("\n>>> SUCCESS. Now reflash prebuilt/all.hex (normal image), replug, and run")
    print(">>> atecc_selftest.py - it should report present: True, ready: True, kdf_ok: True.")
elif status in (2, 3, 4):
    # cfg write / cfg verify / cfg lock: nothing was committed (config still unlocked).
    print("\n>>> Safe failure: nothing was locked (config still unlocked). Just re-run.")
elif status in (5, 6):
    # config zone is now locked (with our template) but data zone is not: recoverable.
    print("\n>>> Config zone is locked (committed) but data isn't. Re-run: it will skip")
    print(">>> the config step and retry the key write + data lock.")
else:  # 7
    print("\n>>> Both zones are locked but the test derivation failed. This unit is spent;")
    print(">>> capture the logic-analyzer trace and move to the next sacrificial chip.")
