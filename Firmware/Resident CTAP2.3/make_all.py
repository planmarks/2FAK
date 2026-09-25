#!/usr/bin/env python3
"""
Build the flashable all.hex for the 2FA Key (Solo-hacker / RDP0 dev flow).

Reproduces what `solo mergehex` does for an unlocked developer image, without the
solo CLI:
  1. merge solo.hex (app) + bootloader.hex
  2. zero the boot AUTH_WORD at 0x08035FF8 so the app is authorised to run
     (otherwise the device stays in the bootloader / "can't read security key")
  3. seed the 32-byte hacker attestation key at 0x08038800; device_migrate writes
     the matching cert + CONFIGURED tag into that page on first boot.

For the muru.global production attestation, run provision_attestation.py on the
resulting all.hex instead of relying on the seeded hacker key.

Usage:
    python make_all.py                 # uses prebuilt/{solo,bootloader}.hex -> prebuilt/all.hex
    python make_all.py in.hex boot.hex out.hex
"""
import sys, os
from intelhex import IntelHex

AUTH_WORD_ADDR   = 0x08035FF8          # 4 bytes -> 0 authorises the app to boot
ATTESTATION_ADDR = 0x08038800          # attestation page; seed 32-byte key
HACKER_KEY = bytes.fromhex(
    "dcc5ce47acd601a4ab22e13032429db1d57ca1669e40dbd76a5df47d536e8685")

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    pb = os.path.join(here, "prebuilt")
    if len(sys.argv) == 4:
        app, boot, out = sys.argv[1:4]
    else:
        app  = os.path.join(pb, "solo.hex")
        boot = os.path.join(pb, "bootloader.hex")
        out  = os.path.join(pb, "all.hex")

    ih = IntelHex(); ih.loadhex(app)
    b  = IntelHex(); b.loadhex(boot)
    ih.merge(b, overlap="replace")

    for i in range(4):                       # AUTH_WORD = 0x00000000
        ih[AUTH_WORD_ADDR + i] = 0x00
    for i, byte in enumerate(HACKER_KEY):    # seed hacker attestation key
        ih[ATTESTATION_ADDR + i] = byte

    ih.write_hex_file(out)
    print(f"wrote {out}  (0x{ih.minaddr():08X}..0x{ih.maxaddr():08X})")

if __name__ == "__main__":
    main()
