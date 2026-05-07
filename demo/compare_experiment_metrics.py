import os
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
FORWARD_METRICS_PATH = str(REPO_ROOT / "GNNTransform" / "forward_test_results" / "forward_test_metrics.csv")
INVERSE_METRICS_PATH = str(REPO_ROOT / "diffusion" / "inverse_test_results" / "inverse_test_metrics.csv")
OUTPUT_DIR = str(SCRIPT_DIR / "comparison_results")


def _improvement_percent(value: float, baseline: float, higher_is_better: bool) -> float:
    baseline = float(baseline)
    value = float(value)
    denom = max(abs(baseline), 1e-12)
    if higher_is_better:
        return (value - baseline) / denom * 100.0
    return (baseline - value) / denom * 100.0


def _find_baseline_model(df: pd.DataFrame, preferred_names: Iterable[str]) -> str:
    model_names = [str(x).lower() for x in df["model"].tolist()]
    for preferred in preferred_names:
        for idx, name in enumerate(model_names):
            if preferred in name:
                return str(df.iloc[idx]["model"])
    return str(df.iloc[0]["model"])


def _build_improvement_table(
    df: pd.DataFrame,
    baseline_model: str,
    metric_directions: Dict[str, bool],
    module_name: str,
) -> pd.DataFrame:
    baseline_row = df.loc[df["model"] == baseline_model].iloc[0]
    rows: List[Dict[str, float]] = []
    for _, row in df.iterrows():
        out = {
            "module": module_name,
            "baseline_model": baseline_model,
            "model": row["model"],
        }
        for metric, higher_is_better in metric_directions.items():
            out[metric] = float(row[metric])
            out[f"{metric}_impr_pct"] = _improvement_percent(
                value=float(row[metric]),
                baseline=float(baseline_row[metric]),
                higher_is_better=higher_is_better,
            )
        rows.append(out)
    return pd.DataFrame(rows)


def _plot_grouped_bars(
    ax: plt.Axes,
    df: pd.DataFrame,
    metrics: List[str],
    title: str,
    ylabel: str,
) -> None:
    x = np.arange(len(metrics), dtype=float)
    model_names = df["model"].tolist()
    n_models = len(model_names)
    width = 0.8 / max(n_models, 1)

    for i, model_name in enumerate(model_names):
        row = df.iloc[i]
        values = [float(row[m]) for m in metrics]
        shift = (i - (n_models - 1) / 2.0) * width
        bars = ax.bar(x + shift, values, width=width, label=model_name)
        for b, v in zip(bars, values):
            ax.text(
                b.get_x() + b.get_width() / 2.0,
                b.get_height(),
                f"{v:.3g}",
                ha="center",
                va="bottom",
                fontsize=8,
                rotation=90,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(metrics, rotation=20)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    ax.legend(fontsize=8)


def _plot_improvement_heatmap(
    ax: plt.Axes,
    impr_df: pd.DataFrame,
    impr_cols: List[str],
    title: str,
) -> None:
    plot_df = impr_df.copy()
    metric_labels = [c.replace("_impr_pct", "") for c in impr_cols]
    data = plot_df[impr_cols].to_numpy(dtype=float)
    model_labels = plot_df["model"].tolist()

    vmax = max(abs(data.min()), abs(data.max()), 1e-6)
    im = ax.imshow(data, cmap="RdYlGn", vmin=-vmax, vmax=vmax, aspect="auto")

    ax.set_xticks(np.arange(len(metric_labels)))
    ax.set_xticklabels(metric_labels, rotation=25, ha="right")
    ax.set_yticks(np.arange(len(model_labels)))
    ax.set_yticklabels(model_labels)
    ax.set_title(title)

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{data[i, j]:.1f}%", ha="center", va="center", fontsize=8)

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Improvement vs baseline (%)\n(+ better)")


def build_comparison_figure(
    forward_raw: pd.DataFrame,
    inverse_raw: pd.DataFrame,
    forward_impr: pd.DataFrame,
    inverse_impr: pd.DataFrame,
    output_path: str,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(18, 11))

    _plot_grouped_bars(
        ax=axes[0, 0],
        df=forward_raw,
        metrics=["mse", "mae", "r2", "nrmse_pct"],
        title="Forward Module: Absolute Metrics",
        ylabel="Metric Value",
    )

    _plot_grouped_bars(
        ax=axes[1, 0],
        df=inverse_raw,
        metrics=[
            "param_mse",
            "param_mae",
            "curve_mse",
            "curve_mae",
            "curve_nrmse_pct",
            "oracle_topk_param_mse",
            "oracle_topk_param_mae",
        ],
        title="Inverse Module: Absolute Metrics",
        ylabel="Metric Value",
    )

    _plot_improvement_heatmap(
        ax=axes[0, 1],
        impr_df=forward_impr,
        impr_cols=["mse_impr_pct", "mae_impr_pct", "r2_impr_pct", "nrmse_pct_impr_pct"],
        title=f"Forward Improvement vs {forward_impr['baseline_model'].iloc[0]}",
    )

    _plot_improvement_heatmap(
        ax=axes[1, 1],
        impr_df=inverse_impr,
        impr_cols=[
            "param_mse_impr_pct",
            "param_mae_impr_pct",
            "curve_mse_impr_pct",
            "curve_mae_impr_pct",
            "curve_nrmse_pct_impr_pct",
            "oracle_topk_param_mse_impr_pct",
            "oracle_topk_param_mae_impr_pct",
        ],
        title=f"Inverse Improvement vs {inverse_impr['baseline_model'].iloc[0]}",
    )

    fig.suptitle("Model Comparison: Forward + Inverse (Absolute & Improvement)")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    forward_df = pd.read_csv(FORWARD_METRICS_PATH)
    inverse_df = pd.read_csv(INVERSE_METRICS_PATH)

    forward_baseline = _find_baseline_model(forward_df, preferred_names=("gat",))
    inverse_baseline = _find_baseline_model(inverse_df, preferred_names=("cvae",))

    forward_dirs = {
        "mse": False,
        "mae": False,
        "r2": True,
        "nrmse_pct": False,
    }
    inverse_dirs = {
        "param_mse": False,
        "param_mae": False,
        "curve_mse": False,
        "curve_mae": False,
        "curve_nrmse_pct": False,
        "oracle_topk_param_mse": False,
        "oracle_topk_param_mae": False,
    }

    forward_impr = _build_improvement_table(
        df=forward_df,
        baseline_model=forward_baseline,
        metric_directions=forward_dirs,
        module_name="forward",
    )
    inverse_impr = _build_improvement_table(
        df=inverse_df,
        baseline_model=inverse_baseline,
        metric_directions=inverse_dirs,
        module_name="inverse",
    )

    summary_path = os.path.join(OUTPUT_DIR, "metrics_comparison_summary.csv")
    summary_df = pd.concat([forward_impr, inverse_impr], axis=0, ignore_index=True)
    summary_df.to_csv(summary_path, index=False)

    fig_path = os.path.join(OUTPUT_DIR, "metrics_comparison_visualization.png")
    build_comparison_figure(
        forward_raw=forward_df,
        inverse_raw=inverse_df,
        forward_impr=forward_impr,
        inverse_impr=inverse_impr,
        output_path=fig_path,
    )

    print(f"[Saved] Summary CSV: {summary_path}")
    print(f"[Saved] Figure:      {fig_path}")
    print("\n[Forward baseline]", forward_baseline)
    print(forward_impr.to_string(index=False))
    print("\n[Inverse baseline]", inverse_baseline)
    print(inverse_impr.to_string(index=False))


if __name__ == "__main__":
    main()



