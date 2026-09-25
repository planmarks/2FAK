# 2FA Key — Project Handoff

**Project:** DIY FIDO2 / U2F USB security key
**Core silicon:** STM32L432KCU6 (SoloKeys Solo 1–compatible)
**Form factor:** USB-A PCB-edge "blade", crystal-less
**Handoff date:** 2026-08-09
**Toolchain:** KiCad 10.0.4

---

## 0. Context for the next assistant / computer

This is a from-scratch open-source hardware 2FA key. Design goals, in priority order:
1. **Run proven firmware** — the STM32L432KC is the exact MCU used by SoloKeys Solo 1 / the maintained
   Nitrokey FIDO2 fork, so mature FIDO2/U2F firmware runs with little or no modification.
2. **Real key protection** — private keys live in internal flash protected by **RDP level 2** (set only
   after firmware is final; it is effectively irreversible and disables SWD). An **optional ATECC608B**
   secure element is on the I²C bus for hardware key isolation if firmware is written to use it. Stock Solo
   firmware does **not** use the ATECC — populate U3 only if you intend to integrate it.
3. **Buildable** — single MCU, no crystal (USB clock via internal HSI48 + CRS), USB-A edge blade.

**Current state:** Schematic complete and ERC-reviewed. PCB routed. DRC reduced from 42 → effectively 0
(last item was a single `starved_thermal` on D1's GND pad — resolve by setting that pad's zone connection
to *Solid*, or freeing a 2nd thermal spoke, then refill zones).

**Open items / things to verify** (see §4).

---

## 1. Bill of Materials

| Ref | Value / Part number | Package | Qty | Function |
|-----|--------------------|---------|-----|----------|
| U1 | **STM32L432KCU6** | UFQFPN-32 | 1 | Main MCU (USB FS, TRNG, 256 KB flash) |
| U2 | **AP2112K-3.3TRG1** | SOT-23-5 | 1 | 5 V → 3.3 V LDO regulator |
| U3 | **ATECC608B-SSHDA-B** | SOIC-8 | 1 | *Optional* secure element (ECC P-256 key store) |
| U4 | **USBLC6-2SC6** | SOT-23-6 | 1 | USB D±/VBUS ESD protection |
| J1 | **USB-A PCB-edge receptacle** | PCB blade | 1 | USB host interface |
| J2 | **SWD header — TagConnect TC2030-NL** | footprintless 6-pos | 1 | Programming / debug (SWD) |
| SW1 | Tactile momentary switch | SMD | 1 | User-presence ("touch to confirm") |
| D1 | LED | 0603/0805 | 1 | Status indicator |
| FB1 | Ferrite bead, **600 Ω @ 100 MHz**, DCR < 0.5 Ω | 0402/0603 | 1 | VDDA analog-supply filter |
| R1 | 10 kΩ | 0402 | 1 | BOOT0 pull-down |
| R2 | 10 kΩ | 0402 | 1 | Button pull-up |
| R3 | 330 Ω | 0402 | 1 | LED current limit |
| R4 | 4.7 kΩ | 0402 | 1 | I²C SDA pull-up |
| R5 | 4.7 kΩ | 0402 | 1 | I²C SCL pull-up |
| C1 | 4.7 µF | 0805 | 1 | VBUS input bulk |
| C2 | 1 µF | 0603 | 1 | +3V3 bulk |
| C3 | 100 nF | 0402 | 1 | U1 VDD (pin 1) decoupling |
| C4 | 100 nF | 0402 | 1 | U1 VDD (pin 17) decoupling |
| C5 | 100 nF | 0402 | 1 | VDDA HF decoupling |
| C6 | 100 nF | 0402 | 1 | NRST filter |
| C7 | 1 µF | 0603 | 1 | VDDA bulk decoupling |
| C8 | 100 nF | 0402 | 1 | U3 (ATECC) VCC decoupling |

Suggested Mouser ferrite options for FB1: Murata BLM18SG601TN1 (0603), BLM15AG601SN1 (0402), or TDK MPZ1608S601A (0603).

---

## 2. Netlist (canonical)

Recommended: rename KiCad nets to these short canonical names and place the **identical** label on every
pin of a net. (KiCad joins pins only when label text matches exactly; the original endpoint-concatenation
names such as `U1/1-C3` work but are error-prone — that string is simply the auto-name of the **+3V3** rail.)

### Power nets

**VBUS (+5 V)** — J1.1 · U2.1 (VIN) · U2.3 (EN) · U4.5 (VBUS) · C1
> EN tied to VIN = LDO always on. C1 low side → GND.

**+3V3** — U2.5 (VOUT) · U1.1 (VDD) · U1.17 (VDD) · U3.8 (VCC) · J2.1 (VCC) · FB1 (input) · C2 · C3 · C4 · C8 · R2 · R4 · R5
> All decoupling-cap high sides and pull-up tops live here. FB1 input taps this rail.

**VDDA** — FB1 (output) · U1.5 (VDDA) · C5 · C7
> Downstream of the ferrite. **Must stay a separate net** from +3V3 (bridged only by FB1), else the filter is defeated.

**GND** — J1.4 · J1.shield* · U2.2 · U4.2 · U1.16 (VSS) · U1 exposed pad (pad 33) · U3.4 · J2.5 · SW1 (one side) · D1 (cathode) · R1 (one side) · C1 · C2 · C3 · C4 · C5 · C6 · C7 · C8
> *If the USB footprint has a shield/pad 5, tie it to GND (see §4, item 2).

### Signal nets

| Net | Pins |
|-----|------|
| **USB_DN** | J1.2 · U4.1 · U4.6 · U1.21 (PA11) |
| **USB_DP** | J1.3 · U4.3 · U4.4 · U1.22 (PA12) |
| **I2C_SCL** | U1.29 (PB6) · U3.6 (SCL) · R5 |
| **I2C_SDA** | U1.30 (PB7) · U3.5 (SDA) · R4 |
| **SWDIO** | U1.23 (PA13) · J2.2 |
| **SWCLK** | U1.24 (PA14) · J2.4 |
| **NRST** | U1.4 (NRST) · J2.3 (RESET) · C6 |
| **BOOT0** | U1.31 (PH3) · R1 |
| **BTN** | U1.6 (PA0) · R2 · SW1 (one side) |
| **LED_DRV** | U1.26 (PB3) · R3 |
| **LED_A** | R3 · D1 (anode) |

> USBLC6 note: pins 1≡6 (I/O1) and 3≡4 (I/O2) are internally bonded; route the data trace *through* U4
> (connector → U4 → MCU) so the clamp sits inline.

### No-connect

- J2.6 (SWO) — NC (SWD flashing/debug does not need it; would collide with PB3/LED).
- U2.4 (NC pad).
- U3 pins 1, 2, 3, 7 — NC.
- U1 unused: PC14 (2), PC15 (3), PA1–PA10 (7–20 except PA11/PA12), PA15 (25), PB0 (14), PB1 (15), PB4 (27), PB5 (28) — NC.

---

## 3. Per-component justification

**U1 — STM32L432KCU6.** Cortex-M4 with native USB 2.0 FS, hardware TRNG (needed for FIDO key generation),
and 256 KB flash — enough for the full FIDO2/CTAP2 stack. Chosen specifically because it is the SoloKeys
Solo 1 MCU, so the maintained open-source firmware runs directly. Supports **crystal-less USB** (HSI48 +
Clock Recovery System locked to USB SOF), removing a crystal and two caps from the BOM. Internal USB DP
pull-up removes the external 1.5 kΩ. Flash readout protection (RDP2) provides the key-at-rest security.

**U2 — AP2112K-3.3.** USB delivers 5 V on VBUS; the STM32 and peripherals run at 3.3 V. This LDO is small
(SOT-23-5), low-dropout, 600 mA (far more than the ~30 mA draw), with an enable pin tied high. *Symbol was
named "AP2112K-1.2" — pinout is identical across voltage variants; confirm the physical part is the 3.3 V
option.*

**U3 — ATECC608B (optional).** Tamper-resistant secure element that generates and stores ECC P-256 private
keys such that they cannot be read out — the ideal home for FIDO credentials. On I²C. Populated only if
firmware is written to use it; stock Solo firmware relies on internal flash + RDP2 instead.

**U4 — USBLC6-2SC6.** Low-capacitance TVS array protecting D+, D−, and VBUS from ESD at the exposed USB
connector. Essential because the port is user-handled. Placed inline on the data pair.

**J1 — USB-A PCB-edge receptacle.** The cheapest USB-A interface: the PCB edge itself is the plug blade
(U2F-Zero/Solo style), no connector cost. Requires correct board thickness/gold fingers at the fab.

**J2 — TagConnect TC2030-NL (SWD).** Footprintless spring-pin SWD programming/debug interface — saves board
area versus a pin header, no part to solder. Carries SWDIO, SWCLK, NRST, 3V3, GND.

**SW1 — tactile switch.** FIDO requires a physical **user-presence** action to authorize each operation.
Digital GPIO input (PA0) with pull-up; press pulls low.

**D1 — LED.** Status/activity indicator (e.g. "touch me now"). Driven high by PB3 through R3.

**FB1 — ferrite bead (VDDA filter).** ST reference-design practice: isolates the analog supply (VDDA / ADC /
internal reference) from digital rail noise. **Optional for this design** since no precision analog is used;
kept as cheap insurance. If omitted, short VDDA to +3V3 directly. 600 Ω @ 100 MHz, low DCR.

**R1 (10 kΩ) — BOOT0 pull-down.** Holds PH3/BOOT0 low so the MCU boots from flash. Pull high to enter the
built-in USB DFU bootloader.

**R2 (10 kΩ) — button pull-up.** Defines PA0 idle-high; SW1 pulls it low when pressed.

**R3 (330 Ω) — LED current limit.** Sets LED current from the 3.3 V GPIO drive.

**R4 / R5 (4.7 kΩ) — I²C pull-ups.** Required bus pull-ups for SDA (PB7) and SCL (PB6) to the ATECC.

**C1 (4.7 µF) — VBUS bulk.** Input-side reservoir for the LDO / USB power.

**C2 (1 µF) — +3V3 bulk.** LDO-output reservoir / rail stabilization.

**C3, C4 (100 nF) — VDD decoupling.** One per MCU VDD pin (1, 17), placed at the pin.

**C5 (100 nF) + C7 (1 µF) — VDDA decoupling.** HF + bulk decoupling on the analog supply, after FB1.

**C6 (100 nF) — NRST filter.** Debounces/filters the reset line; standard on STM32.

**C8 (100 nF) — ATECC decoupling.** Local bypass at U3 VCC.

---

## 4. Open items / verify before fabrication

1. **U2 voltage variant** — schematic symbol reads "AP2112K-1.2"; confirm the **3.3 V** part is fitted. A
   1.2 V regulator would prevent the board from running.
2. **J1 USB shield / pad 5** — earlier DRC flagged a footprint pad (pin 5) with no schematic pin, plus a
   library-footprint mismatch. Decide what pad 5 is: if a shield/mechanical tab, add a symbol pin and tie it
   to **GND**; if spurious, remove it. Do not leave it floating.
3. **Final DRC** — resolve the last `starved_thermal` on D1 GND (set pad zone connection to *Solid* or free a
   2nd spoke), refill zones, re-run DRC to 0 errors.
4. **GND zone coverage** — verify the pour reaches every ground pad with no isolated islands.
5. **USB routing** — D+/D− matched length, ~90 Ω differential, U4 inline near the connector.
6. **Net names (cosmetic)** — optionally rename endpoint-style nets (e.g. `U1/1-C3`) to canonical names
   (`+3V3`, `VDDA`, `USB_DP`, `USB_DN`, `GND`, `SCL`, `SDA`, …) for readability; re-run ERC after.

---

## 5. Firmware & bring-up notes

- Flash via SWD (ST-Link on J2) or built-in USB DFU (pull BOOT0/PH3 high).
- Recommended firmware: maintained Nitrokey FIDO2 fork (Solo 1 lineage) — internal flash + RDP2 key
  protection; does **not** use the ATECC.
- Set **RDP level 2 only after firmware is final** — it is effectively permanent and disables SWD.
- No crystal: ensure firmware enables HSI48 + CRS for USB clocking (Solo firmware already does).

---

## 6. Reference projects

- SoloKeys Solo 1 (same STM32L432) — https://github.com/solokeys/solo
- Nitrokey FIDO2 firmware (maintained fork) — https://github.com/Nitrokey/nitrokey-fido2-firmware
- SoloKeys Solo 2 hardware (KiCad) — https://github.com/solokeys/solo2-hw
- U2F Zero (EFM8 + ATECC, simplest reference) — https://github.com/conorpp/u2f-zero
