"""Train inverse Diffusion on Origami Sheet data: 6 stiffness values -> 8 parameters."""

import os
import sys
import copy
import argparse
import time
from pathlib import Path
from contextlib import nullcontext
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = EXPERIMENT_ROOT.parent
SCRIPT_DIR = EXPERIMENT_ROOT
sys.path.insert(0, str(REPO_ROOT))
from origami_experiments.models.origami_inverse_diffusion import OrigamiConditionalDenoisingMLP

INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]
OUTPUT_COLS = ["bendstiff30", "bendstiff60", "bendstiff90", "axialstiff30", "axialstiff60", "axialstiff90"]
NUM_INPUTS = len(INPUT_COLS)
NUM_OUTPUTS = len(OUTPUT_COLS)


def setup_device():
    if hasattr(torch, "set_float32_matmul_precision"):
        torch.set_float32_matmul_precision("high")
    if torch.cuda.is_available():
        device = torch.device("cuda")
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        print(f"[Device] Running on CUDA: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device("cpu")
        print("[Device] Running on CPU")
    return device


DEVICE = setup_device()


def load_data(npz_path):
    print(f"Loading data from: {npz_path}")
    data = np.load(npz_path)
    X_raw = data["X_raw"]
    y_raw = data["y_raw"]

    curve_raw = y_raw  # stiffness (6)
    param_raw = X_raw  # design params (8)

    curve_train, curve_val, param_train, param_val = train_test_split(
        curve_raw, param_raw, test_size=0.2, random_state=42
    )

    scaler_curve = StandardScaler()
    curve_train = scaler_curve.fit_transform(curve_train)
    curve_val = scaler_curve.transform(curve_val)

    scaler_param = StandardScaler()
    param_train = scaler_param.fit_transform(param_train)
    param_val = scaler_param.transform(param_val)

    print(f"  Train: {curve_train.shape[0]}, Val: {curve_val.shape[0]}")
    return curve_train, curve_val, param_train, param_val, scaler_curve, scaler_param


def build_diffusion_schedule(num_steps, beta_start, beta_end, device):
    betas = torch.linspace(beta_start, beta_end, num_steps, dtype=torch.float32, device=device)
    alphas = 1.0 - betas
    alpha_cumprod = torch.cumprod(alphas, dim=0)
    return {
        "betas": betas, "alphas": alphas, "alpha_cumprod": alpha_cumprod,
        "sqrt_alpha_cumprod": torch.sqrt(alpha_cumprod),
        "sqrt_one_minus_alpha_cumprod": torch.sqrt(1.0 - alpha_cumprod),
    }


def extract_timesteps(values, timesteps, target_shape):
    out = values.gather(0, timesteps)
    return out.view(timesteps.shape[0], *([1] * (len(target_shape) - 1)))


def q_sample(x_start, timesteps, noise, schedule):
    sqrt_ac = extract_timesteps(schedule["sqrt_alpha_cumprod"], timesteps, x_start.shape)
    sqrt_1m_ac = extract_timesteps(schedule["sqrt_one_minus_alpha_cumprod"], timesteps, x_start.shape)
    return sqrt_ac * x_start + sqrt_1m_ac * noise


def predict_x0(x_t, timesteps, predicted_noise, schedule):
    sqrt_ac = extract_timesteps(schedule["sqrt_alpha_cumprod"], timesteps, x_t.shape)
    sqrt_1m_ac = extract_timesteps(schedule["sqrt_one_minus_alpha_cumprod"], timesteps, x_t.shape)
    return (x_t - sqrt_1m_ac * predicted_noise) / sqrt_ac.clamp(min=1e-6)


def get_autocast_context(enabled, amp_dtype):
    if not enabled:
        return nullcontext()
    return torch.autocast(device_type="cuda", dtype=amp_dtype)


@torch.no_grad()
def update_ema(ema_model, model, decay):
    ema_params = dict(ema_model.named_parameters())
    model_params = dict(model.named_parameters())
    for name, ema_param in ema_params.items():
        ema_param.mul_(decay).add_(model_params[name].detach(), alpha=1.0 - decay)
    ema_buffers = dict(ema_model.named_buffers())
    model_buffers = dict(model.named_buffers())
    for name, ema_buffer in ema_buffers.items():
        ema_buffer.copy_(model_buffers[name])


def run_epoch(model, curve_tensor, param_tensor, batch_size, timesteps, schedule,
              amp_enabled, amp_dtype, optimizer=None, grad_scaler=None,
              grad_clip=1.0, x0_loss_weight=0.0):
    is_train = optimizer is not None
    total_obj, total_noise, total_x0 = 0.0, 0.0, 0.0
    n_total = param_tensor.size(0)

    perm = torch.randperm(n_total, device=curve_tensor.device) if is_train else torch.arange(n_total, device=curve_tensor.device)

    for start in range(0, n_total, batch_size):
        idx = perm[start:start + batch_size]
        curve = curve_tensor.index_select(0, idx)
        param = param_tensor.index_select(0, idx)

        t = torch.randint(0, timesteps, (param.size(0),), device=curve_tensor.device, dtype=torch.long)
        noise = torch.randn_like(param)
        noisy_param = q_sample(param, t, noise, schedule)

        autocast_ctx = get_autocast_context(amp_enabled, amp_dtype)
        with autocast_ctx:
            model_output = model(noisy_param, t.float(), curve)
            noise_loss = F.mse_loss(model_output, noise)
            pred_x0 = predict_x0(noisy_param, t, model_output.float(), schedule)
            x0_loss = F.mse_loss(pred_x0, param)
            obj_loss = noise_loss + x0_loss_weight * x0_loss

        if is_train:
            optimizer.zero_grad(set_to_none=True)
            if grad_scaler is not None:
                grad_scaler.scale(obj_loss).backward()
                grad_scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)
                grad_scaler.step(optimizer)
                grad_scaler.update()
            else:
                obj_loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)
                optimizer.step()

        bs = param.size(0)
        total_obj += obj_loss.detach().float().item() * bs
        total_noise += noise_loss.detach().float().item() * bs
        total_x0 += x0_loss.detach().float().item() * bs

    return total_obj / n_total, total_noise / n_total, total_x0 / n_total


def plot_training_curves(history, pipeline_idx, save_dir):
    epochs = range(1, len(history["loss"]) + 1)
    plt.figure(figsize=(14, 6))
    plt.subplot(1, 2, 1)
    plt.plot(epochs, history["loss"], "b-", label="Train Noise MSE")
    plt.plot(epochs, history["val_loss"], "r-", label="Val Noise MSE")
    plt.title(f"Diffusion Pipeline {pipeline_idx} - Noise MSE")
    plt.xlabel("Epochs"); plt.ylabel("MSE"); plt.legend(); plt.grid(True, alpha=0.5)
    plt.subplot(1, 2, 2)
    plt.plot(epochs, history["x0_mse"], "b-", label="Train x0 MSE")
    plt.plot(epochs, history["val_x0_mse"], "r-", label="Val x0 MSE")
    plt.title(f"Diffusion Pipeline {pipeline_idx} - x0 Reconstruction")
    plt.xlabel("Epochs"); plt.ylabel("MSE"); plt.legend(); plt.grid(True, alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, f"diffusion_curve_{pipeline_idx}.png"))
    plt.close()


def train_pipeline(args):
    curve_train, curve_val, param_train, param_val, scaler_curve, scaler_param = load_data(args.data_path)

    train_curve = torch.tensor(curve_train, dtype=torch.float32, device=DEVICE)
    train_param = torch.tensor(param_train, dtype=torch.float32, device=DEVICE)
    val_curve = torch.tensor(curve_val, dtype=torch.float32, device=DEVICE)
    val_param = torch.tensor(param_val, dtype=torch.float32, device=DEVICE)

    schedule = build_diffusion_schedule(args.timesteps, args.beta_start, args.beta_end, DEVICE)

    save_dir = os.path.join(SCRIPT_DIR, "checkpoints", "inverse_diffusion")
    os.makedirs(save_dir, exist_ok=True)
    print(f"Checkpoints saved to: {save_dir}")

    amp_enabled = DEVICE.type == "cuda" and args.amp
    amp_dtype = torch.bfloat16 if amp_enabled and args.amp_dtype == "bfloat16" else torch.float16
    use_grad_scaler = amp_enabled and amp_dtype == torch.float16

    for i in range(args.pipelines):
        print(f"\n{'='*20} Training Diffusion Pipeline {i+1}/{args.pipelines} {'='*20}")

        model = OrigamiConditionalDenoisingMLP(
            param_dim=NUM_INPUTS, curve_dim=NUM_OUTPUTS,
            time_emb_dim=args.time_emb_dim, cond_emb_dim=args.cond_emb_dim, hidden_dim=args.hidden_dim,
        ).to(DEVICE)

        ema_model = copy.deepcopy(model)
        ema_model.eval()
        for p in ema_model.parameters():
            p.requires_grad_(False)

        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=args.min_lr)

        if hasattr(torch, "amp") and hasattr(torch.amp, "GradScaler"):
            grad_scaler = torch.amp.GradScaler("cuda", enabled=use_grad_scaler)
        else:
            grad_scaler = torch.cuda.amp.GradScaler(enabled=use_grad_scaler)

        history = {"loss": [], "val_loss": [], "x0_mse": [], "val_x0_mse": []}
        best_val_x0_mse = float("inf")
        best_epoch = -1
        best_model_state = None
        epochs_no_improve = 0

        for epoch in range(args.epochs):
            model.train()
            warmup_ratio = min(1.0, float(epoch + 1) / float(args.x0_loss_warmup)) if args.x0_loss_warmup > 0 else 1.0
            x0_w = args.x0_loss_weight * warmup_ratio

            train_obj, train_noise, train_x0 = run_epoch(
                model, train_curve, train_param, args.batch_size, args.timesteps,
                schedule, amp_enabled, amp_dtype, optimizer, grad_scaler, args.grad_clip, x0_w,
            )
            update_ema(ema_model, model, args.ema_decay)
            scheduler.step()

            do_val = ((epoch + 1) % args.val_every == 0) or epoch == 0 or (epoch + 1 == args.epochs)
            val_noise, val_x0 = float("nan"), float("nan")
            if do_val:
                model.eval()
                with torch.no_grad():
                    _, val_noise, val_x0 = run_epoch(
                        model, val_curve, val_param, args.val_batch_size, args.timesteps,
                        schedule, amp_enabled, amp_dtype, x0_loss_weight=x0_w,
                    )

                if val_x0 < best_val_x0_mse:
                    best_val_x0_mse = val_x0
                    best_epoch = epoch + 1
                    best_model_state = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += args.val_every

            history["loss"].append(train_noise)
            history["val_loss"].append(val_noise)
            history["x0_mse"].append(train_x0)
            history["val_x0_mse"].append(val_x0)

            if (epoch + 1) % 20 == 0 or epoch == 0:
                lr = optimizer.param_groups[0]["lr"]
                print(f"Epoch {epoch+1}/{args.epochs} | Noise MSE: {train_noise:.5f} | Val Noise: {val_noise:.5f} | x0 MSE: {train_x0:.5f} | Val x0: {val_x0:.5f} | Best x0: {best_val_x0_mse:.5f} | LR: {lr:.2e}")

            if args.early_stop_patience > 0 and epochs_no_improve >= args.early_stop_patience:
                print(f"Early stopped at epoch {epoch+1}")
                break

        model_path = os.path.join(save_dir, f"inverse_diffusion_{i}.pth")
        if best_model_state is not None:
            torch.save({
                "model_state": best_model_state,
                "scaler_curve": scaler_curve, "scaler_param": scaler_param,
                "best_epoch": best_epoch, "best_val_x0_mse": best_val_x0_mse,
                "diffusion_config": {"timesteps": args.timesteps, "beta_start": args.beta_start, "beta_end": args.beta_end},
                "model_config": {"param_dim": NUM_INPUTS, "curve_dim": NUM_OUTPUTS, "time_emb_dim": args.time_emb_dim, "cond_emb_dim": args.cond_emb_dim, "hidden_dim": args.hidden_dim},
            }, model_path)
            print(f"Best model saved: {model_path} (Val x0 MSE: {best_val_x0_mse:.5f}, Epoch: {best_epoch})")

        pd.DataFrame(history).to_excel(os.path.join(save_dir, f"log_diffusion_{i}.xlsx"), index=False)
        plot_training_curves(history, i, save_dir)

    print(f"\nAll {args.pipelines} diffusion pipelines completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", type=str, default=str(SCRIPT_DIR / "data" / "origami_train.npz"))
    parser.add_argument("--epochs", type=int, default=1200)
    parser.add_argument("--batch_size", type=int, default=4096)
    parser.add_argument("--val_batch_size", type=int, default=8192)
    parser.add_argument("--pipelines", type=int, default=1)
    parser.add_argument("--val_every", type=int, default=10)
    parser.add_argument("--early_stop_patience", type=int, default=300)
    parser.add_argument("--timesteps", type=int, default=300)
    parser.add_argument("--beta_start", type=float, default=1e-4)
    parser.add_argument("--beta_end", type=float, default=0.02)
    parser.add_argument("--time_emb_dim", type=int, default=64)
    parser.add_argument("--cond_emb_dim", type=int, default=128)
    parser.add_argument("--hidden_dim", type=int, default=512)
    parser.add_argument("--amp", action="store_true")
    parser.add_argument("--amp_dtype", type=str, default="bfloat16")
    parser.add_argument("--ema_decay", type=float, default=0.99)
    parser.add_argument("--x0_loss_weight", type=float, default=0.3)
    parser.add_argument("--x0_loss_warmup", type=int, default=300)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--min_lr", type=float, default=1e-6)
    parser.add_argument("--weight_decay", type=float, default=1e-5)
    parser.add_argument("--grad_clip", type=float, default=1.0)
    args = parser.parse_args()

    torch.manual_seed(42)
    np.random.seed(42)
    train_pipeline(args)
