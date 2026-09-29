# Showcase figure: M3-26 (densest M3, rv=0.154), first full 25% explicit z-completion for M3 class.
import csv, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 9, "axes.titlesize": 9.5, "axes.titleweight": "bold",
    "axes.labelsize": 9, "legend.fontsize": 8, "legend.frameon": False,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False,
})

BASE = r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/cases/m3_class12_26/results"
d = np.load(BASE + "/m3_class12_26_extract.npz", allow_pickle=True)
node_coords = d["node_coords"]; frames = d["frames"]
U = d["U"]; SENER = d["SENER"]
nlabels = d["node_labels"]
order = np.argsort(nlabels)
pos = np.searchsorted(nlabels[order], d["conn"])
conn = order[pos]

cent0 = node_coords[conn].mean(1)
HALF = 2.0
slab = np.abs(cent0[:, 0]) <= HALF
slab_idx = np.where(slab)[0]
depth = np.abs(cent0[slab_idx, 0])
print("slab elements:", len(slab_idx))

SLABS = [0, 5, 10, 20]
cmap = LinearSegmentedColormap.from_list("ocean", ["#264653", "#2A9D8F", "#E9C46A", "#E76F51"])
vmax = float(np.percentile(SENER[20][slab_idx], 99.0))

fig = plt.figure(figsize=(7.0, 5.6))
gs = fig.add_gridspec(2, 4, height_ratios=[1.05, 1.0], hspace=0.10, wspace=0.22,
                      top=0.88, bottom=0.09, left=0.06, right=0.985)
axes_top = [fig.add_subplot(gs[0, i]) for i in range(4)]

for ax, fi in zip(axes_top, SLABS):
    defc = cent0[slab_idx] + U[fi][conn[slab_idx]].mean(1)
    val = SENER[fi][slab_idx, 0]
    o = np.argsort(depth)
    ax.scatter(defc[o, 1], defc[o, 2], c=val[o], s=0.6 + 1.2 * (1 - depth[o] / HALF),
               cmap=cmap, vmin=0.0, vmax=vmax, rasterized=True, linewidths=0, alpha=0.95)
    ax.set_xlim(-20, 20); ax.set_ylim(-20.5, 20.0)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    t = float(frames[fi][2])
    ax.set_title("%.1f%% strain" % (25.0 * t / 0.1), pad=3)
    for sp in ax.spines.values(): sp.set_color("#B0BEC5")
axes_top[0].set_ylabel("z (mm)", fontsize=8.5)
axes_top[0].text(0.56, 0.30, "SENER (mJ/mm$^3$), mid-slab $|x|\leq$2.0 mm",
                 transform=axes_top[0].transAxes, ha="center", fontsize=7, color="#555")

axc = fig.add_subplot(gs[1, 0:2])
eps, rf = [], []
with open(BASE + "/curve.csv") as f:
    for row in csv.DictReader(f):
        eps.append(float(row["eps_engineering"]) * 100.0)
        rf.append(float(row["RF3_total_N"]))
eps = np.array(eps); rf = np.array(rf)
axc.plot(eps, -rf, color="#264653", lw=1.8)
for e in (0.0, 6.3, 12.5, 25.0):
    i = int(np.argmin(np.abs(eps - e)))
    axc.plot(eps[i], -rf[i], "o", ms=5, color="#E76F51", zorder=3)
axc.annotate("25%: RF$_3$ = 76.76 N", xy=(24.6, 76.0), xytext=(10.5, 62.0),
             fontsize=8, arrowprops=dict(arrowstyle="-", color="#6B7280", lw=0.8))
axc.set_xlabel("engineering strain (%)  \u2014  z-compression, Abaqus/Explicit")
axc.set_ylabel("reaction force $-\Sigma$RF$_3$ (N)")
axc.set_title("(e) M3-26 load\u2013displacement (densest M3, rv=0.154)", loc="left")

axe = fig.add_subplot(gs[1, 2:4])
en = {}
with open(BASE + "/history_energies.csv") as f:
    for row in csv.DictReader(f):
        en.setdefault(row["quantity"], []).append((float(row["time"]), float(row["value_Nmm"])))
def arr(q):
    a = np.array(en[q]); return a[:, 0], a[:, 1]
t_ie, allie = arr("ALLIE"); _, allke = arr("ALLKE"); _, allae = arr("ALLAE")
with np.errstate(divide="ignore", invalid="ignore"):
    r_ke = np.where(allie > 1e-9, allke / allie * 100.0, np.nan)
    r_ae = np.where(allie > 1e-9, allae / allie * 100.0, np.nan)
i_peak = int(np.nanargmax(r_ke))
tt = np.clip(t_ie * 1000.0, 0.6, None)
axe.semilogx(tt, r_ke, color="#E76F51", lw=1.6, label="ALLKE / ALLIE")
axe.semilogx(tt, np.maximum(r_ae, 1e-3), color="#2A9D8F", lw=1.6, label="ALLAE / ALLIE")
axe.axhline(5.0, color="#6B7280", ls="--", lw=1.0)
axe.text(0.75, 0.0012, "5% gate", fontsize=7.5, color="#6B7280")
axe.annotate("start-up transient\npeak %.0f%% @ %.2f ms" % (r_ke[i_peak], t_ie[i_peak]*1000),
             xy=(t_ie[i_peak]*1000, r_ke[i_peak]), xytext=(6.0, 130),
             fontsize=7.5, arrowprops=dict(arrowstyle="-", color="#6B7280", lw=0.8))
axe.set_xlabel("time (ms, log)")
axe.set_ylabel("energy ratio (%)")
axe.set_ylim(5e-4, 200)
axe.legend(loc="upper right")
axe.set_title("(f) quasi-static validity", loc="left")

fig.suptitle("M3-26 (class12:26, rv=0.154) \u00b7 Abaqus/Explicit \u00b7 z-compression to 25% \u00b7 first full M3-class completion",
             fontsize=10.5, weight="bold", y=0.965)
out = BASE + "/figures"
os.makedirs(out, exist_ok=True)
fig.savefig(out + "/fig_m3_26_showcase.pdf")
fig.savefig(out + "/fig_m3_26_showcase.png", dpi=300)
print("saved:", out + "/fig_m3_26_showcase.png")
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    r_k = np.where(allie > 1e-9, allke / allie * 100.0, np.nan)
    m = t_ie >= 0.05
    print("PEAK ALLKE/ALLIE = %.1f%% @ t=%.4f s | late-time(>=50ms) median %.2f%% max %.2f%% | ALLAE max %.2f%%" % (
        np.nanmax(r_k), t_ie[int(np.nanargmax(r_k))], np.nanmedian(r_k[m]), np.nanmax(r_k[m]), np.nanmax(np.where(allie>1e-9, allae/allie*100, np.nan))))
