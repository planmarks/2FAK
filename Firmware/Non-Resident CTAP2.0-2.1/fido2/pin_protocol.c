// PIN/UV Auth Protocol primitives (CTAP2). See pin_protocol.h.
#include "pin_protocol.h"
#include "crypto.h"
#include "device.h"     // ctap_generate_rng
#include <string.h>

// HMAC-SHA-256 over one or two message chunks, using the crypto.c streaming API.
static void hmac256(const uint8_t *key, int klen,
                    const uint8_t *m1, int l1,
                    const uint8_t *m2, int l2, uint8_t out[32])
{
    crypto_sha256_hmac_init((uint8_t *)key, klen, out);
    if (m1 && l1) crypto_sha256_update((uint8_t *)m1, l1);
    if (m2 && l2) crypto_sha256_update((uint8_t *)m2, l2);
    crypto_sha256_hmac_final((uint8_t *)key, klen, out);
}

int pin_protocol_auth_length(int protocol)
{
    return (protocol == PIN_PROTOCOL_V2) ? 32 : 16;
}

int pin_protocol_shared_secret(int protocol, const uint8_t *platform_pubkey,
                               const uint8_t *authnr_privkey, uint8_t *out)
{
    uint8_t z[32];
    crypto_ecc256_shared_secret(platform_pubkey, authnr_privkey, z);

    if (protocol == PIN_PROTOCOL_V1)
    {
        // sharedSecret = SHA-256(Z)
        crypto_sha256_init();
        crypto_sha256_update(z, 32);
        crypto_sha256_final(out);
        memset(z, 0, sizeof(z));
        return 32;
    }
    else if (protocol == PIN_PROTOCOL_V2)
    {
        // HKDF-SHA-256(salt = 32 x 0x00, IKM = Z), then expand two 32-byte keys.
        uint8_t salt[32];
        uint8_t prk[32];
        memset(salt, 0, sizeof(salt));
        hmac256(salt, 32, z, 32, 0, 0, prk);                 // extract
        // expand: T(1) = HMAC(PRK, info || 0x01)
        const uint8_t one = 0x01;
        hmac256(prk, 32, (const uint8_t *)"CTAP2 HMAC key", 14, &one, 1, out);       // HMAC-key
        hmac256(prk, 32, (const uint8_t *)"CTAP2 AES key", 13, &one, 1, out + 32);   // AES-key
        memset(z, 0, sizeof(z));
        memset(prk, 0, sizeof(prk));
        return 64;
    }
    return 0;
}

int pin_protocol_decrypt(int protocol, const uint8_t *secret, uint8_t *buf, int len)
{
    if (protocol == PIN_PROTOCOL_V1)
    {
        crypto_aes256_init((uint8_t *)secret, NULL);   // IV = 0, key = secret
        crypto_aes256_decrypt(buf, len);
        return len;
    }
    else if (protocol == PIN_PROTOCOL_V2)
    {
        uint8_t iv[16];
        if (len < 16) return -1;
        memcpy(iv, buf, 16);
        crypto_aes256_init((uint8_t *)secret + 32, iv);  // key = AES-key, IV = leading 16 bytes
        crypto_aes256_decrypt(buf + 16, len - 16);
        memmove(buf, buf + 16, len - 16);                // shift plaintext to front
        return len - 16;
    }
    return -1;
}

int pin_protocol_encrypt(int protocol, const uint8_t *secret,
                         const uint8_t *in, int len, uint8_t *out)
{
    if (protocol == PIN_PROTOCOL_V1)
    {
        crypto_aes256_init((uint8_t *)secret, NULL);
        memmove(out, in, len);
        crypto_aes256_encrypt(out, len);
        return len;
    }
    else if (protocol == PIN_PROTOCOL_V2)
    {
        uint8_t iv[16];
        ctap_generate_rng(iv, 16);
        memcpy(out, iv, 16);
        crypto_aes256_init((uint8_t *)secret + 32, iv);
        memmove(out + 16, in, len);
        crypto_aes256_encrypt(out + 16, len);
        return len + 16;
    }
    return -1;
}

int pin_protocol_verify(int protocol, const uint8_t *key, int keylen,
                        const uint8_t *msg, int msglen,
                        const uint8_t *sig, int siglen)
{
    uint8_t h[32];
    int cmplen = (protocol == PIN_PROTOCOL_V2) ? 32 : 16;
    if (siglen >= 0 && siglen < cmplen) return 0;
    hmac256(key, keylen, msg, msglen, 0, 0, h);
    return (memcmp(h, sig, cmplen) == 0) ? 1 : 0;
}
