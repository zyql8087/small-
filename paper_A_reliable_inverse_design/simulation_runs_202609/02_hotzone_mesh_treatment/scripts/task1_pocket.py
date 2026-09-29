# Task 1: flood-fill the degenerate pocket around M3 hot nodes; output element list + bbox
import numpy as np
from collections import deque, Counter

INP = r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m1m3_marlow_c3d4_20260923/m3/m3_marlow.inp"
OUT = r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m3_hotzone_mesh_20260923/m3/m3_hotzone_elements.csv"
POLY2_MSG = r"F:/small++/paper_A_reliable_inverse_design/audits/m05_small_mechanism_pilot_20260919/cases/m3_class12_665/solver/m3_small_repro.msg"

SEED_NODES = [8095, 12312, 13910]
Q_POCKET = 0.05          # pocket flood threshold
Q_CAVITY = 0.05          # cavity = pocket (all replaced elements must reach >= this after remesh)

# --- load mesh
nodes_d = {}; elems = []; mode = None
with open(INP, encoding="latin-1") as f:
    for line in f:
        s = line.strip()
        if s.startswith("*"):
            u = s.upper()
            if u == "*NODE": mode = "n"; continue
            if u.startswith("*ELEMENT") and "C3D4" in u: mode = "e"; continue
            mode = None; continue
        if mode == "n":
            p = s.split(","); nodes_d[int(p[0])] = [float(x) for x in p[1:4]]
        elif mode == "e":
            p = [int(x) for x in s.split(",")]; elems.append(p)
nid = np.array(sorted(nodes_d)); nxyz = np.array([nodes_d[i] for i in nid])
idx = {int(n): k for k, n in enumerate(nid)}
E = np.array([[idx[c] for c in r[1:5]] for r in elems], dtype=int)
eid = np.array([r[0] for r in elems])
P = nxyz[E]
def vol(P):
    a,b,c,d = P[:,0],P[:,1],P[:,2],P[:,3]
    return np.einsum('ij,ij->i', np.cross(b-a, c-a), d-a)/6.0
pairs = [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]
L = np.stack([np.linalg.norm(P[:,i]-P[:,j],axis=1) for i,j in pairs],axis=1)
V = vol(P); q = 12.0*np.abs(V)/(L.max(1)**3+1e-30)/1.4142
ne = len(E)
print("mesh: %d nodes %d elems, q median %.3f" % (len(nid), ne, np.median(q)))

# node->elements adjacency
n2e = {}
for k in range(ne):
    for c in E[k]:
        n2e.setdefault(c, []).append(k)

# --- flood pocket from seeds through elements with q < Q_POCKET
seed_elems = set()
for sn in SEED_NODES:
    seed_elems.update(n2e[idx[sn]])
seen = set(); dq = deque()
for e in seed_elems:
    if q[e] < Q_POCKET: seen.add(e); dq.append(e)
while dq:
    e = dq.popleft()
    for c in E[e]:
        for e2 in n2e[c]:
            if e2 not in seen and q[e2] < Q_POCKET:
                seen.add(e2); dq.append(e2)
pocket = np.array(sorted(seen))
print("pocket elements (q<%.2f, connected to seeds): %d" % (Q_POCKET, len(pocket)))

# boundary nodes of pocket (nodes used by pocket elems) and cavity boundary facets later
pnodes = np.unique(E[pocket])
print("pocket nodes: %d" % len(pnodes))
print("pocket q range: %.6f .. %.6f, median %.4f" % (q[pocket].min(), q[pocket].max(), np.median(q[pocket])))
print("pocket vol range: %.3g .. %.3g" % (np.abs(V[pocket]).min(), np.abs(V[pocket]).max()))
pb = nxyz[pnodes]
print("pocket bbox: x[%.2f,%.2f] y[%.2f,%.2f] z[%.2f,%.2f]" % (pb[:,0].min(),pb[:,0].max(),pb[:,1].min(),pb[:,1].max(),pb[:,2].min(),pb[:,2].max()))

# nearest-domain-boundary check: how many pocket nodes sit on x=20 or z=-20 planes (within 1e-6)
onx = np.abs(pb[:,0]-20.0) < 1e-6; onz = np.abs(pb[:,2]+20.0) < 1e-6
print("pocket nodes on x=+20 plane: %d; on z=-20 plane: %d" % (onx.sum(), onz.sum()))

# --- poly2 alignment: main residual nodes in poly2 msg
p2 = re = None
import re as _re
txt2 = open(POLY2_MSG, encoding="latin-1").read()
pat2 = _re.findall(r"NODE\s+(\d+)\s+DOF\s+(\d+)", txt2)
c2 = Counter(int(a) for a, b in pat2)
print("\npoly2-era m3_small_repro.msg top residual nodes:", c2.most_common(5))
print("12312 in poly2 top:", 12312 in dict(c2.most_common(5)))

# --- write element csv
rows = ["element_id,node1,node2,node3,node4,quality,volume,center_x,center_y,center_z"]
for k in pocket:
    c = P[k].mean(0)
    rows.append("%d,%d,%d,%d,%d,%.8g,%.8g,%.4f,%.4f,%.4f" % (
        eid[k], nid[E[k][0]], nid[E[k][1]], nid[E[k][2]], nid[E[k][3]], q[k], V[k], c[0], c[1], c[2]))
open(OUT, "w").write("\n".join(rows))
print("\nwrote", OUT, "(%d data rows)" % len(pocket))
np.save(r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m3_hotzone_mesh_20260923/m3/pocket_elems.npy", eid[pocket])
