import numpy as np

INP = r"F:/small++/paper_A_reliable_inverse_design/audits/m05_small_mechanism_pilot_20260919/cases/m2_class2_1383/solver/m2_small_repro.inp"
nodes = {}
elems = []
mode = None
with open(INP, encoding="latin-1") as f:
    for line in f:
        s = line.strip()
        if s.startswith("*"):
            u = s.upper()
            if u == "*NODE": mode = "n"; continue
            if u.startswith("*ELEMENT") and "C3D4" in u: mode = "e"; continue
            mode = None
            continue
        if mode == "n":
            p = s.split(",")
            nodes[int(p[0])] = [float(x) for x in p[1:4]]
        elif mode == "e":
            p = [int(x) for x in s.split(",")]
            elems.append(p)

nid = np.array(sorted(nodes))
nxyz = np.array([nodes[i] for i in nid])
idx = {int(n): k for k, n in enumerate(nid)}
E = np.array([[idx[c] for c in row[1:5]] for row in elems], dtype=int)
eid = np.array([row[0] for row in elems])
print("nodes=%d elems=%d" % (len(nid), len(E)))

P = nxyz[E]  # (ne,4,3)
def vol(P):
    a,b,c,d = P[:,0],P[:,1],P[:,2],P[:,3]
    return np.einsum('ij,ij->i', np.cross(b-a, c-a), d-a)/6.0
V = vol(P)
absv = np.abs(V)

# edge lengths
pairs = [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]
L = np.stack([np.linalg.norm(P[:,i]-P[:,j], axis=1) for i,j in pairs], axis=1)
aspect = L.max(1)/np.maximum(L.min(1), 1e-9)
# min altitude ~ 2*min face area... use shortest-edge/longest-edge and V/(Lmax^3) normalized
quality = 12.0*absv/ (L.max(1)**3 + 1e-30)  # ~1 for regular tet: V=sqrt2/12 a^3, Lmax=a -> 12V/a^3=1.414... scale
# actually regular tet V=0.11785 a^3 -> 12V=1.414 -> normalize:
quality /= 1.4142

def report(name, mask):
    n = mask.sum()
    if n == 0:
        print(name, "none"); return
    print("%s: n=%d aspect med=%.1f p90=%.1f max=%.1f | q med=%.4f p10=%.4f min=%.5f | vol med=%.4g min=%.3g" % (
        name, n, np.median(aspect[mask]), np.percentile(aspect[mask],90), aspect[mask].max(),
        np.median(quality[mask]), np.percentile(quality[mask],10), quality[mask].min(),
        np.median(absv[mask]), absv[mask].min()))

print("\n--- global ---")
report("ALL     ", np.ones(len(E), bool))
print("\n--- node 97943 neighborhood ---")
k = idx[97943]
nbr = np.isin(E, k).any(1)
report("nbr(97943)", nbr)
print("neighbor element ids:", eid[nbr].tolist())
# the DIAGNOSIS named 368030, 411167, 449238 among neighbors
for target in (368030, 411167, 449238):
    m = eid == target
    if m.any():
        print("elem %d: aspect=%.0f quality=%.6f vol=%.4g" % (target, aspect[m][0], quality[m][0], absv[m][0]))

# global distortion counts by own metrics
print("\n--- own distortion metrics ---")
print("aspect>20: %d (%.2f%%)" % ((aspect>20).sum(), 100*(aspect>20).mean()))
print("aspect>100: %d (%.2f%%)" % ((aspect>100).sum(), 100*(aspect>100).mean()))
print("quality<0.01: %d" % (quality<0.01).sum())
print("quality<0.05: %d" % (quality<0.05).sum())
print("vol<1e-6 mm^3: %d" % (absv<1e-6).sum())

# spatial: where are the worst elements? distance from origin / near boundary x=-20,y=-20?
worst = np.argsort(quality)[:2000]
cx = P[worst].mean(1)
print("\nworst-2000 elements mean position:", cx.mean(0).round(2), " domain bounds:", nxyz.min(0).round(1), nxyz.max(0).round(1))
near = ((np.abs(cx[:,0]+19.7)<1.5) & (np.abs(cx[:,1]+19.7)<1.5)).sum()
print("worst-2000 with center near (-19.7,-19.7) [node 97943 region]:", near)
