#!/usr/bin/env python3
"""
2FAK flashing-station backend.

Hardware-facing logic used by station.py (the operator GUI): discover ST-Link probes,
read each unit's MCU unique ID, flash a chosen firmware image over SWD, run post-flash
tests over USB, mint a unique unit ID with QR + barcode, and append to a master log.

Flashing uses STMicroelectronics' STM32_Programmer_CLI (bundled with STM32CubeIDE).
Testing uses python-fido2 over the unit's USB FIDO interface. Codes use qrcode +
python-barcode + Pillow.

None of the hardware paths can be unit-tested off-bench; they are written against the
documented CLI/USB behaviour and must be validated on real hardware.
"""
import os, re, glob, time, csv, json, subprocess, hashlib, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))          # .../2FAK
FIRMWARE_DIR = os.path.join(REPO, "Firmware")
LOG_DIR = os.path.join(HERE, "logs")                            # append-only logs live here
MASTER_LOG = os.path.join(LOG_DIR, "flashing_master_log.csv")
CODES_DIR = os.path.join(HERE, "codes")                         # exported QR/barcode images

# STM32L442 unique device ID: 96 bits at 0x1FFF7590.
UID_ADDR = 0x1FFF7590
UID_LEN = 12

# Firmware catalog: (variant, kind) -> merged flashable image path.
#   variant: "non-resident" (second factor) | "resident" (passkey)
#   kind:    "dev" (non-verifying bootloader) | "prod" (verifying bootloader, signed updates)
FIRMWARE = {
    ("non-resident", "dev"):  "Non-Resident CTAP2.0-2.1/prebuilt/all-dev.hex",
    ("non-resident", "prod"): "Non-Resident CTAP2.0-2.1/prebuilt/all-verifying.hex",
    ("resident", "dev"):      "Resident CTAP2.3/prebuilt/all-dev.hex",
    ("resident", "prod"):     "Resident CTAP2.3/prebuilt/all-verifying.hex",
}


def firmware_path(variant, kind):
    rel = FIRMWARE.get((variant, kind))
    if not rel:
        return None
    p = os.path.join(FIRMWARE_DIR, rel)
    return p if os.path.exists(p) else None


def available_firmware():
    """Return the catalog entries whose hex image currently exists on disk."""
    out = {}
    for (variant, kind), rel in FIRMWARE.items():
        p = os.path.join(FIRMWARE_DIR, rel)
        if os.path.exists(p):
            out[(variant, kind)] = p
    return out


# --------------------------------------------------------------------------- programmer

def find_programmer():
    """Locate STM32_Programmer_CLI.exe (CubeIDE plugin or standalone), or None."""
    cands = []
    cands += glob.glob(r"C:\ST\STM32CubeIDE_*\STM32CubeIDE\plugins\*cubeprogrammer*\tools\bin\STM32_Programmer_CLI.exe")
    cands += glob.glob(r"C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe")
    cands += glob.glob(r"C:\Program Files (x86)\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe")
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def _run(cli, args, timeout=120):
    """Run STM32_Programmer_CLI with args; return (returncode, combined_output)."""
    try:
        p = subprocess.run([cli] + args, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT running programmer"
    except Exception as e:
        return 1, f"error running programmer: {e}"


def list_probes(cli):
    """Return a list of connected ST-Link serial numbers."""
    rc, out = _run(cli, ["-l", "st-link"], timeout=30)
    sns = re.findall(r"ST-LINK\s+SN\s*[:=]\s*([0-9A-Za-z]+)", out)
    if not sns:  # some CLI versions print "SN   : ..." without the ST-LINK prefix
        sns = re.findall(r"\bSN\s*[:=]\s*([0-9A-Fa-f]{8,})", out)
    return sns


def read_uid(cli, stlink_sn):
    """Read the 96-bit MCU unique ID via a given ST-Link. Returns hex string or None."""
    rc, out = _run(cli, ["-c", f"port=SWD", f"sn={stlink_sn}", "mode=UR",
                         "-r32", hex(UID_ADDR), hex(UID_LEN)], timeout=30)
    # Output has lines like "0x1FFF7590 : 0011AABB 2233CCDD 4455EEFF"
    words = re.findall(r":\s*((?:[0-9A-Fa-f]{8}\s*)+)$", out, re.MULTILINE)
    hexstr = ""
    for grp in words:
        for w in grp.split():
            # device is little-endian; keep raw words, normalise to a stable string
            hexstr += w.lower()
        if len(hexstr) >= UID_LEN * 2:
            break
    return hexstr[:UID_LEN * 2] if len(hexstr) >= UID_LEN * 2 else None


def flash(cli, stlink_sn, hexpath, log_cb=None):
    """Erase + program + verify + reset a unit via its ST-Link. Streams output to log_cb.
    Returns True on success."""
    if not os.path.exists(hexpath):
        if log_cb:
            log_cb(f"ERROR: firmware image not found: {hexpath}")
        return False
    args = ["-c", "port=SWD", f"sn={stlink_sn}", "mode=UR", "-e", "all",
            "-d", hexpath, "-v", "-rst"]
    try:
        proc = subprocess.Popen([cli] + args, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, errors="replace")
    except Exception as e:
        if log_cb:
            log_cb(f"ERROR: cannot start programmer: {e}")
        return False
    ok_markers = 0
    for line in proc.stdout:
        line = line.rstrip()
        if log_cb and line:
            log_cb(line)
        if "Download verified successfully" in line or "File download complete" in line:
            ok_markers += 1
    proc.wait()
    return proc.returncode == 0


# --------------------------------------------------------------------------- unique id + codes

def unique_id(uid_hex, variant):
    """Deterministic, human-usable unit ID derived from the MCU UID (+ variant tag)."""
    tag = "R" if variant == "resident" else "N"
    digest = hashlib.sha256((uid_hex + "|" + variant).encode()).hexdigest().upper()
    return f"2FAK-{tag}-{digest[:12]}"


def make_codes(unit_id, out_dir=CODES_DIR):
    """Write a QR PNG and a Code128 barcode PNG for unit_id. Returns (qr_path, bc_path).
    Raises ImportError if the code libraries are missing (the GUI surfaces that)."""
    os.makedirs(out_dir, exist_ok=True)
    import qrcode
    import barcode
    from barcode.writer import ImageWriter

    qr_path = os.path.join(out_dir, f"{unit_id}_qr.png")
    bc_path = os.path.join(out_dir, f"{unit_id}_barcode.png")

    qrcode.make(unit_id).save(qr_path)
    code128 = barcode.get("code128", unit_id, writer=ImageWriter())
    # python-barcode appends the extension itself; save() returns the final path.
    saved = code128.save(os.path.join(out_dir, f"{unit_id}_barcode"))
    if saved and os.path.exists(saved) and saved != bc_path:
        bc_path = saved
    return qr_path, bc_path


def codes_available():
    try:
        import qrcode, barcode, PIL  # noqa: F401
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- master log

MASTER_FIELDS = [
    "unit_id", "mcu_uid", "variant", "kind",
    "flash_started", "flash_finished", "flash_result",
    "test_started", "test_finished", "tests_passed", "tests_failed",
    "qr_generated", "barcode_generated", "operator", "notes",
]


def append_master_log(record):
    """Append one unit's record to the master CSV. Never overwrites; creates header once."""
    os.makedirs(LOG_DIR, exist_ok=True)
    new = not os.path.exists(MASTER_LOG)
    with open(MASTER_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MASTER_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(record)


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
