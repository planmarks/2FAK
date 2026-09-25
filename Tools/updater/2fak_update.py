#!/usr/bin/env python3
"""
2FAK firmware updater - push firmware to a 2FAK over USB (no SWD programmer).

Speaks the Solo/Nitrokey-lineage secure bootloader protocol over CTAPHID, targeting the
2FAK USB id (0x1209/0x2FA2). Works with both bootloader flavours:

  * DEV unit  (non-verifying bootloader): accepts UNSIGNED firmware. Omit --key.
  * PROD unit (verifying bootloader):     accepts firmware only if signed with the
                                          production bootloader key. Pass --key.

The device must have been flashed once via SWD with an all-*.hex image (which contains
the matching bootloader). After that, updates go over USB with this tool.

Subcommands
-----------
  info                         Show device mode (app / bootloader) and version.
  sign  <app.hex> <key.pem> <out.sig>
                               Offline: compute the ECDSA-P256 signature over the app
                               region. Run this on a secure machine that holds the key.
  program <app.hex> [--key key.pem | --sig out.sig]
                               Enter bootloader (touch), write the app, finalise, reboot.

Wire format (per firmware): CTAPHID_ENTERBOOT(0x51) reboots app -> bootloader (touch
required). In the bootloader, CTAPHID_BOOT(0x50) carries a request:
    op(1) | addr[3] little-endian (low 24 bits of flash addr) | tag[4] | lenH | lenL | payload
BootWrite(0x40) streams the app ascending; BootDone(0x41) carries the 64-byte signature
(verifying bootloader) or empty payload (dev). The signature is ECDSA-P256 (raw r||s)
over SHA256 of flash [APPLICATION_START_ADDR, APPLICATION_END_ADDR).

Requires: python-fido2, intelhex, cryptography  (pip install fido2 intelhex cryptography)
"""
import sys, os, time, struct, argparse

# ---- Flash layout (PAGES=128 / 256KB device; matches memory_layout.h) ----
PAGE_SIZE = 2048
PAGES = 128
APPLICATION_START_ADDR = 0x08000000 + 10 * PAGE_SIZE            # 0x08005000
APPLICATION_END_ADDR   = 0x08000000 + (PAGES - 20) * PAGE_SIZE - 8  # 0x08035FF8
FLASH_BASE = 0x08000000

VID, PID = 0x1209, 0x2FA2

# ---- CTAPHID vendor commands (low 7 bits; the HID layer sets the 0x80 init bit) ----
CTAPHID_BOOT      = 0x50
CTAPHID_ENTERBOOT = 0x51
CTAPHID_REBOOT    = 0x53

# ---- Bootloader operations ----
BootWrite, BootDone, BootCheck, BootErase = 0x40, 0x41, 0x42, 0x43
BootVersion, BootReboot, BootBootloader, BootDisable, BootPubkey = 0x44, 0x45, 0x46, 0x47, 0x48

WRITE_CHUNK = 240  # payload bytes per BootWrite (fits the request struct + a HID message)


def _import_deps():
    try:
        from fido2.hid import CtapHidDevice
        from intelhex import IntelHex
        return CtapHidDevice, IntelHex
    except ImportError as e:
        sys.exit(f"Missing dependency: {e}. Run: pip install fido2 intelhex cryptography")


def find_device(CtapHidDevice):
    # NOTE: on Windows, FIDO HID devices are only visible to an ELEVATED (Administrator)
    # process. If nothing is found, re-run from an Administrator terminal.
    devs = list(CtapHidDevice.list_devices())
    for d in devs:
        vid = pid = None
        desc = getattr(d, "descriptor", None)
        if desc is not None:
            vid = getattr(desc, "vid", None)
            pid = getattr(desc, "pid", None)
            if vid is None and isinstance(desc, dict):   # older fido2 dict-style descriptor
                vid = desc.get("vendor_id")
                pid = desc.get("product_id")
        if (vid, pid) == (VID, PID):
            return d
    # Fallback: exactly one FIDO device present (typical on a flashing bench) -> use it.
    if len(devs) == 1:
        return devs[0]
    return None


def boot_req(op, addr=0, payload=b""):
    """Build a BootloaderReq: op | addr[3] LE | tag[4] | lenH | lenL | payload."""
    off = addr & 0xFFFFFF
    hdr = bytes([op, off & 0xFF, (off >> 8) & 0xFF, (off >> 16) & 0xFF])
    hdr += b"\x00\x00\x00\x00"  # tag (unused by the CTAPHID_BOOT path)
    hdr += bytes([(len(payload) >> 8) & 0xFF, len(payload) & 0xFF])
    return hdr + payload


def boot_call(dev, op, addr=0, payload=b""):
    """Send one CTAPHID_BOOT request; return (status_byte, writeback_bytes)."""
    resp = dev.call(CTAPHID_BOOT, boot_req(op, addr, payload))
    if not resp:
        return 0, b""
    return resp[0], resp[1:]


def in_bootloader(dev):
    """True if the connected device is already in bootloader mode."""
    try:
        status, _ = boot_call(dev, BootVersion)
        return status == 0
    except Exception:
        return False  # app mode does not implement CTAPHID_BOOT


def app_image_and_hash(IntelHex, hexpath):
    """Return (bytes to write starting at APPLICATION_START_ADDR, sha256 over the app
    region [START, END) with unwritten bytes as 0xFF), matching what the bootloader hashes."""
    import hashlib
    ih = IntelHex()
    ih.loadhex(hexpath)
    region_len = APPLICATION_END_ADDR - APPLICATION_START_ADDR
    buf = bytearray(b"\xff" * region_len)
    minaddr, maxaddr = ih.minaddr(), ih.maxaddr()
    if minaddr < APPLICATION_START_ADDR or maxaddr >= APPLICATION_END_ADDR:
        sys.exit(f"hex spans 0x{minaddr:08X}..0x{maxaddr:08X}, outside the app region "
                 f"[0x{APPLICATION_START_ADDR:08X}, 0x{APPLICATION_END_ADDR:08X}).")
    for a in range(minaddr, maxaddr + 1):
        v = ih[a]
        if v is not None:
            buf[a - APPLICATION_START_ADDR] = v
    # bytes to write: from START through the last populated address (rest stays erased 0xFF)
    write_len = maxaddr - APPLICATION_START_ADDR + 1
    return bytes(buf[:write_len]), hashlib.sha256(bytes(buf)).digest()


def sign_digest(key_pem_path, digest):
    """ECDSA-P256 over the prehashed digest -> raw r||s (64 bytes) for uECC_verify."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    with open(key_pem_path, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    der = key.sign(digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
    r, s = utils.decode_dss_signature(der)
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def cmd_info(args):
    CtapHidDevice, _ = _import_deps()
    dev = find_device(CtapHidDevice)
    if not dev:
        sys.exit(f"No 2FAK found (VID/PID {VID:#06x}/{PID:#06x}). Is it plugged in?")
    if in_bootloader(dev):
        status, wb = boot_call(dev, BootVersion)
        ver = ".".join(str(b) for b in wb[:3]) if len(wb) >= 3 else "?"
        print(f"Device in BOOTLOADER mode. Bootloader/app version: {ver}")
    else:
        print("Device in APPLICATION mode (normal FIDO operation).")


def cmd_sign(args):
    _, IntelHex = _import_deps()
    _, digest = app_image_and_hash(IntelHex, args.hex)
    sig = sign_digest(args.key, digest)
    with open(args.out, "wb") as f:
        f.write(sig)
    print(f"app sha256: {digest.hex()}")
    print(f"signature (64 bytes) written to {args.out}")


def cmd_program(args):
    CtapHidDevice, IntelHex = _import_deps()
    image, digest = app_image_and_hash(IntelHex, args.hex)

    signature = b""
    if args.key:
        signature = sign_digest(args.key, digest)
        print("signed firmware with", args.key)
    elif args.sig:
        with open(args.sig, "rb") as f:
            signature = f.read()
        if len(signature) != 64:
            sys.exit("signature file must be exactly 64 bytes")
    else:
        print("No --key/--sig given: programming UNSIGNED (dev / non-verifying bootloader only).")

    dev = find_device(CtapHidDevice)
    if not dev:
        sys.exit(f"No 2FAK found (VID/PID {VID:#06x}/{PID:#06x}).")

    # 1. Ensure we are in the bootloader.
    if not in_bootloader(dev):
        print("Device in app mode; requesting bootloader. TOUCH THE BUTTON when it blinks...")
        try:
            dev.call(CTAPHID_ENTERBOOT, b"")
        except Exception:
            pass  # device reboots and the USB link drops; expected
        dev = None
        for _ in range(30):  # wait up to ~15s for re-enumeration
            time.sleep(0.5)
            dev = find_device(CtapHidDevice)
            if dev and in_bootloader(dev):
                break
            dev = None
        if not dev:
            sys.exit("Device did not re-appear in bootloader mode (was the button pressed?).")
    print("Bootloader ready.")

    # 2. Stream the application, ascending, in chunks (first write erases the app region).
    total = len(image)
    off = 0
    while off < total:
        chunk = image[off:off + WRITE_CHUNK]
        addr = APPLICATION_START_ADDR + off
        status, _ = boot_call(dev, BootWrite, addr, chunk)
        if status != 0:
            sys.exit(f"BootWrite failed at 0x{addr:08X} (status 0x{status:02X}).")
        off += len(chunk)
        print(f"\r  written {off}/{total} bytes", end="", flush=True)
    print()

    # 3. Finalise: BootDone carries the signature (verifying) or is empty (dev).
    status, _ = boot_call(dev, BootDone, 0, signature)
    if status != 0:
        sys.exit(f"BootDone rejected (status 0x{status:02X}). "
                 f"{'Signature invalid or firmware not newer.' if signature else 'Unsigned firmware refused - this is a verifying (production) unit; pass --key.'}")
    print("Firmware accepted; device rebooting into the new application.")


def main():
    p = argparse.ArgumentParser(description="2FAK USB firmware updater")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info", help="show device mode/version").set_defaults(func=cmd_info)

    ps = sub.add_parser("sign", help="offline: sign an app hex")
    ps.add_argument("hex"); ps.add_argument("key"); ps.add_argument("out")
    ps.set_defaults(func=cmd_sign)

    pp = sub.add_parser("program", help="push firmware over USB")
    pp.add_argument("hex", help="app image (solo.hex)")
    g = pp.add_mutually_exclusive_group()
    g.add_argument("--key", help="bootloader private key PEM (signs, for verifying units)")
    g.add_argument("--sig", help="pre-computed 64-byte signature file")
    pp.set_defaults(func=cmd_program)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
