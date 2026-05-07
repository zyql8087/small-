import glob
import os
import re
import zipfile
from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

FORWARD_METRICS_PATH = str(REPO_ROOT / "GNNTransform" / "forward_test_results" / "forward_test_metrics.csv")
INVERSE_METRICS_PATH = str(REPO_ROOT / "diffusion" / "inverse_test_results" / "inverse_test_metrics.csv")
CVAE_TOPK_PATH = str(REPO_ROOT / "diffusion" / "inverse_test_results" / "cvae_topk_candidates.npz")
DIFF_TOPK_PATH = str(REPO_ROOT / "diffusion" / "inverse_test_results" / "diffusion_topk_candidates.npz")
TEST_XLSX_PATH = str(REPO_ROOT / "dataset used for training" / "test.xlsx")

OUTPUT_DIR = str(SCRIPT_DIR / "comparison_results")


def find_supp_docx() -> str:
    candidates = glob.glob(
        os.path.join(r"C:\Users\48186\Desktop", "**", "smll202500634-sup-0001-suppmat.docx"),
        recursive=True,
    )
    if not candidates:
        raise FileNotFoundError("Supplement DOCX not found under C:\\Users\\48186\\Desktop")
    return candidates[0]


def extract_paper_baseline_scores(supp_docx_path: str) -> Dict[str, float]:
    with zipfile.ZipFile(supp_docx_path, "r") as zf:
        xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")

    plain = re.sub(r"<[^>]+>", " ", xml)
    plain = re.sub(r"\s+", " ", plain)

    s1 = re.search(r"Table\s*S\s*1", plain, flags=re.IGNORECASE)
    s2 = re.search(r"Table\s*S\s*2", plain, flags=re.IGNORECASE)
    s7 = re.search(r"Section\s*S\s*7", plain, flags=re.IGNORECASE)
    if not s1 or not s2:
        raise RuntimeError("Could not locate Table S1/S2 in supplementary DOCX.")

    i1 = s1.start()
    i2 = s2.start()
    i3 = s7.start() if s7 else len(plain)
    block_s1 = plain[i1:i2]
    block_s2 = plain[i2:i3]

    vals_s1 = [float(v) for v in re.findall(r"0\.\d+", block_s1) if float(v) < 0.2]
    vals_s2 = [float(v) for v in re.findall(r"0\.\d+", block_s2) if float(v) < 0.2]
    if not vals_s1 or not vals_s2:
        raise RuntimeError("Failed to parse mean test scores from Table S1/S2.")

    # Interpreted baseline from supplementary randomized-search tables:
    # inverse baseline -> best (minimum) mean test score in Table S1
    # forward baseline -> best (minimum) mean test score in Table S2
    return {
        "inverse_mean_test_score": min(vals_s1),
        "forward_mean_test_score": min(vals_s2),
    }


def load_true_params_from_test() -> np.ndarray:
    cols = [
        "V1a",
        "V1v",
        "V1c",
        "w",
        "relativeVolume",
        "relativeArea",
        "thickness",
        "poreDiameter",
        "areaMean",
        "s1",
        "s2",
        "s3",
        "s4",
        "s5",
        "s6",
        "s7",
        "s8",
        "s9",
        "s10",
        "s11",
        "s12",
        "s13",
        "s14",
        "s15",
        "s16",
        "s17",
        "s18",
        "s19",
        "s20",
    ]
    frames = [
        pd.read_excel(TEST_XLSX_PATH, sheet_name="class1", names=cols),
        pd.read_excel(TEST_XLSX_PATH, sheet_name="class2", names=cols),
        pd.read_excel(TEST_XLSX_PATH, sheet_name="class12", names=cols),
    ]
    df = pd.concat(frames, axis=0).reset_index(drop=True)
    return df.iloc[:, :9].to_numpy(dtype=np.float32)


def compute_param_nrmse_from_topk(topk_npz_path: str, true_params: np.ndarray) -> Tuple[float, float, float]:
    topk_params = np.load(topk_npz_path)["topk_params"][:, 0, :]
    diff = true_params - topk_params
    mse = float(np.mean(diff ** 2))
    rmse = float(np.sqrt(mse))
    value_range = max(float(np.max(true_params) - np.min(true_params)), 1e-12)
    nrmse = rmse / value_range
    return mse, rmse, nrmse


def make_raw_metric_plot(ax: plt.Axes, df: pd.DataFrame, metrics: list, title: str) -> None:
    x = np.arange(len(metrics), dtype=float)
    model_names = df["model"].tolist()
    n = len(model_names)
    width = 0.8 / max(n, 1)
    for i, model in enumerate(model_names):
        vals = [float(df.iloc[i][m]) for m in metrics]
        offset = (i - (n - 1) / 2.0) * width
        bars = ax.bar(x + offset, vals, width=width, label=model)
        for b, v in zip(bars, vals):
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
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    ax.legend(fontsize=8)


def make_baseline_aligned_plot(
    ax: plt.Axes,
    labels: list,
    values: list,
    title: str,
    paper_idx: int = 0,
) -> None:
    x = np.arange(len(labels))
    colors = ["#888888"] + ["#1f77b4"] * (len(labels) - 1)
    bars = ax.bar(x, values, color=colors)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15)
    ax.set_title(title)
    ax.set_ylabel("Score (lower is better)")
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)

    paper_v = values[paper_idx]
    for i, (b, v) in enumerate(zip(bars, values)):
        if i == paper_idx:
            txt = f"{v:.5f}\n(baseline)"
        else:
            impr = (paper_v - v) / max(abs(paper_v), 1e-12) * 100.0
            txt = f"{v:.5f}\n{impr:+.1f}% vs paper"
        ax.text(
            b.get_x() + b.get_width() / 2.0,
            b.get_height(),
            txt,
            ha="center",
            va="bottom",
            fontsize=8,
        )


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    forward_df = pd.read_csv(FORWARD_METRICS_PATH)
    inverse_df = pd.read_csv(INVERSE_METRICS_PATH)

    supp_docx_path = find_supp_docx()
    paper_scores = extract_paper_baseline_scores(supp_docx_path)

    true_params = load_true_params_from_test()
    cvae_mse, cvae_rmse, cvae_param_nrmse = compute_param_nrmse_from_topk(CVAE_TOPK_PATH, true_params)
    diff_mse, diff_rmse, diff_param_nrmse = compute_param_nrmse_from_topk(DIFF_TOPK_PATH, true_params)

    forward_aligned_rows = []
    forward_paper = float(paper_scores["forward_mean_test_score"])
    forward_aligned_rows.append(
        {
            "module": "forward",
            "model": "paper_baseline_tableS2_best",
            "aligned_metric": "mean_test_score_from_tableS2",
            "score": forward_paper,
            "improvement_vs_paper_pct": 0.0,
        }
    )
    for _, row in forward_df.iterrows():
        score = float(row["nrmse_pct"]) / 100.0
        forward_aligned_rows.append(
            {
                "module": "forward",
                "model": str(row["model"]),
                "aligned_metric": "nrmse_ratio_from_test",
                "score": score,
                "improvement_vs_paper_pct": (forward_paper - score) / max(abs(forward_paper), 1e-12) * 100.0,
            }
        )
    forward_aligned_df = pd.DataFrame(forward_aligned_rows)

    inverse_paper = float(paper_scores["inverse_mean_test_score"])
    inverse_aligned_df = pd.DataFrame(
        [
            {
                "module": "inverse",
                "model": "paper_baseline_tableS1_best",
                "aligned_metric": "mean_test_score_from_tableS1",
                "score": inverse_paper,
                "improvement_vs_paper_pct": 0.0,
                "param_mse_top1": np.nan,
                "param_rmse_top1": np.nan,
            },
            {
                "module": "inverse",
                "model": "cvae",
                "aligned_metric": "param_nrmse_ratio_from_test_top1",
                "score": cvae_param_nrmse,
                "improvement_vs_paper_pct": (inverse_paper - cvae_param_nrmse) / max(abs(inverse_paper), 1e-12) * 100.0,
                "param_mse_top1": cvae_mse,
                "param_rmse_top1": cvae_rmse,
            },
            {
                "module": "inverse",
                "model": "diffusion",
                "aligned_metric": "param_nrmse_ratio_from_test_top1",
                "score": diff_param_nrmse,
                "improvement_vs_paper_pct": (inverse_paper - diff_param_nrmse) / max(abs(inverse_paper), 1e-12) * 100.0,
                "param_mse_top1": diff_mse,
                "param_rmse_top1": diff_rmse,
            },
        ]
    )

    # Save tables
    with pd.ExcelWriter(os.path.join(OUTPUT_DIR, "paper_baseline_comparison.xlsx")) as writer:
        forward_df.to_excel(writer, index=False, sheet_name="forward_raw_metrics")
        inverse_df.to_excel(writer, index=False, sheet_name="inverse_raw_metrics")
        forward_aligned_df.to_excel(writer, index=False, sheet_name="forward_vs_paper_aligned")
        inverse_aligned_df.to_excel(writer, index=False, sheet_name="inverse_vs_paper_aligned")

    forward_aligned_df.to_csv(
        os.path.join(OUTPUT_DIR, "forward_vs_paper_aligned.csv"),
        index=False,
    )
    inverse_aligned_df.to_csv(
        os.path.join(OUTPUT_DIR, "inverse_vs_paper_aligned.csv"),
        index=False,
    )

    # Build figure
    fig, axes = plt.subplots(2, 2, figsize=(18, 11))
    make_raw_metric_plot(
        ax=axes[0, 0],
        df=forward_df,
        metrics=["mse", "mae", "r2", "nrmse_pct"],
        title="Forward Module: Raw Test Metrics",
    )
    make_raw_metric_plot(
        ax=axes[1, 0],
        df=inverse_df,
        metrics=[
            "param_mse",
            "param_mae",
            "curve_mse",
            "curve_mae",
            "curve_nrmse_pct",
            "oracle_topk_param_mse",
            "oracle_topk_param_mae",
        ],
        title="Inverse Module: Raw Test Metrics",
    )
    make_baseline_aligned_plot(
        ax=axes[0, 1],
        labels=forward_aligned_df["model"].tolist(),
        values=forward_aligned_df["score"].astype(float).tolist(),
        title="Forward: Paper Baseline vs Current Models (Aligned Score)",
    )
    make_baseline_aligned_plot(
        ax=axes[1, 1],
        labels=inverse_aligned_df["model"].tolist(),
        values=inverse_aligned_df["score"].astype(float).tolist(),
        title="Inverse: Paper Baseline vs Current Models (Aligned Score)",
    )

    fig.suptitle(
        "Comparison with Paper Baseline (Supplement Table S1/S2) + Current Experiment Metrics",
        fontsize=14,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig_path = os.path.join(OUTPUT_DIR, "paper_baseline_comparison.png")
    fig.savefig(fig_path, dpi=300)
    plt.close(fig)

    meta = pd.DataFrame(
        [
            {
                "supp_docx_path": supp_docx_path,
                "paper_forward_tableS2_best": forward_paper,
                "paper_inverse_tableS1_best": inverse_paper,
                "note": (
                    "Paper baseline scores are parsed from supplementary Table S1/S2 mean test score; "
                    "cross-protocol comparison should be interpreted cautiously."
                ),
            }
        ]
    )
    meta.to_csv(os.path.join(OUTPUT_DIR, "paper_baseline_meta.csv"), index=False)

    print(f"[Saved] Figure: {fig_path}")
    print(f"[Saved] Excel:  {os.path.join(OUTPUT_DIR, 'paper_baseline_comparison.xlsx')}")
    print(f"[Saved] CSV:    {os.path.join(OUTPUT_DIR, 'forward_vs_paper_aligned.csv')}")
    print(f"[Saved] CSV:    {os.path.join(OUTPUT_DIR, 'inverse_vs_paper_aligned.csv')}")
    print(f"[Saved] Meta:   {os.path.join(OUTPUT_DIR, 'paper_baseline_meta.csv')}")
    print("\n[Forward aligned]")
    print(forward_aligned_df.to_string(index=False))
    print("\n[Inverse aligned]")
    print(inverse_aligned_df.to_string(index=False))


if __name__ == "__main__":
    main()



