# -*- coding: utf-8 -*-
"""M08 selection manifest builder (27 cases = 9 per class).

Rule (plan 2026-09-25-m08-explicit-z27.md section 1):
  - certified pool = gate0 fixture small_gate0_rows.json, 36 rows = 12/12/12
    (sha256 a67890d0...), M04-v2 selection.
  - per class 9 = the 4 zload12-selected rows + 5 supplements.
  - supplements: from the 8 remaining rows of that class, picked across the
    relativeVolume span (low/mid/high). Deterministic rule: for i in 0..4,
    target_rv = rv_min + i*(rv_max-rv_min)/4 over the 8 remaining rows;
    pick the remaining row whose rv is closest to target_rv
    (ties -> lower excel_row). Substitute backup = closest remaining
    unchosen row (documented, used only if a case fails preprocessing).
"""
import csv
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURE = ("F:/small++/.worktrees/m03-continuous-csg-impl/"
           "paper_A_reliable_inverse_design/geometry_compiler_matlab/"
           "tests/fixtures/small_gate0_rows.json")
ZLOAD12_MANIFEST = ("C:/Users/48186/Desktop/zload12_handoff_20260924/"
                    "00_plan/selection_manifest.csv")

ZLOAD12_BY_CLASS = {
    "class1": [944, 1424, 763, 1145],
    "class2": [1383, 833, 871, 45],
    "class12": [665, 1390, 61, 26],
}
# reuse-mesh cases whose C3D4 volume mesh exists hash-listed in the
# zload12 handoff MESH_HASHES.csv (9 designs); keyed by row_id (excel_row
# alone is ambiguous: 1145 exists in both class1 and class2)
REUSE_MESH = {"class1:944", "class1:1424", "class1:763", "class1:1145",
              "class2:1383", "class12:665", "class12:1390", "class12:61",
              "class12:26"}
METHOD_OF_SHEET = {"class1": "M1", "class2": "M2", "class12": "M3"}


def main():
    fx = json.load(open(FIXTURE, encoding="utf-8"))
    fixture_sha = hashlib.sha256(open(FIXTURE, "rb").read()).hexdigest()
    assert fixture_sha.startswith("a67890d0"), fixture_sha
    assert fx["workbook_sha256"].startswith("b4544b09"), fx["workbook_sha256"]

    rows_by_sheet = {}
    for r in fx["rows"]:
        rows_by_sheet.setdefault(r["sheet"], []).append(r)
    for sheet, rows in rows_by_sheet.items():
        assert len(rows) == 12, (sheet, len(rows))

    z12 = {}
    for r in csv.DictReader(open(ZLOAD12_MANIFEST, encoding="utf-8")):
        z12[int(r["parent_design_id"].split(":")[1])] = r
    assert len(z12) == 12

    manifest = []
    for sheet in ("class1", "class2", "class12"):
        method = METHOD_OF_SHEET[sheet]
        rows = rows_by_sheet[sheet]
        chosen = []          # (fixture_row, kind, reason)
        chosen_rows = set()
        for er in ZLOAD12_BY_CLASS[sheet]:
            fr = next(x for x in rows if x["excel_row"] == er)
            z = z12[er]
            reason = ("zload12 selected (order %s): %s" %
                      (z["order"], z["selection_reason"]))
            chosen.append((fr, "zload12_selected", reason))
            chosen_rows.add(er)

        # supplements across the rv span of the remaining 8
        remaining = [x for x in rows if x["excel_row"] not in chosen_rows]
        assert len(remaining) == 8, (sheet, len(remaining))
        rvs = [x["archived_descriptors"]["relativeVolume"] for x in remaining]
        rv_min, rv_max = min(rvs), max(rvs)
        picked = []
        pool = list(remaining)
        for i in range(5):
            target = rv_min + i * (rv_max - rv_min) / 4.0
            best = min(pool,
                       key=lambda x: (abs(x["archived_descriptors"]["relativeVolume"] - target),
                                      x["excel_row"]))
            picked.append(best)
            pool.remove(best)
            span_note = ("low", "mid-low", "mid", "mid-high", "high")[i]
            chosen.append((best, "supplement",
                           "supplement %d/5: rv %.3f closest to span target %.3f (%s of remaining-rv span); "
                           "rule: rv-spread quantile over the 8 rows not chosen by zload12"
                           % (i + 1, best["archived_descriptors"]["relativeVolume"],
                              target, span_note)))
        assert len(pool) == 3
        # substitute backups: closest unchosen remaining row per chosen supplement
        backups = {}
        for fr, kind, _ in chosen:
            if kind != "supplement":
                continue
            rv0 = fr["archived_descriptors"]["relativeVolume"]
            b = min(pool, key=lambda x: (abs(x["archived_descriptors"]["relativeVolume"] - rv0),
                                         x["excel_row"]))
            backups[fr["excel_row"]] = b

        # reuse-mesh rows first within the class (unblocks early solves)
        chosen.sort(key=lambda t: (0 if t[0]["row_id"] in REUSE_MESH else 1,
                                   t[0]["excel_row"]))
        for fr, kind, reason in chosen:
            er = fr["excel_row"]
            rv = fr["archived_descriptors"]["relativeVolume"]
            raw = fr["raw_parameters"]
            sub = ""
            if er in backups:
                b = backups[er]
                sub = ("%s (rv=%.3f)" % (b["row_id"],
                                         b["archived_descriptors"]["relativeVolume"]))
            manifest.append({
                "case_id": "m%d_%s_%d" % ({"M1": 1, "M2": 2, "M3": 3}[method],
                                          {"class1": "class1", "class2": "class2",
                                           "class12": "class12"}[sheet], er),
                "job_name": "m08_%s_%d" % ({"M1": "m1", "M2": "m2", "M3": "m3"}[method], er),
                "method": method,
                "sheet": sheet,
                "parent_design_id": fr["row_id"],
                "excel_row": er,
                "c0": repr(raw["c0"]),
                "c1": repr(raw["c1"]),
                "c2": repr(raw["c2"]),
                "w": repr(raw["w"]),
                "archived_relativeVolume": rv,
                "selection_kind": kind,
                "mesh_source": ("reuse_handoff" if fr["row_id"] in REUSE_MESH
                                else "new_compile"),
                "selection_reason": reason,
                "substitute_for_preprocess_failure": sub,
                "selection_digest": fr["selection_digest"],
                "fixture_sha256": fixture_sha,
                "workbook_sha256": fx["workbook_sha256"],
                "role": fr["role"],
                "solver_status": "not_run",
                "notes": "",
            })

    # queue_order: round-robin across M1/M2/M3, reuse-mesh first inside class
    by_method = {}
    for m in manifest:
        by_method.setdefault(m["method"], []).append(m)
    order = 0
    more = True
    while more:
        more = False
        for meth in ("M1", "M2", "M3"):
            lst = by_method[meth]
            if lst:
                m = lst.pop(0)
                order += 1
                m["queue_order"] = order
                more = True

    out = os.path.join(ROOT, "selection_manifest_m08.csv")
    cols = ["case_id", "job_name", "queue_order", "method", "sheet",
            "parent_design_id", "excel_row", "c0", "c1", "c2", "w",
            "archived_relativeVolume", "selection_kind", "mesh_source",
            "selection_reason", "substitute_for_preprocess_failure",
            "selection_digest", "fixture_sha256", "workbook_sha256",
            "role", "solver_status", "notes"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for m in sorted(manifest, key=lambda x: x["queue_order"]):
            w.writerow(m)
    print("wrote", out, len(manifest), "rows")
    for m in sorted(manifest, key=lambda x: x["queue_order"]):
        print("%2d %-16s %-3s rv=%.3f %-9s %s" %
              (m["queue_order"], m["case_id"], m["method"],
               m["archived_relativeVolume"], m["mesh_source"],
               m["selection_kind"]))


if __name__ == "__main__":
    main()
