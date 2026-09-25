#!/usr/bin/env python3
"""
Generate the 2FAK production verifying-bootloader signing key (NIST P-256 / secp256r1).

The PRIVATE key signs firmware images and must stay in secrets/ (never published).
The PUBLIC key (64-byte raw x||y, uECC format) is embedded in the verifying bootloader
at targets/stm32l432/bootloader/pubkey_bootloader.c, so a production device only accepts
firmware signed by this key.

Usage:
    python keys/make_bootloader_key.py <private_key_out.pem>

Idempotent: refuses to overwrite an existing key file. Prints the C byte-string to
paste into pubkey_bootloader.c and the raw hex (for records).
"""
import sys, os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization


def escaped(b):
    return "".join(f"\\x{x:02x}" for x in b)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    out = sys.argv[1]
    if os.path.exists(out):
        print(f"ERROR: {out} already exists; refusing to overwrite a signing key.")
        sys.exit(1)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    key = ec.generate_private_key(ec.SECP256R1())
    with open(out, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM,
                                  serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption()))
    try:
        os.chmod(out, 0o600)
    except OSError:
        pass

    n = key.public_key().public_numbers()
    pub = n.x.to_bytes(32, "big") + n.y.to_bytes(32, "big")
    assert len(pub) == 64

    print(f"wrote PRIVATE key: {out}  (KEEP SECRET, never commit)")
    print(f"pubkey hex: {pub.hex()}")
    print("PUBKEY_C_STRING=\"" + escaped(pub) + "\"")


if __name__ == "__main__":
    main()
