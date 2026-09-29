import numpy as np
from scipy.optimize import least_squares

# Full author curve (1201 pts, stress/strain)
data = np.genfromtxt("F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/iteration_diagnosis/author_uniaxial_full.csv", delimiter=",", skip_header=1)
S, E = data[:,0], data[:,1]
lam = 1.0 + E

def invs(l):
    return l**2 + 2.0/l, 2.0*l + 1.0/l**2

def stress(l, C):
    c10,c01,c20,c11,c02 = C
    a,b = invs(l); ap,bp = invs(l+1e-6); am,bm = invs(l-1e-6)
    W  = c10*a  + c01*b  + c20*a*a  + c11*a*b  + c02*b*b
    Wp = c10*ap + c01*bp + c20*ap*ap + c11*ap*bp + c02*bp*bp
    Wm = c10*am + c01*bm + c20*am*am + c11*am*bm + c02*bm*bm
    return (Wp-Wm)/(2e-6)

def fit(S, E, seeds):
    lam = 1.0 + E
    best = None
    for seed in seeds:
        r = least_squares(lambda C: stress(lam, C) - S, seed, method='lm', max_nfev=50000)
        if best is None or r.cost < best.cost: best = r
    return best

seeds = [[0.1,0.1,0,0,0],[1,1,0,0,0],[0.5,0,0.1,0,0],[0.05,0.05,0.01,0.01,0.01],[2,0.5,0,0,0]]
rf = fit(S, E, seeds)
print("FULL-curve fit C =", np.array2string(rf.x, precision=6), " rms=%.5f MPa" % np.sqrt(np.mean(rf.fun**2)))

# stability scan: uniaxial tangent over lambda 0.05..3.0
lscan = np.concatenate([np.linspace(0.05,1.0,600), np.linspace(1.001,3.0,600)])
P = np.array([stress(l, rf.x) for l in lscan])
dP = np.gradient(P, lscan)
neg = dP <= 1e-9
segs=[]; start=None
for i,u in enumerate(neg):
    if u and start is None: start=i
    if (not u or i==len(neg)-1) and start is not None:
        end = i if not u else i+0
        segs.append((lscan[start], lscan[end])); start=None
if segs:
    print("FULL-curve fit UNSTABLE stretches:", [(round(a,3),round(b,3)) for a,b in segs])
    print("   (nominal strain):", [(round(a-1,3),round(b-1,3)) for a,b in segs])
else:
    print("FULL-curve fit: tangent POSITIVE everywhere on lambda in [0.05, 3.0]  => STABLE")

# compare with the 8-point fit's coefficients for the record
print("\n(8-pt fit was: C10=0.098165 C01=2.606212 C20=0.115927 C11=0.087328 C02=-0.730452, unstable lambda 0.05-0.605)")
