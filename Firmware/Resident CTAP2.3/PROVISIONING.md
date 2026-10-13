# ATECC608B Provisioning Runbook (Resident firmware)

Provisioned units derive the FIDO master secret inside the ATECC608B (unreadable root,
per-credential keys derived on demand, nothing long-term in MCU flash).

**Status: PROVEN.** Board `207C37AF3631` is fully provisioned and validated end-to-end
(`atecc_selftest.py` reports `provisioned & ready: True`, `test KDF succeeded: True`). The
derivation command is `MAC` mode `0x06`. This is now the **per-unit production procedure** for
new units, not a first-time bring-up - and the flashing station orchestrates it for you
(see Stage 4). Run it by hand only when debugging a unit outside the station.

**The config- and data-zone locks are IRREVERSIBLE.** The procedure is proven, so no
sacrificial units are needed - but never interrupt a provisioning run. The firmware fails
safe: `atecc_ready()` is false until a chip is provisioned+locked, so an unprovisioned or
absent chip changes nothing.

Run all Python from an **Administrator** terminal (`pip install fido2`).

---

## Stage 0 - build the PROVISION image

```bash
cd "Firmware/Resident CTAP2.3"
RESIDENT=1 FIDO23=1 PROVISION=1 bash build.sh      # -> prebuilt/provision/all.hex
```

`PROVISION=1` compiles the button-gated CTAPHID commands `0x64` (provision) and `0x65` (diag).
These are **never** in a shipping image.

## Stage 1 - confirm the chip answers (read-only, safe)

1. Flash `prebuilt/provision/all.hex` to a **sacrificial** unit over SWD.
2. Plug in via USB-A, then:
   ```bash
   python atecc_selftest.py        # CTAPHID 0x63
   ```
   Expect: **present, NOT provisioned** (LED 2 blinks). This is the normal pre-provision state.
   - 5 blinks / "not answering" => I2C wiring/address problem (PB6/PB7, pull-ups, 0x60 vs 0x6A).
     Fix this before going further; provisioning a chip you can't talk to wastes it.

## Stage 2 - provision (IRREVERSIBLE)

```bash
python atecc_provision.py          # CTAPHID 0x64; TOUCH the key to confirm
```

Read the returned step code:

| Code | Meaning | Chip state |
|---|---|---|
| 0 | OK - provisioned **and** derivation verified | **done** |
| 1 | COMMS / button not pressed | intact |
| 2 | CFG_WRITE failed | intact (not locked) |
| 3 | CFG_VERIFY mismatch, aborted | intact (not locked) |
| 4 | CFG_LOCK failed | config lock attempted |
| 5 | KEY_WRITE failed | config locked, no key |
| 6 | DATA_LOCK failed | config locked |
| 7 | zones locked but **KDF failed** | **spent** - see Stage 2a |

Codes 2-3 are safe (debug I2C/config and retry the same chip). Code 0 => go to Stage 3.

### Stage 2a - if code 7 (KDF mode wrong for the locked slot config)

The chip is spent for use, but it's now a perfect **diagnostic** chip:
```bash
python atecc_diag.py               # CTAPHID 0x65; read-only
```
Find the candidate whose `len == 32` (a full digest = that mode works). Then in
`targets/stm32l432/src/atecc.c` set `KDF_OP` / `KDF_MODE` to that opcode/mode, rebuild Stage 0,
and provision the **next** sacrificial unit. (Current setting: `OP_MAC` / `0x06`, previously
confirmed by diag; Stage 2a only applies if the locked slot config behaves differently.)

## Stage 3 - validate the hardware root end-to-end

1. Reflash the **normal** image to the now-provisioned unit:
   ```bash
   RESIDENT=1 FIDO23=1 VERIFY_BOOT=1 bash build.sh    # or VERIFY_BOOT=0 for a dev image
   # flash prebuilt/all-verifying.hex (or all-dev.hex) over SWD
   ```
2. Replug, then:
   ```bash
   python atecc_selftest.py
   ```
   Expect: **present AND provisioned, ready = True** (LED 3 blinks). This proves
   `crypto_load_master_secret()` is now deriving the root from the ATECC.
3. Functional check: register a FIDO credential (e.g. on a test WebAuthn page or with
   `python-fido2`) and authenticate. It must work normally.
4. Reset semantics check: the per-device flash salt still gates derivation - an
   `authenticatorReset` (which regenerates the salt) must invalidate existing credentials,
   as before. Confirm a credential made pre-reset no longer authenticates post-reset.

## Stage 4 - on the production line (flashing station)

This is **already wired into the flashing station** (`Tools/flashing-station`). The manual
stages above are the fallback / debugging path. On the line:

- In the station's **Firmware** step, tick **"Provision secure element (ATECC608B)"** (needs the
  PROVISION build present and USB-A connected). The station then, at the flash stage:
  flash PROVISION build -> `CTAPHID_ATECC_PROVISION` (0x64, you TOUCH) -> check the step code ->
  flash the chosen normal build. A safe failure (chip intact) aborts the unit for a retry;
  `code 7` means the chip is spent.
- Then: test -> mint ID/codes -> **Close Debug (RDP-2)** -> log. Secure-element provisioning is
  done **at the flash stage** (while SWD + USB are both available), BEFORE RDP-2, so a retry can
  still re-flash.
- Skip the tick for units already provisioned (e.g. `207C37AF3631`); the station's test step
  still verifies `provisioned & ready` via the self-test.

## Notes

- Provisioning writes a **random** root generated on-device (`ctap_generate_rng`); no key
  material is ever exported or stored off-chip. Only the chip holds the root.
- This is independent of attestation provisioning (`provision_attestation.py`, the muru leaf
  cert) and of the RDP-2 debug lock - three separate hardening steps.
- Do **not** ship the PROVISION build; `0x64`/`0x65` must not exist in shipping firmware.
