#!/usr/bin/env python3
"""
2FAK flashing station - operator wizard (Tkinter).

Ten-step flow: detect ST-Link probes -> select units -> assign firmware (variant + dev/prod)
-> confirm/warn -> flash (live log) -> test per firmware (skippable) -> generate a unique ID
+ QR + barcode per passing unit -> append to an append-only master log.

Run from an ELEVATED terminal on Windows (FIDO USB tests need admin):
    python station.py

Backends: station_core (programmer/flash/UID/codes/log), station_tests (USB FIDO tests).
Hardware paths cannot be tested off-bench; validate on real units. Deps for codes:
    pip install qrcode python-barcode pillow fido2 intelhex
"""
import os, threading, queue, webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

import station_core as core
import station_tests as tests

PAD = 10


class StationApp:
    def __init__(self, root):
        self.root = root
        root.title("2FAK Flashing Station")
        root.geometry("860x620")
        self.cli = core.find_programmer()
        self.fw = core.available_firmware()      # {(variant,kind): path}

        # session state
        self.probes = []                          # all detected ST-Link SNs
        self.selected = []                        # SNs chosen to flash
        self.assign = {}                          # sn -> {"variant","kind"}
        self.uids = {}                            # sn -> uid hex
        self.results = {}                         # sn -> record dict

        self.header = tk.Label(root, font=("Segoe UI", 15, "bold"), anchor="w")
        self.header.pack(fill="x", padx=PAD, pady=(PAD, 0))
        self.sub = tk.Label(root, fg="#555", anchor="w", justify="left")
        self.sub.pack(fill="x", padx=PAD)
        self.body = tk.Frame(root)
        self.body.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self.nav = tk.Frame(root)
        self.nav.pack(fill="x", padx=PAD, pady=(0, PAD))

        self.step_welcome()

    # ---------------------------------------------------------------- helpers
    def _clear(self):
        for w in self.body.winfo_children():
            w.destroy()
        for w in self.nav.winfo_children():
            w.destroy()

    def _set_head(self, title, subtitle=""):
        self.header.config(text=title)
        self.sub.config(text=subtitle)

    def _nav_button(self, text, cmd, side="right", default=False, state="normal"):
        b = tk.Button(self.nav, text=text, command=cmd, width=14, state=state)
        b.pack(side=side, padx=4)
        if default:
            b.focus_set()
        return b

    def _log_widget(self):
        frame = tk.Frame(self.body)
        frame.pack(fill="both", expand=True)
        txt = tk.Text(frame, wrap="word", height=18, font=("Consolas", 9))
        sb = tk.Scrollbar(frame, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return txt

    def _run_bg(self, work, on_done):
        """Run work(log) in a thread; log lines pumped to the GUI; on_done() on the main thread."""
        q = queue.Queue()

        def log(msg):
            q.put(("log", msg))

        def runner():
            try:
                work(log)
            except Exception as e:
                q.put(("log", f"ERROR: {e}"))
            finally:
                q.put(("done", None))

        threading.Thread(target=runner, daemon=True).start()

        def pump():
            try:
                while True:
                    kind, payload = q.get_nowait()
                    if kind == "log" and self._active_log is not None:
                        self._active_log.insert("end", payload + "\n")
                        self._active_log.see("end")
                    elif kind == "done":
                        on_done()
                        return
            except queue.Empty:
                pass
            self.root.after(80, pump)

        self.root.after(80, pump)

    _active_log = None

    # ---------------------------------------------------------------- step 1: welcome
    def step_welcome(self):
        self._clear()
        self._set_head("2FAK Flashing Station",
                       "Flash and test 2FAK units connected over ST-Link, then mint IDs and codes.")
        f = self.body
        status = []
        status.append(("STM32_Programmer_CLI", "found" if self.cli else "NOT FOUND - install STM32CubeProgrammer/CubeIDE"))
        status.append(("Firmware images", f"{len(self.fw)} of 4 available" if self.fw else "none built - run build.sh first"))
        status.append(("Code libraries (QR/barcode)", "ready" if core.codes_available() else "MISSING - pip install qrcode python-barcode pillow"))
        for name, val in status:
            tk.Label(f, text=f"  {name}: {val}", anchor="w",
                     fg=("#c00" if ("NOT" in val or "none" in val or "MISSING" in val) else "#070")
                     ).pack(fill="x")
        tk.Label(f, text="\n1. Connect one or more 2FAK units via ST-Link (and USB for testing).\n"
                          "2. Click Detect.", justify="left", anchor="w").pack(fill="x", pady=PAD)
        self._nav_button("Detect devices >", self.step_detect, default=True,
                         state=("normal" if self.cli and self.fw else "disabled"))

    # ---------------------------------------------------------------- steps 2-3: detect/select
    def step_detect(self):
        self._clear()
        self._set_head("Connected units", "Detecting ST-Link probes...")
        self.root.update_idletasks()
        self.probes = core.list_probes(self.cli)

        f = self.body
        if not self.probes:
            self._set_head("Connected units", "No ST-Link probes found.")
            tk.Label(f, text="Plug a 2FAK in via ST-Link and click Re-scan. "
                             "On Windows, run this tool as Administrator.").pack(anchor="w")
            self._nav_button("Re-scan", self.step_detect, default=True)
            self._nav_button("< Back", self.step_welcome, side="left")
            return

        if len(self.probes) == 1:
            self._set_head("1 unit connected",
                           f"ST-Link {self.probes[0]} is ready. Press Continue to proceed.")
            self.selected = list(self.probes)
            tk.Label(f, text=f"  ST-Link SN: {self.probes[0]}", anchor="w").pack(fill="x")
        else:
            self._set_head(f"{len(self.probes)} units connected", "Select which units to flash.")
            self._sel_vars = {}
            for sn in self.probes:
                v = tk.BooleanVar(value=True)
                self._sel_vars[sn] = v
                tk.Checkbutton(f, text=f"ST-Link SN: {sn}", variable=v, anchor="w").pack(fill="x")

        self._nav_button("Continue >", self._detect_next, default=True)
        self._nav_button("Re-scan", self.step_detect, side="left")
        self._nav_button("< Back", self.step_welcome, side="left")

    def _detect_next(self):
        if len(self.probes) > 1:
            self.selected = [sn for sn, v in self._sel_vars.items() if v.get()]
        if not self.selected:
            messagebox.showwarning("No units", "Select at least one unit.")
            return
        self.step_assign()

    # ---------------------------------------------------------------- step 4: firmware assignment
    def step_assign(self):
        self._clear()
        self._set_head("Choose firmware", "Pick the variant and build for each unit.")
        f = self.body
        variants = sorted({v for (v, k) in self.fw})
        kinds = sorted({k for (v, k) in self.fw})

        # "apply to all" convenience
        top = tk.Frame(f); top.pack(fill="x", pady=(0, PAD))
        tk.Label(top, text="Apply to all:").pack(side="left")
        self._all_variant = tk.StringVar(value=variants[0])
        self._all_kind = tk.StringVar(value=("prod" if "prod" in kinds else kinds[0]))
        ttk.Combobox(top, textvariable=self._all_variant, values=variants, width=14, state="readonly").pack(side="left", padx=4)
        ttk.Combobox(top, textvariable=self._all_kind, values=kinds, width=8, state="readonly").pack(side="left", padx=4)
        tk.Button(top, text="Apply", command=self._apply_all).pack(side="left", padx=4)

        # per-unit table
        self._rows = {}
        grid = tk.Frame(f); grid.pack(fill="x")
        tk.Label(grid, text="Unit (ST-Link SN)", width=28, anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(grid, text="Variant", width=16, anchor="w").grid(row=0, column=1, sticky="w")
        tk.Label(grid, text="Build", width=10, anchor="w").grid(row=0, column=2, sticky="w")
        for i, sn in enumerate(self.selected, start=1):
            vv = tk.StringVar(value=self.assign.get(sn, {}).get("variant", variants[0]))
            kv = tk.StringVar(value=self.assign.get(sn, {}).get("kind", self._all_kind.get()))
            tk.Label(grid, text=sn, anchor="w").grid(row=i, column=0, sticky="w")
            ttk.Combobox(grid, textvariable=vv, values=variants, width=14, state="readonly").grid(row=i, column=1, sticky="w")
            ttk.Combobox(grid, textvariable=kv, values=kinds, width=8, state="readonly").grid(row=i, column=2, sticky="w")
            self._rows[sn] = (vv, kv)

        self._nav_button("Continue >", self._assign_next, default=True)
        self._nav_button("< Back", self.step_detect, side="left")

    def _apply_all(self):
        for sn, (vv, kv) in self._rows.items():
            vv.set(self._all_variant.get())
            kv.set(self._all_kind.get())

    def _assign_next(self):
        self.assign = {}
        for sn, (vv, kv) in self._rows.items():
            variant, kind = vv.get(), kv.get()
            if not core.firmware_path(variant, kind):
                messagebox.showerror("Missing image", f"No image for {variant}/{kind}. Build it first.")
                return
            self.assign[sn] = {"variant": variant, "kind": kind}
        self.step_confirm()

    # ---------------------------------------------------------------- step 5: confirm / warnings
    def step_confirm(self):
        self._clear()
        self._set_head("Confirm", "Review before flashing.")
        f = self.body
        for sn in self.selected:
            a = self.assign[sn]
            tk.Label(f, text=f"  {sn}  ->  {a['variant']} / {a['kind']}", anchor="w").pack(fill="x")
        warn = ("\nWarnings:\n"
                "  - Flashing ERASES the unit.\n"
                "  - 'prod' installs the verifying bootloader (accepts only muru-signed USB updates).\n"
                "  - This tool does NOT set RDP-2. Lock units separately, last, with 2fak_update.py lock.\n"
                "  - Keep only the intended units connected.")
        tk.Label(f, text=warn, justify="left", anchor="w", fg="#a60").pack(fill="x", pady=PAD)
        self._nav_button("Flash now >", self.step_flash, default=True)
        self._nav_button("< Back", self.step_assign, side="left")

    # ---------------------------------------------------------------- step 6: flashing
    def step_flash(self):
        self._clear()
        self._set_head("Flashing", "Programming each unit over SWD. Do not unplug.")
        self._active_log = self._log_widget()
        self._nav_button("...", lambda: None, state="disabled")

        def work(log):
            for sn in self.selected:
                a = self.assign[sn]
                hexp = core.firmware_path(a["variant"], a["kind"])
                rec = self.results.setdefault(sn, {})
                rec.update({"mcu_uid": "", "variant": a["variant"], "kind": a["kind"],
                            "flash_started": core.now(), "operator": ""})
                log(f"\n=== {sn}: reading MCU UID ===")
                uid = core.read_uid(self.cli, sn) or ""
                self.uids[sn] = uid
                rec["mcu_uid"] = uid
                log(f"MCU UID: {uid or '(unavailable)'}")
                log(f"=== {sn}: flashing {os.path.basename(hexp)} ===")
                ok = core.flash(self.cli, sn, hexp, log_cb=log)
                rec["flash_finished"] = core.now()
                rec["flash_result"] = "PASS" if ok else "FAIL"
                log(f"=== {sn}: flash {'OK' if ok else 'FAILED'} ===")

        def done():
            for w in self.nav.winfo_children():
                w.destroy()
            any_ok = any(self.results[sn].get("flash_result") == "PASS" for sn in self.selected)
            self._nav_button("Test >", self.step_test, default=True, state=("normal" if any_ok else "disabled"))
            self._nav_button("Skip testing", self.step_codes, side="left")
        self._run_bg(work, done)

    # ---------------------------------------------------------------- steps 7-8: testing
    def step_test(self):
        self._clear()
        self._set_head("Testing", "Running firmware-appropriate checks over USB.")
        self._active_log = self._log_widget()
        btns = tk.Frame(self.body); btns.pack(fill="x")
        tk.Button(btns, text="Copy log", command=self._copy_log).pack(side="left")
        self._nav_button("...", lambda: None, state="disabled")

        def work(log):
            for sn in self.selected:
                rec = self.results.get(sn, {})
                if rec.get("flash_result") != "PASS":
                    log(f"\n=== {sn}: skipped (flash failed) ===")
                    continue
                variant = rec["variant"]
                log(f"\n=== {sn}: testing ({variant}) ===")
                rec["test_started"] = core.now()
                before = tests.snapshot_paths()   # best-effort multi-unit disambiguation
                passed, failed, info = tests.run_tests(variant, before_paths=None, log_cb=log)
                rec["test_finished"] = core.now()
                rec["_passed"] = passed
                rec["_failed"] = failed
                rec["_info"] = info
                for n, d in passed: log(f"  PASS  {n}: {d}")
                for n, d in info:   log(f"  info  {n}: {d}")
                for n, d in failed: log(f"  FAIL  {n}: {d}")
                log(f"=== {sn}: {'PASS' if not failed else 'FAIL'} "
                    f"({len(passed)} passed, {len(failed)} failed) ===")

        def done():
            for w in self.nav.winfo_children():
                w.destroy()
            tk.Button(self.nav, text="Copy log", command=self._copy_log).pack(side="left")
            self._nav_button("Continue >", self.step_codes, default=True)
        self._run_bg(work, done)

    def _copy_log(self):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(self._active_log.get("1.0", "end"))
            messagebox.showinfo("Copied", "Test log copied to clipboard.")
        except Exception:
            pass

    # ---------------------------------------------------------------- step 9: IDs + codes
    def step_codes(self):
        self._clear()
        self._set_head("Unit IDs & codes", "Minting a unique ID + QR + barcode for each passing unit.")
        f = self.body
        log = self._log_widget(); self._active_log = log
        can_codes = core.codes_available()
        if not can_codes:
            log("Code libraries missing: pip install qrcode python-barcode pillow")

        for sn in self.selected:
            rec = self.results.get(sn, {})
            flashed = rec.get("flash_result") == "PASS"
            failed = rec.get("_failed", [])
            tested_ok = "test_finished" not in rec or not failed
            passed_all = flashed and tested_ok
            uid = self.uids.get(sn, "") or rec.get("mcu_uid", "")
            if not passed_all:
                log(f"{sn}: NOT eligible for an ID (flash/test failed) - skipping codes.")
                rec["unit_id"] = ""
                rec["qr_generated"] = rec["barcode_generated"] = "no"
                self._write_log_row(rec)
                continue
            unit_id = core.unique_id(uid or sn, rec["variant"])
            rec["unit_id"] = unit_id
            log(f"{sn}: unit ID {unit_id}  (UID {uid or 'n/a'})")
            if can_codes:
                try:
                    qr, bc = core.make_codes(unit_id)
                    rec["qr_generated"] = "yes"; rec["barcode_generated"] = "yes"
                    log(f"   QR: {qr}")
                    log(f"   barcode: {bc}")
                except Exception as e:
                    rec["qr_generated"] = rec["barcode_generated"] = "no"
                    log(f"   code generation failed: {e}")
            else:
                rec["qr_generated"] = rec["barcode_generated"] = "no"
            self._write_log_row(rec)

        btns = tk.Frame(self.body); btns.pack(fill="x")
        if can_codes:
            tk.Button(btns, text="Open codes folder", command=lambda: self._open(core.CODES_DIR)).pack(side="left")
        self._nav_button("Finish >", self.step_done, default=True)

    def _write_log_row(self, rec):
        passed = rec.get("_passed", [])
        failed = rec.get("_failed", [])
        row = dict(rec)
        row["tests_passed"] = "; ".join(n for n, _ in passed)
        row["tests_failed"] = "; ".join(n for n, _ in failed)
        core.append_master_log(row)

    def _open(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            webbrowser.open(path)
        except Exception:
            pass

    # ---------------------------------------------------------------- step 10: done
    def step_done(self):
        self._clear()
        self._set_head("Session complete", f"Master log: {core.MASTER_LOG}")
        f = self.body
        for sn in self.selected:
            rec = self.results.get(sn, {})
            uid = rec.get("unit_id") or "(no ID)"
            fr = rec.get("flash_result", "?")
            failed = rec.get("_failed", [])
            tr = "n/a" if "test_finished" not in rec else ("PASS" if not failed else f"FAIL({len(failed)})")
            tk.Label(f, text=f"  {sn}: flash {fr}, test {tr}, id {uid}", anchor="w").pack(fill="x")
        tk.Label(f, text="\nThe master log is appended, never overwritten. "
                         "Lock finished units separately with 2fak_update.py lock.",
                 justify="left", anchor="w", fg="#555").pack(fill="x", pady=PAD)
        tk.Button(self.nav, text="Open master log", command=lambda: self._open(core.LOG_DIR)).pack(side="left")
        self._nav_button("New session", self._restart, default=True)

    def _restart(self):
        self.probes, self.selected, self.assign, self.uids, self.results = [], [], {}, {}, {}
        self.step_welcome()


def main():
    root = tk.Tk()
    StationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
