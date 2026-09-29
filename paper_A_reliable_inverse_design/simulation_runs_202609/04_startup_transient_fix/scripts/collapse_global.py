# Global coincident-node collapse (promotion of hotzone task2_collapse_iter.py to whole mesh).
import numpy as np

INP = r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/cases/m3_class12_26/mesh/outputs/m3_class12_26_volume_mesh_c3d4.inp"
OUT = r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/diagnosis_transient/m3_26_mesh_cleaned.inp"
COINCIDENT = 0.05
MAX_ROUNDS = 12

nodes_d = {}; elems = []; nset_mem = {}; mode = None; cur_set = None
with open(INP, encoding="latin-1") as f:
    for line in f:
        s = line.strip()
        if s.startswith("*"):
            u = s.upper()
            if u == "*NODE": mode = "n"; cur_set = None; continue
            if u.startswith("*ELEMENT") and "C3D4" in u: mode = "e"; cur_set = None; continue
            if u.startswith("*NSET"):
                cur_set = s.split(",")[1].strip().split("=")[1].strip()
                nset_mem[cur_set] = set(); mode = "s"; continue
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

def face_sets(Ea):
    faces = np.sort(np.concatenate([Ea[:,[0,1,2]],Ea[:,[0,1,3]],Ea[:,[0,2,3]],Ea[:,[1,2,3]]]), axis=1)
    uf, cnt = np.unique(faces, axis=0, return_counts=True)
    return set(map(tuple, uf[cnt==1].tolist())), int((cnt>2).sum())

q0, V0 = qual(E0, nxyz)
print("start: %d elems, q<0.05: %d (%.1f%%), global qmin=%.3g" % (
    len(E0), (q0<0.05).sum(), 100*(q0<0.05).mean(), q0.min()))
single0, bad0 = face_sets(E0)
print("original 1x faces: %d, >2x: %d" % (len(single0), bad0))

Ecur = E0.copy(); ridx = np.arange(len(E0))
removed_nodes = []; rep = {}; log = []
for rnd in range(1, MAX_ROUNDS+1):
    qc, _ = qual(Ecur, nxyz)
    bad = qc < 0.05
    nbad = int(bad.sum())
    if nbad == 0:
        print("round %d: no q<0.05 elems - done" % rnd); break
    cand = set()
    for k in np.where(bad)[0]:
        for a in range(4):
            for b in range(a+1, 4):
                u, v = int(Ecur[k][a]), int(Ecur[k][b])
                if u == v: continue
                d = float(np.linalg.norm(nxyz[u]-nxyz[v]))
                if d < COINCIDENT:
                    cand.add((min(u,v), max(u,v), round(d,6)))
    if not cand:
        print("round %d: %d bad elems but no coincident pairs - plateau" % (rnd, nbad)); break
    merged_this = []; used = set()
    for u, v, d in sorted(cand, key=lambda t: t[2]):
        if u in used or v in used: continue
        if on_plane(u) or on_plane(v):
            log.append("skip plane pair %d-%d" % (nid_arr[u], nid_arr[v])); continue
        u_n, v_n = int(nid_arr[u]), int(nid_arr[v])
        if set_of.get(u_n) and not set_of.get(v_n): keep, van = u, v
        elif set_of.get(v_n) and not set_of.get(u_n): keep, van = v, u
        elif set_of.get(u_n) and set_of.get(v_n):
            log.append("skip both-in-set %d-%d" % (u_n, v_n)); continue
        else:
            keep, van = (u, v) if u < v else (v, u)
        Ecur[Ecur == van] = keep
        removed_nodes.append(van); rep[van] = keep
        used.update([u, v]); merged_this.append((int(nid_arr[van]), int(nid_arr[keep]), d))
    if not merged_this:
        print("round %d: no collapsible pair - stop" % rnd); break
    total_deg = 0; total_dup = 0
    while True:
        deg = ((Ecur[:,0]==Ecur[:,1])|(Ecur[:,0]==Ecur[:,2])|(Ecur[:,0]==Ecur[:,3])|
               (Ecur[:,1]==Ecur[:,2])|(Ecur[:,1]==Ecur[:,3])|(Ecur[:,2]==Ecur[:,3]))
        key = np.sort(Ecur, axis=1)
        _, first, cnts = np.unique(key, axis=0, return_index=True, return_counts=True)
        ndeg = int(deg.sum()); ndup = int((cnts-1).sum())
        if ndeg == 0 and ndup == 0: break
        total_deg += ndeg; total_dup += ndup
        alive = np.zeros(len(Ecur), bool); alive[np.sort(first)] = True
        m = alive & ~deg
        Ecur = Ecur[m]; ridx = ridx[m]
    log.append("round %d: merged %d pairs; removed %d deg + %d dup (fixpoint)" % (
        rnd, len(merged_this), total_deg, total_dup))
    print(log[-1])

# --- cleanup to fixpoint: drop zero/ultra-thin elements, re-dedupe, repeat ---
def cleanup(Ea, ridx_a):
    rounds = 0; removed = 0
    while True:
        q_, V_ = qual(Ea, nxyz)
        dead = (V_ < 1e-11) | ((q_ < 0.005) & (V_ < 1e-6))
        if not dead.any():
            key = np.sort(Ea, axis=1)
            _, cnts = np.unique(key, axis=0, return_counts=True)
            if (cnts-1).sum() == 0: break
        key = np.sort(Ea, axis=1)
        _, first, cnts = np.unique(key, axis=0, return_index=True, return_counts=True)
        alive = np.zeros(len(Ea), bool); alive[np.sort(first)] = True
        m = alive & ~dead
        n_drop = int((~m).sum())
        if n_drop == 0: break
        removed += n_drop; rounds += 1
        Ea = Ea[m]; ridx_a = ridx_a[m]
    return Ea, ridx_a, rounds, removed

Ecur, ridx, cl_rounds, cl_removed = cleanup(Ecur, ridx)
print("cleanup: %d sweeps, removed %d zero/thin elements" % (cl_rounds, cl_removed))

def resolve(k):
    seen = set()
    while k in rep:
        assert k not in seen; seen.add(k)
        k = rep[k]
    return k

qc, Vc = qual(Ecur, nxyz)
print("\nfinal: q<0.05: %d (%.2f%%) | qmin=%.5g | removed nodes=%d elems=%d" % (
    (qc<0.05).sum(), 100*(qc<0.05).mean(), qc.min(), len(removed_nodes), len(E0)-len(Ecur)))

singleF, badF = face_sets(Ecur)
# verify whether >2x faces come from duplicated tets sharing same 4 nodes
faces = np.sort(np.concatenate([Ecur[:,[0,1,2]],Ecur[:,[0,1,3]],Ecur[:,[0,2,3]],Ecur[:,[1,2,3]]]), axis=1)
uf, cnt = np.unique(faces, axis=0, return_counts=True)
gt2 = uf[cnt>2]
n_dup_pairs = 0
for fi in gt2:
    sel = [r for r in range(len(Ecur)) if np.intersect1d(fi, Ecur[r]).size == 3]
    node_sets = [tuple(sorted(Ecur[r].tolist())) for r in sel]
    from collections import Counter
    cc = Counter(node_sets)
    for ns, c in cc.items():
        if c > 1: n_dup_pairs += 1
print("badF=%d; >2x faces with duplicated tet node-sets among them: %d / %d" % (badF, n_dup_pairs, len(gt2)))
open("gt2_analysis.txt","w").write("badF=%d dup_tets_among_gt2=%d/%d" % (badF, n_dup_pairs, len(gt2)))
assert badF == 0
remap1x = set()
for f in single0:
    g = tuple(sorted(resolve(int(c)) for c in f))
    if len(set(g)) == 3:
        remap1x.add(g)
lost = remap1x - singleF; gained = singleF - remap1x
print("boundary faces: before(remapped)=%d after=%d lost=%d gained=%d" % (
    len(remap1x), len(singleF), len(lost), len(gained)))
assert not lost and not gained
cent = nxyz[Ecur].mean(1)
ctl = (cent[:,0]>18.5)&(cent[:,1]>8.5)&(cent[:,1]<12.5)&(cent[:,2]>-21)
ctl0 = (nxyz[E0].mean(1)[:,0]>18.5)&(nxyz[E0].mean(1)[:,1]>8.5)&(nxyz[E0].mean(1)[:,1]<12.5)&(nxyz[E0].mean(1)[:,2]>-21)
rel = abs(Vc[ctl].sum()-V0[ctl0].sum())/max(V0[ctl0].sum(),1e-30)
print("control-box volume rel diff=%.3g" % rel)
for v in removed_nodes:
    assert not set_of.get(int(nid_arr[v])), int(nid_arr[v])
print("removed nodes in no set OK")

surviving = {}
for j, r in enumerate(ridx):
    surviving[int(eid0[r])] = j
dropped = set(int(x) for x in eid0.tolist()) - set(surviving.keys())
print("surviving: %d, dropped: %d" % (len(surviving), len(dropped)))

vanished_ids = set(int(nid_arr[v]) for v in removed_nodes)
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
            r = Ecur[surviving[e_l]]
            g.write("%d, %d, %d, %d, %d\n" % (e_l, nid_arr[r[0]], nid_arr[r[1]], nid_arr[r[2]], nid_arr[r[3]]))
        else:
            g.write(s + "\n")
print("wrote", OUT)
np.savez_compressed(r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/diagnosis_transient/clean_sidecar.npz",
                    Ecur=Ecur, nid_arr=nid_arr, removed_nodes=np.array(removed_nodes),
                    rep_keys=np.array(list(rep.keys())), rep_vals=np.array(list(rep.values())))
