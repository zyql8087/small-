# Guarded STL short-edge collapse (option 1).
# Guards: manifold edges only (exactly 2 adjacent tris), normal-flip <=60deg,
# area-drop <=50%, plane-vertex protection. Drops degenerate tris after each round.
import numpy as np
import struct

IN_STL = r"F:/small++/paper_A_reliable_inverse_design/audits/m06_m1m3_c3d4_night_20260923/cases/m3_class12_26/mesh/geometry.stl"
OUT_STL = r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/diagnosis_transient/geometry_guarded.stl"
TOL = 0.05
ANG_GUARD = 60.0

with open(IN_STL, "rb") as f:
    hdr = f.read(80); n = struct.unpack("<I", f.read(4))[0]
    data = np.frombuffer(f.read(n*50), dtype=np.uint8).reshape(n, 50)
tris_xyz = data[:, 12:48].copy().view("<f4").reshape(n, 3, 3).astype(np.float64)
key = np.round(tris_xyz.reshape(-1, 3), 9)
uniq, inv = np.unique(key, axis=0, return_inverse=True)
verts = uniq.copy()
tri_v = inv.reshape(n, 3).astype(np.int64)
print("loaded: %d tris, %d verts" % (len(tri_v), len(verts)))

def on_plane(v):
    return bool((np.abs(np.abs(verts[v]) - 20) < 1e-6).any())

def tri_normals_and_area(tv):
    p = verts[tv]
    n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    a = 0.5 * np.linalg.norm(n, axis=1)
    return n, a

for rnd in range(1, 10):
    # edge -> adjacent triangle list
    ea = np.concatenate([tri_v[:, [0, 1]], tri_v[:, [1, 2]], tri_v[:, [2, 0]]], axis=0)
    tri_id = np.tile(np.arange(len(tri_v)), 3)
    esorted = np.sort(ea, axis=1)
    ue, inv_e, cnts = np.unique(esorted, axis=0, return_inverse=True, return_counts=True)
    el = np.linalg.norm(verts[ue[:, 0]] - verts[ue[:, 1]], axis=1)
    short = np.where(el < TOL)[0]
    # manifold filter: exactly 2 adjacent tris
    e2tri = {}
    for k in short:
        members = tri_id[inv_e == k]
        e2tri[k] = members
    short = np.array([k for k in short if len(e2tri[k]) == 2])
    if len(short) == 0:
        print("round %d: no manifold short edges - done" % rnd); break
    # order short edges by length
    short = short[np.argsort(el[short])]
    merges = {}; used = set(); merged = 0; skipped_guard = 0
    for k in short:
        u, v = int(ue[k, 0]), int(ue[k, 1])
        ru, rv = merges.get(u, u), merges.get(v, v)
        if ru == rv or ru in used or rv in used: continue
        t0, t1 = e2tri[k]
        # keep-point: plane vertex wins; else midpoint
        pu, pv = on_plane(ru), on_plane(rv)
        if pu and not pv: keep_pos = verts[ru].copy(); van, keep = rv, ru
        elif pv and not pu: keep_pos = verts[rv].copy(); van, keep = ru, rv
        elif pu and pv: continue
        else:
            keep_pos = 0.5 * (verts[ru] + verts[rv]); van, keep = rv, ru
        # guards on the two adjacent triangles
        ok = True
        for t in (t0, t1):
            tv0 = tri_v[t].copy()
            if van not in tv0: continue
            n_before, a_before = tri_normals_and_area(tv0[None, :])
            tv1 = tv0.copy(); tv1[tv1 == van] = -1  # placeholder
            tv1[tv1 == -1] = len(verts)  # temp; we compute with new pos below
            # compute after-normal using keep_pos in place of van
            pts = verts[tv0].copy()
            pts[pts_search := (pts == verts[van]).all(1)] = keep_pos
            # simpler: rebuild
            idxs = [keep_pos if (row == verts[van]).all() else row for row in pts]
            pts_after = np.array(idxs)
            n_after = np.cross(pts_after[1] - pts_after[0], pts_after[2] - pts_after[0])
            a_after = 0.5 * np.linalg.norm(n_after)
            if a_before[0] < 1e-14: continue
            if a_after < 0.5 * a_before[0]: ok = False; break
            nb = n_before[0] / (np.linalg.norm(n_before[0]) + 1e-30)
            na = n_after / (np.linalg.norm(n_after) + 1e-30)
            cosang = float(np.clip(np.dot(nb, na), -1, 1))
            if np.degrees(np.arccos(cosang)) > ANG_GUARD: ok = False; break
        if not ok:
            skipped_guard += 1; continue
        verts[van] = keep_pos
        merges[van] = keep
        used.update([ru, rv]); merged += 1
    if merged == 0:
        print("round %d: nothing merged (guard-skipped %d) - stop" % (rnd, skipped_guard)); break
    def res(x):
        seen = set()
        while x in merges:
            assert x not in seen; seen.add(x)
            x = merges[x]
        return x
    flat = tri_v.reshape(-1)
    tv = np.array([res(int(x)) for x in flat]).reshape(tri_v.shape)
    keepm = (tv[:, 0] != tv[:, 1]) & (tv[:, 1] != tv[:, 2]) & (tv[:, 0] != tv[:, 2])
    tv = tv[keepm]
    nn, aa = tri_normals_and_area(tv)
    tv = tv[aa > 1e-10]
    tri_v = tv
    print("round %d: merged %d verts (guard-skipped %d) -> tris %d" % (rnd, merged, skipped_guard, len(tri_v)))

# final stats
ea = np.concatenate([tri_v[:, [0,1]], tri_v[:, [1,2]], tri_v[:, [2,0]]], axis=0)
ue = np.unique(ea, axis=0)
el = np.linalg.norm(verts[ue[:, 0]] - verts[ue[:, 1]], axis=1)
nn, aa = tri_normals_and_area(tri_v)
print("final: tris=%d verts=%d min_edge=%.4g edges<%.2fmm: %d | area_min=%.3g" % (
    len(tri_v), len(verts), el.min(), TOL, (el < TOL).sum(), aa.min()))
with open(OUT_STL, "wb") as f:
    f.write(b"\0" * 80)
    f.write(struct.pack("<I", len(tri_v)))
    for i in range(len(tri_v)):
        f.write(struct.pack("<3f", 0.0, 0.0, 0.0))
        for j in range(3):
            f.write(struct.pack("<3f", *verts[tri_v[i, j]]))
        f.write(struct.pack("<H", 0))
print("wrote", OUT_STL)
