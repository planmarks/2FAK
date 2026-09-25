// 2FAK - ATECC608B secure element support (I2C1 on PB6/PB7)
//
// Purpose: hold the FIDO root secret inside the tamper-resistant chip. The MCU
// derives the 64-byte master secret from the ATECC (HMAC with a stored slot key)
// mixed with a per-device, reset-regenerated salt kept in flash. The root never
// leaves the chip; flash holds only the (useless-on-its-own) salt.
//
// SAFETY: atecc_ready() returns true ONLY when the chip is present AND provisioned
// (config+data locked). On any un-provisioned unit, or if the chip does not answer,
// the firmware falls back to the existing software master secret with no behaviour
// change. So this code is dormant until a unit is deliberately provisioned.
#ifndef _ATECC_H_
#define _ATECC_H_

#include <stdint.h>

// Call once early in device_init(). Probes the chip and caches its state.
void atecc_init(void);

// True only if the ATECC answered AND is provisioned (locked). Governs whether
// the hardware root is used. False -> software fallback (current behaviour).
int  atecc_ready(void);

// Fill `out` (outlen bytes, <= 64) with key material derived from the ATECC root
// slot and the given 32-byte salt. Returns 1 on success, 0 on any failure.
int  atecc_kdf(const uint8_t *salt32, uint8_t *out, uint32_t outlen);

// Diagnostics: 4-byte revision from Info. Returns 1 on success.
int  atecc_info(uint8_t rev[4]);

// Lock status (config/data). Returns 1 on success and sets the flags.
int  atecc_lock_status(int *config_locked, int *data_locked);

#ifdef ATECC_PROVISION
// One-time factory provisioning: writes the slot config template, verifies it, locks
// the config zone, installs a random root in the root slot, locks the data zone, and
// proves the derivation works. IRREVERSIBLE for that chip. Only compiled when
// -DATECC_PROVISION is set. Returns ATECC_PROV_OK (0) on success, else the step it
// failed at. Steps up to (and including) CFG_VERIFY do not lock anything, so those
// failures leave the chip intact and re-provisionable.
enum {
    ATECC_PROV_OK            = 0,
    ATECC_PROV_ERR_COMMS     = 1,  // could not read lock status
    ATECC_PROV_ERR_CFG_WRITE = 2,  // writing the slot config failed (chip intact)
    ATECC_PROV_ERR_CFG_VERIFY= 3,  // config read-back mismatch, aborted (chip intact)
    ATECC_PROV_ERR_CFG_LOCK  = 4,  // config-zone lock failed
    ATECC_PROV_ERR_KEY_WRITE = 5,  // writing the root key failed
    ATECC_PROV_ERR_DATA_LOCK = 6,  // data-zone lock failed
    ATECC_PROV_ERR_KDF       = 7,  // locked, but the test derivation failed
};
int  atecc_provision(void);

// Derivation probe for a locked chip. Tries several MAC/HMAC modes over the root slot
// and reports each result (4 bytes each: opcode, mode, len, status). Returns bytes
// written. Used to find which keyed command works with the provisioned slot config.
int  atecc_diag(uint8_t *out, int cap);
#endif

#endif
