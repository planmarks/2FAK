"""
2FA Key - ATECC608B derivation probe (for a LOCKED chip).

Read-only. Loads TempKey via a passthrough nonce, then tries several MAC/HMAC modes
over the root slot and prints which one the chip accepts. Use this to find the keyed
command that works with the provisioned slot config, so we can point atecc_kdf at it
and turn the locked chip into a working provisioned unit (no new chip needed).

Only works on the PROVISION build (prebuilt/provision/all.hex). Elevated terminal.
Needs: python -m pip install fido2

    python atecc_diag.py
"""
import sys
from fido2.hid import CtapHidDevice

CTAPHID_ATECC_DIAG = 0x80 | 0x65

OPCODE = {0x11: "HMAC", 0x08: "MAC"}
STATUS = {
    0x00: "success", 0x01: "checkmac/verify miscompare", 0x03: "parse error (bad mode/params)",
    0x05: "ECC fault", 0x07: "self-test error", 0x0F: "execution error (config/state disallows)",
    0x11: "wake (no command)", 0xEE: "watchdog expiring", 0xFF: "CRC/comms error",
}

def main():
    devs = list(CtapHidDevice.list_devices())
    if not devs:
        print("No FIDO HID device. Elevate the terminal and plug in the key.")
        sys.exit(1)
    dev = devs[0]
    print("product:", getattr(dev, "product_name", "?"),
          "| serial:", getattr(dev, "serial_number", "?"))
    try:
        resp = dev.call(CTAPHID_ATECC_DIAG, b"")
    except Exception as e:
        print("Command failed:", repr(e))
        print("=> Needs the PROVISION build (prebuilt/provision/all.hex).")
        sys.exit(2)

    if len(resp) < 4:
        print("Short response:", resp.hex()); sys.exit(3)

    print("\n== derivation probe (root slot) ==")
    winners = []
    for i in range(0, len(resp) - 3, 4):
        op, mode, ln, st = resp[i], resp[i+1], resp[i+2], resp[i+3]
        name = OPCODE.get(op, "0x%02X" % op)
        if ln == 32:
            verdict = "  <-- WORKS (32-byte digest)"
            winners.append((op, mode))
        elif ln == 0xFD:
            verdict = "nonce failed"
        elif ln == 0xFE:
            verdict = "comms/CRC failure"
        elif ln == 1:
            verdict = "error status 0x%02X (%s)" % (st, STATUS.get(st, "?"))
        else:
            verdict = "returned %d bytes" % ln
        print("  %-4s mode 0x%02X : %s" % (name, mode, verdict))

    print()
    if winners:
        op, mode = winners[0]
        print(">>> Working primitive: %s mode 0x%02X." % (OPCODE.get(op, hex(op)), mode))
        print(">>> Tell Claude this and it will point atecc_kdf at it; this locked chip")
        print(">>> then becomes a working provisioned unit.")
    else:
        print(">>> No mode produced a digest. Send Claude the full list above (the error")
        print(">>> codes tell us whether it's the slot config or the command sequence).")

if __name__ == "__main__":
    main()
