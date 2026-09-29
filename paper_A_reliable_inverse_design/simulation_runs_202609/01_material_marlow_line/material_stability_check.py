import numpy as np

# Exact uniaxial test data from m2_small_repro.inp (*Uniaxial Test Data)
stress = np.array([-0.0096, 0.0024, 0.0174, 0.03264, 4.017, 4.01772, 4.01844, 4.01904])
strain = np.array([0.0,     0.0002, 0.0011, 0.002,   0.9978, 0.9987, 0.9995, 1.0003])

# Reduced polynomial n=2, incompressible uniaxial nominal stress:
# W = C10(I1-3)+C01(I2-3)+C20(I1-3)^2+C11(I1-3)(I2-3)+C02(I2-3)^2
def principal_stretch_to_invariants(lam):
    I1 = lam**2 + 2.0/lam
    I2 = 2.0*lam + 1.0/lam**2
    return I1-3.0, I2-3.0

def model_stress(lam, C):
    c10,c01,c20,c11,c02 = C
    a,b = principal_stretch_to_invariants(lam)
    # P = dW/dlam via central difference on analytic W
    W = c10*a + c01*b + c20*a*a + c11*a*b + c02*b*b
    h = 1e-6
    ap,bp = principal_stretch_to_invariants(lam+h)
    am,bm = principal_stretch_to_invariants(lam-h)
    Wp = c10*ap + c01*bp + c20*ap*ap + c11*ap*bp + c02*bp*bp
    Wm = c10*am + c01*bm + c20*am*am + c11*am*bm + c02*bm*bm
    return (Wp-Wm)/(2*h)

def fit():
    from scipy.optimize import least_squares
    lam = 1.0 + strain
    def resid(C):
        return model_stress(lam, C) - stress
    best=None
    for seed in [[0.1,0.1,0,0,0],[1,1,0,0,0],[0.5,0.0,0.1,0,0],[0.05,0.05,0.01,0.01,0.01]]:
        try:
            r = least_squares(resid, seed, method='lm', max_nfev=20000)
            if best is None or r.cost < best.cost: best = r
        except Exception as e:
            pass
    return best

r = fit()
C = r.x
print("fitted C10,C01,C20,C11,C02 =", np.array2string(C, precision=6))
print("rms residual =", np.sqrt(np.mean(r.fun**2)), "max|resid| =", np.max(np.abs(r.fun)))

# Scan uniaxial tangent stability dP/dlam over compression & tension beyond data range
lam_scan = np.concatenate([np.linspace(0.05,1.0,400), np.linspace(1.001,3.0,400)])
P = np.array([model_stress(l, C) for l in lam_scan])
dP = np.gradient(P, lam_scan)
unstable = dP <= 0
if unstable.any():
    # report unstable stretches
    segs=[]; start=None
    for i,u in enumerate(unstable):
        if u and start is None: start=i
        if (not u or i==len(unstable)-1) and start is not None:
            end = i if not u else i
            segs.append((lam_scan[start], lam_scan[end])); start=None
    print("UNSTABLE uniaxial stretch ranges (tangent<=0):", [(round(a,3),round(b,3)) for a,b in segs])
    print("  => nominal strain ranges:", [(round(a-1,3),round(b-1,3)) for a,b in segs])
else:
    print("uniaxial tangent stable over scanned range")

# Local bottleneck strain levels (log strain LE13 up to 5.5 => equivalent shear)
print("\ncontext: bottleneck elements reach |LE13| up to ~5.5 (log shear), global 24% compression")
print("data coverage: only strain<=1.0; polynomial extrapolates uncontrolled beyond")
