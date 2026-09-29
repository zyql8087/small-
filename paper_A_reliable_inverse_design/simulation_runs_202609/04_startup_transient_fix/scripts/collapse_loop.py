# Iterative quality-blocklist collapse for m3_26 (clean rewrite).
# Each cycle: pass1 collapse -> gt2-blocklist -> pass2 collapse -> write INP -> datacheck
# -> extend blocklist with rep-pairs touching the worst-flagged elements. Until 0 errors.
import numpy as np
import subprocess, os, re, time
t0 = time.time()

INP = r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/cases/m3_class12_26/mesh/outputs/m3_class12_26_volume_mesh_c3d4.inp"
OUT_INP = r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/diagnosis_transient/m3_26_mesh_cleaned.inp"
DC_DIR = r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/diagnosis_transient"
ABAQUS_BAT = r"F:\SIMULIA\Commands\abaqus.bat"
COINCIDENT = 0.05
MAX_CYCLES = 4

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
                try: nset_mem[cur_set].add(int(tok.strip()))
                except ValueError: pass

nid_arr = np.array(sorted(nodes_d))
nxyz = np.array([nodes_d[i] for i in nid_arr])
idx = {int(n): k for k, n in enumerate(nid_arr)}
E0 = np.array([[idx[c] for c in r[1:5]] for r in elems], dtype=int)
eid0 = np.array([r[0] for r in elems])
set_of = {}
for sname, mem in nset_mem.items():
    for n in mem: set_of.setdefault(n, []).append(sname)
PAIRS = [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]

def qual(Ea, Pa):
    P = Pa[Ea]
    V = np.abs(np.einsum('ij,ij->i', np.cross(P[:,1]-P[:,0], P[:,2]-P[:,0]), P[:,3]-P[:,0]))/6.0
    L = np.stack([np.linalg.norm(P[:,i]-P[:,j],axis=1) for i,j in PAIRS],axis=1)
    return 12.0*V/(L.max(1)**3+1e-30)/1.4142, V

def on_plane(k):
    x, y, z = nxyz[k]
    return abs(abs(x)-20) < 1e-6 or abs(abs(y)-20) < 1e-6 or abs(abs(z)-20) < 1e-6

def gt2_count(Ea):
    faces = np.sort(np.concatenate([Ea[:,[0,1,2]],Ea[:,[0,1,3]],Ea[:,[0,2,3]],Ea[:,[1,2,3]]]), axis=1)
    _, cnt = np.unique(faces, axis=0, return_counts=True)
    return int((cnt>2).sum())

def gt2_blocklist_from(rep, Ea):
    g = gt2_count(Ea)
    bl = set()
    if g == 0: return bl
    faces = np.sort(np.concatenate([Ea[:,[0,1,2]],Ea[:,[0,1,3]],Ea[:,[0,2,3]],Ea[:,[1,2,3]]]), axis=1)
    _, cnt = np.unique(faces, axis=0, return_counts=True)
    uf2 = faces  # need uf with cnt>2
    uq, cc = np.unique(faces, axis=0, return_counts=True)
    bad_nodes = set()
    for fi in uq[cc>2]:
        bad_nodes.update(int(x) for x in fi)
    for van, keep in rep.items():
        if van in bad_nodes or keep in bad_nodes:
            bl.add((min(van, keep), max(van, keep)))
    return bl

def collapse(blocklist):
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
                    if d < COINCIDENT and (min(u,v), max(u,v)) not in blocklist:
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

def write_inp(Ecur, surviving, dropped, vanished_ids, out_path):
    with open(INP, encoding="latin-1") as f, open(out_path, "w", encoding="latin-1", newline="") as g:
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

def datacheck(tag):
    r = subprocess.run([os.environ.get("COMSPEC", "cmd.exe"), "/c", ABAQUS_BAT,
                        "job=dc_" + tag, "input=" + OUT_INP, "datacheck", "interactive"],
                       capture_output=True, text=True, cwd=DC_DIR, timeout=900)
    dat = os.path.join(DC_DIR, "dc_" + tag + ".dat")
    nerr = 0; completed = False
    if os.path.exists(dat):
        txt = open(dat, encoding="latin-1").read()
        m = re.search(r"The volume of (\d+) elements", txt)
        if m: nerr = int(m.group(1))
        if nerr == 0 and "***ERROR" in txt: nerr = -1
        completed = ("COMPLETED" in txt) and nerr == 0
    return nerr, completed

accumulated = set()
NFLAG = 920
ok = False
for cyc in range(1, MAX_CYCLES+1):
    E1, r1, rep1, rm1 = collapse(accumulated)
    gt2_bl = gt2_blocklist_from(rep1, E1)
    combined = accumulated | gt2_bl
    E2, ridx2, rep2, rm2 = collapse(combined)
    surviving = {}
    for j, r in enumerate(ridx2):
        surviving[int(eid0[r])] = j
    dropped = set(int(x) for x in eid0.tolist()) - set(surviving.keys())
    vanished_ids = {int(nid_arr[v]) for v in rm2}
    write_inp(E2, surviving, dropped, vanished_ids, OUT_INP)
    g2 = gt2_count(E2)
    qf, _ = qual(E2, nxyz)
    nerr, completed = datacheck("cyc%d" % cyc)
    print("cycle %d: gt2=%d volume_errors=%d completed=%s (%.0fs)" % (
        cyc, g2, nerr, completed, time.time()-t0), flush=True)
    if nerr == 0 and completed:
        ok = True
        np.savez_compressed(DC_DIR + "/final_clean_state.npz",
                            Ecur=E2, nid_arr=nid_arr,
                            surviving=np.array(sorted(surviving.keys())))
        print("FINAL MESH OK ->", OUT_INP, flush=True)
        break
    if nerr > 0: NFLAG = max(nerr, 50)
    worst = np.argsort(qf)[:NFLAG]
    touched = set()
    for k in worst:
        touched.update(int(x) for x in nid_arr[E2[k]])
    added = 0
    for van, keep in rep2.items():
        if van in touched or keep in touched:
            pr = (min(van, keep), max(van, keep))
            if pr not in accumulated:
                accumulated.add(pr); added += 1
    print("blocklist +%d (total %d); NFLAG=%d" % (added, len(accumulated), NFLAG), flush=True)
if not ok:
    print("NOT CONVERGED in %d cycles" % MAX_CYCLES)
