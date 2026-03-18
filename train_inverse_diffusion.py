import os
import copy
import argparse
import time
from contextlib import nullcontext
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

from diffusion_module import ConditionalDenoisingMLP


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
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TRAIN_DATA_PATH = os.path.join(SCRIPT_DIR, "dataset used for training", "train.xlsx")


def load_inverse_data(excel_path):
    print("------------------------------------------------------------------------")
    print(f"Loading data for INVERSE DIFFUSION task: {excel_path}")
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"File not found: {excel_path}")

    columns = [
        "V1a", "V1v", "V1c", "w",
        "relativeVolume", "relativeArea", "thickness", "poreDiameter", "areaMean",
        "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10",
        "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20",
    ]

    try:
        dfs = [
            pd.read_excel(excel_path, sheet_name=sheet_name, names=columns)
            for sheet_name in ["class1", "class2", "class12"]
        ]
    except Exception as e:
        raise RuntimeError(f"Error reading Excel: {e}")

    df_all = pd.concat(dfs, axis=0).reset_index(drop=True)
    data_curve = df_all.iloc[:, 9:].values.astype(np.float32)
    data_param = df_all.iloc[:, :9].values.astype(np.float32)

    print(f"Inverse Diffusion Dataset: Curves {data_curve.shape} -> Params {data_param.shape}")
    return data_curve, data_param


def build_diffusion_schedule(num_steps, beta_start, beta_end, device):
    betas = torch.linspace(beta_start, beta_end, num_steps, dtype=torch.float32, device=device)
    alphas = 1.0 - betas
    alpha_cumprod = torch.cumprod(alphas, dim=0)

    return {
        "betas": betas,
        "alphas": alphas,
        "alpha_cumprod": alpha_cumprod,
        "sqrt_alpha_cumprod": torch.sqrt(alpha_cumprod),
        "sqrt_one_minus_alpha_cumprod": torch.sqrt(1.0 - alpha_cumprod),
    }


def extract_timesteps(values, timesteps, target_shape):
    out = values.gather(0, timesteps)
    return out.view(timesteps.shape[0], *([1] * (len(target_shape) - 1)))


def q_sample(x_start, timesteps, noise, schedule):
    sqrt_alpha_cumprod_t = extract_timesteps(
        schedule["sqrt_alpha_cumprod"], timesteps, x_start.shape
    )
    sqrt_one_minus_alpha_cumprod_t = extract_timesteps(
        schedule["sqrt_one_minus_alpha_cumprod"], timesteps, x_start.shape
    )
    return sqrt_alpha_cumprod_t * x_start + sqrt_one_minus_alpha_cumprod_t * noise


def predict_x0(x_t, timesteps, predicted_noise, schedule):
    sqrt_alpha_cumprod_t = extract_timesteps(
        schedule["sqrt_alpha_cumprod"], timesteps, x_t.shape
    )
    sqrt_one_minus_alpha_cumprod_t = extract_timesteps(
        schedule["sqrt_one_minus_alpha_cumprod"], timesteps, x_t.shape
    )
    return (x_t - sqrt_one_minus_alpha_cumprod_t * predicted_noise) / sqrt_alpha_cumprod_t.clamp(min=1e-6)


def plot_training_curves(history, pipeline_idx, save_dir):
    epochs = range(1, len(history["loss"]) + 1)
    plt.figure(figsize=(14, 6))

    plt.subplot(1, 2, 1)
    plt.plot(epochs, history["loss"], "b-", label="Train Noise MSE")
    plt.plot(epochs, history["val_loss"], "r-", label="Val Noise MSE")
    plt.title(f"Inverse Diffusion Pipeline {pipeline_idx} - Noise MSE")
    plt.xlabel("Epochs")
    plt.ylabel("MSE")
    plt.legend()
    plt.grid(True, alpha=0.5)

    plt.subplot(1, 2, 2)
    plt.plot(epochs, history["x0_mse"], "b-", label="Train x0 MSE")
    plt.plot(epochs, history["val_x0_mse"], "r-", label="Val x0 MSE")
    plt.title(f"Inverse Diffusion Pipeline {pipeline_idx} - x0 Reconstruction")
    plt.xlabel("Epochs")
    plt.ylabel("MSE")
    plt.legend()
    plt.grid(True, alpha=0.5)

    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, f"inverse_diffusion_curve_{pipeline_idx}.png"))
    plt.close()


def get_autocast_context(enabled, amp_dtype):
    if not enabled:
        return nullcontext()
    return torch.autocast(device_type="cuda", dtype=amp_dtype)


def run_epoch(
    model,
    curve_tensor,
    param_tensor,
    batch_size,
    timesteps,
    schedule,
    amp_enabled,
    amp_dtype,
    optimizer=None,
    grad_scaler=None,
    grad_clip=1.0,
):
    is_train = optimizer is not None
    total_noise_loss = 0.0
    total_x0_mse = 0.0
    total_count = param_tensor.size(0)

    if is_train:
        permutation = torch.randperm(total_count, device=curve_tensor.device)
    else:
        permutation = torch.arange(total_count, device=curve_tensor.device)

    for start in range(0, total_count, batch_size):
        indices = permutation[start:start + batch_size]
        curve = curve_tensor.index_select(0, indices)
        param = param_tensor.index_select(0, indices)

        sampled_t = torch.randint(
            0, timesteps, (param.size(0),), device=curve_tensor.device, dtype=torch.long
        )
        noise = torch.randn_like(param)
        noisy_param = q_sample(param, sampled_t, noise, schedule)

        autocast_context = get_autocast_context(amp_enabled, amp_dtype)
        with autocast_context:
            predicted_noise = model(noisy_param, sampled_t.float(), curve)
            noise_loss = F.mse_loss(predicted_noise, noise)

        if is_train:
            optimizer.zero_grad(set_to_none=True)
            if grad_scaler is not None:
                grad_scaler.scale(noise_loss).backward()
                grad_scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)
                grad_scaler.step(optimizer)
                grad_scaler.update()
            else:
                noise_loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)
                optimizer.step()

        with torch.no_grad():
            pred_x0 = predict_x0(noisy_param, sampled_t, predicted_noise.float(), schedule)
            x0_mse = F.mse_loss(pred_x0, param)

        curr_batch_size = param.size(0)
        total_noise_loss += noise_loss.detach().float().item() * curr_batch_size
        total_x0_mse += x0_mse.detach().float().item() * curr_batch_size

    return total_noise_loss / total_count, total_x0_mse / total_count


def train_pipeline(args):
    X_raw, y_raw = load_inverse_data(args.data_path)
    X_train, X_val, y_train, y_val = train_test_split(
        X_raw, y_raw, test_size=0.2, random_state=42
    )

    scaler_curve = StandardScaler()
    X_train = scaler_curve.fit_transform(X_train)
    X_val = scaler_curve.transform(X_val)

    scaler_param = StandardScaler()
    y_train = scaler_param.fit_transform(y_train)
    y_val = scaler_param.transform(y_val)

    train_curve_tensor = torch.tensor(X_train, dtype=torch.float32, device=DEVICE)
    train_param_tensor = torch.tensor(y_train, dtype=torch.float32, device=DEVICE)
    val_curve_tensor = torch.tensor(X_val, dtype=torch.float32, device=DEVICE)
    val_param_tensor = torch.tensor(y_val, dtype=torch.float32, device=DEVICE)

    schedule = build_diffusion_schedule(
        num_steps=args.timesteps,
        beta_start=args.beta_start,
        beta_end=args.beta_end,
        device=DEVICE,
    )

    save_dir = os.path.join(SCRIPT_DIR, "inverse_diffusion_checkpoints")
    os.makedirs(save_dir, exist_ok=True)
    print(f"Checkpoints will be saved to: {save_dir}")

    curve_dim = X_train.shape[1]
    param_dim = y_train.shape[1]
    amp_enabled = DEVICE.type == "cuda" and args.amp
    amp_dtype = (
        torch.bfloat16
        if amp_enabled and args.amp_dtype == "bfloat16"
        else torch.float16
    )
    use_grad_scaler = amp_enabled and amp_dtype == torch.float16

    if amp_enabled:
        print(f"[AMP] Enabled with dtype={args.amp_dtype}")
    print(
        f"[Training Setup] train_batch_size={args.batch_size}, "
        f"val_batch_size={args.val_batch_size}, val_every={args.val_every}"
    )

    for i in range(args.pipelines):
        print(f"\n{'=' * 20} Training Inverse Diffusion Pipeline {i + 1}/{args.pipelines} {'=' * 20}")

        model = ConditionalDenoisingMLP(
            param_dim=param_dim,
            curve_dim=curve_dim,
            time_emb_dim=args.time_emb_dim,
            cond_emb_dim=args.cond_emb_dim,
            hidden_dim=args.hidden_dim,
        ).to(DEVICE)

        if args.compile and hasattr(torch, "compile"):
            model = torch.compile(model)

        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=args.lr,
            weight_decay=args.weight_decay,
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=args.epochs,
            eta_min=args.min_lr,
        )

        history = {"loss": [], "val_loss": [], "x0_mse": [], "val_x0_mse": []}
        best_val_x0_mse = float("inf")
        best_epoch = -1
        best_model_state = None
        epochs_without_improve = 0
        last_val_noise_loss = float("nan")
        last_val_x0_mse = float("nan")
        if hasattr(torch, "amp") and hasattr(torch.amp, "GradScaler"):
            grad_scaler = torch.amp.GradScaler("cuda", enabled=use_grad_scaler)
        else:
            grad_scaler = torch.cuda.amp.GradScaler(enabled=use_grad_scaler)

        for epoch in range(args.epochs):
            epoch_start = time.perf_counter()
            model.train()
            train_noise_loss, train_x0_mse = run_epoch(
                model=model,
                curve_tensor=train_curve_tensor,
                param_tensor=train_param_tensor,
                batch_size=args.batch_size,
                timesteps=args.timesteps,
                schedule=schedule,
                amp_enabled=amp_enabled,
                amp_dtype=amp_dtype,
                optimizer=optimizer,
                grad_scaler=grad_scaler,
                grad_clip=args.grad_clip,
            )

            should_validate = ((epoch + 1) % args.val_every == 0) or epoch == 0 or (epoch + 1 == args.epochs)
            if should_validate:
                model.eval()
                with torch.no_grad():
                    val_noise_loss, val_x0_mse = run_epoch(
                        model=model,
                        curve_tensor=val_curve_tensor,
                        param_tensor=val_param_tensor,
                        batch_size=args.val_batch_size,
                        timesteps=args.timesteps,
                        schedule=schedule,
                        amp_enabled=amp_enabled,
                        amp_dtype=amp_dtype,
                    )

                scheduler.step()
                last_val_noise_loss = val_noise_loss
                last_val_x0_mse = val_x0_mse

                if val_x0_mse < best_val_x0_mse:
                    best_val_x0_mse = val_x0_mse
                    best_epoch = epoch + 1
                    best_model_state = copy.deepcopy(model.state_dict())
                    epochs_without_improve = 0
                else:
                    epochs_without_improve += args.val_every

            history["loss"].append(train_noise_loss)
            history["val_loss"].append(last_val_noise_loss)
            history["x0_mse"].append(train_x0_mse)
            history["val_x0_mse"].append(last_val_x0_mse)

            epoch_time = time.perf_counter() - epoch_start
            samples_per_second = train_curve_tensor.size(0) / max(epoch_time, 1e-6)

            if (epoch + 1) % 20 == 0 or epoch == 0:
                current_lr = optimizer.param_groups[0]["lr"]
                print(
                    f"Epoch {epoch + 1}/{args.epochs} | "
                    f"Train Noise MSE: {train_noise_loss:.5f} | "
                    f"Val Noise MSE: {last_val_noise_loss:.5f} | "
                    f"Train x0 MSE: {train_x0_mse:.5f} | "
                    f"Val x0 MSE: {last_val_x0_mse:.5f} | "
                    f"Best Val x0 MSE: {best_val_x0_mse:.5f} | "
                    f"LR: {current_lr:.2e} | "
                    f"Time: {epoch_time:.2f}s | "
                    f"Samples/s: {samples_per_second:.0f}"
                )

            if args.early_stop_patience > 0 and epochs_without_improve >= args.early_stop_patience:
                print(
                    f"Early stopped at epoch {epoch + 1} "
                    f"(no validation improvement for {epochs_without_improve} epochs)."
                )
                break

        checkpoint_path = os.path.join(save_dir, f"inverse_diffusion_{i}.pth")
        if best_model_state is not None:
            torch.save(
                {
                    "model_state": best_model_state,
                    "scaler_curve": scaler_curve,
                    "scaler_param": scaler_param,
                    "best_epoch": best_epoch,
                    "best_val_x0_mse": best_val_x0_mse,
                    "diffusion_config": {
                        "timesteps": args.timesteps,
                        "beta_start": args.beta_start,
                        "beta_end": args.beta_end,
                    },
                    "model_config": {
                        "param_dim": param_dim,
                        "curve_dim": curve_dim,
                        "time_emb_dim": args.time_emb_dim,
                        "cond_emb_dim": args.cond_emb_dim,
                        "hidden_dim": args.hidden_dim,
                    },
                    "train_config": vars(args),
                },
                checkpoint_path,
            )
            print(
                f"Best model saved to {checkpoint_path} "
                f"(Val x0 MSE: {best_val_x0_mse:.5f}, Epoch: {best_epoch})"
            )

        pd.DataFrame(history).to_excel(
            os.path.join(save_dir, f"log_inverse_diffusion_{i}.xlsx"),
            index=False,
        )
        plot_training_curves(history, i, save_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", type=str, default=DEFAULT_TRAIN_DATA_PATH)
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--batch_size", type=int, default=2048)
    parser.add_argument("--val_batch_size", type=int, default=4096)
    parser.add_argument("--pipelines", type=int, default=6)
    parser.add_argument("--val_every", type=int, default=5)
    parser.add_argument("--early_stop_patience", type=int, default=60)

    parser.add_argument("--timesteps", type=int, default=300)
    parser.add_argument("--beta_start", type=float, default=1e-4)
    parser.add_argument("--beta_end", type=float, default=0.02)

    parser.add_argument("--time_emb_dim", type=int, default=64)
    parser.add_argument("--cond_emb_dim", type=int, default=128)
    parser.add_argument("--hidden_dim", type=int, default=256)
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--amp", action="store_true")
    parser.add_argument("--amp_dtype", type=str, choices=["float16", "bfloat16"], default="bfloat16")

    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--min_lr", type=float, default=1e-7)
    parser.add_argument("--weight_decay", type=float, default=1e-5)
    parser.add_argument("--grad_clip", type=float, default=1.0)

    args = parser.parse_args()

    torch.manual_seed(42)
    np.random.seed(42)
    train_pipeline(args)
