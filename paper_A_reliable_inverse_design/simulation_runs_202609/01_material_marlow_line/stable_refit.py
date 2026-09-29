# Stability-constrained refit of the SAME 1202-point author curve.
# Form: polynomial n=2 (same as author), D1 fixed from nu=0.47, deviatoric C refit
# with dP/dlambda > 0 constraints on uniaxial/biaxial/planar grids.
import numpy as np
from scipy.optimize import least_squares, minimize

D1 = 1.720906188E-02
data = np.genfromtxt("F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/iteration_diagnosis/author_uniaxial_full.csv", delimiter=",", skip_header=1)
S, E = data[:,0], data[:,1]
lam = 1.0 + E

def stretch_paths(l):
    # returns (I1-3, I2-3) for uniaxial(l), biaxial(l), planar(l) and the deformation gradient scale
    return {
        'uni':  (l**2 + 2.0/l, 2.0*l + 1.0/l**2),
        'biax': (2.0*l**2 + 1.0/l**4, l**4 + 2.0/l**2),
        'plan': (l**2 + l**-2 + 1.0, l**2 + l**-2 + 1.0),  # placeholder (same W arg but stress differs)
    }

def W(C, a, b):
    c10,c01,c20,c11,c02 = C
    return c10*a + c01*b + c20*a*a + c11*a*b + c02*b*b

def stress_uni(l, C):
    a,b = stretch_paths(l)['uni']
    h = 1e-6
    ap,bp = stretch_paths(l+h)['uni']; am,bm = stretch_paths(l-h)['uni']
    return (W(C,ap,bp) - W(C,am,bm))/(2*h)

def stress_biax(l, C):
    # P_biaxial = dW/dl under l1=l2=l, l3=1/l^2
    def F(x):
        a = 2*x**2 + 1.0/x**4; b = x**4 + 2.0/x**2
        return W(C, a, b)
    h=1e-6
    return (F(l+h)-F(l-h))/(2*h)

def stress_planar(l, C):
    # P_planar = dW/dl under l1=l, l2=1, l3=1/l
    def F(x):
        a = x**2 + 1.0 + 1.0/x**2
        b = x**2 + 1.0 + 1.0/x**2  # wrong split; compute directly from invariants
        I1 = x**2 + 1.0 + x**-2
        I2 = x**2 + 1.0 + x**-2
        return W(C, I1-3.0, I2-3.0)
    h=1e-6
    return (F(l+h)-F(l-h))/(2*h)

# NOTE: planar invariants I1=I2 for this path, and P = dW/dl (the path derivative) —
# since both invariants move together, dW/dl = dW/dI1 * dI1/dl + dW/dI2 * dI2/dl.
# The numeric F above handles it correctly via invariants depending on l.

# ---- unconstrained refit (reference) ----
def resid_uni(C):
    return stress_uni(lam, C) - S
best=None
for seed in [[0.1,0.1,0,0,0],[1,1,0,0,0],[-1,1,0,0,0],[0.5,0.5,0.1,0,0]]:
    r = least_squares(resid_uni, seed, method='lm', max_nfev=50000)
    if best is None or r.cost < best.cost: best = r
print("unconstrained C:", np.array2string(best.x, precision=5), "rms=%.4f" % np.sqrt(np.mean(best.fun**2)))

# ---- stability-constrained refit ----
l_uni  = np.concatenate([np.linspace(0.62, 1.0, 40), np.linspace(1.001, 2.7, 60)])
l_biax = np.concatenate([np.linspace(0.70, 1.0, 30), np.linspace(1.001, 1.7, 50)])
l_plan = np.concatenate([np.linspace(0.62, 1.0, 30), np.linspace(1.001, 1.7, 50)])

def tangents(C):
    tu = np.gradient([stress_uni(l, C) for l in l_uni], l_uni)
    tb = np.gradient([stress_biax(l, C) for l in l_biax], l_biax)
    tp = np.gradient([stress_planar(l, C) for l in l_plan], l_plan)
    return tu, tb, tp

def obj(C):
    r = stress_uni(lam, C) - S
    return np.mean(r*r)

cons = []
def make_tang_cons(vals, lgrid, margin):
    def f(C):
        P = np.array([stress_uni(l, C) for l in lgrid])
        return np.min(np.gradient(P, lgrid)) - margin
    return f
# enforce via penalty (SLSQP with single min-constraint is non-smooth; use soft penalties)
def penal(C):
    tu, tb, tp = tangents(C)
    m = 0.02  # required minimum tangent (MPa per unit strain), a bit above 0
    p = np.sum(np.maximum(0.0, m - tu)**2) + np.sum(np.maximum(0.0, m - tb)**2) + np.sum(np.maximum(0.0, m - tp)**2)
    return obj(C) + 1e4 * p

from scipy.optimize import minimize as spmin
x0 = best.x
res = spmin(penal, x0, method='Nelder-Mead', options={'maxiter':20000, 'xatol':1e-8, 'fatol':1e-12})
# polish with Powell
res2 = spmin(penal, res.x, method='Powell', options={'maxiter':20000, 'xtol':1e-10, 'ftol':1e-12})
Cst = res2.x
tu, tb, tp = tangents(Cst)
print("constrained C:", np.array2string(Cst, precision=6))
print("rms=%.4f MPa  min tangents: uni=%.4f biax=%.4f plan=%.4f" % (
    np.sqrt(np.mean((stress_uni(lam, Cst)-S)**2)), tu.min(), tb.min(), tp.min()))

# final stability scan (report ranges where tangent<=0, if any)
def scan(C, name):
    bad=[]
    for g,(f,l) in {'uni':(stress_uni,l_uni),'biax':(stress_biax,l_biax),'plan':(stress_planar,l_plan)}.items():
        P = np.array([f(l,C) for l in l]); t = np.gradient(P,l)
        if (t<=0).any(): bad.append((g, float(l[t<=0].min()), float(l[t<=0].max())))
    print(name, "unstable segs:", bad if bad else "NONE on scanned grids")
scan(best.x, "unconstrained:")
scan(Cst,  "constrained: ")
np.savetxt("F:/small++/paper_A_reliable_inverse_design/audits/m05_post_round6_20260921/iteration_diagnosis/stable_refit_constants.csv",
           np.append(Cst, D1)[None,:], delimiter=",", header="C10,C01,C20,C11,C02,D1", comments="")
print("saved -> stable_refit_constants.csv")
