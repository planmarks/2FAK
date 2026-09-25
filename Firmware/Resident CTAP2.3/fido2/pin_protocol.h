// PIN/UV Auth Protocol primitives (CTAP2).
//
// Supports protocol 1 (legacy) and protocol 2. The two protocols differ only in
// how the ECDH output is turned into key material and how encrypt/decrypt/verify
// work:
//
//   protocol 1: sharedSecret = SHA-256(Z)            (single 32-byte key)
//               encrypt/decrypt = AES-256-CBC, IV = 0
//               authenticate    = HMAC-SHA-256(secret, msg) truncated to 16 bytes
//
//   protocol 2: HKDF-SHA-256(Z) -> HMAC-key(32) || AES-key(32)
//               encrypt = random 16-byte IV prepended, AES-256-CBC with AES-key
//               decrypt = strip leading IV, AES-256-CBC with AES-key
//               authenticate = HMAC-SHA-256(HMAC-key, msg), full 32 bytes
//
// This module is additive: protocol 1 behaviour is identical to the original inline
// code, so existing (validated) flows do not change.
#ifndef _PIN_PROTOCOL_H_
#define _PIN_PROTOCOL_H_

#include <stdint.h>

#define PIN_PROTOCOL_V1 1
#define PIN_PROTOCOL_V2 2

// Max derived-secret size (protocol 2 = 64 bytes: HMAC-key || AES-key).
#define PIN_PROTOCOL_SECRET_MAX 64

// Derive the shared secret from the platform public key and the authenticator's
// key-agreement private key. `out` must hold at least PIN_PROTOCOL_SECRET_MAX bytes.
// Returns the secret length (32 for protocol 1, 64 for protocol 2), or 0 on bad args.
int pin_protocol_shared_secret(int protocol, const uint8_t *platform_pubkey,
                               const uint8_t *authnr_privkey, uint8_t *out);

// Decrypt `buf` (len bytes) in place. For protocol 2 the leading 16-byte IV is
// consumed and the plaintext is shifted to the front. Returns the plaintext length,
// or -1 on error.
int pin_protocol_decrypt(int protocol, const uint8_t *secret, uint8_t *buf, int len);

// Encrypt `len` bytes from `in` into `out`. For protocol 2 the output is
// IV(16) || ciphertext, so `out` must hold len+16 bytes. Returns the output length.
int pin_protocol_encrypt(int protocol, const uint8_t *secret,
                         const uint8_t *in, int len, uint8_t *out);

// Verify a pinUvAuthParam `sig` (siglen bytes) over `msg`. `key` is the HMAC key
// (the shared secret for protocol 1, the HMAC-key for protocol 2, or a pinUvAuthToken).
// Compares 16 bytes for protocol 1 and 32 for protocol 2. Returns 1 if valid, else 0.
int pin_protocol_verify(int protocol, const uint8_t *key, int keylen,
                        const uint8_t *msg, int msglen,
                        const uint8_t *sig, int siglen);

// Length of a valid pinUvAuthParam for the protocol (16 for v1, 32 for v2).
int pin_protocol_auth_length(int protocol);

#endif
