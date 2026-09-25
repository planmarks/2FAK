#!/usr/bin/env python3
"""
Generate the 2FAK attestation PKI: a self-signed attestation Root CA and a batch
attestation leaf certificate signed by it, for FIDO2 "packed" (basic_full) attestation.

Outputs (into keys/2fak/):
  ca_key.pem     Root CA private key           (SECRET - gitignored)
  ca_cert.pem    Root CA certificate           (public; goes in the metadata statement)
  ca_cert.der    Root CA cert, DER
  root_b64.txt   base64(DER root cert)         (paste into attestationRootCertificates)
  att_key.pem    Leaf (batch) private key      (SECRET - gitignored)
  priv.bin       Leaf private scalar, 32 bytes (SECRET - used by provision_attestation.py)
  att_cert.pem   Leaf certificate              (public; embedded in the device, sent as x5c)
  att_cert.der   Leaf cert, DER

The leaf certificate carries the FIDO AAGUID extension (1.3.6.1.4.1.45724.1.1.4) whose
value MUST equal the authenticator's AAGUID (from keys/2fak/aaguid.hex and the firmware),
or attestation validation fails.

Run once to establish the CA. Re-running overwrites everything (new keys), which would
invalidate already-provisioned devices - so keep ca_key.pem safe and back it up.

    python keys/make_attestation_ca.py
"""
import os, base64, datetime
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "2fak")
AAGUID_OID = x509.ObjectIdentifier("1.3.6.1.4.1.45724.1.1.4")

# Subject identity. OU MUST be exactly "Authenticator Attestation" for FIDO packed attestation.
COUNTRY = "SI"
ORG = "muru.global"
LEAF_CN = "muru.global 2FAK Series"
ROOT_CN = "muru.global 2FAK Attestation Root CA"

def aaguid_bytes():
    hexstr = open(os.path.join(OUT, "aaguid.hex")).read().strip()
    b = bytes.fromhex(hexstr)
    assert len(b) == 16, "aaguid.hex must be 16 bytes"
    return b

def save(name, data, binary=False):
    path = os.path.join(OUT, name)
    if isinstance(data, str):
        data = data.encode()
    with open(path, "wb") as f:
        f.write(data)
    return path

def main():
    os.makedirs(OUT, exist_ok=True)
    aaguid = aaguid_bytes()
    now = datetime.datetime.utcnow()
    far = now + datetime.timedelta(days=365 * 25)

    # --- Root CA ---
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, COUNTRY),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, ORG),
        x509.NameAttribute(NameOID.COMMON_NAME, ROOT_CN),
    ])
    ca_cert = (x509.CertificateBuilder()
        .subject_name(ca_name).issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now).not_valid_after(far)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=False, key_cert_sign=True,
                                     crl_sign=True, key_encipherment=False,
                                     content_commitment=False, data_encipherment=False,
                                     key_agreement=False, encipher_only=False,
                                     decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256()))

    # --- Leaf (batch) attestation cert ---
    leaf_key = ec.generate_private_key(ec.SECP256R1())
    leaf_name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, COUNTRY),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, ORG),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Authenticator Attestation"),
        x509.NameAttribute(NameOID.COMMON_NAME, LEAF_CN),
    ])
    # AAGUID extension value is a DER OCTET STRING wrapping the 16 raw bytes.
    aaguid_ext_value = b"\x04\x10" + aaguid
    leaf_cert = (x509.CertificateBuilder()
        .subject_name(leaf_name).issuer_name(ca_name)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now).not_valid_after(far)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.UnrecognizedExtension(AAGUID_OID, aaguid_ext_value), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256()))

    # --- write outputs ---
    save("ca_key.pem", ca_key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    save("ca_cert.pem", ca_cert.public_bytes(serialization.Encoding.PEM))
    ca_der = ca_cert.public_bytes(serialization.Encoding.DER)
    save("ca_cert.der", ca_der, binary=True)
    save("root_b64.txt", base64.b64encode(ca_der).decode() + "\n")

    save("att_key.pem", leaf_key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    save("att_cert.pem", leaf_cert.public_bytes(serialization.Encoding.PEM))
    save("att_cert.der", leaf_cert.public_bytes(serialization.Encoding.DER), binary=True)
    # 32-byte raw private scalar for provision_attestation.py
    save("priv.bin", leaf_key.private_numbers().private_value.to_bytes(32, "big"), binary=True)

    print("AAGUID:", aaguid.hex())
    print("Root CA subject:", ROOT_CN)
    print("Leaf subject:", leaf_name.rfc4514_string())
    print("Wrote CA + leaf into", OUT)
    print("attestationRootCertificates (base64 DER) is in keys/2fak/root_b64.txt")

if __name__ == "__main__":
    main()
