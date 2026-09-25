#!/usr/bin/env python3
"""
2FAK attestation provisioning.

Injects the muru.global batch attestation key + certificate into the attestation
flash page of a built image, so the key attests as muru.global 2FAK with our AAGUID.

This is a FACTORY step. Run it at flash time. The private key stays in keys/2fak/
(gitignored) and is written only into the output hex, never into tracked source.

Inputs  (from keys/2fak/, created by the openssl step):
    priv.bin       32-byte P-256 private scalar
    att_cert.der   DER attestation certificate (carries the AAGUID extension)
Base image:
    an all.hex that already contains bootloader + app + boot auth word
Output:
    a provisioned all.hex with the attestation page filled in (unlocked / RDP 0)

Usage:
    pip install intelhex
    python provision_attestation.py prebuilt/all.hex prebuilt/all_provisioned.hex

The attestation page layout must match targets/stm32l432/src/memory_layout.h:
    struct flash_attestation_page {
        uint8_t  attestation_key[32];   # offset 0
        uint64_t device_settings;       # offset 32  (tag<<32 | flags)
        uint64_t attestation_cert_size; # offset 40
        uint8_t  attestation_cert[...]; # offset 48
    }
"""
import sys, os, struct
from intelhex import IntelHex

ATTESTATION_ADDR = 0x08038800          # ATTESTATION_PAGE (PAGES-15), page 113
CONFIGURED_TAG   = 0xAA551E79          # ATTESTATION_CONFIGURED_TAG
# device_settings = tag in the high 32 bits, low bits 0 => not locked (RDP 0 build)
DEVICE_SETTINGS  = (CONFIGURED_TAG << 32)

def main():
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(1)
    base, out = sys.argv[1], sys.argv[2]
    here = os.path.dirname(os.path.abspath(__file__))
    kdir = os.path.join(here, "keys", "2fak")
    key  = open(os.path.join(kdir, "priv.bin"), "rb").read()
    cert = open(os.path.join(kdir, "att_cert.der"), "rb").read()
    assert len(key) == 32, "priv.bin must be 32 bytes"
    assert len(cert) <= (2048 - 48), "certificate too large for the page"

    page  = bytearray()
    page += key                                  # [0..31]
    page += struct.pack("<Q", DEVICE_SETTINGS)   # [32..39]
    page += struct.pack("<Q", len(cert))         # [40..47]
    page += cert                                  # [48..]
    while len(page) % 8:                          # pad to a flash doubleword
        page.append(0xFF)

    ih = IntelHex(); ih.loadhex(base)
    for i, b in enumerate(page):
        ih[ATTESTATION_ADDR + i] = b
    ih.write_hex_file(out)
    print(f"Provisioned {out}: key(32) + cert({len(cert)}) at 0x{ATTESTATION_ADDR:08X}")

if __name__ == "__main__":
    main()
