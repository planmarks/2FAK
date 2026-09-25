// 2FAK - ATECC608B secure element driver (I2C1 on PB6/PB7)
// See atecc.h. Dormant until a unit is provisioned+locked; otherwise atecc_ready()
// is false and the firmware uses the software master secret unchanged.
//
// NOTE: this is a bring-up implementation. The ATECC protocol (I2C address, wake
// timing, command execution delays, CRC) is exact and usually needs one hardware
// pass with a logic analyzer. Because atecc_ready() gates everything, an unresponsive
// or un-provisioned chip changes nothing about current behaviour.
#include "atecc.h"
#include "stm32l4xx.h"
#include "stm32l4xx_ll_gpio.h"
#include "stm32l4xx_ll_bus.h"
#include <string.h>

extern uint32_t millis(void);

// ---- tunables that may need hardware validation ----
#define ATECC_ADDR        0x60u      // 7-bit; default 0xC0>>1. Some parts use 0x6A.
#define ATECC_ADDR_ALT    0x6Au
#define ATECC_ROOT_SLOT   0          // slot holding the HMAC root key
#define I2C_TIMINGR_100K  0x10909CECu // 100 kHz @ 48 MHz PCLK1 (CubeMX value; verify)

// word addresses
#define WA_RESET   0x00
#define WA_SLEEP   0x01
#define WA_IDLE    0x02
#define WA_COMMAND 0x03
// opcodes
#define OP_READ    0x02
#define OP_WRITE   0x12
#define OP_NONCE   0x16
#define OP_HMAC    0x11
#define OP_MAC     0x08
#define OP_INFO    0x30
#define OP_LOCK    0x17
#define OP_RANDOM  0x1B

// Derivation command/mode. The ATECC608B rejects the legacy HMAC command (0x11) with a
// parse error, so we use the MAC command in PTNONCE_TEMPKEY mode: block1 = TempKey (our
// salt, loaded via a passthrough nonce), block2 = the secret root-slot key. The 32-byte
// digest is keyed by the unreadable root and is deterministic for a given salt.
// (Confirmed on hardware via atecc_diag: MAC mode 0x06 returns a 32-byte digest.)
#define KDF_OP     OP_MAC
#define KDF_MODE   0x06

static uint8_t s_addr = ATECC_ADDR;
static int s_ready = 0;

// ---------- tiny delays ----------
static void delay_ms(uint32_t ms){ uint32_t t = millis(); while ((millis() - t) < ms) { __NOP(); } }
static void delay_us(uint32_t us){ volatile uint32_t n = us * 8u; while (n--) { __NOP(); } }

// ---------- CRC16 (Atmel/Microchip CryptoAuth) ----------
static void atca_crc(uint8_t len, const uint8_t *data, uint8_t out_le[2])
{
    uint16_t reg = 0;
    for (uint8_t i = 0; i < len; i++) {
        for (uint8_t shift = 0x01; shift; shift <<= 1) {
            uint8_t d = (data[i] & shift) ? 1 : 0;
            uint8_t c = (uint8_t)(reg >> 15);
            reg <<= 1;
            if (d != c) reg ^= 0x8005;
        }
    }
    out_le[0] = (uint8_t)(reg & 0xFF);
    out_le[1] = (uint8_t)(reg >> 8);
}

// ---------- raw I2C1 ----------
static void i2c_init(void)
{
    LL_AHB2_GRP1_EnableClock(LL_AHB2_GRP1_PERIPH_GPIOB);
    // PB6=SCL, PB7=SDA -> AF4, open-drain, high speed (external pull-ups R4/R5)
    LL_GPIO_SetPinMode(GPIOB, LL_GPIO_PIN_6, LL_GPIO_MODE_ALTERNATE);
    LL_GPIO_SetPinMode(GPIOB, LL_GPIO_PIN_7, LL_GPIO_MODE_ALTERNATE);
    LL_GPIO_SetAFPin_0_7(GPIOB, LL_GPIO_PIN_6, LL_GPIO_AF_4);
    LL_GPIO_SetAFPin_0_7(GPIOB, LL_GPIO_PIN_7, LL_GPIO_AF_4);
    LL_GPIO_SetPinOutputType(GPIOB, LL_GPIO_PIN_6, LL_GPIO_OUTPUT_OPENDRAIN);
    LL_GPIO_SetPinOutputType(GPIOB, LL_GPIO_PIN_7, LL_GPIO_OUTPUT_OPENDRAIN);
    LL_GPIO_SetPinSpeed(GPIOB, LL_GPIO_PIN_6, LL_GPIO_SPEED_FREQ_HIGH);
    LL_GPIO_SetPinSpeed(GPIOB, LL_GPIO_PIN_7, LL_GPIO_SPEED_FREQ_HIGH);

    RCC->APB1ENR1 |= RCC_APB1ENR1_I2C1EN;
    I2C1->CR1 &= ~I2C_CR1_PE;
    I2C1->TIMINGR = I2C_TIMINGR_100K;
    I2C1->CR1 |= I2C_CR1_PE;
}

// returns 0 ok, -1 error/nack. len<=255.
static int i2c_xfer(uint8_t addr7, const uint8_t *tx, uint16_t txn, uint8_t *rx, uint16_t rxn)
{
    uint32_t to;
    if (tx && txn) {
        I2C1->ICR = I2C_ICR_STOPCF | I2C_ICR_NACKCF;
        I2C1->CR2 = ((uint32_t)addr7 << 1) | ((uint32_t)txn << 16) | I2C_CR2_AUTOEND | I2C_CR2_START;
        for (uint16_t i = 0; i < txn; i++) {
            to = 200000; while (!(I2C1->ISR & (I2C_ISR_TXIS | I2C_ISR_NACKF)) && --to) {}
            if (!to || (I2C1->ISR & I2C_ISR_NACKF)) return -1;
            I2C1->TXDR = tx[i];
        }
        to = 200000; while (!(I2C1->ISR & I2C_ISR_STOPF) && --to) {}
        I2C1->ICR = I2C_ICR_STOPCF;
        if (!to) return -1;
    }
    if (rx && rxn) {
        I2C1->ICR = I2C_ICR_STOPCF | I2C_ICR_NACKCF;
        I2C1->CR2 = ((uint32_t)addr7 << 1) | ((uint32_t)rxn << 16) | I2C_CR2_RD_WRN | I2C_CR2_AUTOEND | I2C_CR2_START;
        for (uint16_t i = 0; i < rxn; i++) {
            to = 200000; while (!(I2C1->ISR & (I2C_ISR_RXNE | I2C_ISR_NACKF)) && --to) {}
            if (!to || (I2C1->ISR & I2C_ISR_NACKF)) return -1;
            rx[i] = (uint8_t)I2C1->RXDR;
        }
        to = 200000; while (!(I2C1->ISR & I2C_ISR_STOPF) && --to) {}
        I2C1->ICR = I2C_ICR_STOPCF;
        if (!to) return -1;
    }
    return 0;
}

// ---------- ATECC framing ----------
static void atecc_wake(void)
{
    // Hold SDA low > 60us: drive PB7 as GPIO low, then release and re-init I2C.
    LL_GPIO_SetPinMode(GPIOB, LL_GPIO_PIN_7, LL_GPIO_MODE_OUTPUT);
    LL_GPIO_ResetOutputPin(GPIOB, LL_GPIO_PIN_7);
    delay_us(100);
    LL_GPIO_SetPinMode(GPIOB, LL_GPIO_PIN_7, LL_GPIO_MODE_ALTERNATE);
    delay_ms(2);   // tWHI
}

static void atecc_idle(void){ uint8_t w = WA_IDLE; i2c_xfer(s_addr, &w, 1, 0, 0); }

// send a command packet; word address 0x03 prefix
static int atecc_send(uint8_t op, uint8_t p1, uint16_t p2, const uint8_t *data, uint8_t dlen)
{
    uint8_t buf[1 + 155];
    uint8_t count = 1 + 1 + 1 + 2 + dlen + 2; // count,op,p1,p2(2),data,crc(2)
    if ((int)dlen > 150) return -1;
    buf[0] = WA_COMMAND;
    buf[1] = count;
    buf[2] = op;
    buf[3] = p1;
    buf[4] = (uint8_t)(p2 & 0xFF);
    buf[5] = (uint8_t)(p2 >> 8);
    if (dlen) memcpy(&buf[6], data, dlen);
    atca_crc(count - 2, &buf[1], &buf[6 + dlen]); // crc over count..data
    return i2c_xfer(s_addr, buf, (uint16_t)(1 + count), 0, 0);
}

// read a response of up to `cap` bytes into out (excluding count/crc); returns data len or -1
static int atecc_recv(uint8_t *out, uint8_t cap)
{
    uint8_t frame[64];
    if (i2c_xfer(s_addr, 0, 0, frame, sizeof(frame)) != 0) return -1;
    uint8_t count = frame[0];
    if (count < 4 || count > sizeof(frame)) return -1;
    uint8_t crc[2];
    atca_crc(count - 2, frame, crc);
    if (crc[0] != frame[count - 2] || crc[1] != frame[count - 1]) return -1;
    uint8_t dlen = count - 3; // minus count + crc
    if (dlen > cap) dlen = cap;
    memcpy(out, &frame[1], dlen);
    return dlen;
}

// one full command with fixed execution delay (ms)
static int atecc_cmd(uint8_t op, uint8_t p1, uint16_t p2, const uint8_t *data, uint8_t dlen,
                     uint8_t *out, uint8_t cap, uint32_t exec_ms)
{
    if (atecc_send(op, p1, p2, data, dlen) != 0) return -1;
    delay_ms(exec_ms);
    return atecc_recv(out, cap);
}

// For commands that reply with a single status byte (Write, Lock, Nonce-passthrough).
// Returns the status byte (0x00 = success) or -1 on a comms/CRC failure. Callers MUST
// treat anything other than 0 as an error - a non-zero status is a valid 4-byte frame,
// so checking only that bytes arrived is not enough.
static int atecc_cmd_stat(uint8_t op, uint8_t p1, uint16_t p2,
                          const uint8_t *data, uint8_t dlen, uint32_t exec_ms)
{
    uint8_t st[1];
    int n = atecc_cmd(op, p1, p2, data, dlen, st, 1, exec_ms);
    if (n < 1) return -1;
    return st[0];
}

// ---------- public ----------
int atecc_info(uint8_t rev[4])
{
    atecc_wake();
    int n = atecc_cmd(OP_INFO, 0x00, 0x0000, 0, 0, rev, 4, 2);
    atecc_idle();
    return n == 4;
}

int atecc_lock_status(int *config_locked, int *data_locked)
{
    uint8_t w[4];
    atecc_wake();
    // config zone word 21 -> bytes 84..87 (86=LockValue/data, 87=LockConfig)
    int n = atecc_cmd(OP_READ, 0x00, 21, 0, 0, w, 4, 5);
    atecc_idle();
    if (n != 4) return 0;
    if (data_locked)   *data_locked   = (w[2] == 0x00);
    if (config_locked) *config_locked = (w[3] == 0x00);
    return 1;
}

int atecc_kdf(const uint8_t *salt32, uint8_t *out, uint32_t outlen)
{
    if (!s_ready || outlen > 64) return 0;
    atecc_wake();
    uint32_t done = 0;
    uint8_t round = 0;
    while (done < outlen) {
        uint8_t nin[32];
        memcpy(nin, salt32, 32);
        nin[0] ^= round;                 // vary input per 32-byte block
        // Nonce passthrough (mode 0x03): load nin into TempKey. Replies with a single
        // status byte; 0x00 = success.
        if (atecc_cmd_stat(OP_NONCE, 0x03, 0x0000, nin, 32, 29) != 0) { atecc_idle(); return 0; }
        // MAC over the root slot (block1=TempKey, block2=slot key); 32-byte digest.
        uint8_t mac[32];
        if (atecc_cmd(KDF_OP, KDF_MODE, ATECC_ROOT_SLOT, 0, 0, mac, 32, 30) != 32) { atecc_idle(); return 0; }
        uint32_t take = (outlen - done) < 32 ? (outlen - done) : 32;
        memcpy(out + done, mac, take);
        done += take; round++;
    }
    atecc_idle();
    return 1;
}

void atecc_init(void)
{
    uint8_t rev[4];
    s_ready = 0;
#ifdef CONFORMANCE_BUILD
    // Conformance build uses the software root only: no ATECC I2C anywhere (keeps reset /
    // boot deterministic and free of I2C timing variability during automated testing).
    return;
#endif
    i2c_init();

    // probe both possible addresses
    s_addr = ATECC_ADDR;
    if (!atecc_info(rev)) {
        s_addr = ATECC_ADDR_ALT;
        if (!atecc_info(rev)) { s_addr = ATECC_ADDR; return; } // absent -> fallback
    }
    // present: only use it if fully provisioned (locked)
    int cfg = 0, data = 0;
    if (atecc_lock_status(&cfg, &data) && cfg && data) {
        s_ready = 1;
    }
}

int atecc_ready(void) { return s_ready; }

#ifdef ATECC_PROVISION
// One-time, IRREVERSIBLE provisioning of the root slot. Returns 0 on full success,
// else the step it failed at (see atecc.h ATECC_PROV_* codes). Steps 1-2 do not touch
// any lock and fail safe (the chip survives, config still unlocked); the locks happen
// only at steps 3 and 5.
//
// Config template for the root slot (assumes ATECC_ROOT_SLOT == 0; the config word
// addresses below are computed for slot 0):
//   SlotConfig[0] = 0x2080  WriteConfig=0b0010 (Never, so immutable once data locked),
//                           IsSecret=1 (unreadable), NoMac=0 (usable by HMAC),
//                           EncryptedRead=0, ReadKey=0.
//   KeyConfig[0]  = 0x003C  KeyType=7 (non-ECC/generic secret), Lockable=1, Private=0,
//                           ReqRandom=0 (so a passthrough nonce is allowed).
// The key itself is written in the clear, which the chip permits only while the data
// zone is still unlocked. Values verified against the ATECC608B datasheet / cryptoauthlib.
#if ATECC_ROOT_SLOT != 0
#error "provisioning config-word addresses assume ATECC_ROOT_SLOT == 0"
#endif
#define CFG_WORD_SLOTCFG0  5     // config zone word for bytes 20..23 (SlotConfig[0],[1])
#define CFG_WORD_KEYCFG0   24    // config zone word for bytes 96..99 (KeyConfig[0],[1])
#define SLOTCFG0_LO        0x80
#define SLOTCFG0_HI        0x20
#define KEYCFG0_LO         0x3C
#define KEYCFG0_HI         0x00

extern void ctap_generate_rng(uint8_t * dst, size_t num);

// Read a 4-byte config word, replace its low 2 bytes (this slot's config field),
// keep the high 2 bytes (the neighbouring slot's field), write it back. Returns 0 ok.
static int cfg_word_rmw(uint8_t word_addr, uint8_t lo, uint8_t hi)
{
    uint8_t w[4];
    atecc_wake();
    if (atecc_cmd(OP_READ, 0x00, word_addr, 0, 0, w, 4, 5) != 4) { atecc_idle(); return -1; }
    w[0] = lo; w[1] = hi;
    int st = atecc_cmd_stat(OP_WRITE, 0x00, word_addr, w, 4, 45);
    atecc_idle();
    return (st == 0) ? 0 : -1;
}

// Read back a config word's low 2 bytes and confirm they match. Returns 0 ok.
static int cfg_word_verify(uint8_t word_addr, uint8_t lo, uint8_t hi)
{
    uint8_t w[4];
    atecc_wake();
    int n = atecc_cmd(OP_READ, 0x00, word_addr, 0, 0, w, 4, 5);
    atecc_idle();
    if (n != 4) return -1;
    return (w[0] == lo && w[1] == hi) ? 0 : -1;
}

// Lock a zone. Wakes first: every helper above idles the chip when it finishes, so a
// lock issued without its own wake would hit a sleeping part and fail. Returns 0 ok.
static int atecc_lock_zone(uint8_t mode)
{
    atecc_wake();
    int st = atecc_cmd_stat(OP_LOCK, mode, 0x0000, 0, 0, 40);
    atecc_idle();
    return st;
}

int atecc_provision(void)
{
    int cfg = 0, data = 0;
    if (!atecc_lock_status(&cfg, &data)) return ATECC_PROV_ERR_COMMS;

    // --- Step 1+2: write and verify the slot config (only while config unlocked). ---
    if (!cfg)
    {
        if (cfg_word_rmw(CFG_WORD_SLOTCFG0, SLOTCFG0_LO, SLOTCFG0_HI) != 0) return ATECC_PROV_ERR_CFG_WRITE;
        if (cfg_word_rmw(CFG_WORD_KEYCFG0,  KEYCFG0_LO,  KEYCFG0_HI)  != 0) return ATECC_PROV_ERR_CFG_WRITE;
        // Verify BEFORE locking - if the write was garbled, abort with the chip intact.
        if (cfg_word_verify(CFG_WORD_SLOTCFG0, SLOTCFG0_LO, SLOTCFG0_HI) != 0) return ATECC_PROV_ERR_CFG_VERIFY;
        if (cfg_word_verify(CFG_WORD_KEYCFG0,  KEYCFG0_LO,  KEYCFG0_HI)  != 0) return ATECC_PROV_ERR_CFG_VERIFY;

        // --- Step 3: lock config zone (IRREVERSIBLE). ---
        if (atecc_lock_zone(0x80) != 0) return ATECC_PROV_ERR_CFG_LOCK;
    }

    // --- Step 4: write the random root key (clear write; allowed until data locked). ---
    if (!data)
    {
        uint8_t root[32];
        ctap_generate_rng(root, 32);
        atecc_wake();
        int st = atecc_cmd_stat(OP_WRITE, 0x82, (uint16_t)(ATECC_ROOT_SLOT << 3), root, 32, 45);
        atecc_idle();
        memset(root, 0, sizeof(root));
        if (st != 0) return ATECC_PROV_ERR_KEY_WRITE;

        // --- Step 5: lock data zone (IRREVERSIBLE; makes the key valid + immutable). ---
        if (atecc_lock_zone(0x81) != 0) return ATECC_PROV_ERR_DATA_LOCK;
    }

    // --- Step 6: prove the derivation works end to end. ---
    s_ready = 1;                             // allow atecc_kdf to run
    uint8_t salt[32], out[32];
    memset(salt, 0x5A, sizeof(salt));
    int ok = atecc_kdf(salt, out, sizeof(out));
    memset(out, 0, sizeof(out));
    if (!ok) { s_ready = 0; return ATECC_PROV_ERR_KDF; }

    return ATECC_PROV_OK;                     // caller should reboot so the root loads
}

// Derivation probe for a locked chip: loads TempKey via Nonce passthrough, then tries
// several MAC/HMAC modes over the root slot and reports each result. Read-only (no
// writes/locks). Fills `out` with 4 bytes per candidate: [opcode, mode, len, status]
//   len    = bytes the command returned: 32 = a full digest (this mode WORKS),
//            1 = an error-status frame, 0xFE = comms/CRC failure, 0xFD = Nonce failed.
//   status = the ATECC status byte when len==1 (e.g. 0x0F execution, 0x03 parse), else 0.
// Returns the number of bytes written.
int atecc_diag(uint8_t *out, int cap)
{
    static const uint8_t cand[][2] = {
        { OP_HMAC, 0x04 },   // HMAC, TempKey non-random (our current KDF)
        { OP_HMAC, 0x00 },   // HMAC, TempKey random flag
        { OP_HMAC, 0x44 },   // HMAC, non-random + full SN
        { 0x08,    0x06 },   // MAC, PTNONCE_TEMPKEY (block1=TempKey, source match)
        { 0x08,    0x01 },   // MAC, block2=TempKey, block1=slot key
        { 0x08,    0x05 },   // MAC, block2=TempKey + source match
        { 0x08,    0x41 },   // MAC, block2=TempKey + full SN
        { 0x08,    0x02 },   // MAC, block1=TempKey, block2=slot key
    };
    const int n = (int)(sizeof(cand) / sizeof(cand[0]));
    if (cap < n * 4) return 0;

    uint8_t salt[32];
    memset(salt, 0x5A, sizeof(salt));
    atecc_wake();
    for (int i = 0; i < n; i++)
    {
        uint8_t *e = out + i * 4;
        e[0] = cand[i][0]; e[1] = cand[i][1]; e[2] = 0xFE; e[3] = 0;
        if (atecc_cmd_stat(OP_NONCE, 0x03, 0x0000, salt, 32, 29) != 0) { e[2] = 0xFD; continue; }
        uint8_t buf[32];
        int r = atecc_cmd(cand[i][0], cand[i][1], ATECC_ROOT_SLOT, 0, 0, buf, 32, 30);
        if (r < 0)      { e[2] = 0xFE; }
        else if (r == 1){ e[2] = 1; e[3] = buf[0]; }
        else            { e[2] = (uint8_t)r; }
        memset(buf, 0, sizeof(buf));
    }
    atecc_idle();
    return n * 4;
}
#endif
