# -*- coding: utf-8 -*-
"""M08 per-case preparation driver.

Subcommands:
  build <case_id>  run the M05 gen_build_model.py on the staged mesh INP,
                   then text-patch ONLY the new-dir copy of build_model.py
                   with the 2 part-level node sets M05_ZFIX/M05_ZDRIVE
                   (extraction handles; same bounding boxes as A_ZNEG/A_ZPOS;
                   see EXECUTION_STATE.md ruling). Then run Abaqus/CAE noGUI
                   to write the implicit solver INP (<job>.inp, drive -10.0).
  adapt <case_id>  run z_explicit_adapter.py: <job>.inp -> <job>_zexp.inp
                   (prefix byte-identical assertion inside).
  check <case_id>  run m08_check_inp.py on <job>_zexp.inp.
  all <case_id>    build + adapt + check.

Parameters read from ../selection_manifest_m08.csv.
"""
import csv
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
M05_SCRIPTS = ("F:/small++/paper_A_reliable_inverse_design/"
               "audits/m05_small_mechanism_pilot_20260919/scripts")
ABAQUS_BAT = r"F:\SIMULIA\Commands\abaqus.bat"

PATCH_LINES = [
    'p.Set(nodes=p.nodes.getByBoundingBox(**ZN_BB), name="M05_ZFIX")',
    'p.Set(nodes=p.nodes.getByBoundingBox(**ZP_BB), name="M05_ZDRIVE")',
]
ANCHOR = 'p.Set(nodes=p.nodes.getByBoundingBox(**DRV_BB), name="M05_DRIVE")'


def load_manifest():
    with open(os.path.join(ROOT, "selection_manifest_m08.csv"),
              encoding="utf-8") as f:
        return {r["case_id"]: r for r in csv.DictReader(f)}


def case_paths(case_id):
    c = os.path.join(ROOT, "cases", case_id)
    return {
        "case": c,
        "outputs": os.path.join(c, "mesh", "outputs"),
        "solver": os.path.join(c, "solver"),
    }


def sh(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, **kw)


def cmd_build(case_id):
    P = case_paths(case_id)
    row = load_manifest()[case_id]
    inp_path = os.path.join(P["outputs"], f"{case_id}_volume_mesh_c3d4.inp")
    assert os.path.isfile(inp_path), f"{case_id}: mesh inp missing: {inp_path}"
    solver = P["solver"]
    os.makedirs(solver, exist_ok=True)
    job_name = row["job_name"]
    if os.path.isfile(os.path.join(solver, f"{job_name}.inp")):
        print(f"{case_id}: {job_name}.inp already built; skipping CAE "
              "(delete to rebuild)")
        return
    r = sh([sys.executable, os.path.join(M05_SCRIPTS, "gen_build_model.py"),
            inp_path, solver, job_name], capture_output=True, text=True)
    print(r.stdout.strip(), r.stderr.strip())
    assert r.returncode == 0, f"{case_id}: gen_build_model failed"

    src = os.path.join(solver, "build_model.py")
    text = open(src, encoding="utf-8").read()
    n = text.count(ANCHOR)
    assert n == 1, f"{case_id}: anchor found {n} times, expected 1"
    assert 'name="M05_ZDRIVE"' not in text
    text = text.replace(ANCHOR, ANCHOR + "\n" + "\n".join(PATCH_LINES))
    with open(src, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    with open(os.path.join(solver, "build_patch.diff"), "w",
              encoding="utf-8") as f:
        f.write(
            "# M08 patch vs m05 gen_build_model.py output (drive kept -10.0;\n"
            "# numCpus left at job-card value, irrelevant: solve uses command line)\n"
            "# +2 part-level node sets (extraction handles for extract_odb.py,\n"
            "# which requires instance nodeSets; assembly A_* sets do not appear\n"
            "# there - verified on m06_m1_1145.odb). BCs still reference A_* sets.\n"
            "--- (before)\n"
            "+++ (after)\n"
            "+ " + "\n+ ".join(PATCH_LINES) + "\n")
    print(f"{case_id}: build_model.py patched (+2 part nsets)")

    log = open(os.path.join(solver, "build_cae.log"), "w", encoding="utf-8")
    comspec = os.environ.get("COMSPEC") or r"C:\Windows\System32\cmd.exe"
    r2 = sh([comspec, "/c", ABAQUS_BAT, "cae", f"noGUI=build_model.py"],
            stdout=log, stderr=subprocess.STDOUT, cwd=solver)
    log.close()
    print(f"{case_id}: abaqus cae exit={r2.returncode}")
    out_inp = os.path.join(solver, f"{job_name}.inp")
    assert r2.returncode == 0 and os.path.isfile(out_inp), \
        f"{case_id}: CAE build failed, see {solver}/build_cae.log"
    print(f"{case_id}: implicit INP written: {out_inp}")


def cmd_adapt(case_id):
    P = case_paths(case_id)
    row = load_manifest()[case_id]
    job = row["job_name"]
    src = os.path.join(P["solver"], f"{job}.inp")
    dst = os.path.join(P["solver"], f"{job}_zexp.inp")
    assert os.path.isfile(src), src
    r = sh([sys.executable, os.path.join(HERE, "z_explicit_adapter.py"), src, dst])
    assert r.returncode == 0, f"{case_id}: adapter assertions failed"


def cmd_check(case_id):
    P = case_paths(case_id)
    row = load_manifest()[case_id]
    job = row["job_name"]
    inp = os.path.join(P["solver"], f"{job}_zexp.inp")
    out = os.path.join(P["solver"], "inp_check.json")
    r = sh([sys.executable, os.path.join(HERE, "m08_check_inp.py"), inp, out])
    assert r.returncode == 0, f"{case_id}: inp check failed, see {out}"


if __name__ == "__main__":
    cmd = sys.argv[1]
    case_id = sys.argv[2]
    if cmd == "build":
        cmd_build(case_id)
    elif cmd == "adapt":
        cmd_adapt(case_id)
    elif cmd == "check":
        cmd_check(case_id)
    elif cmd == "all":
        cmd_build(case_id)
        cmd_adapt(case_id)
        cmd_check(case_id)
    else:
        raise SystemExit(__doc__)
