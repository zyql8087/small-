"""Audit trained taskfit model artifacts and summarize usability."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch

from train_taskfit import TaskfitPreprocessor


globals()["TaskfitPreprocessor"] = TaskfitPreprocessor


SCRIPT_DIR = Path(__file__).resolve().parent


MODEL_CANDIDATES = [
    {
        "name": "forward_resmlp",
        "role": "forward",
        "checkpoint": SCRIPT_DIR / "checkpoints_taskfit" / "forward_resmlp" / "forward_resmlp_best.pth",
        "history": SCRIPT_DIR / "results_taskfit" / "forward_resmlp_history.csv",
        "metric": "val_total",
        "usable_below": 0.0010,
        "production": True,
    },
    {
        "name": "forward_gat_physical_sparse",
        "role": "forward",
        "checkpoint": SCRIPT_DIR
        / "gat_grid_sparse"
        / "checkpoints_h192_d0p12_lr0p0002"
        / "forward_gat"
        / "forward_gat_best.pth",
        "history": SCRIPT_DIR / "gat_grid_sparse" / "results_h192_d0p12_lr0p0002" / "forward_gat_history.csv",
        "metric": "val_total",
        "usable_below": 0.0010,
        "production": True,
    },
    {
        "name": "forward_transformer",
        "role": "forward",
        "checkpoint": SCRIPT_DIR
        / "tf_grid"
        / "checkpoints_h192_d0p08_lr0p0002"
        / "forward_transformer"
        / "forward_transformer_best.pth",
        "history": SCRIPT_DIR / "tf_grid" / "results_h192_d0p08_lr0p0002" / "forward_transformer_history.csv",
        "metric": "val_total",
        "usable_below": 0.0010,
        "production": True,
    },
    {
        "name": "inverse_resmlp",
        "role": "inverse_parameter_recovery",
        "checkpoint": SCRIPT_DIR / "checkpoints_taskfit" / "inverse_resmlp" / "inverse_resmlp_best.pth",
        "history": SCRIPT_DIR / "results_taskfit" / "inverse_resmlp_history.csv",
        "metric": "val_closed_loop",
        "usable_below": 0.0030,
        "production": True,
    },
    {
        "name": "inverse_cvae_physical",
        "role": "inverse_closed_loop",
        "checkpoint": SCRIPT_DIR / "checkpoints_taskfit_round3_physical" / "inverse_cvae" / "inverse_cvae_best.pth",
        "history": SCRIPT_DIR / "results_taskfit_round3_physical" / "inverse_cvae_history.csv",
        "metric": "val_closed_loop",
        "usable_below": 0.0015,
        "production": True,
    },
    {
        "name": "inverse_diffusion_x0",
        "role": "inverse_closed_loop",
        "checkpoint": SCRIPT_DIR / "diffusion_x0_round1" / "checkpoints" / "inverse_diffusion" / "inverse_diffusion_best.pth",
        "history": SCRIPT_DIR / "diffusion_x0_round1" / "results" / "inverse_diffusion_history.csv",
        "metric": "val_closed_loop",
        "usable_below": 0.0020,
        "production": True,
    },
    {
        "name": "inverse_classifier",
        "role": "inverse_discrete",
        "checkpoint": SCRIPT_DIR / "split_diff_round1" / "checkpoints" / "inverse_classifier" / "inverse_classifier_best.pth",
        "history": SCRIPT_DIR / "split_diff_round1" / "results" / "inverse_classifier_history.csv",
        "metric": "val_total",
        "usable_below": 0.08,
        "production": False,
    },
    {
        "name": "inverse_cont_diffusion_split",
        "role": "inverse_continuous_experimental",
        "checkpoint": SCRIPT_DIR / "split_diff_x0_round3" / "checkpoints" / "inverse_cont_diffusion" / "inverse_cont_diffusion_best.pth",
        "history": SCRIPT_DIR / "split_diff_x0_round3" / "results" / "inverse_cont_diffusion_history.csv",
        "metric": "val_select",
        "usable_below": 0.20,
        "production": False,
    },
]


def checkpoint_status(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing"
    try:
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as exc:
        return False, f"load_failed: {type(exc).__name__}: {exc}"
    if not isinstance(ckpt, dict) or "model_state" not in ckpt:
        return False, "missing model_state"
    state = ckpt["model_state"]
    if not isinstance(state, dict) or not state:
        return False, "empty model_state"
    return True, "ok"


def best_history(path: Path, metric: str) -> dict[str, float | int | str]:
    if not path.exists():
        return {"history_status": "missing"}
    df = pd.read_csv(path)
    if metric not in df.columns:
        return {"history_status": f"missing metric {metric}"}
    row = df.loc[df[metric].idxmin()]
    out: dict[str, float | int | str] = {
        "history_status": "ok",
        "best_epoch": int(row["epoch"]),
        "best_metric": float(row[metric]),
    }
    for col in [
        "val_total",
        "val_bending",
        "val_axial",
        "val_select",
        "val_x0",
        "val_class",
        "val_param",
        "val_kl",
        "val_closed_loop",
        "val_pattern_acc",
        "val_m_acc",
        "val_n_acc",
    ]:
        if col in row:
            out[col] = float(row[col])
    if "train_total" in row and "val_total" in row:
        out["generalization_gap"] = float(row["val_total"] - row["train_total"])
    return out


def main() -> None:
    rows = []
    for item in MODEL_CANDIDATES:
        checkpoint_ok, checkpoint_status_text = checkpoint_status(item["checkpoint"])
        hist = best_history(item["history"], item["metric"])
        best_metric = hist.get("best_metric")
        metric_ok = isinstance(best_metric, (float, np.floating)) and float(best_metric) <= item["usable_below"]
        status = "usable" if checkpoint_ok and metric_ok else "needs_attention"
        if not item["production"] and status == "usable":
            status = "experimental_usable"
        rows.append(
            {
                "name": item["name"],
                "role": item["role"],
                "production_candidate": item["production"],
                "status": status,
                "checkpoint_status": checkpoint_status_text,
                "selected_metric": item["metric"],
                "usable_below": item["usable_below"],
                "checkpoint": str(item["checkpoint"]),
                "history": str(item["history"]),
                **hist,
            }
        )
    out = pd.DataFrame(rows)
    out_dir = SCRIPT_DIR / "model_audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_dir / "trained_model_audit.csv", index=False)
    try:
        out.to_excel(out_dir / "trained_model_audit.xlsx", index=False)
    except Exception as exc:  # pragma: no cover - optional Excel engine.
        print(f"[WARN] Could not write xlsx: {exc}")
    print(out[["name", "role", "status", "selected_metric", "best_metric", "best_epoch"]].to_string(index=False))
    print(f"[Saved] {out_dir / 'trained_model_audit.csv'}")


if __name__ == "__main__":
    main()
