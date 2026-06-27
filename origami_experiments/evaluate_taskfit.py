"""Evaluate taskfit Origami models on the held-out test set."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, r2_score

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from modules.origami_taskfit_models import (  # noqa: E402
    OrigamiForwardGATTaskfit,
    OrigamiForwardResMLP,
    OrigamiInverseCVAEHeaded,
    OrigamiInverseResMLP,
)
from train_taskfit import (  # noqa: E402
    CAT_VALUES,
    CONT_COLS,
    INPUT_COLS,
    OUTPUT_COLS,
    TaskfitPreprocessor,
    build_adjacency,
    load_train_val,
)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def metric_row(target: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    target = np.asarray(target, dtype=np.float64)
    pred = np.asarray(pred, dtype=np.float64)
    mae = float(np.mean(np.abs(target - pred)))
    rmse = float(np.sqrt(np.mean((target - pred) ** 2)))
    r2 = float(r2_score(target.reshape(-1), pred.reshape(-1)))
    value_range = max(float(np.max(target) - np.min(target)), 1e-12)
    return {"MAE": mae, "RMSE": rmse, "R2": r2, "NRMSE%": float(rmse / value_range * 100.0)}


def load_test_raw(path: str) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(path)
    return data["X_raw"].astype(np.float32), data["y_raw"].astype(np.float32)


def inverse_curve_transform(prep: TaskfitPreprocessor, curve_scaled: np.ndarray) -> np.ndarray:
    log_curve = prep.curve_scaler.inverse_transform(curve_scaled)
    return np.power(10.0, log_curve).astype(np.float32)


def inverse_x_transform(prep: TaskfitPreprocessor, cat_ids: np.ndarray, cont_scaled: np.ndarray) -> np.ndarray:
    cont_log = prep.cont_scaler.inverse_transform(cont_scaled)
    cont_raw = np.power(10.0, cont_log).astype(np.float32)
    x = np.zeros((cat_ids.shape[0], 8), dtype=np.float32)
    x[:, 0] = CAT_VALUES["pattern"][cat_ids[:, 0]]
    x[:, 1] = CAT_VALUES["m"][cat_ids[:, 1]]
    x[:, 2] = CAT_VALUES["n"][cat_ids[:, 2]]
    x[:, 3:8] = cont_raw
    return x


def instantiate_forward_gat(config: dict) -> OrigamiForwardGATTaskfit:
    return OrigamiForwardGATTaskfit(
        hidden_dim=config.get("gat_hidden", 256),
        heads=config.get("gat_heads", 8),
        mlp_dim=config.get("gat_mlp_dim", config.get("gat_hidden", 256)),
        dropout=config.get("gat_dropout", config.get("forward_dropout", 0.1)),
    ).to(DEVICE)


def instantiate_forward_resmlp(config: dict) -> OrigamiForwardResMLP:
    return OrigamiForwardResMLP(
        hidden_dim=config.get("forward_hidden", 256),
        dropout=config.get("forward_dropout", 0.1),
    ).to(DEVICE)


def instantiate_inverse_resmlp(config: dict) -> OrigamiInverseResMLP:
    return OrigamiInverseResMLP(
        hidden_dim=config.get("inverse_hidden", 256),
        dropout=config.get("inverse_dropout", 0.2),
    ).to(DEVICE)


def instantiate_inverse_cvae(config: dict) -> OrigamiInverseCVAEHeaded:
    return OrigamiInverseCVAEHeaded(
        latent_dim=config.get("cvae_latent_dim", 8),
        hidden_dim=config.get("cvae_hidden", 512),
    ).to(DEVICE)


def load_checkpoint(path: str) -> dict:
    # Checkpoints were saved by train_taskfit.py when run as __main__; this alias
    # keeps its pickled preprocessor loadable while evaluation rebuilds scalers.
    globals()["TaskfitPreprocessor"] = TaskfitPreprocessor
    return torch.load(path, map_location=DEVICE, weights_only=False)


@torch.no_grad()
def predict_forward_gat(model: OrigamiForwardGATTaskfit, prep: TaskfitPreprocessor, x_raw: np.ndarray, graph: str) -> np.ndarray:
    cat, cont = prep.transform_x(x_raw)
    cat_t = torch.tensor(cat, dtype=torch.long, device=DEVICE)
    cont_t = torch.tensor(cont, dtype=torch.float32, device=DEVICE)
    adj = build_adjacency(graph, DEVICE)
    model.eval()
    pred_scaled = model(cat_t, cont_t, adj).cpu().numpy()
    return inverse_curve_transform(prep, pred_scaled)


@torch.no_grad()
def predict_forward_resmlp(model: OrigamiForwardResMLP, prep: TaskfitPreprocessor, x_raw: np.ndarray) -> np.ndarray:
    cat, cont = prep.transform_x(x_raw)
    cat_t = torch.tensor(cat, dtype=torch.long, device=DEVICE)
    cont_t = torch.tensor(cont, dtype=torch.float32, device=DEVICE)
    model.eval()
    pred_scaled = model(cat_t, cont_t).cpu().numpy()
    return inverse_curve_transform(prep, pred_scaled)


def summarize_forward(y_true: np.ndarray, y_pred: np.ndarray, model_name: str) -> list[dict]:
    rows = []
    overall = metric_row(y_true, y_pred)
    overall.update({"Model": model_name, "Group": "All", "N": len(y_true)})
    rows.append(overall)
    for i, col in enumerate(OUTPUT_COLS):
        row = metric_row(y_true[:, i], y_pred[:, i])
        row.update({"Model": model_name, "Group": col, "N": len(y_true)})
        rows.append(row)
    return rows


def summarize_inverse_params(x_true: np.ndarray, x_pred: np.ndarray, model_name: str) -> list[dict]:
    rows = []
    for i, col in enumerate(INPUT_COLS):
        if col in ("pattern", "m", "n"):
            acc = float(accuracy_score(x_true[:, i], x_pred[:, i]))
            rows.append({"Model": model_name, "Group": col, "Accuracy": acc, "MAE": float(np.mean(np.abs(x_true[:, i] - x_pred[:, i]))), "N": len(x_true)})
        else:
            row = metric_row(x_true[:, i], x_pred[:, i])
            row.update({"Model": model_name, "Group": col, "N": len(x_true)})
            rows.append(row)
    all_row = metric_row(x_true[:, 3:8], x_pred[:, 3:8])
    all_row.update({"Model": model_name, "Group": "continuous_params_all", "N": len(x_true)})
    rows.append(all_row)
    return rows


def inverse_outputs_to_raw(prep: TaskfitPreprocessor, outputs: dict[str, torch.Tensor]) -> tuple[np.ndarray, np.ndarray]:
    cat = torch.stack(
        [
            outputs["pattern"].argmax(dim=1),
            outputs["m"].argmax(dim=1),
            outputs["n"].argmax(dim=1),
        ],
        dim=1,
    ).cpu().numpy()
    cont = outputs["cont"].detach().cpu().numpy()
    return inverse_x_transform(prep, cat, cont), cat


@torch.no_grad()
def eval_inverse_resmlp(
    ckpt_path: str,
    forward_model: OrigamiForwardGATTaskfit,
    prep: TaskfitPreprocessor,
    x_raw: np.ndarray,
    y_raw: np.ndarray,
    graph: str,
) -> tuple[list[dict], list[dict]]:
    ckpt = load_checkpoint(ckpt_path)
    config = ckpt.get("config", {})
    model = instantiate_inverse_resmlp(config)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    curve = prep.transform_y(y_raw)
    out = model(torch.tensor(curve, dtype=torch.float32, device=DEVICE))
    x_pred, _ = inverse_outputs_to_raw(prep, out)
    param_rows = summarize_inverse_params(x_raw, x_pred, "Inverse ResMLP")

    y_loop = predict_forward_gat(forward_model, prep, x_pred, graph)
    loop_rows = summarize_forward(y_raw, y_loop, "Inverse ResMLP closed_loop")
    return param_rows, loop_rows


@torch.no_grad()
def eval_inverse_cvae(
    ckpt_path: str,
    forward_model: OrigamiForwardGATTaskfit,
    prep: TaskfitPreprocessor,
    x_raw: np.ndarray,
    y_raw: np.ndarray,
    graph: str,
    samples: int,
) -> tuple[list[dict], list[dict]]:
    ckpt = load_checkpoint(ckpt_path)
    config = ckpt.get("config", {})
    model = instantiate_inverse_cvae(config)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    curve = torch.tensor(prep.transform_y(y_raw), dtype=torch.float32, device=DEVICE)

    pred_xs = []
    loop_losses = []
    for _ in range(samples):
        out = model.inference(curve)
        x_pred, _ = inverse_outputs_to_raw(prep, out)
        y_loop = predict_forward_gat(forward_model, prep, x_pred, graph)
        loop_mse = np.mean((prep.transform_y(y_loop) - prep.transform_y(y_raw)) ** 2, axis=1)
        pred_xs.append(x_pred)
        loop_losses.append(loop_mse)

    pred_stack = np.stack(pred_xs, axis=0)
    loop_stack = np.stack(loop_losses, axis=0)
    best_idx = np.argmin(loop_stack, axis=0)
    x_best = pred_stack[best_idx, np.arange(len(x_raw))]

    param_rows = summarize_inverse_params(x_raw, x_best, f"Inverse CVAE best_of_{samples}")
    y_loop_best = predict_forward_gat(forward_model, prep, x_best, graph)
    loop_rows = summarize_forward(y_raw, y_loop_best, f"Inverse CVAE best_of_{samples} closed_loop")
    return param_rows, loop_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_path", type=str, default=str(SCRIPT_DIR / "data" / "origami_train.npz"))
    parser.add_argument("--test_path", type=str, default=str(SCRIPT_DIR / "data" / "origami_test.npz"))
    parser.add_argument(
        "--forward_gat_ckpt",
        type=str,
        default=str(SCRIPT_DIR / "gat_grid_sparse" / "checkpoints_h192_d0p12_lr0p0002" / "forward_gat" / "forward_gat_best.pth"),
    )
    parser.add_argument(
        "--forward_resmlp_ckpt",
        type=str,
        default=str(SCRIPT_DIR / "checkpoints_taskfit" / "forward_resmlp" / "forward_resmlp_best.pth"),
    )
    parser.add_argument(
        "--inverse_resmlp_ckpt",
        type=str,
        default=str(SCRIPT_DIR / "checkpoints_taskfit_round2" / "inverse_resmlp" / "inverse_resmlp_best.pth"),
    )
    parser.add_argument(
        "--inverse_cvae_ckpt",
        type=str,
        default=str(SCRIPT_DIR / "checkpoints_taskfit_round4_sparse" / "inverse_cvae" / "inverse_cvae_best.pth"),
    )
    parser.add_argument("--save_dir", type=str, default=str(SCRIPT_DIR / "results_taskfit_test"))
    parser.add_argument("--cvae_samples", type=int, default=50)
    args = parser.parse_args()

    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    _, _, prep = load_train_val(args.train_path)
    x_test, y_test = load_test_raw(args.test_path)

    forward_ckpt = load_checkpoint(args.forward_gat_ckpt)
    forward_config = forward_ckpt.get("config", {})
    graph = forward_config.get("gat_graph", "physical_sparse")
    forward_model = instantiate_forward_gat(forward_config)
    forward_model.load_state_dict(forward_ckpt["model_state"])
    forward_model.eval()

    y_forward = predict_forward_gat(forward_model, prep, x_test, graph)
    forward_rows = summarize_forward(y_test, y_forward, "Forward GAT physical_sparse grid_best")

    if Path(args.forward_resmlp_ckpt).exists():
        resmlp_ckpt = load_checkpoint(args.forward_resmlp_ckpt)
        resmlp_model = instantiate_forward_resmlp(resmlp_ckpt.get("config", {}))
        resmlp_model.load_state_dict(resmlp_ckpt["model_state"])
        resmlp_model.eval()
        y_resmlp = predict_forward_resmlp(resmlp_model, prep, x_test)
        forward_rows.extend(summarize_forward(y_test, y_resmlp, "Forward ResMLP round1_best"))

    inverse_param_rows = []
    inverse_loop_rows = []
    rows, loop = eval_inverse_resmlp(args.inverse_resmlp_ckpt, forward_model, prep, x_test, y_test, graph)
    inverse_param_rows.extend(rows)
    inverse_loop_rows.extend(loop)
    rows, loop = eval_inverse_cvae(args.inverse_cvae_ckpt, forward_model, prep, x_test, y_test, graph, args.cvae_samples)
    inverse_param_rows.extend(rows)
    inverse_loop_rows.extend(loop)

    pd.DataFrame(forward_rows).to_csv(save_dir / "forward_metrics.csv", index=False)
    pd.DataFrame(inverse_param_rows).to_csv(save_dir / "inverse_parameter_metrics.csv", index=False)
    pd.DataFrame(inverse_loop_rows).to_csv(save_dir / "inverse_closed_loop_metrics.csv", index=False)
    (save_dir / "test_config.json").write_text(json.dumps(vars(args), indent=2), encoding="utf-8")

    print("\n[Forward]")
    print(pd.DataFrame(forward_rows).to_string(index=False))
    print("\n[Inverse parameter]")
    print(pd.DataFrame(inverse_param_rows).to_string(index=False))
    print("\n[Inverse closed-loop]")
    print(pd.DataFrame(inverse_loop_rows).to_string(index=False))
    print(f"\n[DONE] Saved test metrics to {save_dir}")


if __name__ == "__main__":
    main()
