from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle


ROOT = Path(r"F:\small++")
DATA_DIR = (
    ROOT
    / "origami_experiments"
    / "curve_dataset"
    / "miura_nonlinear_v2"
    / "data_random_quality_filtered"
)
OUT_DIR = ROOT / "output" / "figures"
OUT_PNG = OUT_DIR / "miura_curve_coverage_schematic.png"
OUT_SVG = OUT_DIR / "miura_curve_coverage_schematic.svg"


COND_LABELS = [
    "Bending, deploy=0.3",
    "Bending, deploy=0.6",
    "Bending, deploy=0.9",
    "Axial, deploy=0.3",
    "Axial, deploy=0.6",
    "Axial, deploy=0.9",
]
COND_COLORS = ["#6C8EBF", "#8FAADC", "#B7C9E8", "#D95F02", "#F28E2B", "#FFBE7D"]


def load_curves() -> np.ndarray:
    train = np.load(DATA_DIR / "origami_curve_train.npz", allow_pickle=True)
    test = np.load(DATA_DIR / "origami_curve_test.npz", allow_pickle=True)
    return np.concatenate([train["curve_raw"], test["curve_raw"]], axis=0).astype(float)


def draw_miura_sheet(ax: plt.Axes, y0: float, mode: str) -> None:
    """Draw a polished pseudo-3D Miura sheet in axes coordinates."""
    x0 = 0.17
    dx = 0.087
    dy = 0.072
    cols = 7
    rows = 3
    row_skew = 0.036
    fold_amp = 0.026
    edge_color = "#2F2F2F"
    facet_light = "#F3F3F3"
    facet_mid = "#D8D8D8"
    facet_dark = "#C3C3C3"

    min_x = x0 - 0.07
    max_x = x0 + (cols - 1) * dx + (rows - 1) * row_skew + 0.075
    min_y = y0 - 0.145
    max_y = y0 + 0.145

    # Soft ground shadow to give the folded sheet depth.
    shadow = [
        (min_x + 0.03, min_y - 0.025),
        (max_x - 0.02, min_y - 0.025),
        (max_x + 0.045, min_y + 0.01),
        (min_x + 0.005, min_y + 0.01),
    ]
    ax.add_patch(Polygon(shadow, closed=True, facecolor="#E9E9E9", edgecolor="none", alpha=0.75, zorder=0))

    all_left_nodes: list[tuple[float, float]] = []
    all_right_nodes: list[tuple[float, float]] = []

    for r in range(rows):
        row_center = y0 + (r - 1) * dy
        for c in range(cols):
            cx = x0 + c * dx + r * row_skew
            cy = row_center + (0.5 - (c % 2)) * fold_amp
            half_w = dx * 0.55
            half_h = dy * (0.47 + 0.04 * ((c + r) % 2))
            left = (cx - half_w, cy - 0.006)
            top = (cx + 0.012, cy + half_h)
            right = (cx + half_w, cy + 0.006)
            bottom = (cx - 0.012, cy - half_h)
            center = (cx, cy)

            shade_a = facet_light if (c + r) % 2 == 0 else facet_mid
            shade_b = facet_dark if (c + r) % 2 == 0 else "#E5E5E5"
            ax.add_patch(
                Polygon(
                    [left, top, center],
                    closed=True,
                    facecolor=shade_a,
                    edgecolor=edge_color,
                    lw=0.65,
                    joinstyle="round",
                    zorder=2,
                )
            )
            ax.add_patch(
                Polygon(
                    [top, right, center],
                    closed=True,
                    facecolor=shade_b,
                    edgecolor=edge_color,
                    lw=0.65,
                    joinstyle="round",
                    zorder=2,
                )
            )
            ax.add_patch(
                Polygon(
                    [right, bottom, center],
                    closed=True,
                    facecolor=shade_a,
                    edgecolor=edge_color,
                    lw=0.65,
                    joinstyle="round",
                    zorder=2,
                )
            )
            ax.add_patch(
                Polygon(
                    [bottom, left, center],
                    closed=True,
                    facecolor=shade_b,
                    edgecolor=edge_color,
                    lw=0.65,
                    joinstyle="round",
                    zorder=2,
                )
            )
            ax.plot([left[0], top[0], right[0], bottom[0], left[0]], [left[1], top[1], right[1], bottom[1], left[1]], color=edge_color, lw=0.85, zorder=3)
            ax.plot([left[0], right[0]], [left[1], right[1]], color="#5C5C5C", lw=0.45, zorder=3)
            ax.plot([top[0], bottom[0]], [top[1], bottom[1]], color="#777777", lw=0.45, zorder=3)

            if c == 0:
                all_left_nodes.extend([left, top, bottom])
            if c == cols - 1:
                all_right_nodes.extend([right, top, bottom])

    node_y = np.linspace(min_y + 0.018, max_y - 0.018, 6)
    left_x = min_x
    right_x = max_x
    ax.scatter([left_x] * len(node_y), node_y, s=30, color="#1E63FF", zorder=4)
    ax.scatter([right_x] * len(node_y), node_y, s=30, color="#D7191C", zorder=4)

    # Fixed boundary hatches and label.
    for yy in node_y:
        ax.plot([left_x - 0.025, left_x - 0.006], [yy - 0.018, yy + 0.018], color="#1E63FF", lw=1.4)
        ax.plot([left_x - 0.032, left_x - 0.012], [yy - 0.018, yy + 0.018], color="#1E63FF", lw=1.4)
    ax.text(
        left_x - 0.035,
        max_y + 0.045,
        "Fixed left edge\nUx=Uy=Uz=0",
        color="#1E63FF",
        fontsize=8,
        ha="right",
        va="center",
        bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="#1E63FF", lw=1),
    )

    # Applied nodal forces.
    if mode == "bending":
        for yy in node_y:
            ax.add_patch(
                FancyArrowPatch(
                    (right_x + 0.022, yy + 0.032),
                    (right_x + 0.022, yy - 0.045),
                    arrowstyle="-|>",
                    mutation_scale=13,
                    color="#D7191C",
                    lw=1.3,
                )
            )
        load_text = "Bending:\nforce-control\n-Z load"
        text_xy = (right_x + 0.065, y0 + 0.09)
    else:
        for yy in node_y:
            ax.add_patch(
                FancyArrowPatch(
                    (right_x + 0.005, yy),
                    (right_x + 0.085, yy),
                    arrowstyle="-|>",
                    mutation_scale=13,
                    color="#D7191C",
                    lw=1.3,
                )
            )
        load_text = "Axial:\nforce-control\n+X load"
        text_xy = (right_x + 0.065, y0 - 0.01)

    ax.text(
        *text_xy,
        load_text,
        color="#D7191C",
        fontsize=8,
        fontweight="bold",
        ha="center",
        va="center",
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#D7191C", lw=1),
    )


def draw_parameter_panel(ax: plt.Axes) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.0, 0.98, "A  Simulation domain", fontsize=12, fontweight="bold", va="top")
    draw_miura_sheet(ax, 0.68, "bending")
    ax.plot([0.04, 0.96], [0.5, 0.5], ls=(0, (4, 4)), color="#BBBBBB", lw=1)
    draw_miura_sheet(ax, 0.28, "axial")

    ax.text(
        0.08,
        0.08,
        "Parameter coverage\n"
        "pattern=Miura only | m=24/30/36 | n=6/9/12\n"
        "tcrease=0.50-1.00 mm | tpanel=1.00-6.00 mm | W=1.00-4.00 mm\n"
        "creaseE=1.01-5.00 GPa | panelE=1.00-5.00 GPa",
        fontsize=7.5,
        color="#333333",
        ha="left",
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.28", fc="#F7F7F7", ec="#C8C8C8", lw=0.8),
    )

    ax.plot([0.08, 0.22], [0.02, 0.02], color="#1E63FF", lw=2)
    ax.text(0.24, 0.02, "fixed boundary", fontsize=7, va="center", color="#333333")
    ax.plot([0.43, 0.57], [0.02, 0.02], color="#D7191C", lw=2)
    ax.text(0.59, 0.02, "applied nodal force", fontsize=7, va="center", color="#333333")


def make_line_collection(x: np.ndarray, y: np.ndarray, color: str, alpha: float, lw: float) -> LineCollection:
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    return LineCollection(segments, colors=color, linewidths=lw, alpha=alpha)


def draw_curve_panel(ax: plt.Axes, curve: np.ndarray) -> None:
    disp_mm = curve[..., 0] * 1000.0
    force_n = curve[..., 1]
    ax.set_title("B  Actual force-displacement coverage", loc="left", fontsize=12, fontweight="bold", pad=10)

    rng = np.random.default_rng(7)
    for cond, color in enumerate(COND_COLORS):
        idx = rng.choice(curve.shape[0], size=min(160, curve.shape[0]), replace=False)
        for sample_idx in idx:
            ax.add_collection(
                make_line_collection(
                    disp_mm[sample_idx, cond, :],
                    force_n[sample_idx, cond, :],
                    color=color,
                    alpha=0.05,
                    lw=0.45,
                )
            )
        x_med = np.nanmedian(disp_mm[:, cond, :], axis=0)
        y_med = np.nanmedian(force_n[:, cond, :], axis=0)
        ax.plot(x_med, y_med, color=color, lw=2.2, label=COND_LABELS[cond], zorder=5)

    ax.axhline(10000, color="#666666", lw=1, ls=(0, (4, 3)))
    ax.text(74.0, 10150, "10 kN force cap", fontsize=7, ha="right", va="bottom", color="#555555")
    ax.set_xlim(0, 78)
    ax.set_ylim(0, 10800)
    ax.set_xlabel("Displacement magnitude (mm)", labelpad=6)
    ax.set_ylabel("Force magnitude (N)")
    ax.grid(True, color="#DDDDDD", lw=0.6)
    ax.legend(loc="upper left", fontsize=6.4, frameon=False, ncols=1)

    stats_text = (
        "Filtered dataset: 1,999 samples\n"
        "6 conditions x 80 load steps\n"
        "Total curve points: 959,520\n"
        "Displacement: 0.09-74.3 mm\n"
        "Force: 0.08-10,000 N"
    )
    ax.text(
        0.98,
        0.04,
        stats_text,
        transform=ax.transAxes,
        fontsize=8,
        ha="right",
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#999999", lw=0.8, alpha=0.95),
    )


def draw_condition_summary(ax: plt.Axes, curve: np.ndarray) -> None:
    disp_final = curve[:, :, -1, 0] * 1000.0
    force_final = curve[:, :, -1, 1]
    short_labels = ["Bend 0.3", "Bend 0.6", "Bend 0.9", "Axial 0.3", "Axial 0.6", "Axial 0.9"]
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.0, 0.99, "C  Coverage by loading condition", fontsize=12, fontweight="bold", va="top")

    x0, y0 = 0.02, 0.82
    row_h = 0.108
    col_x = [0.02, 0.34, 0.58, 0.81]
    headers = ["Condition", "Final disp.\np50/p95/max", "Final force\np50/p95/max", "Nonlinearity\nmean/p95"]
    for j, h in enumerate(headers):
        ax.text(col_x[j], y0, h, fontsize=6.7, fontweight="bold", ha="left", va="top", linespacing=1.18)
    ax.plot([x0, 0.97], [y0 - 0.074, y0 - 0.074], color="#999999", lw=0.8)

    # Known audit values after quality filtering, computed from audit CSV.
    secant_mean_p95 = [
        (0.2770, 0.7123),
        (0.0283, 0.0970),
        (0.0080, 0.0157),
        (0.0812, 0.1095),
        (0.1615, 0.2258),
        (0.5713, 0.9464),
    ]
    for i, label in enumerate(COND_LABELS):
        y = y0 - 0.112 - i * row_h
        ax.add_patch(Rectangle((x0, y - 0.042), 0.95, row_h * 0.72, facecolor="#FAFAFA" if i % 2 else "white", edgecolor="none"))
        ax.add_patch(Rectangle((x0, y - 0.017), 0.016, 0.016, facecolor=COND_COLORS[i], edgecolor="none"))
        d = np.quantile(disp_final[:, i], [0.5, 0.95, 1.0])
        f = np.quantile(force_final[:, i], [0.5, 0.95, 1.0])
        values = [
            short_labels[i],
            f"{d[0]:.1f}/{d[1]:.1f}/{d[2]:.1f} mm",
            f"{f[0]:.0f}/{f[1]:.0f}/{f[2]:.0f} N",
            f"{secant_mean_p95[i][0]:.3f}/{secant_mean_p95[i][1]:.3f}",
        ]
        for j, val in enumerate(values):
            ax.text(col_x[j] + (0.024 if j == 0 else 0.0), y, val, fontsize=6.35, ha="left", va="center", color="#222222")

    ax.text(
        0.02,
        0.015,
        "Transparent traces: sampled curves. Thick lines: median responses.\n"
        "Scope: SWOMPS NR force-controlled stable paths, not top-platen compression.",
        fontsize=7.0,
        color="#444444",
        va="bottom",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    curve = load_curves()

    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )

    fig = plt.figure(figsize=(16, 10), dpi=200)
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "Miura-ori Nonlinear Simulation Curve Coverage",
        fontsize=18,
        fontweight="bold",
        y=0.975,
    )

    gs = fig.add_gridspec(
        2,
        2,
        width_ratios=[1.28, 1.0],
        height_ratios=[1.0, 0.72],
        left=0.035,
        right=0.985,
        top=0.89,
        bottom=0.055,
        wspace=0.12,
        hspace=0.38,
    )

    ax_a = fig.add_subplot(gs[:, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 1])
    draw_parameter_panel(ax_a)
    draw_curve_panel(ax_b, curve)
    draw_condition_summary(ax_c, curve)

    fig.savefig(OUT_PNG, bbox_inches="tight", dpi=300)
    fig.savefig(OUT_SVG, bbox_inches="tight")
    print(OUT_PNG)
    print(OUT_SVG)


if __name__ == "__main__":
    main()
