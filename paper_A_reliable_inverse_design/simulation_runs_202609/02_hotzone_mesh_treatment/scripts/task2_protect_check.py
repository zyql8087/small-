# Protected-node check for collapse candidates + exact coords + set membership
import numpy as np, re

INP = r"F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/m1m3_marlow_c3d4_20260923/m3/m3_marlow.inp"
CANDS = [12275, 12312, 13910, 13911, 13947, 15629]

nodes_d = {}; sets_d = {}; cur_set = None; mode = None; elems_n = 0
with open(INP, encoding="latin-1") as f:
    for line in f:
        s = line.strip()
        if s.startswith("*"):
            u = s.upper()
            if u == "*NODE": mode = "n"; cur_set = None; continue
            if u.startswith("*ELEMENT"): mode = "e"; cur_set = None; elems_n += 1; continue
            if u.startswith("*NSET"):
                cur_set = s.split(",")[1].strip().split("=")[1].strip(); sets_d.setdefault(cur_set, []); mode = "s"; continue
            mode = None; cur_set = None; continue
        if mode == "n":
            p = s.split(","); nodes_d[int(p[0])] = [float(x) for x in p[1:4]]
        elif mode == "s":
            for tok in s.split(","):
                tok = tok.strip()
                if tok and tok.replace('.','').isdigit() is False:
                    continue
                if tok:
                    try: sets_d[cur_set].append(int(float(tok)))
                    except ValueError: pass
print("node sets found:", list(sets_d.keys()), {k: len(v) for k, v in sets_d.items()})
set_members = {n: [k for k, v in sets_d.items() if n in v] for n in CANDS}

print("\ncollapse candidates:")
for n in CANDS:
    x, y, z = nodes_d[n]
    planes = []
    for ax, val, nm in ((abs(x),20.0,'x=+20'),(abs(x),20.0,'x=-20'),(abs(y),20.0,'y'),(abs(z),20.0,'z')):
        if abs(abs([x,y,z][['x','x','y','z'.replace('z','z')].index(nm[0])]) - val) < 1e-6:
            planes.append(nm)
    print(" node %d coord=(%.9g, %.9g, %.9g) sets=%s" % (n, x, y, z, set_members[n] or "NONE"))

# pairwise distances
C = [nodes_d[n] for n in CANDS]
print("\npairwise distances (mm):")
for i in range(len(CANDS)):
    for j in range(i+1, len(CANDS)):
        d = float(np.linalg.norm(np.array(C[i])-np.array(C[j])))
        if d < 0.1:
            print(" %d-%d: %.6f" % (CANDS[i], CANDS[j], d))
