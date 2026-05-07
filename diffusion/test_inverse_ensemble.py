import argparse
import math
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
CVAE_DIR = REPO_ROOT / "CVAE"
GAT_DIR = REPO_ROOT / "GAT"
GNNTRANSFORM_DIR = REPO_ROOT / "GNNTransform"
if str(CVAE_DIR) not in sys.path:
    sys.path.insert(0, str(CVAE_DIR))
if str(GAT_DIR) not in sys.path:
    sys.path.insert(0, str(GAT_DIR))
if str(GNNTRANSFORM_DIR) not in sys.path:
    sys.path.insert(0, str(GNNTRANSFORM_DIR))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from CVAE_module import CVAE
from GAT_module import GNNForwardNetwork
from GNNtransformer_module import TPMSForwardTransformer
from diffusion_module import ConditionalDenoisingMLP


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[Inverse Test] Running on device: {DEVICE}")

DEFAULT_TEST_DATA_PATH = str(REPO_ROOT / "dataset used for training" / "test.xlsx")
DEFAULT_CVAE_CHECKPOINT = str(REPO_ROOT / "CVAE" / "cvae_checkpoints" / "cvae_0.pth")
DEFAULT_DIFFUSION_CHECKPOINT = str(
    SCRIPT_DIR / "inverse_diffusion_checkpoints" / "single_pipeline_20260319" / "inverse_diffusion_0.pth"
)
DEFAULT_GAT_CHECKPOINT = str(REPO_ROOT / "GAT" / "forward_gnn_checkpoints" / "forward_gnn_0.pth")
DEFAULT_TRANSFORMER_CHECKPOINT = ""
DEFAULT_TRANSFORMER_CHECKPOINT_DIR = str(REPO_ROOT / "GNNTransform" / "forward_transformer_checkpoints")
DEFAULT_TRANSFORMER_ENSEMBLE_INDICES = "0,1,2,3,4"
DEFAULT_SAVE_DIR = str(SCRIPT_DIR / "inverse_test_results")


def load_tpms_test_data(excel_path):
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Test file not found: {excel_path}")

    columns = [
        "V1a", "V1v", "V1c", "w",
        "relativeVolume", "relativeArea", "thickness", "poreDiameter", "areaMean",
        "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10",
        "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20",
    ]

    frames = []
    for sheet_name in ("class1", "class2", "class12"):
        try:
            frames.append(pd.read_excel(excel_path, sheet_name=sheet_name, names=columns))
        except ValueError:
            continue

    if not frames:
        frames.append(pd.read_excel(excel_path, names=columns))

    df_all = pd.concat(frames, axis=0).reset_index(drop=True)
    params_raw = df_all.iloc[:, :9].values.astype(np.float32)
    curves_raw = df_all.iloc[:, 9:].values.astype(np.float32)
    print(f"[Data] Loaded {len(df_all)} test samples. params={params_raw.shape}, curves={curves_raw.shape}")
    return params_raw, curves_raw


def compute_metrics(target, pred):
    mse = float(np.mean((target - pred) ** 2))
    mae = float(np.mean(np.abs(target - pred)))
    value_range = max(float(np.max(target) - np.min(target)), 1e-12)
    nrmse_pct = float(np.sqrt(mse) / value_range * 100.0)
    return mse, mae, nrmse_pct


def parse_index_list(raw_indices):
    if raw_indices is None:
        return []
    tokens = [token.strip() for token in str(raw_indices).split(",")]
    result = []
    for token in tokens:
        if not token:
            continue
        result.append(int(token))
    return result


def resolve_transformer_checkpoints(args):
    if args.forward_transformer_checkpoint:
        if not os.path.exists(args.forward_transformer_checkpoint):
            raise FileNotFoundError(
                f"Transformer checkpoint not found: {args.forward_transformer_checkpoint}"
            )
        return [args.forward_transformer_checkpoint]

    if args.forward_transformer_ensemble_size > 0:
        target_indices = list(range(args.forward_transformer_ensemble_size))
    else:
        target_indices = parse_index_list(args.forward_transformer_ensemble_indices)
        if not target_indices:
            target_indices = [0]

    checkpoint_paths = []
    for idx in target_indices:
        path = os.path.join(
            args.forward_transformer_checkpoint_dir,
            f"forward_transformer_{idx}.pth",
        )
        if os.path.exists(path):
            checkpoint_paths.append(path)
        else:
            print(f"[Warn] Transformer checkpoint missing, skipped: {path}")

    if not checkpoint_paths:
        raise FileNotFoundError("No valid transformer checkpoints found for ensemble.")
    return checkpoint_paths


def infer_cvae_config(state_dict):
    hidden_dim = int(state_dict["encoder_fc.0.weight"].shape[0])
    latent_dim = int(state_dict["encoder_fc.6.weight"].shape[0] // 2)
    param_dim = int(state_dict["decoder_fc.6.weight"].shape[0])
    return param_dim, latent_dim, hidden_dim


def load_cvae_bundle(checkpoint_path):
    ckpt = torch.load(checkpoint_path, map_location=DEVICE, weights_only=False)
    state_dict = ckpt["model_state"]
    param_dim, latent_dim, hidden_dim = infer_cvae_config(state_dict)

    model = CVAE(param_dim=param_dim, curve_points=20, latent_dim=latent_dim, hidden_dim=hidden_dim).to(DEVICE)
    model.load_state_dict(state_dict)
    model.eval()

    return {
        "model": model,
        "latent_dim": latent_dim,
        "scaler_curve": ckpt["scaler_curve"],
        "scaler_param": ckpt["scaler_param"],
    }


def load_diffusion_bundle(checkpoint_path):
    ckpt = torch.load(checkpoint_path, map_location=DEVICE, weights_only=False)
    model = ConditionalDenoisingMLP(**ckpt["model_config"]).to(DEVICE)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    train_cfg = ckpt.get("train_config", {})
    return {
        "model": model,
        "scaler_curve": ckpt["scaler_curve"],
        "scaler_param": ckpt["scaler_param"],
        "diffusion_config": ckpt["diffusion_config"],
        "prediction_target": train_cfg.get("prediction_target", "epsilon"),
    }


def load_forward_gat_bundle(checkpoint_path):
    ckpt = torch.load(checkpoint_path, map_location=DEVICE, weights_only=False)
    model = GNNForwardNetwork(
        units_layer1=512,
        units_layer2=256,
        units_layer3=128,
        units_layer4=64,
        gnn_hidden_dim=256,
        gnn_heads=8,
        dropout_rate=0.0,
    ).to(DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    return {
        "model": model,
        "scaler_x": ckpt["scaler_x"],
        "scaler_y": ckpt["scaler_y"],
    }


def load_forward_transformer_bundle(checkpoint_path):
    ckpt = torch.load(checkpoint_path, map_location=DEVICE, weights_only=False)
    cfg = ckpt.get("config", {})

    model = TPMSForwardTransformer(
        num_parameters=9,
        hidden_dim=cfg.get("hidden_dim", 256),
        num_heads=cfg.get("num_heads", 8),
        num_layers=cfg.get("num_layers", 4),
        out_dim=20,
        dropout=cfg.get("dropout", 0.10),
    ).to(DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    return {
        "model": model,
        "scaler_x": ckpt["scaler_x"],
        "scaler_y": ckpt["scaler_y"],
    }


def load_forward_transformer_ensemble(checkpoint_paths):
    bundles = []
    for path in checkpoint_paths:
        bundles.append(load_forward_transformer_bundle(path))
    return bundles


def predict_curves_blended(params_raw, gat_bundle, tr_bundles, batch_size):
    adj = torch.ones((9, 9), dtype=torch.float32, device=DEVICE)
    pred_curves = []

    for start in range(0, len(params_raw), batch_size):
        batch_raw = params_raw[start:start + batch_size]

        x_gat = gat_bundle["scaler_x"].transform(batch_raw).astype(np.float32)
        x_gat_t = torch.tensor(x_gat, dtype=torch.float32, device=DEVICE)
        with torch.no_grad():
            batch_adj = adj.unsqueeze(0).repeat(x_gat_t.size(0), 1, 1)
            y_gat_scaled = gat_bundle["model"](x_gat_t, batch_adj).detach().cpu().numpy()
        y_gat = gat_bundle["scaler_y"].inverse_transform(y_gat_scaled)

        y_tr_models = []
        for tr_bundle in tr_bundles:
            x_tr = tr_bundle["scaler_x"].transform(batch_raw).astype(np.float32)
            x_tr_t = torch.tensor(x_tr, dtype=torch.float32, device=DEVICE)
            with torch.no_grad():
                y_tr_scaled = tr_bundle["model"](x_tr_t).detach().cpu().numpy()
            y_tr = tr_bundle["scaler_y"].inverse_transform(y_tr_scaled)
            y_tr_models.append(y_tr)
        y_tr = np.mean(np.stack(y_tr_models, axis=0), axis=0)

        pred_curves.append(0.5 * (y_gat + y_tr))

    return np.concatenate(pred_curves, axis=0)


def sample_cvae_candidates(cvae_bundle, curves_raw, batch_size, candidates_per_sample):
    model = cvae_bundle["model"]
    scaler_curve = cvae_bundle["scaler_curve"]
    scaler_param = cvae_bundle["scaler_param"]
    latent_dim = cvae_bundle["latent_dim"]

    all_candidates = []
    for start in range(0, len(curves_raw), batch_size):
        curve_batch_raw = curves_raw[start:start + batch_size]
        curve_batch_scaled = scaler_curve.transform(curve_batch_raw).astype(np.float32)
        curve_tensor = torch.tensor(curve_batch_scaled, dtype=torch.float32, device=DEVICE)
        repeated_curve = curve_tensor.repeat_interleave(candidates_per_sample, dim=0)

        with torch.no_grad():
            z = torch.randn(repeated_curve.size(0), latent_dim, device=DEVICE, dtype=torch.float32)
            params_scaled = model.inference(repeated_curve, z=z).detach().cpu().numpy()

        params_raw = scaler_param.inverse_transform(params_scaled)
        batch_candidates = params_raw.reshape(curve_tensor.size(0), candidates_per_sample, -1)
        all_candidates.append(batch_candidates)

    return np.concatenate(all_candidates, axis=0)


def build_diffusion_schedule(num_steps, beta_start, beta_end, device):
    betas = torch.linspace(beta_start, beta_end, num_steps, dtype=torch.float32, device=device)
    alphas = 1.0 - betas
    alpha_cumprod = torch.cumprod(alphas, dim=0)
    return {
        "alpha_cumprod": alpha_cumprod,
        "sqrt_alpha_cumprod": torch.sqrt(alpha_cumprod),
        "sqrt_one_minus_alpha_cumprod": torch.sqrt(1.0 - alpha_cumprod),
    }


def extract_timesteps(values, timesteps, target_shape):
    out = values.gather(0, timesteps)
    return out.view(timesteps.shape[0], *([1] * (len(target_shape) - 1)))


def predict_x0_from_output(x_t, timesteps, model_output, schedule, prediction_target):
    sqrt_alpha_cumprod_t = extract_timesteps(schedule["sqrt_alpha_cumprod"], timesteps, x_t.shape)
    sqrt_one_minus_alpha_cumprod_t = extract_timesteps(
        schedule["sqrt_one_minus_alpha_cumprod"], timesteps, x_t.shape
    )
    if prediction_target == "epsilon":
        return (x_t - sqrt_one_minus_alpha_cumprod_t * model_output) / sqrt_alpha_cumprod_t.clamp(min=1e-6)
    return sqrt_alpha_cumprod_t * x_t - sqrt_one_minus_alpha_cumprod_t * model_output


def predict_epsilon_from_output(x_t, timesteps, model_output, schedule, prediction_target):
    if prediction_target == "epsilon":
        return model_output
    sqrt_alpha_cumprod_t = extract_timesteps(schedule["sqrt_alpha_cumprod"], timesteps, x_t.shape)
    sqrt_one_minus_alpha_cumprod_t = extract_timesteps(
        schedule["sqrt_one_minus_alpha_cumprod"], timesteps, x_t.shape
    )
    return sqrt_alpha_cumprod_t * model_output + sqrt_one_minus_alpha_cumprod_t * x_t


def make_sampling_timesteps(total_timesteps, inference_steps):
    if inference_steps >= total_timesteps:
        return list(range(total_timesteps - 1, -1, -1))
    step_ids = np.linspace(0, total_timesteps - 1, inference_steps, dtype=np.int64)
    step_ids = sorted(set(step_ids.tolist()), reverse=True)
    if step_ids[-1] != 0:
        step_ids.append(0)
    return step_ids


def ddim_step(x_t, pred_x0, eps, alpha_t, alpha_next, eta):
    sigma = eta * torch.sqrt((1.0 - alpha_next) / (1.0 - alpha_t)).clamp(min=0.0)
    sigma = sigma * torch.sqrt((1.0 - alpha_t / alpha_next).clamp(min=0.0))
    direction = torch.sqrt((1.0 - alpha_next - sigma ** 2).clamp(min=0.0)) * eps
    if float(sigma.detach().cpu()) > 0:
        return torch.sqrt(alpha_next) * pred_x0 + direction + sigma * torch.randn_like(x_t)
    return torch.sqrt(alpha_next) * pred_x0 + direction


def sample_diffusion_candidates(diff_bundle, curves_raw, batch_size, candidates_per_sample, inference_steps, eta):
    model = diff_bundle["model"]
    scaler_curve = diff_bundle["scaler_curve"]
    scaler_param = diff_bundle["scaler_param"]
    diff_cfg = diff_bundle["diffusion_config"]
    prediction_target = diff_bundle["prediction_target"]

    schedule = build_diffusion_schedule(
        num_steps=diff_cfg["timesteps"],
        beta_start=diff_cfg["beta_start"],
        beta_end=diff_cfg["beta_end"],
        device=DEVICE,
    )
    sampling_timesteps = make_sampling_timesteps(diff_cfg["timesteps"], inference_steps)

    all_candidates = []
    for start in range(0, len(curves_raw), batch_size):
        curve_batch_raw = curves_raw[start:start + batch_size]
        curve_batch_scaled = scaler_curve.transform(curve_batch_raw).astype(np.float32)
        curve_tensor = torch.tensor(curve_batch_scaled, dtype=torch.float32, device=DEVICE)
        repeated_curve = curve_tensor.repeat_interleave(candidates_per_sample, dim=0)

        x_t = torch.randn(repeated_curve.size(0), 9, device=DEVICE, dtype=torch.float32)

        with torch.no_grad():
            for step_idx, timestep in enumerate(sampling_timesteps):
                t_batch = torch.full((x_t.size(0),), timestep, device=DEVICE, dtype=torch.long)
                model_output = model(x_t, t_batch.float(), repeated_curve)
                pred_x0 = predict_x0_from_output(x_t, t_batch, model_output.float(), schedule, prediction_target)

                if step_idx == len(sampling_timesteps) - 1:
                    x_t = pred_x0
                else:
                    next_timestep = sampling_timesteps[step_idx + 1]
                    alpha_t = schedule["alpha_cumprod"][timestep]
                    alpha_next = schedule["alpha_cumprod"][next_timestep]
                    eps = predict_epsilon_from_output(
                        x_t, t_batch, model_output.float(), schedule, prediction_target
                    )
                    x_t = ddim_step(x_t, pred_x0, eps, alpha_t, alpha_next, eta=eta)

        params_raw = scaler_param.inverse_transform(x_t.detach().cpu().numpy())
        batch_candidates = params_raw.reshape(curve_tensor.size(0), candidates_per_sample, -1)
        all_candidates.append(batch_candidates)

    return np.concatenate(all_candidates, axis=0)


def rank_candidates_with_forward(candidates_raw, target_curves_raw, gat_bundle, tr_bundles, batch_size, top_k):
    num_samples, num_candidates, param_dim = candidates_raw.shape
    flat_params = candidates_raw.reshape(num_samples * num_candidates, param_dim)
    flat_curves = predict_curves_blended(flat_params, gat_bundle, tr_bundles, batch_size)
    pred_curves = flat_curves.reshape(num_samples, num_candidates, -1)

    ranking_error = np.mean((pred_curves - target_curves_raw[:, None, :]) ** 2, axis=2)
    order = np.argsort(ranking_error, axis=1)
    top_k = max(1, min(top_k, num_candidates))
    topk_idx = order[:, :top_k]

    topk_params = np.take_along_axis(candidates_raw, topk_idx[:, :, None], axis=1)
    topk_curves = np.take_along_axis(pred_curves, topk_idx[:, :, None], axis=1)
    topk_scores = np.take_along_axis(ranking_error, topk_idx, axis=1)

    return {
        "topk_idx": topk_idx,
        "topk_params": topk_params,
        "topk_curves": topk_curves,
        "topk_scores": topk_scores,
    }


def evaluate_topk_selection(model_name, topk_params, topk_curves, true_params, target_curves):
    top1_params = topk_params[:, 0, :]
    top1_curves = topk_curves[:, 0, :]

    param_mse, param_mae, _ = compute_metrics(true_params, top1_params)
    curve_mse, curve_mae, curve_nrmse = compute_metrics(target_curves, top1_curves)

    # Oracle over top-k w.r.t. true parameter MAE (for reference)
    param_abs = np.mean(np.abs(topk_params - true_params[:, None, :]), axis=2)
    best_param_idx = np.argmin(param_abs, axis=1)
    oracle_params = topk_params[np.arange(len(topk_params)), best_param_idx]
    oracle_param_mse, oracle_param_mae, _ = compute_metrics(true_params, oracle_params)

    # Diversity among top-k parameter candidates
    diversity = float(np.mean(np.std(topk_params, axis=1)))

    return {
        "model": model_name,
        "param_mse": param_mse,
        "param_mae": param_mae,
        "curve_mse": curve_mse,
        "curve_mae": curve_mae,
        "curve_nrmse_pct": curve_nrmse,
        "oracle_topk_param_mse": oracle_param_mse,
        "oracle_topk_param_mae": oracle_param_mae,
        "topk_param_diversity": diversity,
    }


def save_topk_artifacts(save_dir, model_prefix, rank_result):
    np.savez_compressed(
        os.path.join(save_dir, f"{model_prefix}_topk_candidates.npz"),
        topk_idx=rank_result["topk_idx"],
        topk_params=rank_result["topk_params"],
        topk_scores=rank_result["topk_scores"],
    )


def plot_inverse_comparison(target_curves, cvae_topk_curves, diffusion_topk_curves, save_path, random_seed, num_plots):
    rng = np.random.default_rng(random_seed)
    num_plots = min(num_plots, len(target_curves))
    indices = rng.choice(len(target_curves), size=num_plots, replace=False)

    cols = 3
    rows = int(math.ceil(num_plots / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 3.8 * rows))
    axes = np.array(axes).reshape(-1)
    x_axis = np.arange(1, target_curves.shape[1] + 1)

    top_k = cvae_topk_curves.shape[1]

    for ax_idx, sample_idx in enumerate(indices):
        ax = axes[ax_idx]
        target = target_curves[sample_idx]
        cvae_curves = cvae_topk_curves[sample_idx]
        diff_curves = diffusion_topk_curves[sample_idx]

        ax.plot(x_axis, target, "k-", linewidth=2.0, label="Target")

        for k in range(top_k):
            if k == 0:
                ax.plot(x_axis, cvae_curves[k], "b-.", linewidth=1.9, label="CVAE Top-1")
                ax.plot(x_axis, diff_curves[k], "r--", linewidth=1.9, label="Diffusion Top-1")
            else:
                ax.plot(x_axis, cvae_curves[k], "b:", linewidth=1.1, alpha=0.35)
                ax.plot(x_axis, diff_curves[k], "r:", linewidth=1.1, alpha=0.35)

        mse_cvae = float(np.mean((target - cvae_curves[0]) ** 2))
        mse_diff = float(np.mean((target - diff_curves[0]) ** 2))
        ax.set_title(f"Sample {sample_idx} | Top1 MSE C={mse_cvae:.3f}, D={mse_diff:.3f}")
        ax.set_xlabel("Point")
        ax.set_ylabel("Stress")
        ax.grid(True, linestyle=":", alpha=0.6)

    for i in range(num_plots, len(axes)):
        axes[i].axis("off")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(save_path, dpi=300)
    plt.close(fig)


def main(args):
    torch.manual_seed(args.random_seed)
    np.random.seed(args.random_seed)
    os.makedirs(args.save_dir, exist_ok=True)

    true_params_raw, target_curves_raw = load_tpms_test_data(args.test_data_path)

    cvae_bundle = load_cvae_bundle(args.cvae_checkpoint)
    diff_bundle = load_diffusion_bundle(args.diffusion_checkpoint)
    gat_bundle = load_forward_gat_bundle(args.forward_gat_checkpoint)
    transformer_ckpts = resolve_transformer_checkpoints(args)
    tr_bundles = load_forward_transformer_ensemble(transformer_ckpts)

    print(
        f"[Config] CVAE candidates={args.cvae_candidates_per_sample}, "
        f"Diffusion candidates={args.diffusion_candidates_per_sample}, top_k={args.top_k}, "
        f"Transformer ensemble={len(tr_bundles)}"
    )

    cvae_candidates = sample_cvae_candidates(
        cvae_bundle,
        target_curves_raw,
        batch_size=args.batch_size,
        candidates_per_sample=args.cvae_candidates_per_sample,
    )

    diff_candidates = sample_diffusion_candidates(
        diff_bundle,
        target_curves_raw,
        batch_size=args.batch_size,
        candidates_per_sample=args.diffusion_candidates_per_sample,
        inference_steps=args.diffusion_steps,
        eta=args.diffusion_eta,
    )

    cvae_rank = rank_candidates_with_forward(
        cvae_candidates,
        target_curves_raw,
        gat_bundle,
        tr_bundles,
        batch_size=args.batch_size,
        top_k=args.top_k,
    )
    diff_rank = rank_candidates_with_forward(
        diff_candidates,
        target_curves_raw,
        gat_bundle,
        tr_bundles,
        batch_size=args.batch_size,
        top_k=args.top_k,
    )

    cvae_summary = evaluate_topk_selection(
        "cvae",
        cvae_rank["topk_params"],
        cvae_rank["topk_curves"],
        true_params_raw,
        target_curves_raw,
    )
    diff_summary = evaluate_topk_selection(
        "diffusion",
        diff_rank["topk_params"],
        diff_rank["topk_curves"],
        true_params_raw,
        target_curves_raw,
    )

    summary_df = pd.DataFrame([cvae_summary, diff_summary])
    summary_df.insert(1, "top_k", max(1, args.top_k))

    summary_csv = os.path.join(args.save_dir, "inverse_test_metrics.csv")
    summary_df.to_csv(summary_csv, index=False)

    save_topk_artifacts(args.save_dir, "cvae", cvae_rank)
    save_topk_artifacts(args.save_dir, "diffusion", diff_rank)

    figure_path = os.path.join(args.save_dir, "inverse_test_comparison.png")
    plot_inverse_comparison(
        target_curves=target_curves_raw,
        cvae_topk_curves=cvae_rank["topk_curves"],
        diffusion_topk_curves=diff_rank["topk_curves"],
        save_path=figure_path,
        random_seed=args.random_seed,
        num_plots=args.num_plots,
    )

    print("\n==================== Inverse Test Summary ====================")
    print(summary_df.to_string(index=False))
    print(f"[Saved] Metrics: {summary_csv}")
    print(f"[Saved] Figure:  {figure_path}")
    print(f"[Saved] Top-k NPZ: {os.path.join(args.save_dir, 'cvae_topk_candidates.npz')}")
    print(f"[Saved] Top-k NPZ: {os.path.join(args.save_dir, 'diffusion_topk_candidates.npz')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_data_path", type=str, default=DEFAULT_TEST_DATA_PATH)
    parser.add_argument("--cvae_checkpoint", type=str, default=DEFAULT_CVAE_CHECKPOINT)
    parser.add_argument("--diffusion_checkpoint", type=str, default=DEFAULT_DIFFUSION_CHECKPOINT)
    parser.add_argument("--forward_gat_checkpoint", type=str, default=DEFAULT_GAT_CHECKPOINT)
    parser.add_argument("--forward_transformer_checkpoint", type=str, default=DEFAULT_TRANSFORMER_CHECKPOINT)
    parser.add_argument("--forward_transformer_checkpoint_dir", type=str, default=DEFAULT_TRANSFORMER_CHECKPOINT_DIR)
    parser.add_argument("--forward_transformer_ensemble_indices", type=str, default=DEFAULT_TRANSFORMER_ENSEMBLE_INDICES)
    parser.add_argument("--forward_transformer_ensemble_size", type=int, default=0)
    parser.add_argument("--save_dir", type=str, default=DEFAULT_SAVE_DIR)
    parser.add_argument("--batch_size", type=int, default=512)
    parser.add_argument("--cvae_candidates_per_sample", type=int, default=30)
    parser.add_argument("--diffusion_candidates_per_sample", type=int, default=6)
    parser.add_argument("--top_k", type=int, default=3)
    parser.add_argument("--diffusion_steps", type=int, default=30)
    parser.add_argument("--diffusion_eta", type=float, default=0.0)
    parser.add_argument("--num_plots", type=int, default=6)
    parser.add_argument("--random_seed", type=int, default=42)
    cli_args = parser.parse_args()
    main(cli_args)



