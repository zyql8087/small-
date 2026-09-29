# Final global collapse for m3_26: two-pass (blocklist) with FULL validation + INP write.
# Produces the cleaned mesh used for the explicit re-validation solve.
import numpy as np
import time
t0 = time.time()

INP = r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/cases/m3_class12_26/mesh/outputs/m3_class12_26_volume_mesh_c3d4.inp"
OUT = r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/diagnosis_transient/m3_26_mesh_cleaned.inp"
COINCIDENT = 0.05

nodes_d = {}; elems = []; nset_mem = {}; mode = None; cur_set = None
with open(INP, encoding="latin-1") as f:
    for line in f:
        s = line.strip()
        if s.startswith("*"):
            u = s.upper()
            if u == "*NODE": mode = "n"; cur_set = None; continue
            if u.startswith("*ELEMENT") and "C3D4" in u: mode = "e"; cur_set = None; continue
            if u.startswith("*NSET"):
                cur_set = s.split(",")[1].strip().split("=")[1].strip(); nset_mem[cur_set] = set(); mode = "s"; continue
            mode = None; cur_set = None; continue
        if mode == "n":
            p = s.split(","); nodes_d[int(p[0])] = [float(x) for x in p[1:4]]
        elif mode == "e":
            elems.append([int(x) for x in s.split(",")])
        elif mode == "s" and cur_set:
            for tok in s.split(","):
                try:
                    nset_mem[cur_set].add(int(tok.strip()))
                except ValueError:
                    pass

nid_arr = np.array(sorted(nodes_d))
nxyz = np.array([nodes_d[i] for i in nid_arr])
idx = {int(n): k for k, n in enumerate(nid_arr)}
E0 = np.array([[idx[c] for c in r[1:5]] for r in elems], dtype=int)
eid0 = np.array([r[0] for r in elems])
set_of = {}
for sname, mem in nset_mem.items():
    for n in mem:
        set_of.setdefault(n, []).append(sname)
PAIRS = [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]

def qual(Ea, Pa):
    P = Pa[Ea]
    V = np.abs(np.einsum('ij,ij->i', np.cross(P[:,1]-P[:,0], P[:,2]-P[:,0]), P[:,3]-P[:,0]))/6.0
    L = np.stack([np.linalg.norm(P[:,i]-P[:,j],axis=1) for i,j in PAIRS],axis=1)
    return 12.0*V/(L.max(1)**3+1e-30)/1.4142, V

def on_plane(k):
    x, y, z = nxyz[k]
    return abs(abs(x)-20) < 1e-6 or abs(abs(y)-20) < 1e-6 or abs(abs(z)-20) < 1e-6

def face_count(Ea):
    faces = np.sort(np.concatenate([Ea[:,[0,1,2]],Ea[:,[0,1,3]],Ea[:,[0,2,3]],Ea[:,[1,2,3]]]), axis=1)
    uf, cnt = np.unique(faces, axis=0, return_counts=True)
    return uf, cnt

def gt2_faces(Ea):
    uf, cnt = face_count(Ea)
    return uf[cnt>2]

q0, V0 = qual(E0, nxyz)
uf0, cnt0 = face_count(E0)
single0 = set(map(tuple, uf0[cnt0==1].tolist()))
print("original: %d elems, q<0.05=%d (%.1f%%), 1x faces=%d, >2x=0" % (
    len(E0), (q0<0.05).sum(), 100*(q0<0.05).mean(), len(single0)))

def collapse(blocklist_pairs=frozenset()):
    Ecur = E0.copy(); ridx = np.arange(len(E0)); rep = {}; removed_nodes = []
    for rnd in range(1, 13):
        qc, _ = qual(Ecur, nxyz)
        bad = qc < 0.05
        if not bad.any(): break
        cand = set()
        for k in np.where(bad)[0]:
            for a in range(4):
                for b in range(a+1, 4):
                    u, v = int(Ecur[k][a]), int(Ecur[k][b])
                    if u == v: continue
                    d = float(np.linalg.norm(nxyz[u]-nxyz[v]))
                    if d < COINCIDENT and (min(u,v), max(u,v)) not in blocklist_pairs:
                        cand.add((min(u,v), max(u,v), round(d,6)))
        if not cand: break
        merged = []; used = set()
        for u, v, d in sorted(cand, key=lambda t: t[2]):
            if u in used or v in used: continue
            if on_plane(u) or on_plane(v): continue
            u_n, v_n = int(nid_arr[u]), int(nid_arr[v])
            if set_of.get(u_n) and set_of.get(v_n): continue
            if set_of.get(u_n): keep, van = u, v
            elif set_of.get(v_n): keep, van = v, u
            else: keep, van = (u, v) if u < v else (v, u)
            Ecur[Ecur == van] = keep
            removed_nodes.append(van); rep[van] = keep
            used.update([u, v]); merged.append((u, v))
        if not merged: break
        while True:
            deg = ((Ecur[:,0]==Ecur[:,1])|(Ecur[:,0]==Ecur[:,2])|(Ecur[:,0]==Ecur[:,3])|
                   (Ecur[:,1]==Ecur[:,2])|(Ecur[:,1]==Ecur[:,3])|(Ecur[:,2]==Ecur[:,3]))
            key = np.sort(Ecur, axis=1)
            _, first, cnts = np.unique(key, axis=0, return_index=True, return_counts=True)
            if int(deg.sum()) == 0 and int((cnts-1).sum()) == 0: break
            alive = np.zeros(len(Ecur), bool); alive[np.sort(first)] = True
            m = alive & ~deg
            Ecur = Ecur[m]; ridx = ridx[m]
    while True:
        q_, V_ = qual(Ecur, nxyz)
        dead = (V_ < 1e-11) | ((q_ < 0.005) & (V_ < 1e-6))
        key = np.sort(Ecur, axis=1)
        _, first, cnts = np.unique(key, axis=0, return_index=True, return_counts=True)
        if not dead.any() and int((cnts-1).sum()) == 0: break
        alive = np.zeros(len(Ecur), bool); alive[np.sort(first)] = True
        m = alive & ~dead
        Ecur = Ecur[m]; ridx = ridx[m]
    return Ecur, ridx, rep, removed_nodes

E1, r1, rep1, rm1 = collapse()
g1 = gt2_faces(E1)
bad_nodes = set()
for fi in g1:
    bad_nodes.update(int(x) for x in fi)
blocked = set()
for van, keep in rep1.items():
    if van in bad_nodes or keep in bad_nodes:
        blocked.add((min(van, keep), max(van, keep)))
print("pass1 gt2=%d -> blocklist %d pairs" % (len(g1), len(blocked)))

E2, ridx2, rep2, rm2 = collapse(blocklist_pairs=blocked)
g2 = gt2_faces(E2)
print("pass2 gt2=%d" % len(g2))

def resolve(k):
    seen = set()
    while k in rep2:
        assert k not in seen; seen.add(k)
        k = rep2[k]
    return k

qc, Vc = qual(E2, nxyz)
uf2, cnt2 = face_count(E2)
single2 = set(map(tuple, uf2[cnt2==1].tolist()))
remap1x = set()
for f in single0:
    g = tuple(sorted(resolve(int(c)) for c in f))
    if len(set(g)) == 3:
        remap1x.add(g)
lost = remap1x - single2; gained = single2 - remap1x
print("\n=== validation ===")
print("q<0.05: %d (%.2f%%) | qmin=%.5g" % ((qc<0.05).sum(), 100*(qc<0.05).mean(), qc.min()))
print("boundary: before(remapped)=%d after=%d lost=%d gained=%d" % (len(remap1x), len(single2), len(lost), len(gained)))
print(">2x faces: %d" % len(g2))
cent = nxyz[E2].mean(1)
ctl = (cent[:,0]>18.5)&(cent[:,1]>8.5)&(cent[:,1]<12.5)&(cent[:,2]>-21)
ctl0 = (nxyz[E0].mean(1)[:,0]>18.5)&(nxyz[E0].mean(1)[:,1]>8.5)&(nxyz[E0].mean(1)[:,1]<12.5)&(nxyz[E0].mean(1)[:,2]>-21)
print("control-box volume rel diff=%.3g" % (abs(Vc[ctl].sum()-V0[ctl0].sum())/max(V0[ctl0].sum(),1e-30)))
for v in rm2:
    assert not set_of.get(int(nid_arr[v])), int(nid_arr[v])
print("removed nodes in no set OK; nodes removed=%d elems removed=%d" % (len(rm2), len(E0)-len(E2)))
# Boundary verification (perturbation-limited): collapse may align coincident nodes onto one
# representative, but NO boundary point may move more than 0.06mm (= 1/3 of min element edge 0.2mm).
# Verify by KD-tree: every ORIGINAL boundary node must have a surviving node within 0.06mm.
from scipy.spatial import cKDTree
s0_nodes = sorted({int(x) for f in single0 for x in f})
used_nodes = np.unique(E2)
tree = cKDTree(nxyz[used_nodes])
rng = np.random.default_rng(0)
sample = rng.choice(np.array(s0_nodes), size=min(5000, len(s0_nodes)), replace=False)
dist, _ = tree.query(nxyz[sample], k=1)
p99 = float(np.percentile(dist, 99)); mx = float(dist.max())
frac_bad = float((dist > 0.06).mean())
print("surface perturbation (sample %d bnd nodes): median=%.4g p99=%.4g max=%.4g | frac>0.06mm=%.4f" % (
    len(sample), float(np.median(dist)), p99, mx, frac_bad))
assert frac_bad == 0.0 and mx <= 0.06, "surface moved beyond collapse tolerance!"
assert len(g2) == 0

surviving = {}
for j, r in enumerate(ridx2):
    surviving[int(eid0[r])] = j
dropped = set(int(x) for x in eid0.tolist()) - set(surviving.keys())
print("surviving=%d dropped=%d" % (len(surviving), len(dropped)))

vanished_ids = set(int(nid_arr[v]) for v in rm2)
with open(INP, encoding="latin-1") as f, open(OUT, "w", encoding="latin-1", newline="") as g:
    mode = None
    for line in f:
        s = line.rstrip("\r\n"); st = s.strip()
        if st.startswith("*"):
            u = st.upper()
            if u == "*NODE": mode = "n"
            elif u.startswith("*ELEMENT") and "C3D4" in u: mode = "e"
            elif u.startswith("*NSET"): mode = "s"
            else: mode = None
            g.write(s + "\n"); continue
        if mode == "n":
            nid_l = int(st.split(",")[0])
            if nid_l in vanished_ids: continue
            g.write(s + "\n")
        elif mode == "e":
            e_l = int(st.split(",")[0])
            if e_l in dropped: continue
            r = E2[surviving[e_l]]
            g.write("%d, %d, %d, %d, %d\n" % (e_l, nid_arr[r[0]], nid_arr[r[1]], nid_arr[r[2]], nid_arr[r[3]]))
        else:
            g.write(s + "\n")
print("wrote", OUT, "in %.0fs" % (time.time()-t0))
np.savez_compressed(r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/diagnosis_transient/final_clean_state.npz",
                    Ecur=E2, nid_arr=nid_arr, rep_keys=np.array(list(rep2.keys())), rep_vals=np.array(list(rep2.values())))
