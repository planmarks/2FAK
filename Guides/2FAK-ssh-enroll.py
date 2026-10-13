#!/usr/bin/env python3
"""
2FAK-ssh-enroll - a small helper for using a 2FAK Passkey (Resident) key as a
hardware-backed SSH key.

It is a thin, auditable wrapper around OpenSSH's own `ssh-keygen`. It does not
talk to the device directly and stores nothing itself; the private key material
never leaves the 2FAK. Everything it does, you could do by hand with ssh-keygen -
this tool just makes the resident-key workflow less error-prone and nudges you to
enroll a BACKUP key at the same time (the #1 operational mistake with hardware
SSH keys is having only one).

Requires: OpenSSH 8.2+ (for FIDO/`-sk` keys) with libfido2 support, and a
2FAK Passkey (Resident) firmware key. ES256 (`ecdsa-sk`) is used because that is
what the firmware supports; `ed25519-sk` is intentionally not offered.

Subcommands:
  enroll   Create a RESIDENT ecdsa-sk key on the token (portable; can be pulled
           onto any machine later with `export`). Prompts to also enroll a backup.
  export   Download resident keys from a token onto the current machine
           (wraps `ssh-keygen -K`), e.g. on a new admin workstation.
  check    Report whether the local OpenSSH supports FIDO/`-sk` keys.

Examples:
  python 2FAK-ssh-enroll.py enroll --name prod --verify-required
  python 2FAK-ssh-enroll.py enroll --name lab --no-backup
  python 2FAK-ssh-enroll.py export --dir ~/.ssh
  python 2FAK-ssh-enroll.py check

This is a convenience tool, not a provisioning tool. Apache-2.0.
"""

import argparse
import os
import shutil
import subprocess
import sys


def _find_ssh_keygen() -> str:
    exe = shutil.which("ssh-keygen")
    if not exe:
        sys.exit("error: ssh-keygen not found on PATH. Install OpenSSH 8.2+ "
                 "(and libfido2) first.")
    return exe


def _keygen_version(exe: str) -> str:
    # `ssh-keygen` has no --version; the version comes from `ssh -V` (stderr).
    ssh = shutil.which("ssh")
    if not ssh:
        return "unknown"
    try:
        out = subprocess.run([ssh, "-V"], capture_output=True, text=True)
        return (out.stderr or out.stdout).strip()
    except Exception:
        return "unknown"


def _supports_sk(exe: str) -> bool:
    """Best-effort probe: ssh-keygen lists sk types in its -t help text."""
    try:
        out = subprocess.run([exe, "-t", "ecdsa-sk", "-f", os.devnull, "-N", "",
                              "-C", "__probe__", "-y"],
                             capture_output=True, text=True)
        # A build without sk support prints "unknown key type ecdsa-sk".
        blob = (out.stderr + out.stdout).lower()
        if "unknown key type" in blob:
            return False
        return True
    except Exception:
        return True  # don't block on a probe failure; enroll will surface it


def cmd_check(args: argparse.Namespace) -> int:
    exe = _find_ssh_keygen()
    ver = _keygen_version(exe)
    ok = _supports_sk(exe)
    print(f"ssh-keygen : {exe}")
    print(f"OpenSSH    : {ver}")
    print(f"FIDO (-sk) : {'supported' if ok else 'NOT supported - upgrade OpenSSH / install libfido2'}")
    if not ok:
        return 1
    print("\nReady. Enroll a resident key with:  "
          "python 2FAK-ssh-enroll.py enroll --name <label>")
    return 0


def _run_enroll(exe: str, keyfile: str, application: str, comment: str,
                verify_required: bool) -> int:
    cmd = [exe, "-t", "ecdsa-sk", "-O", "resident",
           "-O", f"application={application}",
           "-f", keyfile, "-C", comment]
    if verify_required:
        cmd += ["-O", "verify-required"]
    print("\n>> " + " ".join(cmd))
    print("   Touch the 2FAK when its LED blinks"
          + (" (you will also be asked for the device PIN)." if verify_required else "."))
    return subprocess.run(cmd).returncode


def cmd_enroll(args: argparse.Namespace) -> int:
    exe = _find_ssh_keygen()
    if not _supports_sk(exe):
        sys.exit("error: this OpenSSH build has no FIDO/-sk support. "
                 "Upgrade OpenSSH (>=8.2) and install libfido2.")

    application = args.application or f"ssh:{args.name}"
    if not application.startswith("ssh:"):
        sys.exit("error: --application must start with 'ssh:' (OpenSSH requirement).")

    outdir = os.path.expanduser(args.dir)
    os.makedirs(outdir, exist_ok=True)
    keyfile = os.path.join(outdir, f"id_ecdsa_sk_{args.name}")

    if os.path.exists(keyfile) and not args.force:
        sys.exit(f"error: {keyfile} already exists (use --force to overwrite the "
                 f"local handle file; this does not delete the on-device credential).")

    print(f"Enrolling PRIMARY resident SSH key")
    print(f"  application : {application}")
    print(f"  key file    : {keyfile}")
    print(f"  verify (PIN): {'required' if args.verify_required else 'not required'}")
    input("\nInsert your PRIMARY 2FAK Passkey key, then press Enter...")
    rc = _run_enroll(exe, keyfile, application, args.comment or f"2fak:{args.name}",
                     args.verify_required)
    if rc != 0:
        return rc
    print(f"\nOK. Public key: {keyfile}.pub")

    if args.no_backup:
        print("\nNOTE: you skipped the backup key. Enroll one before you rely on this "
              "for production access:\n  python 2FAK-ssh-enroll.py enroll --name "
              f"{args.name} --dir <other-dir>  (with the backup key inserted)")
        _print_next_steps(keyfile)
        return 0

    print("\n--- BACKUP KEY ---")
    print("Strongly recommended: enroll a second (backup) key now so a lost or broken "
          "key never locks you out.")
    ans = input("Enroll a backup key now? [Y/n] ").strip().lower()
    if ans in ("", "y", "yes"):
        backupfile = os.path.join(outdir, f"id_ecdsa_sk_{args.name}_backup")
        input("Remove the primary key, insert the BACKUP 2FAK key, then press Enter...")
        rc = _run_enroll(exe, backupfile, application,
                         (args.comment or f"2fak:{args.name}") + "-backup",
                         args.verify_required)
        if rc == 0:
            print(f"\nOK. Backup public key: {backupfile}.pub")
            print("Add BOTH .pub lines to every server's authorized_keys / your SSH CA.")
    else:
        print("Skipped. Remember: one key = one hardware failure away from lockout.")

    _print_next_steps(keyfile)
    return 0


def _print_next_steps(keyfile: str) -> None:
    print("\nNext steps:")
    print(f"  1. Install the public key on a server:")
    print(f"       ssh-copy-id -f -i {keyfile}.pub user@server")
    print(f"     (or add the '{os.path.basename(keyfile)}.pub' line to ~/.ssh/authorized_keys there)")
    print(f"  2. Connect (you will be asked to touch the key):")
    print(f"       ssh -i {keyfile} user@server")
    print(f"  3. On a NEW machine, pull the resident key off the token instead of copying files:")
    print(f"       python 2FAK-ssh-enroll.py export --dir ~/.ssh")


def cmd_export(args: argparse.Namespace) -> int:
    exe = _find_ssh_keygen()
    outdir = os.path.expanduser(args.dir)
    os.makedirs(outdir, exist_ok=True)
    print("Downloading resident SSH keys from the inserted 2FAK token into:")
    print(f"  {outdir}")
    input("Insert the 2FAK key, then press Enter...")
    # -K writes the resident keys as id_<type>_sk[_rk*] in the current directory.
    cmd = [exe, "-K"]
    print("\n>> (cd " + outdir + ") && " + " ".join(cmd))
    print("   Touch the key when its LED blinks (enter the PIN if prompted).")
    rc = subprocess.run(cmd, cwd=outdir).returncode
    if rc == 0:
        print("\nOK. The downloaded key files are in the directory above; reference them "
              "with `ssh -i <file>` or an IdentityFile entry in ~/.ssh/config.")
    return rc


def main() -> int:
    p = argparse.ArgumentParser(
        prog="2FAK-ssh-enroll",
        description="Helper for using a 2FAK Passkey (Resident) key as a hardware SSH key.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("enroll", help="create a resident ecdsa-sk key (+ optional backup)")
    pe.add_argument("--name", required=True,
                    help="short label for this key/role, e.g. prod, lab, infra")
    pe.add_argument("--application", default=None,
                    help="FIDO application string (must start with 'ssh:'); "
                         "default 'ssh:<name>'")
    pe.add_argument("--verify-required", action="store_true",
                    help="require the device PIN in addition to touch (recommended for prod)")
    pe.add_argument("--dir", default="~/.ssh", help="output directory (default ~/.ssh)")
    pe.add_argument("--comment", default=None, help="key comment (default 2fak:<name>)")
    pe.add_argument("--no-backup", action="store_true",
                    help="do not prompt to enroll a backup key")
    pe.add_argument("--force", action="store_true",
                    help="overwrite an existing local handle file of the same name")
    pe.set_defaults(func=cmd_enroll)

    px = sub.add_parser("export", help="download resident keys off a token (ssh-keygen -K)")
    px.add_argument("--dir", default="~/.ssh", help="output directory (default ~/.ssh)")
    px.set_defaults(func=cmd_export)

    pc = sub.add_parser("check", help="check local OpenSSH for FIDO/-sk support")
    pc.set_defaults(func=cmd_check)

    args = p.parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\naborted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
