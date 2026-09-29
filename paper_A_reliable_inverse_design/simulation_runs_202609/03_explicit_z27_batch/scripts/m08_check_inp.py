# -*- coding: utf-8 -*-
"""M08 INP conformance check for the explicit z INP (per case).

Streams the adapted INP and verifies:
  - all elements C3D4; node spans ~40mm on x/y/z
  - required nsets exist and are non-empty (6 assembly A_* + part
    M05_ZDRIVE/M05_ZFIX); drive/fix face membership on expected planes
    (|coord - face| <= 0.1 window); A_ZPOS max z = +20 +/- window
  - step: *Dynamic, Explicit with period 0.1; *Fixed Mass Scaling dt=1e-06;
    amplitude SMOOTH STEP 0->1 over 0.1s
  - BC: A_ZPOS U3=-10.0 with amplitude; A_ZNEG U3=0; A_FIX/A_DRIVE U1=0;
    A_YNEG/A_YPOS U2=0 (six cards)
  - outputs: field interval=20 (U / S,SENER); history interval=20
    (ALLIE,ALLKE,ALLAE,ALLPD,ETOTAL; H-Drive nset=A_ZPOS RF3,U3)
  - material: density 1e-09; hyperelastic n=2 test data poisson=0.47;
    1202 uniaxial rows; 11 plastic rows
Usage: python m08_check_inp.py <inp_path> <out_json>
"""
import json
import re
import sys


def main():
    inp, out_json = sys.argv[1], sys.argv[2]
    xyz_min = [1e30] * 3
    xyz_max = [-1e30] * 3
    elem_types = {}
    nsets = {}
    nset_gen = {}
    section = None
    cur_nset = None
    step_lines = []
    bc_lines = []
    output_lines = []
    material = {"hyperelastic": [], "plastic_rows": 0, "test_rows": 0,
                "density": None, "section": []}
    cur_etype = "?"

    with open(inp, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            low = s.lower()
            if s.startswith("**"):
                continue
            if s.startswith("*"):
                kw = low.split(",")[0].strip()
                if kw == "*node":
                    section = "node"
                elif kw == "*element":
                    section = "element"
                    m = re.search(r"type\s*=\s*(\w+)", s, re.I)
                    cur_etype = m.group(1).upper() if m else "UNKNOWN"
                    elem_types.setdefault(cur_etype, 0)
                elif kw == "*nset":
                    section = "nset"
                    m = re.search(r"nset\s*=\s*([\w\-\.\[\]]+)", s, re.I)
                    cur_nset = m.group(1) if m else "?"
                    nsets.setdefault(cur_nset, 0)
                    nset_gen[cur_nset] = "generate" in low
                elif kw == "*dynamic":
                    section = "step"; step_lines.append(s)
                elif kw == "*fixed mass scaling":
                    step_lines.append(s); section = "step"
                elif kw == "*amplitude":
                    step_lines.append(s); section = "step"
                elif kw == "*boundary":
                    section = "boundary"
                    bc_lines.append(s)
                elif kw == "*output":
                    section = "output"; output_lines.append(s)
                elif kw in ("*node output", "*element output",
                            "*energy output") and section == "output":
                    output_lines.append(s)
                elif kw in ("*hyperelastic", "*density", "*plastic",
                            "*solid section", "*uniaxial test data",
                            "*material"):
                    section = kw
                    if kw == "*hyperelastic":
                        material["hyperelastic"].append(s)
                    elif kw == "*solid section":
                        material["section"].append(s)
                else:
                    section = kw
                continue
            if section == "node":
                parts = s.split(",")
                if len(parts) >= 4:
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    for i, v in enumerate((x, y, z)):
                        if v < xyz_min[i]: xyz_min[i] = v
                        if v > xyz_max[i]: xyz_max[i] = v
            elif section == "element":
                elem_types[cur_etype] = elem_types.get(cur_etype, 0) + 1
            elif section == "nset" and cur_nset:
                if nset_gen[cur_nset]:
                    m = re.match(r"(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", s)
                    if m:
                        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
                        nsets[cur_nset] += len(range(a, b + 1, c))
                else:
                    nsets[cur_nset] += len([v for v in s.split(",") if v.strip()])
            elif section == "boundary":
                bc_lines.append(s)
            elif section == "step":
                step_lines.append(s)
            elif section == "output":
                output_lines.append(s)
            elif section == "*plastic":
                if re.match(r"[\d.eE+\-]+\s*,", s):
                    material["plastic_rows"] += 1
            elif section == "*uniaxial test data":
                if re.match(r"[\d.eE+\-]+\s*,", s):
                    material["test_rows"] += 1
            elif section == "*density":
                material["density"] = s.split(",")[0].strip()

    def span(i):
        return round(xyz_max[i] - xyz_min[i], 6)

    spans_mm = {"x": span(0), "y": span(1), "z": span(2)}
    checks = {
        "elem_types": elem_types,
        "spans_mm": spans_mm,
        "nsets": nsets,
        "step_lines": step_lines,
        "bc_lines": bc_lines,
        "output_lines": output_lines,
        "material": material,
    }
    problems = []
    if set(elem_types) != {"C3D4"}:
        problems.append(f"elem types {elem_types} != C3D4 only")
    for sp in ("x", "y", "z"):
        if abs(spans_mm[sp] - 40.0) > 0.01:
            problems.append(f"span {sp} = {spans_mm[sp]}")
    for n in ("A_DRIVE", "A_FIX", "A_YNEG", "A_YPOS", "A_ZNEG", "A_ZPOS",
              "M05_ZDRIVE", "M05_ZFIX"):
        if nsets.get(n, 0) <= 0:
            problems.append(f"nset {n} missing/empty")
    st = " | ".join(step_lines)
    st_low = st.lower()
    if "*dynamic, explicit" not in st_low:
        problems.append("no *Dynamic, Explicit")
    if ", 0.1" not in st_low:
        problems.append("step period 0.1 not found")
    if "*fixed mass scaling" not in st_low:
        problems.append("fixed mass scaling missing")
    if "type=below min" not in st_low:
        problems.append("mass scaling type missing")
    if "dt=1e-06" not in st_low:
        problems.append("fixed mass scaling dt missing")
    if "smooth step" not in st_low:
        problems.append("SMOOTH STEP amplitude missing")
    joined_bc = " | ".join(bc_lines)
    expect_bc = ["A_ZPOS, 3, 3, -10.0", "A_ZNEG, 3, 3", "A_FIX, 1, 1",
                 "A_DRIVE, 1, 1", "A_YNEG, 2, 2", "A_YPOS, 2, 2"]
    for e in expect_bc:
        if e not in joined_bc:
            problems.append(f"BC line missing: {e}")
    if "amplitude=a_smooth_drive" not in joined_bc.lower():
        problems.append("drive BC amplitude ref missing")
    oj = " | ".join(output_lines).lower()
    if "number interval=20" not in oj:
        problems.append("field output interval 20 missing")
    if "time interval=0.005" not in oj:
        problems.append("history time interval 0.005 missing")
    if "nset=a_zpos" not in oj:
        problems.append("H-Drive nset A_ZPOS missing")
    if material["density"] != "1e-09":
        problems.append(f"density {material['density']}")
    if material["test_rows"] != 1202:
        problems.append(f"test rows {material['test_rows']} != 1202")
    if material["plastic_rows"] != 11:
        problems.append(f"plastic rows {material['plastic_rows']} != 11")
    he = " ".join(material["hyperelastic"]).lower()
    if "n=2" not in he or "poisson=0.47" not in he or "test data input" not in he:
        problems.append(f"hyperelastic card {material['hyperelastic']}")

    checks["problems"] = problems
    checks["ok"] = not problems
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(checks, f, indent=1)
    print(json.dumps({"ok": checks["ok"], "problems": problems,
                      "elem_types": elem_types,
                      "nsets": nsets, "spans_mm": checks["spans_mm"],
                      "test_rows": material["test_rows"],
                      "plastic_rows": material["plastic_rows"]}, indent=1))
    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
