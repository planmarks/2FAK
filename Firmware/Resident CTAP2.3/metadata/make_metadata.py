#!/usr/bin/env python3
"""
Generate the FIDO Metadata Statement (v3.0 schema) for the 2FAK Non-resident authenticator.

It mirrors what the firmware actually advertises in the DEFAULT build (CTAP up to
FIDO_2_1, U2F off, PIN optional) and embeds the attestation Root CA produced by
keys/make_attestation_ca.py. Run that first.

Output: metadata/2fak_metadata.json

IMPORTANT (vendor/legal steps this script cannot do):
  * legalHeader: including the FIDO legal-header URL constitutes acceptance of the FIDO
    Alliance Metadata Service legal terms. That is a business/legal decision.
  * Submitting this statement to the FIDO Metadata Service requires a FIDO account and,
    for MDS inclusion, certification. This file is a correct, self-consistent draft.
  * If you change the build flags (U2F=1, PIN_POLICY, FIDO23=1) the authenticatorGetInfo
    block and upv below must be regenerated to match.
"""
import os, json, base64, zlib, struct, binascii

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KEYS = os.path.join(ROOT, "keys", "2fak")

def _png_chunk(typ, data):
    return (struct.pack(">I", len(data)) + typ + data
            + struct.pack(">I", binascii.crc32(typ + data) & 0xffffffff))

def icon_data_url():
    # Minimal valid 8x8 opaque PNG (dark square) as a data: URL, so the metadata has a
    # well-formed icon (the conformance tool requires the field).
    w = h = 8
    raw = b""
    for _ in range(h):
        raw += b"\x00" + bytes([0x1b, 0x2a, 0x4a]) * w   # filter byte + RGB per pixel
    png = (b"\x89PNG\r\n\x1a\n"
           + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + _png_chunk(b"IDAT", zlib.compress(raw, 9))
           + _png_chunk(b"IEND", b""))
    return "data:image/png;base64," + base64.b64encode(png).decode()

def aaguid_dashed():
    h = open(os.path.join(KEYS, "aaguid.hex")).read().strip()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

def root_b64():
    return open(os.path.join(KEYS, "root_b64.txt")).read().strip()

# firmwareVersion = (MAJ<<16)|(MIN<<8)|PATCH ; matches getInfo 0x0E and build VER 5.0.0
FIRMWARE_VERSION = (5 << 16) | (0 << 8) | 0

def main():
    statement = {
        # Exact MDS3 legal header string the conformance tools require.
        "legalHeader": "Submission of this statement and retrieval and use of this statement indicates acceptance of the appropriate agreement located at https://fidoalliance.org/metadata/metadata-legal-terms/.",
        "aaguid": aaguid_dashed(),
        "description": "muru.global 2FAK Security Key",
        "authenticatorVersion": FIRMWARE_VERSION,
        "protocolFamily": "fido2",
        "schema": 3,
        # This (CTAP2.3) build advertises FIDO_2_0, FIDO_2_1 and FIDO_2_3
        # -> CTAP upv 1.0, 1.1 and 1.3. The conformance tool requires upv to
        # contain {1,3} for the CTAP2.3 profile, and this list must match the
        # device getInfo versions exactly.
        "upv": [
            {"major": 1, "minor": 0},
            {"major": 1, "minor": 1},
            {"major": 1, "minor": 3}
        ],
        "authenticationAlgorithms": ["secp256r1_ecdsa_sha256_raw"],
        "publicKeyAlgAndEncodings": ["cose"],
        "attestationTypes": ["basic_full"],
        # User verification: touch (presence) OR client PIN. With CTAP Client PIN the PIN
        # is collected by the platform and sent to the authenticator, so it is declared as
        # "passcode_external" (the conformance tool requires this when ClientPin/
        # pinUvAuthProtocols is supported).
        "userVerificationDetails": [
            [{"userVerificationMethod": "presence_internal"}],
            [{"userVerificationMethod": "passcode_external"}]
        ],
        # Credential keys are generated and used on-chip and never exported. Only the
        # optional device ROOT (on provisioned units) lives in the ATECC secure element;
        # the per-credential keys are hardware-protected on the MCU.
        "keyProtection": ["hardware"],
        "matcherProtection": ["on_chip"],
        "cryptoStrength": 128,
        # "external" must be combined with a transport flag; this is a wired USB device.
        "attachmentHint": ["external", "wired"],
        "tcDisplay": [],
        "attestationRootCertificates": [root_b64()],
        "icon": icon_data_url(),
        "authenticatorGetInfo": {
            "versions": ["FIDO_2_0", "FIDO_2_1_PRE", "FIDO_2_1", "FIDO_2_3"],
            "extensions": ["credProtect", "hmac-secret"],
            "aaguid": open(os.path.join(KEYS, "aaguid.hex")).read().strip(),
            "options": {
                "rk": True,
                "up": True,
                "plat": False,
                "credMgmt": True,
                "clientPin": False,
                "pinUvAuthToken": True
            },
            "maxMsgSize": 1200,
            "pinUvAuthProtocols": [1, 2],
            "maxCredentialCountInList": 20,
            "maxCredentialIdLength": 128,
            "transports": ["usb"],
            "algorithms": [{"type": "public-key", "alg": -7}],
            "minPINLength": 4,
            "firmwareVersion": FIRMWARE_VERSION
        }
    }

    out = os.path.join(HERE, "2fak_metadata.json")
    with open(out, "w") as f:
        json.dump(statement, f, indent=2)
        f.write("\n")
    print("wrote", out)
    print("aaguid:", statement["aaguid"])
    print("attestationRootCertificates length:", len(root_b64()), "b64 chars")

if __name__ == "__main__":
    main()
