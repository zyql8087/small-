# Inspect cavity topology: boundary facets, their quality as tet-bases, planarity
import numpy as np
from collections import Counter

INP = r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m1m3_marlow_c3d4_20260923/m3/m3_marlow.inp"
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
            elems.append([int(x) for x in s.split(",")])
nid = np.array(sorted(nodes_d)); nxyz = np.array([nodes_d[i] for i in nid])
idx = {int(n): k for k, n in enumerate(nid)}
E = np.array([[idx[c] for c in r[1:5]] for r in elems], dtype=int)
eid = np.array([r[0] for r in elems])
P = nxyz[E]
pairs = [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]
L = np.stack([np.linalg.norm(P[:,i]-P[:,j],axis=1) for i,j in pairs],axis=1)
V = np.abs(np.einsum('ij,ij->i', np.cross(P[:,1]-P[:,0], P[:,2]-P[:,0]), P[:,3]-P[:,0]))/6.0
q = 12.0*V/(L.max(1)**3+1e-30)/1.4142

pocket = np.load(r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m3_hotzone_mesh_20260923/m3/pocket_elems.npy")
pid = {v:i for i,v in enumerate(eid)}
sel = np.array([pid[e] for e in pocket])
C = E[sel]; Pc = P[sel]; qc = q[sel]; Vc = V[sel]

# tet faces
faces = []
for t in range(len(C)):
    a,b,c,d = C[t]
    faces += [(a,b,c,t),(a,b,d,t),(a,c,d,t),(b,c,d,t)]
fc = Counter(frozenset(f[:3]) for f in faces)
bnd = [f for f in faces if fc[frozenset(f[:3])] == 1]
print("cavity: %d tets, %d nodes, %d boundary facets" % (len(C), len(np.unique(C)), len(bnd)))

# each boundary facet: is it shared with outside elements? compute facet normal/area, and
# the best tet quality achievable with this facet: try apex = centroid of the adjacent outside element
# (approximation): instead compute facet area & longest edge -> aspect
print("\nboundary facet properties:")
facets = np.array([sorted(f[:3]) for f in bnd])
uniq_f = np.unique(facets, axis=0)
for fi, f in enumerate(uniq_f):
    a,b,c = nxyz[f]
    area = 0.5*np.linalg.norm(np.cross(b-a, c-a))
    el = [np.linalg.norm(b-a), np.linalg.norm(c-a), np.linalg.norm(c-b)]
    print(" facet %d nodes %s area=%.4g edges=%.4g/%.4g/%.4g" % (fi, nid[f].tolist(), area, *el))

# cavity edge stats
ce = set()
for t in range(len(C)):
    for i,j in pairs:
        ce.add(frozenset([C[t][i], C[t][j]]))
print("\ncavity edges: %d" % len(ce))

# element 12312/13910 adjacency: which pocket elements touch these hot nodes
for hn in (12312, 13910, 8095):
    k = idx[hn]
    touch = [eid[t] for t in sel if k in C[t]]
    print("hot node %d touched by pocket elems: %s" % (hn, touch))
