# Task 2 (final): iterative protected collapse of coincident node clusters in the M3 hot zone.
# Validation: no degenerate/duplicate tets; face-manifold; the SET of 1x (boundary) faces after
# collapse must be IDENTICAL to the original 1x faces remapped through the merge map (interior
# collapse must not create or destroy boundary). Writes m3_hotzone_fixed.inp.
import numpy as np

INP = r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m1m3_marlow_c3d4_20260923/m3/m3_marlow.inp"
OUT = r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m3_hotzone_mesh_20260923/m3/m3_hotzone_fixed.inp"
Q_TARGET = 0.05
COINCIDENT = 0.05   # mm; mesh min nominal edge ~0.2mm -> anything closer is a generation artifact
MAX_ROUNDS = 8

nodes_d = {}; elems = []; nset_mem = {}; mode = None; cur_set = None
with open(INP, encoding="latin-1") as f:
    for line in f:
        s = line.strip()
        if s.startswith("*"):
            u = s.upper()
            if u == "*NODE":
                mode = "n"; cur_set = None; continue
            if u.startswith("*ELEMENT") and "C3D4" in u:
                mode = "e"; cur_set = None; continue
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

def hotmask(cent):
    return (cent[:,0]>19.5)&(cent[:,1]>9.5)&(cent[:,1]<11.5)&(cent[:,2]>-20.2)&(cent[:,2]<-18.8)

def face_sets(Ea):
    faces = np.sort(np.concatenate([Ea[:,[0,1,2]],Ea[:,[0,1,3]],Ea[:,[0,2,3]],Ea[:,[1,2,3]]]), axis=1)
    uf, cnt = np.unique(faces, axis=0, return_counts=True)
    single = uf[cnt==1]
    dbl = uf[cnt==2]
    return set(map(tuple, single.tolist())), set(map(tuple, dbl.tolist())), (cnt>2).sum()

q0, V0 = qual(E0, nxyz)
print("start: %d elems, global qmin=%.3g" % (len(E0), q0.min()))
single0, dbl0, bad0 = face_sets(E0)
print("original 1x faces: %d, 2x: %d, >2x: %d" % (len(single0), len(dbl0), bad0))

Ecur = E0.copy(); ridx = np.arange(len(E0)); removed_nodes = []; log = []; rep = {}   # rep: vanished node-idx -> kept node-idx
for rnd in range(1, MAX_ROUNDS+1):
    qc, _ = qual(Ecur, nxyz)
    cent = nxyz[Ecur].mean(1)
    hot = hotmask(cent) & (qc < Q_TARGET)
    nbad = int(hot.sum())
    if nbad == 0:
        print("round %d: no bad elements in hot region - done" % rnd); break
    cand = set()
    for k in np.where(hot)[0]:
        for a in range(4):
            for b in range(a+1, 4):
                u, v = int(Ecur[k][a]), int(Ecur[k][b])
                if u == v: continue
                d = float(np.linalg.norm(nxyz[u]-nxyz[v]))
                if d < COINCIDENT:
                    cand.add((min(u,v), max(u,v), round(d,6)))
    if not cand:
        print("round %d: %d bad elems but NO coincident pairs (plateau) - stop" % (rnd, nbad)); break
    merged_this = []; used = set()
    for u, v, d in sorted(cand, key=lambda t: t[2]):
        if u in used or v in used: continue
        if on_plane(u) or on_plane(v):
            log.append("skip plane node pair %d-%d d=%.6f" % (nid_arr[u], nid_arr[v], d)); continue
        u_n, v_n = int(nid_arr[u]), int(nid_arr[v])
        if set_of.get(u_n) and not set_of.get(v_n): keep, van = u, v
        elif set_of.get(v_n) and not set_of.get(u_n): keep, van = v, u
        elif set_of.get(u_n) and set_of.get(v_n):
            log.append("skip both-in-set pair %d-%d" % (u_n, v_n)); continue
        else:
            keep, van = (u, v) if u < v else (v, u)
        Ecur[Ecur == van] = keep
        removed_nodes.append(van); rep[van] = keep
        used.update([u, v])
        merged_this.append((int(nid_arr[van]), int(nid_arr[keep]), d))
    if not merged_this:
        print("round %d: no collapsible pair - stop" % rnd); break
    deg = ((Ecur[:,0]==Ecur[:,1])|(Ecur[:,0]==Ecur[:,2])|(Ecur[:,0]==Ecur[:,3])|
           (Ecur[:,1]==Ecur[:,2])|(Ecur[:,1]==Ecur[:,3])|(Ecur[:,2]==Ecur[:,3]))
    key = np.sort(Ecur, axis=1)
    _, first, cnts = np.unique(key, axis=0, return_index=True, return_counts=True)
    alive = np.zeros(len(Ecur), bool); alive[np.sort(first)] = True
    ndeg = int(deg.sum()); ndup = int((cnts-1).sum())
    m = alive & ~deg
    Ecur = Ecur[m]; ridx = ridx[m]
    log.append("round %d: merged %s; removed %d degenerate + %d duplicate" % (rnd, merged_this, ndeg, ndup))
    print(log[-1])

# resolve rep chains (vanish -> keep may itself be vanished later)
def resolve(k):
    seen = set()
    while k in rep:
        assert k not in seen; seen.add(k)
        k = rep[k]
    return k

qc, Vc = qual(Ecur, nxyz)
cent = nxyz[Ecur].mean(1)
hot = hotmask(cent)
print("\nfinal hot-region: elems=%d qmin=%.4f qmed=%.4f" % (hot.sum(), qc[hot].min(), np.median(qc[hot])))
print("total removed nodes: %s" % [int(nid_arr[v]) for v in removed_nodes])
print("total removed elems: %d (from %d to %d)" % (len(E0)-len(Ecur), len(E0), len(Ecur)))

# ---- validations ----
singleF, dblF, badF = face_sets(Ecur)
assert badF == 0, "non-manifold >2x faces!"
# original 1x faces remapped through rep must equal final 1x faces
remap1x = set()
for f in single0:
    g = tuple(resolve(int(c)) for c in f)
    gs = tuple(sorted(g))
    if len(set(gs)) == 3:
        remap1x.add(gs)
lost = remap1x - singleF
gained = singleF - remap1x
print("boundary faces: before(remapped)=%d after=%d lost=%d gained=%d" % (
    len(remap1x), len(singleF), len(lost), len(gained)))
assert not lost and not gained, "boundary changed -> hole/overlap!"
# control-box volume conservation
ctl = (cent[:,0]>18.5)&(cent[:,1]>8.5)&(cent[:,1]<12.5)&(cent[:,2]>-21)
ctl0 = (nxyz[E0].mean(1)[:,0]>18.5)&(nxyz[E0].mean(1)[:,1]>8.5)&(nxyz[E0].mean(1)[:,1]<12.5)&(nxyz[E0].mean(1)[:,2]>-21)
rel = abs(Vc[ctl].sum()-V0[ctl0].sum())/V0[ctl0].sum()
print("control-box volume before=%.8g after=%.8g rel=%.3g" % (V0[ctl0].sum(), Vc[ctl].sum(), rel))
for v in removed_nodes:
    n_n = int(nid_arr[v])
    assert not set_of.get(n_n), (n_n, set_of[n_n])
print("removed nodes were in no set OK; node-set membership unchanged (representatives kept)")

# ---- write INP ----
vanished_ids = set(int(nid_arr[v]) for v in removed_nodes)
surviving = {}
for j, r in enumerate(ridx):
    surviving[int(eid0[r])] = j
dropped = set(int(x) for x in eid0.tolist()) - set(surviving.keys())
print("surviving elements: %d, dropped: %d" % (len(surviving), len(dropped)))

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
np.save(r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m3_hotzone_mesh_20260923/m3/final_E.npy", Ecur)
with open(r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m3_hotzone_mesh_20260923/m3/collapse_log.txt", "w") as h:
    h.write("\n".join(log))
