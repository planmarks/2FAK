#!/usr/bin/env python3
"""
2FAK flashing-station post-flash tests (over the unit's USB FIDO interface).

Automated, no-touch checks: getInfo responds, AAGUID valid, the advertised versions and
options match the firmware variant that was flashed, ES256 is offered, and the ATECC608B
secure element is probed. A unit PASSES when the `failed` list is empty; `info` items are
reported but never fail the unit.

Multi-unit note: on a bench with several powered units, all present a FIDO interface at the
same USB id, so this module can be told the set of FIDO device paths seen BEFORE a unit was
flashed/reset and will target the one that (re)appeared. For robust multi-unit testing the
firmware should expose the MCU UID as the USB serial number (a follow-up); with a single
unit connected this is unambiguous.
"""
CTAPHID_ATECC = 0x63
CTAPHID_GETVERSION = 0x61


def _import():
    from fido2.hid import CtapHidDevice
    from fido2.ctap2 import Ctap2
    return CtapHidDevice, Ctap2


def _dev_path(d):
    desc = getattr(d, "descriptor", None)
    p = getattr(desc, "path", None)
    if p is None and isinstance(desc, dict):
        p = desc.get("path")
    return p if p is not None else repr(desc)


def snapshot_paths():
    """Return the set of FIDO HID device paths currently present (for before/after diff)."""
    CtapHidDevice, _ = _import()
    paths = set()
    try:
        for d in CtapHidDevice.list_devices():
            paths.add(_dev_path(d))
    except Exception:
        pass
    return paths


def _open_target(before_paths):
    """Open the 2FAK FIDO device. If before_paths is given, prefer a device that was NOT
    present before (the freshly-flashed/reset unit); else the sole device."""
    from fido2.hid import CtapHidDevice, list_descriptors, open_connection
    only = None
    count = 0
    try:
        descs = list(list_descriptors())
    except Exception:
        descs = []
    for desc in descs:
        try:
            dev = CtapHidDevice(desc, open_connection(desc))
        except Exception:
            continue
        count += 1
        only = dev
        path = getattr(desc, "path", None) or (desc.get("path") if isinstance(desc, dict) else repr(desc))
        vid = getattr(desc, "vid", None) or (desc.get("vendor_id") if isinstance(desc, dict) else None)
        pid = getattr(desc, "pid", None) or (desc.get("product_id") if isinstance(desc, dict) else None)
        if (vid, pid) == (0x1209, 0x2FA2) and (before_paths is None or path not in before_paths):
            return dev
    return only if count == 1 else None


def run_tests(variant, before_paths=None, log_cb=None, settle_s=3.0):
    """Run the test suite for `variant` ('resident'|'non-resident').
    Returns (passed, failed, info) lists of (name, detail)."""
    import time
    CtapHidDevice, Ctap2 = _import()
    passed, failed, info = [], [], []

    def log(m):
        if log_cb:
            log_cb(m)

    # Wait for the unit to re-enumerate after reset.
    dev = None
    for _ in range(int(settle_s / 0.5) + 6):
        dev = _open_target(before_paths)
        if dev:
            break
        time.sleep(0.5)
    if not dev:
        failed.append(("usb-enumerate", "unit did not present a FIDO interface after flashing"))
        return passed, failed, info

    try:
        ctap = Ctap2(dev)
        gi = ctap.get_info()
    except Exception as e:
        failed.append(("getInfo", f"getInfo failed: {e}"))
        return passed, failed, info
    passed.append(("getInfo", "authenticator responded"))

    versions = list(gi.versions)
    options = dict(gi.options or {})
    log(f"versions={versions}")
    log(f"options={options}")

    # AAGUID
    try:
        aa = gi.aaguid
        if aa and len(aa) == 16:
            passed.append(("aaguid", aa.hex()))
        else:
            failed.append(("aaguid", f"missing/invalid ({aa!r})"))
    except Exception as e:
        failed.append(("aaguid", str(e)))

    # ES256 offered
    algs = [a.get("alg") for a in (gi.algorithms or [])] if getattr(gi, "algorithms", None) else []
    if -7 in algs:
        passed.append(("algorithm-es256", "present"))
    else:
        failed.append(("algorithm-es256", f"ES256(-7) not offered (algs={algs})"))

    # Variant-specific version/option expectations
    if variant == "resident":
        if "FIDO_2_3" in versions:
            passed.append(("version-fido_2_3", "advertised"))
        else:
            failed.append(("version-fido_2_3", f"expected FIDO_2_3 (got {versions})"))
        if options.get("rk") is True:
            passed.append(("option-rk", "true"))
        else:
            failed.append(("option-rk", f"expected rk=true (got {options.get('rk')})"))
        if options.get("credMgmt") is True:
            passed.append(("option-credMgmt", "true"))
        else:
            failed.append(("option-credMgmt", f"expected credMgmt=true (got {options.get('credMgmt')})"))
    else:  # non-resident
        if "FIDO_2_3" not in versions and "FIDO_2_1" in versions:
            passed.append(("versions", "FIDO_2_1 max, no FIDO_2_3 (correct for second-factor)"))
        else:
            failed.append(("versions", f"unexpected for non-resident: {versions}"))
        if not options.get("rk"):
            passed.append(("option-rk", "false/absent (correct)"))
        else:
            failed.append(("option-rk", "rk advertised on a non-resident unit"))
        if "credMgmt" not in options:
            passed.append(("option-credMgmt", "absent (correct)"))
        else:
            failed.append(("option-credMgmt", "credMgmt advertised on a non-resident unit"))

    # Lock status (informational)
    try:
        r = dev.call(CTAPHID_GETVERSION, b"")
        if len(r) >= 4:
            info.append(("lock-status", "LOCKED (RDP-2)" if r[3] else "unlocked (SWD open)"))
    except Exception:
        pass

    # ATECC608B secure element probe (informational: software fallback is valid).
    try:
        r = dev.call(CTAPHID_ATECC, b"")
        if r and len(r) >= 9:
            present, ready = r[0], r[1]
            rev = bytes(r[4:8]).hex()
            kdf_ok = r[8]
            if present and ready:
                info.append(("atecc", f"present & provisioned (rev {rev}, kdf_ok={kdf_ok})"))
            elif present:
                info.append(("atecc", f"present, not provisioned (rev {rev})"))
            else:
                info.append(("atecc", "absent - using software key root (valid fallback)"))
        else:
            info.append(("atecc", "no/short response"))
    except Exception as e:
        info.append(("atecc", f"probe not available: {e}"))

    return passed, failed, info
