# -*- coding: utf-8 -*-
"""M08 solve scheduler (background).

Picks cases in queue_order whose datacheck gate passed and that have no
solve_result.json yet. Maintains <=2 concurrent Explicit solves. Each
solve: write <solver>/solve_<job>.bat (NO '%' characters anywhere), launch
hidden via PowerShell Start-Process, verify .com records cpus/memory
values, poll .lck; on termination run m08_extract_case.py and append a
batch_ledger.csv row (m05_post_round6 9-column format). Jobs exceeding 8h
wall are recorded (not retried) when their .lck disappears.

Usage: python m08_solver.py
"""
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ABAQUS_BAT = r"F:\SIMULIA\Commands\abaqus.bat"
SCRATCH = r"F:\abaqus_scratch"
MAX_CONC = 2
WALL_LIMIT_S = 8 * 3600
POLL_S = 20
STOP_AFTER_CONSEC = 3  # discipline 4: 3 consecutive same-signature failures

# RESUME window (user-approved 2026-09-27 00:3x): hard deadline 12:00 today
DEADLINE = datetime(2026, 9, 27, 12, 0, 0)
GATE_TIME = datetime(2026, 9, 27, 10, 0, 0)  # projected-timeout M2/M3 gate

LEDGER_COLS = ["case", "job", "parent_design_id", "start_time", "config",
               "status", "last_step_time", "termination_evidence", "notes"]
CONFIG = ("cpus=4 memory=6GB double=both scratch=F:\\abaqus_scratch "
          "Abaqus/Explicit z-drive U3=-10.0 smoothstep T=0.1s")


def log(msg):
    print(time.strftime("[%H:%M:%S] ") + msg, flush=True)


def manifest_rows():
    return sorted(csv.DictReader(open(os.path.join(
        ROOT, "selection_manifest_m08.csv"), encoding="utf-8")),
        key=lambda r: int(r["queue_order"]))


def dc_pass(case_id):
    p = os.path.join(ROOT, "cases", case_id, "solver", "datacheck",
                     "datacheck_result.json")
    if not os.path.isfile(p):
        return None
    return json.load(open(p, encoding="utf-8")).get("gate_pass") is True


def solved(case_id):
    return os.path.isfile(os.path.join(ROOT, "cases", case_id, "results",
                                       "solve_result.json"))


def write_bat(solver, job, bat_path):
    assert "%" not in bat_path
    lines = [
        "@echo off",
        f"cd /d {solver}",
        f"{ABAQUS_BAT} job={job} input={job}_zexp.inp cpus=4 memory=6GB "
        f"double=both scratch={SCRATCH} > solve.log 2>&1",
    ]
    text = "\r\n".join(lines) + "\r\n"
    assert "%" not in text, "bat must not contain percent characters"
    with open(bat_path, "w", encoding="ascii", newline="") as f:
        f.write(text)


def launch(case_id, job):
    solver = os.path.join(ROOT, "cases", case_id, "solver")
    bat = os.path.join(solver, f"solve_{job}.bat")
    write_bat(solver, job, bat)
    ps = ("Start-Process -WindowStyle Hidden -FilePath '{}' "
          "-ArgumentList '{}' -PassThru | Select-Object -ExpandProperty Id"
          .format(r"C:\Windows\System32\cmd.exe", "/c " + bat))
    r = subprocess.run(["powershell", "-Command", ps], capture_output=True,
                       text=True)
    pid = r.stdout.strip()
    log(f"launched {case_id} job={job} pid={pid}")
    return {"case_id": case_id, "job": job, "pid": pid,
            "start": time.time(), "start_time": time.strftime(
                "%Y-%m-%d %H:%M:%S")}


def check_com(case_id, job):
    com = os.path.join(ROOT, "cases", case_id, "solver", job + ".com")
    if not os.path.isfile(com):
        return None
    text = open(com, encoding="utf-8", errors="replace").read()
    cpus = memory = double = scratch = None
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("'cpus':"):
            cpus = s.split(":", 1)[1].strip().rstrip(",")
        elif s.startswith("'memory':"):
            memory = s.split(":", 1)[1].strip().rstrip(",")
        elif s.startswith("'double':"):
            double = s.split(":", 1)[1].strip().rstrip(",")
        elif s.startswith("'scratch':"):
            scratch = s.split(":", 1)[1].strip().rstrip(",")
    return {"cpus": cpus, "memory": memory, "double": double,
            "scratch": scratch}


def append_ledger(row):
    p = os.path.join(ROOT, "batch_ledger.csv")
    exists = os.path.isfile(p)
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS)
        if not exists:
            w.writeheader()
        w.writerow(row)


def rebuild_ledger(proc):
    """Idempotent: regenerate batch_ledger.csv from per-case evidence
    (solve_result.json / datacheck_result.json / prep_status.json)."""
    rows = []
    for r in sorted(proc.values(), key=lambda x: int(x["queue_order"])):
        c = r["case_id"]
        res_p = os.path.join(ROOT, "cases", c, "results", "solve_result.json")
        dc_p = os.path.join(ROOT, "cases", c, "solver", "datacheck",
                            "datacheck_result.json")
        prep_p = os.path.join(ROOT, "cases", c, "solver", "prep_status.json")
        if os.path.isfile(res_p):
            res = json.load(open(res_p, encoding="utf-8"))
            gate = res.get("energy_gate", {})
            notes = [f"com cpus/memory/double recorded in solve_result.json"]
            if gate:
                notes.append(f"ke/ALLIE max={gate.get('ke_ratio_max')}, "
                             f"ae/ALLIE max={gate.get('ae_ratio_max')} "
                             f"-> quasi_static={gate.get('quasi_static')}")
            if res.get("error_signature"):
                notes.append("sig: " +
                             " | ".join(res["error_signature"])[:200])
            m0 = [g for g in res.get("mass_scaling_grep", [])
                  if "CHNG MASS" in g or "percent" in g.lower()]
            if m0:
                notes.append("mass: " + m0[0][:130])
            eps = ""
            if res.get("final_u3_mm") is not None:
                eps = f" ({abs(res['final_u3_mm'])/40*100:.4f}% strain)"
            rows.append({
                "case": c, "job": r["job_name"],
                "parent_design_id": r["parent_design_id"],
                "start_time": res.get("solve_start_time", ""),
                "config": CONFIG,
                "status": res.get("judgment", "?"),
                "last_step_time": (f"{res.get('final_step_time')} (T=0.1){eps}"
                                   if res.get("final_step_time") is not None
                                   else "n/a"),
                "termination_evidence": "; ".join(
                    (res.get("sta_tail") or ["no sta"])[-1:])[:200] or "no sta",
                "notes": " | ".join(notes)[:600],
            })
        elif os.path.isfile(prep_p):
            rows.append({"case": c, "job": r["job_name"],
                         "parent_design_id": r["parent_design_id"],
                         "start_time": "", "config": "",
                         "status": "not_started_prep_failed",
                         "last_step_time": "n/a",
                         "termination_evidence": "no solve launched",
                         "notes": json.load(open(prep_p,
                                                 encoding="utf-8"))
                         .get("error", "")[:200]})
        elif os.path.isfile(dc_p):
            dc = json.load(open(dc_p, encoding="utf-8"))
            ok = dc.get("gate_pass") is True
            rows.append({"case": c, "job": r["job_name"],
                         "parent_design_id": r["parent_design_id"],
                         "start_time": "", "config": "",
                         "status": ("not_started_datacheck_failed"
                                    if not ok else "not_started_pending_solve"),
                         "last_step_time": "n/a",
                         "termination_evidence": "no solve launched",
                         "notes": ("dc errors: " +
                                   "; ".join(dc.get("errors", []))[:180])
                         if not ok else ""})
        else:
            rows.append({"case": c, "job": r["job_name"],
                         "parent_design_id": r["parent_design_id"],
                         "start_time": "", "config": "",
                         "status": "not_started_pending_prep",
                         "last_step_time": "n/a",
                         "termination_evidence": "no solve launched",
                         "notes": ""})
    with open(os.path.join(ROOT, "batch_ledger.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS)
        w.writeheader()
        w.writerows(rows)


def finalize(run, proc):
    case_id, job = run["case_id"], run["job"]
    solver = os.path.join(ROOT, "cases", case_id, "solver")
    results = os.path.join(ROOT, "cases", case_id, "results")
    wall_s = time.time() - run["start"]
    log(f"finished {case_id} after {wall_s/60:.1f} min; extracting")
    r = subprocess.run([sys.executable, os.path.join(HERE,
                       "m08_extract_case.py"), case_id],
                       capture_output=True, text=True)
    print(r.stdout[-4000:], r.stderr[-2000:], flush=True)
    res = {}
    p = os.path.join(results, "solve_result.json")
    if os.path.isfile(p):
        res = json.load(open(p, encoding="utf-8"))
        res["solve_start_time"] = run["start_time"]
        res["wall_s"] = round(wall_s, 1)
        com = check_com(case_id, job)
        res["com_values"] = com
        if wall_s > WALL_LIMIT_S:
            res["wall_limit_8h_exceeded"] = True
        with open(p, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)
    status = res.get("judgment", "extraction_failed")
    rebuild_ledger(proc)
    update_manifest_status(case_id, status)
    log(f"{case_id}: ledger rebuilt, status={status}")


def update_manifest_status(case_id, status):
    p = os.path.join(ROOT, "selection_manifest_m08.csv")
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    cols = rows[0].keys()
    for r in rows:
        if r["case_id"] == case_id:
            r["solver_status"] = status
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def free_mem_gb():
    # "available" (free + standby-reclaimable) — FreePhysicalMemory undercounts
    # when large ODB file caches sit in the standby list
    r = subprocess.run(["powershell", "-Command",
                        "[math]::Round((Get-CimInstance "
                        "Win32_PerfFormattedData_PerfOS_Memory)"
                        ".AvailableMBytes/1024,1)"],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def main():
    lockf = os.path.join(HERE, "scheduler.lock")
    if os.path.exists(lockf):
        old = None
        try:
            old = int(open(lockf).read().strip())
        except (ValueError, OSError):
            pass
        if old is not None:
            alive = False
            r = subprocess.run(["tasklist", "/FI", f"PID eq {old}"],
                               capture_output=True, text=True)
            alive = f"{old}" in (r.stdout or "")
            if alive:
                raise SystemExit(f"another scheduler (pid {old}) already running")
    import os as _os
    with open(lockf, "w") as f:
        f.write(str(_os.getpid()))
    try:
        _main_loop()
    finally:
        if os.path.exists(lockf):
            try:
                os.remove(lockf)
            except OSError:
                pass


def class_median_min(proc):
    """Median wall minutes per method from decided solves (RESUME projection)."""
    by = {}
    for r in proc.values():
        p = os.path.join(ROOT, "cases", r["case_id"], "results",
                         "solve_result.json")
        if os.path.isfile(p):
            d = json.load(open(p, encoding="utf-8"))
            if d.get("wall_s"):
                by.setdefault(r["method"], []).append(d["wall_s"] / 60.0)
    import statistics
    return {m: statistics.median(v) for m, v in by.items()}


def _main_loop():
    proc = {r["case_id"]: r for r in manifest_rows()}
    running = []
    consec_sigs = []
    stopped = False
    # adopt orphan in-flight solves from a previous scheduler instance
    for r in proc.values():
        c, j = r["case_id"], r["job_name"]
        if r.get("solver_status", "") == "practical_terminated":
            log(f"skip {c}: practical_terminated (never adopt, even with lck)")
            continue
        lck = os.path.join(ROOT, "cases", c, "solver", j + ".lck")
        if os.path.isfile(lck) and not solved(c):
            mtime = os.path.getmtime(lck)
            log(f"adopting in-flight {c} (lck since "
                f"{time.strftime('%H:%M:%S', time.localtime(mtime))})")
            running.append({"case_id": c, "job": j, "pid": "?",
                            "start": mtime,
                            "start_time": time.strftime(
                                "%Y-%m-%d %H:%M:%S", time.localtime(mtime))})
    log("M08 solver scheduler start")
    while True:
        # finalize finished runs
        still = []
        for run in running:
            lck = os.path.join(ROOT, "cases", run["case_id"], "solver",
                               run["job"] + ".lck")
            if os.path.isfile(lck):
                if time.time() - run["start"] > WALL_LIMIT_S:
                    log(f"{run['case_id']}: over 8h wall, still running; "
                        "leaving it (record at termination)")
                still.append(run)
            else:
                finalize(run, proc)
                # discipline 4: consecutive same-signature stop rule
                p = os.path.join(ROOT, "cases", run["case_id"], "results",
                                 "solve_result.json")
                sig = ""
                if os.path.isfile(p):
                    sig = (json.load(open(p, encoding="utf-8"))
                           .get("error_signature") or [""])[0][:80]
                if sig:
                    if consec_sigs and consec_sigs[-1] == sig:
                        consec_sigs.append(sig)
                    else:
                        consec_sigs = [sig]
                else:
                    consec_sigs = []
                if len(consec_sigs) >= STOP_AFTER_CONSEC and not stopped:
                    # Ruling (EXECUTION_STATE 2026-09-25): the plan's
                    # "3 consecutive same-signature -> stop" targets
                    # SYSTEMATIC failure. A live run or any non-solver_error
                    # result is a counterexample to "systematic"; stop only
                    # when the streak is >=3 AND nothing is running AND no
                    # healthy result exists in the batch.
                    healthy = any(
                        (json.load(open(os.path.join(
                            ROOT, "cases", r["case_id"], "results",
                            "solve_result.json"), encoding="utf-8"))
                         .get("judgment") != "solver_error")
                        for r in proc.values() if solved(r["case_id"]))
                    if running or healthy:
                        if not getattr(main, "_streak_note", False):
                            log(f"streak {len(consec_sigs)}x {sig!r} observed "
                                "but a live run / healthy result exists -> "
                                "not systematic, continuing (ruling)")
                            main._streak_note = True
                    else:
                        stopped = True
                        msg = (f"BATCH STOPPED by discipline 4: "
                               f"{len(consec_sigs)} consecutive solves with "
                               f"same signature and no counterexample: {sig!r}")
                        log(msg)
                        with open(os.path.join(ROOT, "EXECUTION_STATE.md"),
                                  "a", encoding="utf-8") as f:
                            f.write(f"\n- {time.strftime('%Y-%m-%d %H:%M:%S')} "
                                    f"{msg}\n")
        running = still
        now = datetime.now()
        if now >= DEADLINE:
            # hard stop: terminate everything in flight, finalize, exit
            log("DEADLINE 12:00 reached: terminating all in-flight solves")
            os.environ["M08_DEADLINE_TERMINATE"] = "1"
            for run in running:
                comspec = os.environ.get("COMSPEC") or \
                    r"C:\Windows\System32\cmd.exe"
                subprocess.run([comspec, "/c", ABAQUS_BAT,
                                f"job={run['job']}", "terminate"],
                               capture_output=True, text=True)
                log(f"terminate issued for {run['case_id']}")
            # wait for lcks (graceful: solver writes final frames)
            wait_deadline = time.time() + 3600
            for run in running:
                lck = os.path.join(ROOT, "cases", run["case_id"], "solver",
                                   run["job"] + ".lck")
                while os.path.isfile(lck) and time.time() < wait_deadline:
                    time.sleep(15)
            for run in running:
                finalize(run, proc)
            rebuild_ledger(proc)
            log("DEADLINE window closed; scheduler exiting")
            break
        if stopped:
            if not running:
                break
            time.sleep(POLL_S)
            continue
        # launch new (resource gate >=16GB free; projection gate after 10:00)
        med = class_median_min(proc)
        for row in proc.values():
            if len(running) >= MAX_CONC:
                break
            c = row["case_id"]
            if solved(c) or any(x["case_id"] == c for x in running):
                continue
            if row.get("solver_status", "") == "practical_terminated":
                continue
            if dc_pass(c) is True:
                mem = free_mem_gb()
                if mem < 16.0:
                    log(f"memory gate: {mem}GB free < 16GB, holding launch")
                    break
                if now >= GATE_TIME and row["method"] in ("M2", "M3"):
                    proj = med.get(row["method"], 1e9)
                    if now.timestamp() + proj * 60 > DEADLINE.timestamp():
                        log(f"projection gate: {c} ({row['method']}, median "
                            f"{proj:.0f} min) would finish after 12:00; skip")
                        continue
                running.append(launch(c, row["job_name"]))
                time.sleep(10)  # stagger
        # exit?
        pending = [r["case_id"] for r in proc.values()
                   if not solved(r["case_id"])
                   and dc_pass(r["case_id"]) is None]
        failed_dc = [r["case_id"] for r in proc.values()
                     if dc_pass(r["case_id"]) is False]
        if not pending and not running:
            log(f"all cases decided; dc_failed={len(failed_dc)}")
            break
        time.sleep(POLL_S)
    rebuild_ledger(proc)
    log("M08_SOLVER_SCHEDULER_DONE")


if __name__ == "__main__":
    main()
