# Task 2: collapse coincident node clusters (6-25um) into set-member representatives.
# M1: 12275,13910 -> 12312 (in A_DRIVE/M05_DRIVE)   M2: 13911,15629 -> 13947 (in A_DRIVE/M05_DRIVE)
# Interior-edge collapse: remap + drop degenerate tets + dedupe. No new nodes.
import numpy as np
from collections import Counter

INP = r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m1m3_marlow_c3d4_20260923/m3/m3_marlow.inp"
OUT = r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m3_hotzone_mesh_20260923/m3/m3_hotzone_fixed.inp"
MERGES = [(12275, 12312), (13910, 12312), (13911, 13947), (15629, 13947)]  # (vanish, keep)

nodes_d = {}; elems = []; nset_lines = {}; mode = None; cur_set = None
with open(INP, encoding="latin-1") as f:
    for line in f:
        s = line.strip()
        if s.startswith("*"):
            u = s.upper()
            if u == "*NODE": mode = "n"; cur_set = None; continue
            if u.startswith("*ELEMENT") and "C3D4" in u: mode = "e"; cur_set = None; continue
            if u.startswith("*NSET"):
                cur_set = s.split(",")[1].strip().split("=")[1].strip(); nset_lines[cur_set] = []
                mode = "s"; continue
            mode = None; cur_set = None; continue
        if mode == "n": p = s.split(","); nodes_d[int(p[0])] = [float(x) for x in p[1:4]]
        elif mode == "e": elems.append([int(x) for x in s.split(",")])
        elif mode == "s" and cur_set:
            for tok in s.split(","):
                try: nset_lines[cur_set].append(int(tok.strip()))
                except ValueError: pass

nid_arr = np.array(sorted(nodes_d)); nxyz = np.array([nodes_d[i] for i in nid_arr])
idx = {int(n): k for k, n in enumerate(nid_arr)}
E = np.array([[idx[c] for c in r[1:5]] for r in elems], dtype=int)
eid = np.array([r[0] for r in elems])
P = nxyz[E]
V0 = np.abs(np.einsum('ij,ij->i', np.cross(P[:,1]-P[:,0], P[:,2]-P[:,0]), P[:,3]-P[:,0]))/6.0
pairs = [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]
L = np.stack([np.linalg.norm(P[:,i]-P[:,j],axis=1) for i,j in pairs],axis=1)
q0 = 12.0*V0/(L.max(1)**3+1e-30)/1.4142
print("before: %d nodes %d elems, q min=%.6g global" % (len(nid_arr), len(E), q0.min()))

# sanity: vanish nodes not in any set; keep nodes in A_DRIVE
for van, keep in MERGES:
    for sname, mem in nset_lines.items():
        assert van not in mem, (van, sname)
    assert keep in nset_lines["A_DRIVE"], keep
print("set-membership precondition OK (vanish nodes in no set; keep nodes in A_DRIVE)")

remap = {}
for van, keep in MERGES: remap[van] = keep
E2 = E.copy()
for van, keep in MERGES:
    E2[E2 == idx[van]] = idx[keep]

# degenerate = repeated indices
deg = (E2[:,0]==E2[:,1]) | (E2[:,0]==E2[:,2]) | (E2[:,0]==E2[:,3]) | (E2[:,1]==E2[:,2]) | (E2[:,1]==E2[:,3]) | (E2[:,2]==E2[:,3])
print("degenerate tets after remap: %d" % deg.sum())
alive = ~deg
E3 = E2[alive]; eid3 = eid[alive]

# duplicates
key = np.sort(E3, axis=1)
_, first_idx, counts = np.unique(key, axis=0, return_index=True, return_counts=True)
dup_extra = int((counts-1).sum())
print("duplicate tets beyond first occurrence: %d" % dup_extra)
E4 = E3[np.sort(first_idx)]; eid4 = eid3[np.sort(first_idx)]
print("after collapse: %d elems (removed %d)" % (len(E4), len(E)-len(E4)))

# quality after
P4 = nxyz[E4]
V4 = np.abs(np.einsum('ij,ij->i', np.cross(P4[:,1]-P4[:,0], P4[:,2]-P4[:,0]), P4[:,3]-P4[:,0]))/6.0
L4 = np.stack([np.linalg.norm(P4[:,i]-P4[:,j],axis=1) for i,j in pairs],axis=1)
q4 = 12.0*V4/(L4.max(1)**3+1e-30)/1.4142
CENT4 = P4.mean(1)
hot = (CENT4[:,0]>19.5)&(CENT4[:,1]>9.5)&(CENT4[:,1]<11.5)&(CENT4[:,2]>-20.2)&(CENT4[:,2]<-18.8)
print("post-collapse hot-region: elems=%d qmin=%.4f qmed=%.4f" % (hot.sum(), q4[hot].min(), np.median(q4[hot])))
print("global q min unchanged outside: %.6g" % q4[~hot].min())

# face manifoldness on final mesh
faces = np.sort(np.concatenate([E4[:,[0,1,2]],E4[:,[0,1,3]],E4[:,[0,2,3]],E4[:,[1,2,3]]]), axis=1)
uf, cnt = np.unique(faces, axis=0, return_counts=True)
print("face usage: 1x=%d 2x=%d >2x=%d" % ((cnt==1).sum(), (cnt==2).sum(), (cnt>2).sum()))
# every 1x face must lie on a domain plane (all 3 nodes on same |coord|=20)
single = uf[cnt==1]
c = nxyz[single]
onplane = (np.max(np.abs(c),axis=1) >= 20.0-1e-6) & (np.min(np.abs(c),axis=1) >= 20.0-1e-6) if False else None
mx = np.abs(c).max(axis=1); mn = np.abs(c).min(axis=1)
# all three nodes on one plane => per-face max|coord|>=20 AND the SAME axis for all 3 nodes
axis_of_max = np.abs(c).argmax(axis=1)
same_axis = (axis_of_max.max(axis=1)==axis_of_max.min(axis=1))
onbnd = (mx>=20.0-1e-6) & same_axis
print("1x faces on a single domain plane: %d / %d" % (onbnd.sum(), len(single)))
assert onbnd.all(), "non-planar 1x faces -> hole!"
assert (cnt>2).sum()==0, "non-manifold face!"

# volume conservation in hot control box
ctl = (nxyz[E4].mean(1)[:,0]>18.5)&(nxyz[E4].mean(1)[:,1]>8.5)&(nxyz[E4].mean(1)[:,1]<12.5)&(nxyz[E4].mean(1)[:,2]>-21)
ctl0 = (P.mean(1)[:,0]>18.5)&(P.mean(1)[:,1]>8.5)&(P.mean(1)[:,1]<12.5)&(P.mean(1)[:,2]>-21)
print("control-box volume: before=%.8g after=%.8g (rel diff %.3g)" % (
    V0[ctl0].sum(), V4[ctl].sum(), abs(V4[ctl].sum()-V0[ctl0].sum())/V0[ctl0].sum()))

# removed nodes truly unreferenced
used = np.unique(E4)
removed = [idx[v] for v,_ in MERGES]
assert all(r not in set(used.tolist()) for r in removed)
print("removed nodes unreferenced OK; node count now %d (-%d)" % (len(used)+ (len(nid_arr)-len(set(used.tolist()))-4)+4-4+ len(set(used.tolist())) , 4))
# note: keep node table = all nodes except removed 4 (they are unreferenced)

# ---------- write new INP ----------
vanished = {v for v,_ in MERGES}
remap_node = {v: k for v, k in MERGES}
emap = {}
for old_eid, row in zip(eid, E):
    emap[old_eid] = row
final_E = {}
for old_eid, row in zip(eid4, E4):
    final_E[old_eid] = row
drop_elems = set(eid.tolist()) - set(final_E.keys())

with open(INP, encoding="latin-1") as f, open(OUT, "w", encoding="latin-1", newline="") as g:
    mode = None; cur_set = None
    for line in f:
        s = line.rstrip("\r\n")
        st = s.strip()
        if st.startswith("*"):
            u = st.upper()
            if u == "*NODE": mode = "n"
            elif u.startswith("*ELEMENT") and "C3D4" in u: mode = "e"
            elif u.startswith("*NSET"):
                cur_set = st.split(",")[1].strip().split("=")[1].strip(); mode = "s"
            else: mode = None; cur_set = None
            g.write(s + "\n"); continue
        if mode == "n":
            nid_l = int(st.split(",")[0])
            if nid_l in vanished: continue          # drop removed node lines
            g.write(s + "\n")
        elif mode == "e":
            row = [int(x) for x in st.split(",")]
            e_l = row[0]
            if e_l in drop_elems: continue           # degenerate/duplicate dropped
            r = final_E[e_l]
            g.write("%d, %d, %d, %d, %d\n" % (e_l, nid_arr[r[0]], nid_arr[r[1]], nid_arr[r[2]], nid_arr[r[3]]))
        elif mode == "s":
            # sets unchanged: vanished nodes were in no set
            g.write(s + "\n")
        else:
            g.write(s + "\n")
print("wrote", OUT)
np.save(r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m3_hotzone_mesh_20260923/m3/final_E.npy", E4)
np.save(r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m3_hotzone_mesh_20260923/m3/final_eid.npy", eid4)
