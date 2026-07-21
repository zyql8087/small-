"""Evaluate all final portable taskfit models on the held-out test set."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, r2_score

EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = EXPERIMENT_ROOT.parent
SCRIPT_DIR = EXPERIMENT_ROOT
sys.path.insert(0, str(REPO_ROOT))

from origami_experiments.models.origami_taskfit_models import (
    OrigamiForwardGATTaskfit,
    OrigamiForwardResMLP,
    OrigamiForwardTransformerTaskfit,
    OrigamiInverseCVAEHeaded,
    OrigamiInverseDiffusionTaskfit,
    OrigamiInverseDiscreteClassifier,
    OrigamiInverseResMLP,
)
from origami_experiments.workflows.training.train_taskfit import (
    CAT_VALUES,
    INPUT_COLS,
    OUTPUT_COLS,
    TaskfitPreprocessor,
    build_adjacency,
    load_train_val,
    predict_x0,
    target_to_cat_probs,
)
MODEL_DIR = SCRIPT_DIR / "best_models_taskfit"
OUT_DIR = SCRIPT_DIR / "results_final_model_test"
FIG_DIR = OUT_DIR / "figures"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
globals()["TaskfitPreprocessor"] = TaskfitPreprocessor


def load_test_raw(path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(path)
    return data["X_raw"].astype(np.float32), data["y_raw"].astype(np.float32)


def metric_row(target: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    target = np.asarray(target, dtype=np.float64)
    pred = np.asarray(pred, dtype=np.float64)
    mae = float(np.mean(np.abs(target - pred)))
    rmse = float(np.sqrt(np.mean((target - pred) ** 2)))
    r2 = float(r2_score(target.reshape(-1), pred.reshape(-1)))
    value_range = max(float(np.max(target) - np.min(target)), 1e-12)
    return {"MAE": mae, "RMSE": rmse, "R2": r2, "NRMSE%": float(rmse / value_range * 100.0)}


def inverse_curve_transform(prep: TaskfitPreprocessor, curve_scaled: np.ndarray) -> np.ndarray:
    return np.power(10.0, prep.curve_scaler.inverse_transform(curve_scaled)).astype(np.float32)


def inverse_x_transform(prep: TaskfitPreprocessor, cat_ids: np.ndarray, cont_scaled: np.ndarray) -> np.ndarray:
    cont_raw = np.power(10.0, prep.cont_scaler.inverse_transform(cont_scaled)).astype(np.float32)
    x = np.zeros((cat_ids.shape[0], len(INPUT_COLS)), dtype=np.float32)
    x[:, 0] = CAT_VALUES["pattern"][cat_ids[:, 0]]
    x[:, 1] = CAT_VALUES["m"][cat_ids[:, 1]]
    x[:, 2] = CAT_VALUES["n"][cat_ids[:, 2]]
    x[:, 3:8] = cont_raw
    return x


def load_portable(name: str) -> dict:
    return torch.load(MODEL_DIR / f"{name}_portable.pth", map_location=DEVICE, weights_only=False)


def load_legacy(path: Path) -> dict:
    return torch.load(path, map_location=DEVICE, weights_only=False)


def instantiate_forward_resmlp(config: dict) -> OrigamiForwardResMLP:
    return OrigamiForwardResMLP(
        hidden_dim=config.get("forward_hidden", 256),
        dropout=config.get("forward_dropout", 0.1),
    ).to(DEVICE)


def instantiate_forward_gat(config: dict) -> OrigamiForwardGATTaskfit:
    return OrigamiForwardGATTaskfit(
        hidden_dim=config.get("gat_hidden", 256),
        heads=config.get("gat_heads", 8),
        mlp_dim=config.get("gat_mlp_dim", config.get("gat_hidden", 256)),
        dropout=config.get("gat_dropout", config.get("forward_dropout", 0.1)),
    ).to(DEVICE)


def instantiate_forward_transformer(config: dict) -> OrigamiForwardTransformerTaskfit:
    return OrigamiForwardTransformerTaskfit(
        hidden_dim=config.get("transformer_hidden", 192),
        num_heads=config.get("transformer_heads", 4),
        num_layers=config.get("transformer_layers", 3),
        dropout=config.get("transformer_dropout", 0.12),
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


def instantiate_inverse_diffusion(config: dict, diffusion_config: dict) -> OrigamiInverseDiffusionTaskfit:
    return OrigamiInverseDiffusionTaskfit(
        target_dim=diffusion_config.get("target_dim", 8),
        cond_extra_dim=diffusion_config.get("cond_extra_dim", 0),
        time_dim=config.get("diffusion_time_dim", 64),
        cond_dim=config.get("diffusion_cond_dim", 128),
        hidden_dim=config.get("diffusion_hidden", 512),
        dropout=config.get("diffusion_dropout", 0.1),
    ).to(DEVICE)


def instantiate_inverse_classifier(config: dict) -> OrigamiInverseDiscreteClassifier:
    return OrigamiInverseDiscreteClassifier(
        hidden_dim=config.get("inverse_classifier_hidden", 256),
        dropout=config.get("inverse_classifier_dropout", 0.1),
    ).to(DEVICE)


def load_model(name: str, factory):
    ckpt = load_portable(name)
    model = factory(ckpt.get("config", {}), ckpt.get("diffusion_config", {}))
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model, ckpt


@torch.no_grad()
def predict_forward(model, prep: TaskfitPreprocessor, x_raw: np.ndarray, kind: str, graph: str = "physical_sparse") -> np.ndarray:
    cat, cont = prep.transform_x(x_raw)
    cat_t = torch.tensor(cat, dtype=torch.long, device=DEVICE)
    cont_t = torch.tensor(cont, dtype=torch.float32, device=DEVICE)
    if kind == "gat":
        pred_scaled = model(cat_t, cont_t, build_adjacency(graph, DEVICE)).cpu().numpy()
    else:
        pred_scaled = model(cat_t, cont_t).cpu().numpy()
    return inverse_curve_transform(prep, pred_scaled)


def summarize_forward(y_true: np.ndarray, y_pred: np.ndarray, model_name: str) -> list[dict]:
    rows = []
    row = metric_row(y_true, y_pred)
    row.update({"Model": model_name, "Group": "All", "N": len(y_true)})
    rows.append(row)
    for idx, col in enumerate(OUTPUT_COLS):
        row = metric_row(y_true[:, idx], y_pred[:, idx])
        row.update({"Model": model_name, "Group": col, "N": len(y_true)})
        rows.append(row)
    return rows


def summarize_inverse_params(x_true: np.ndarray, x_pred: np.ndarray, model_name: str) -> list[dict]:
    rows = []
    for idx, col in enumerate(INPUT_COLS):
        if col in ("pattern", "m", "n"):
            rows.append(
                {
                    "Model": model_name,
                    "Group": col,
                    "Accuracy": float(accuracy_score(x_true[:, idx], x_pred[:, idx])),
                    "MAE": float(np.mean(np.abs(x_true[:, idx] - x_pred[:, idx]))),
                    "N": len(x_true),
                }
            )
        else:
            row = metric_row(x_true[:, idx], x_pred[:, idx])
            row.update({"Model": model_name, "Group": col, "N": len(x_true)})
            rows.append(row)
    row = metric_row(x_true[:, 3:8], x_pred[:, 3:8])
    row.update({"Model": model_name, "Group": "continuous_params_all", "N": len(x_true)})
    rows.append(row)
    return rows


def inverse_outputs_to_raw(prep: TaskfitPreprocessor, outputs: dict[str, torch.Tensor]) -> np.ndarray:
    cat = torch.stack(
        [
            outputs["pattern"].argmax(dim=1),
            outputs["m"].argmax(dim=1),
            outputs["n"].argmax(dim=1),
        ],
        dim=1,
    ).cpu().numpy()
    cont = outputs["cont"].detach().cpu().numpy()
    return inverse_x_transform(prep, cat, cont)


@torch.no_grad()
def eval_inverse_resmlp(model: OrigamiInverseResMLP, prep: TaskfitPreprocessor, y_raw: np.ndarray) -> np.ndarray:
    curve = torch.tensor(prep.transform_y(y_raw), dtype=torch.float32, device=DEVICE)
    return inverse_outputs_to_raw(prep, model(curve))


@torch.no_grad()
def eval_inverse_cvae(
    model: OrigamiInverseCVAEHeaded,
    prep: TaskfitPreprocessor,
    forward_surrogate: OrigamiForwardTransformerTaskfit,
    y_raw: np.ndarray,
    samples: int = 50,
) -> np.ndarray:
    curve_np = prep.transform_y(y_raw)
    curve = torch.tensor(curve_np, dtype=torch.float32, device=DEVICE)
    best_x = None
    best_loss = None
    for _ in range(samples):
        outputs = model.inference(curve)
        x_pred = inverse_outputs_to_raw(prep, outputs)
        y_loop = predict_forward(forward_surrogate, prep, x_pred, "transformer")
        loop_loss = np.mean((prep.transform_y(y_loop) - curve_np) ** 2, axis=1)
        if best_x is None:
            best_x = x_pred
            best_loss = loop_loss
        else:
            mask = loop_loss < best_loss
            best_x[mask] = x_pred[mask]
            best_loss[mask] = loop_loss[mask]
    return best_x


def make_diffusion_schedule(num_steps: int, beta_start: float, beta_end: float) -> dict[str, torch.Tensor]:
    betas = torch.linspace(beta_start, beta_end, num_steps, dtype=torch.float32, device=DEVICE)
    alphas = 1.0 - betas
    alpha_cumprod = torch.cumprod(alphas, dim=0)
    return {
        "alpha_cumprod": alpha_cumprod,
        "sqrt_alpha_cumprod": torch.sqrt(alpha_cumprod),
        "sqrt_one_minus_alpha_cumprod": torch.sqrt(1.0 - alpha_cumprod),
    }


@torch.no_grad()
def ddim_sample(
    model,
    x_T: torch.Tensor,
    schedule: dict[str, torch.Tensor],
    total_steps: int,
    prediction_type: str,
    inference_steps: int = 50,
    *model_extra_args,
) -> torch.Tensor:
    """DDIM multi-step deterministic sampling (eta=0).

    Iteratively denoises from pure noise ``x_T`` to a clean prediction using
    ``inference_steps`` sub-steps out of the ``total_steps`` training steps.
    This is dramatically more accurate than single-step evaluation.
    """
    alpha_cumprod = schedule["alpha_cumprod"]
    batch_size = x_T.size(0)

    step_ids = np.linspace(total_steps - 1, 0, inference_steps, dtype=np.int64)
    step_ids = sorted(set(step_ids.tolist()), reverse=True)
    if step_ids[-1] != 0:
        step_ids.append(0)

    x_t = x_T
    for i, t_val in enumerate(step_ids):
        t_batch = torch.full((batch_size,), t_val, device=x_T.device, dtype=torch.float32)
        model_output = model(x_t, t_batch, *model_extra_args)

        # Convert model output to x0 prediction
        if prediction_type == "x0":
            x0_pred = model_output
        else:
            x0_pred = predict_x0(x_t, t_batch.long(), model_output, schedule)

        # DDIM update (eta=0, deterministic)
        if i < len(step_ids) - 1:
            next_t = step_ids[i + 1]
            ac_t = alpha_cumprod[t_val].view(1, 1)
            ac_next = alpha_cumprod[next_t].view(1, 1)
            # Recover noise prediction from x0 and x_t
            eps_pred = (x_t - torch.sqrt(ac_t) * x0_pred) / torch.sqrt(1.0 - ac_t).clamp(min=1e-6)
            x_t = torch.sqrt(ac_next) * x0_pred + torch.sqrt(1.0 - ac_next) * eps_pred
        else:
            x_t = x0_pred

    return x_t


@torch.no_grad()
def eval_inverse_diffusion(
    model: OrigamiInverseDiffusionTaskfit,
    ckpt: dict,
    prep: TaskfitPreprocessor,
    forward_surrogate: OrigamiForwardTransformerTaskfit,
    y_raw: np.ndarray,
    samples: int = 50,
    ddim_inference_steps: int = 50,
) -> np.ndarray:
    config = ckpt.get("config", {})
    diffusion_config = ckpt.get("diffusion_config", {})
    steps = diffusion_config.get("steps", config.get("diffusion_steps", 200))
    target_dim = diffusion_config.get("target_dim", 8)
    prediction_type = diffusion_config.get("prediction_type", config.get("diffusion_prediction_type", "epsilon"))
    schedule = make_diffusion_schedule(
        steps,
        diffusion_config.get("beta_start", config.get("diffusion_beta_start", 1e-4)),
        diffusion_config.get("beta_end", config.get("diffusion_beta_end", 0.02)),
    )
    curve_np = prep.transform_y(y_raw)
    curve = torch.tensor(curve_np, dtype=torch.float32, device=DEVICE)
    best_x = None
    best_loss = None
    for _ in range(samples):
        x_T = torch.randn(len(y_raw), target_dim, dtype=torch.float32, device=DEVICE)
        x0_pred = ddim_sample(
            model, x_T, schedule, steps, prediction_type, ddim_inference_steps, curve,
        )
        cat_probs = target_to_cat_probs(x0_pred[:, :3], temperature=config.get("diffusion_category_temperature", 0.12))
        cat = torch.stack([prob.argmax(dim=1) for prob in cat_probs], dim=1).cpu().numpy()
        x_pred = inverse_x_transform(prep, cat, x0_pred[:, 3:].detach().cpu().numpy())
        y_loop = predict_forward(forward_surrogate, prep, x_pred, "transformer")
        loop_loss = np.mean((prep.transform_y(y_loop) - curve_np) ** 2, axis=1)
        if best_x is None:
            best_x = x_pred
            best_loss = loop_loss
        else:
            mask = loop_loss < best_loss
            best_x[mask] = x_pred[mask]
            best_loss[mask] = loop_loss[mask]
    return best_x


@torch.no_grad()
def eval_split_cont_diffusion(
    model: OrigamiInverseDiffusionTaskfit,
    ckpt: dict,
    classifier: OrigamiInverseDiscreteClassifier,
    prep: TaskfitPreprocessor,
    forward_surrogate: OrigamiForwardTransformerTaskfit,
    y_raw: np.ndarray,
    samples: int = 50,
    ddim_inference_steps: int = 50,
) -> np.ndarray:
    config = ckpt.get("config", {})
    diffusion_config = ckpt.get("diffusion_config", {})
    steps = diffusion_config.get("steps", config.get("diffusion_steps", 200))
    target_dim = diffusion_config.get("target_dim", 5)
    prediction_type = diffusion_config.get("prediction_type", config.get("diffusion_prediction_type", "epsilon"))
    schedule = make_diffusion_schedule(
        steps,
        diffusion_config.get("beta_start", config.get("diffusion_beta_start", 1e-4)),
        diffusion_config.get("beta_end", config.get("diffusion_beta_end", 0.02)),
    )
    curve_np = prep.transform_y(y_raw)
    curve = torch.tensor(curve_np, dtype=torch.float32, device=DEVICE)
    cls_out = classifier(curve)
    cls_probs = [
        torch.softmax(cls_out["pattern"], dim=1),
        torch.softmax(cls_out["m"], dim=1),
        torch.softmax(cls_out["n"], dim=1),
    ]
    cls_cond = torch.cat(cls_probs, dim=1)
    cat = torch.stack([prob.argmax(dim=1) for prob in cls_probs], dim=1).cpu().numpy()
    best_x = None
    best_loss = None
    for _ in range(samples):
        x_T = torch.randn(len(y_raw), target_dim, dtype=torch.float32, device=DEVICE)
        cont_pred = ddim_sample(
            model, x_T, schedule, steps, prediction_type, ddim_inference_steps, curve, cls_cond,
        )
        x_pred = inverse_x_transform(prep, cat, cont_pred.detach().cpu().numpy())
        y_loop = predict_forward(forward_surrogate, prep, x_pred, "transformer")
        loop_loss = np.mean((prep.transform_y(y_loop) - curve_np) ** 2, axis=1)
        if best_x is None:
            best_x = x_pred
            best_loss = loop_loss
        else:
            mask = loop_loss < best_loss
            best_x[mask] = x_pred[mask]
            best_loss[mask] = loop_loss[mask]
    return best_x


@torch.no_grad()
def eval_inverse_classifier(model: OrigamiInverseDiscreteClassifier, prep: TaskfitPreprocessor, y_raw: np.ndarray) -> np.ndarray:
    curve = torch.tensor(prep.transform_y(y_raw), dtype=torch.float32, device=DEVICE)
    outputs = model(curve)
    return torch.stack(
        [outputs["pattern"].argmax(dim=1), outputs["m"].argmax(dim=1), outputs["n"].argmax(dim=1)],
        dim=1,
    ).cpu().numpy()


def plot_bar(df: pd.DataFrame, path: Path, title: str, value: str, ylabel: str) -> None:
    plot_df = df.copy()
    plt.figure(figsize=(10, 5))
    colors = plt.cm.Set2(np.linspace(0, 1, len(plot_df)))
    plt.bar(plot_df["Model"], plot_df[value], color=colors)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=20, ha="right")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=240)
    plt.close()


def plot_grouped(df: pd.DataFrame, path: Path, title: str, value: str, ylabel: str) -> None:
    pivot = df.pivot(index="Group", columns="Model", values=value)
    ax = pivot.plot(kind="bar", figsize=(12, 5), width=0.82)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=240)
    plt.close()


def save_table(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path.with_suffix(".csv"), index=False)
    try:
        df.to_excel(path.with_suffix(".xlsx"), index=False)
    except Exception as exc:
        print(f"[WARN] Could not write {path.with_suffix('.xlsx').name}: {exc}")


def main() -> None:
    np.random.seed(42)
    torch.manual_seed(42)
    if DEVICE.type == "cuda":
        torch.cuda.manual_seed_all(42)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    _, _, prep = load_train_val(str(SCRIPT_DIR / "data" / "origami_train.npz"))
    x_test, y_test = load_test_raw(SCRIPT_DIR / "data" / "origami_test.npz")

    forward_resmlp, _ = load_model("forward_resmlp", lambda config, _dc: instantiate_forward_resmlp(config))
    forward_gat, gat_ckpt = load_model("forward_gat_physical_sparse", lambda config, _dc: instantiate_forward_gat(config))
    forward_transformer, _ = load_model("forward_transformer", lambda config, _dc: instantiate_forward_transformer(config))
    inverse_resmlp, _ = load_model("inverse_resmlp", lambda config, _dc: instantiate_inverse_resmlp(config))
    inverse_cvae, _ = load_model("inverse_cvae_physical", lambda config, _dc: instantiate_inverse_cvae(config))
    inverse_diffusion, diffusion_ckpt = load_model("inverse_diffusion_x0", instantiate_inverse_diffusion)
    inverse_classifier, _ = load_model("inverse_classifier", lambda config, _dc: instantiate_inverse_classifier(config))
    split_ckpt_path = SCRIPT_DIR / "split_diff_x0_round3" / "checkpoints" / "inverse_cont_diffusion" / "inverse_cont_diffusion_best.pth"
    split_diffusion = None
    split_ckpt = None
    if split_ckpt_path.exists():
        split_ckpt = load_legacy(split_ckpt_path)
        split_diffusion = instantiate_inverse_diffusion(split_ckpt.get("config", {}), split_ckpt.get("diffusion_config", {}))
        split_diffusion.load_state_dict(split_ckpt["model_state"])
        split_diffusion.eval()

    forward_preds = {
        "Forward ResMLP": predict_forward(forward_resmlp, prep, x_test, "resmlp"),
        "Forward GAT physical_sparse": predict_forward(
            forward_gat,
            prep,
            x_test,
            "gat",
            gat_ckpt.get("config", {}).get("gat_graph", "physical_sparse"),
        ),
        "Forward Transformer": predict_forward(forward_transformer, prep, x_test, "transformer"),
    }
    forward_rows = []
    for name, pred in forward_preds.items():
        forward_rows.extend(summarize_forward(y_test, pred, name))
    forward_df = pd.DataFrame(forward_rows)

    inverse_preds = {
        "Inverse ResMLP": eval_inverse_resmlp(inverse_resmlp, prep, y_test),
        "Inverse CVAE best_of_50": eval_inverse_cvae(inverse_cvae, prep, forward_transformer, y_test, samples=50),
        "Inverse Diffusion x0 best_of_50": eval_inverse_diffusion(
            inverse_diffusion,
            diffusion_ckpt,
            prep,
            forward_transformer,
            y_test,
            samples=50,
        ),
    }
    if split_diffusion is not None and split_ckpt is not None:
        inverse_preds["Inverse Split ContDiff x0 best_of_50"] = eval_split_cont_diffusion(
            split_diffusion,
            split_ckpt,
            inverse_classifier,
            prep,
            forward_transformer,
            y_test,
            samples=50,
        )
    param_rows = []
    loop_rows = []
    for name, x_pred in inverse_preds.items():
        param_rows.extend(summarize_inverse_params(x_test, x_pred, name))
        y_loop = predict_forward(forward_transformer, prep, x_pred, "transformer")
        loop_rows.extend(summarize_forward(y_test, y_loop, f"{name} closed_loop"))
    param_df = pd.DataFrame(param_rows)
    loop_df = pd.DataFrame(loop_rows)

    classifier_cat = eval_inverse_classifier(inverse_classifier, prep, y_test)
    true_cat, _ = prep.transform_x(x_test)
    classifier_df = pd.DataFrame(
        [
            {"Model": "Inverse Classifier", "Group": "pattern", "Accuracy": float(accuracy_score(true_cat[:, 0], classifier_cat[:, 0]))},
            {"Model": "Inverse Classifier", "Group": "m", "Accuracy": float(accuracy_score(true_cat[:, 1], classifier_cat[:, 1]))},
            {"Model": "Inverse Classifier", "Group": "n", "Accuracy": float(accuracy_score(true_cat[:, 2], classifier_cat[:, 2]))},
        ]
    )

    save_table(forward_df, OUT_DIR / "forward_test_metrics")
    save_table(param_df, OUT_DIR / "inverse_parameter_test_metrics")
    save_table(loop_df, OUT_DIR / "inverse_closed_loop_test_metrics")
    save_table(classifier_df, OUT_DIR / "inverse_classifier_test_metrics")

    forward_all = forward_df[forward_df["Group"] == "All"].sort_values("NRMSE%")
    loop_all = loop_df[loop_df["Group"] == "All"].sort_values("NRMSE%")
    cont_all = param_df[param_df["Group"] == "continuous_params_all"].sort_values("NRMSE%")
    discrete = param_df[param_df["Group"].isin(["pattern", "m", "n"])][["Model", "Group", "Accuracy"]]

    plot_bar(forward_all, FIG_DIR / "forward_overall_nrmse.png", "Forward Model Test NRMSE", "NRMSE%", "NRMSE (%)")
    plot_bar(forward_all, FIG_DIR / "forward_overall_mae.png", "Forward Model Test MAE", "MAE", "MAE")
    plot_grouped(
        forward_df[forward_df["Group"].isin(OUTPUT_COLS)],
        FIG_DIR / "forward_per_stiffness_mae.png",
        "Forward Per-Stiffness MAE",
        "MAE",
        "MAE",
    )
    plot_bar(loop_all, FIG_DIR / "inverse_closed_loop_nrmse.png", "Inverse Closed-Loop Test NRMSE", "NRMSE%", "NRMSE (%)")
    plot_bar(cont_all, FIG_DIR / "inverse_continuous_param_nrmse.png", "Inverse Continuous Parameter NRMSE", "NRMSE%", "NRMSE (%)")
    plot_grouped(discrete, FIG_DIR / "inverse_discrete_accuracy.png", "Inverse Discrete Variable Accuracy", "Accuracy", "Accuracy")
    plot_grouped(classifier_df, FIG_DIR / "inverse_classifier_accuracy.png", "Inverse Classifier Accuracy", "Accuracy", "Accuracy")

    summary = {
        "device": str(DEVICE),
        "test_path": str(SCRIPT_DIR / "data" / "origami_test.npz"),
        "n_test": int(len(x_test)),
        "cvae_samples": 50,
        "diffusion_samples": 50,
        "includes_split_cont_diffusion": split_diffusion is not None,
    }
    (OUT_DIR / "test_run_config.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n[Forward overall]")
    print(forward_all[["Model", "MAE", "RMSE", "R2", "NRMSE%"]].to_string(index=False))
    print("\n[Inverse continuous params]")
    print(cont_all[["Model", "MAE", "RMSE", "R2", "NRMSE%"]].to_string(index=False))
    print("\n[Inverse closed-loop overall]")
    print(loop_all[["Model", "MAE", "RMSE", "R2", "NRMSE%"]].to_string(index=False))
    print("\n[Inverse classifier]")
    print(classifier_df.to_string(index=False))
    print(f"\n[DONE] Saved final test metrics and figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
