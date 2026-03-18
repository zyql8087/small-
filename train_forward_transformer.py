import os
import copy
import argparse
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

from GNNtransformer_module import TPMSForwardTransformer


def setup_device():
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


def load_raw_data(excel_path):
    print("------------------------------------------------------------------------")
    print(f"Loading raw data from Excel: {excel_path}")

    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Cannot find training file at: {excel_path}")

    columns = [
        "V1a", "V1v", "V1c", "w",
        "relativeVolume", "relativeArea", "thickness", "poreDiameter", "areaMean",
        "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10",
        "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20",
    ]
    input_cols = columns[:9]

    try:
        df1 = pd.read_excel(excel_path, sheet_name="class1", names=columns)
        df2 = pd.read_excel(excel_path, sheet_name="class2", names=columns)
        df12 = pd.read_excel(excel_path, sheet_name="class12", names=columns)
    except Exception as e:
        raise RuntimeError(f"Error reading Excel sheets: {e}")

    df_all = pd.concat([df1, df2, df12], axis=0).reset_index(drop=True)
    data_x = df_all[input_cols].values.astype(np.float32)
    data_y = df_all.iloc[:, 9:].values.astype(np.float32)

    print(f"Raw Data shape: X {data_x.shape}, Y {data_y.shape}")
    return data_x, data_y, input_cols


def plot_training_curves(history, pipeline_idx, save_dir):
    epochs = range(1, len(history["loss"]) + 1)
    plt.figure(figsize=(14, 6))

    plt.subplot(1, 2, 1)
    plt.plot(epochs, history["loss"], "b-", label="Training MSE")
    plt.plot(epochs, history["val_loss"], "r-", label="Validation MSE")
    plt.title(f"Transformer Pipeline {pipeline_idx} - MSE")
    plt.xlabel("Epochs")
    plt.ylabel("MSE")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.7)

    plt.subplot(1, 2, 2)
    plt.plot(epochs, history["mae"], "b-", label="Training MAE")
    plt.plot(epochs, history["val_mae"], "r-", label="Validation MAE")
    plt.title(f"Transformer Pipeline {pipeline_idx} - MAE")
    plt.xlabel("Epochs")
    plt.ylabel("MAE")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.7)

    plt.tight_layout()
    fig_path = os.path.normpath(
        os.path.join(save_dir, f"training_curves_transformer_pipeline_{pipeline_idx}.png")
    )
    plt.savefig(fig_path, dpi=300)
    plt.close()
    print(f"Training curves saved to: {fig_path}")


def weighted_mse_loss(pred, target, dim_weights, stress_threshold, high_stress_weight):
    # Penalize tail stress dimensions and high-stress samples to reduce catastrophic large-error cases.
    mse = (pred - target) ** 2
    weighted = mse * dim_weights.unsqueeze(0)
    sample_w = torch.where(
        target[:, -1] > stress_threshold,
        torch.full_like(target[:, -1], high_stress_weight),
        torch.ones_like(target[:, -1]),
    )
    weighted = weighted * sample_w.unsqueeze(1)
    return weighted.mean()


def train_pipeline(args):
    X_raw, y_raw, input_cols = load_raw_data(args.data_path)

    X_train_raw, X_val_raw, y_train_raw, y_val_raw = train_test_split(
        X_raw, y_raw, test_size=0.2, random_state=42
    )

    scaler_x = StandardScaler()
    X_train = scaler_x.fit_transform(X_train_raw)
    X_val = scaler_x.transform(X_val_raw)

    scaler_y = StandardScaler()
    y_train = scaler_y.fit_transform(y_train_raw)
    y_val = scaler_y.transform(y_val_raw)

    train_dataset = TensorDataset(
        torch.tensor(X_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32),
    )
    val_dataset = TensorDataset(
        torch.tensor(X_val, dtype=torch.float32),
        torch.tensor(y_val, dtype=torch.float32),
    )

    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size, shuffle=True, pin_memory=True
    )
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size, shuffle=False, pin_memory=True
    )

    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.normpath(os.path.join(script_dir, "forward_transformer_checkpoints"))
    os.makedirs(save_dir, exist_ok=True)
    print(f"Checkpoints will be saved to: {save_dir}")

    # Emphasize late stress points (s16~s20) to address observed tail failures.
    dim_weights = torch.ones(20, device=DEVICE)
    dim_weights[15:] = args.tail_dim_weight

    y_train_tensor = torch.tensor(y_train, dtype=torch.float32, device=DEVICE)
    stress_threshold = torch.quantile(y_train_tensor[:, -1], args.high_stress_quantile)

    for i in range(args.pipelines):
        print(f"\n{'=' * 20} Training Transformer Pipeline {i + 1}/{args.pipelines} {'=' * 20}")

        model = TPMSForwardTransformer(
            num_parameters=9,
            hidden_dim=args.hidden_dim,
            num_heads=args.num_heads,
            num_layers=args.num_layers,
            out_dim=20,
            dropout=args.dropout,
        ).to(DEVICE)

        optimizer = torch.optim.AdamW(
            model.parameters(), lr=args.lr, weight_decay=args.weight_decay
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=args.lr_patience, min_lr=1e-7
        )

        mse_metric = nn.MSELoss()
        mae_metric = nn.L1Loss()
        history = {"loss": [], "val_loss": [], "mae": [], "val_mae": []}

        best_val_mse = float("inf")
        best_model_state = None
        best_epoch = -1

        warmup_epochs = args.warmup_epochs
        early_stop_count = 0

        for epoch in range(args.epochs):
            if epoch < warmup_epochs:
                warmup_lr = args.lr * (epoch + 1) / warmup_epochs
                for g in optimizer.param_groups:
                    g["lr"] = warmup_lr

            model.train()
            train_loss_epoch = 0.0
            train_mae_epoch = 0.0

            for batch_x, batch_y in train_loader:
                batch_x, batch_y = batch_x.to(DEVICE), batch_y.to(DEVICE)

                if epoch > 0 and args.noise_start > 0:
                    decay_rate = max(0.0, 1 - epoch / (args.epochs * 0.9))
                    current_noise = (args.noise_start - args.noise_min) * decay_rate + args.noise_min
                    if current_noise > 0:
                        batch_x = batch_x + torch.randn_like(batch_x) * current_noise

                optimizer.zero_grad()
                outputs = model(batch_x)

                loss = weighted_mse_loss(
                    outputs,
                    batch_y,
                    dim_weights=dim_weights,
                    stress_threshold=stress_threshold,
                    high_stress_weight=args.high_stress_weight,
                )
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip)
                optimizer.step()

                train_loss_epoch += mse_metric(outputs, batch_y).item() * batch_x.size(0)
                train_mae_epoch += mae_metric(outputs, batch_y).item() * batch_x.size(0)

            train_loss_avg = train_loss_epoch / len(train_dataset)
            train_mae_avg = train_mae_epoch / len(train_dataset)

            model.eval()
            val_loss_epoch = 0.0
            val_mae_epoch = 0.0
            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    batch_x, batch_y = batch_x.to(DEVICE), batch_y.to(DEVICE)
                    outputs = model(batch_x)
                    val_loss_epoch += mse_metric(outputs, batch_y).item() * batch_x.size(0)
                    val_mae_epoch += mae_metric(outputs, batch_y).item() * batch_x.size(0)

            val_loss_avg = val_loss_epoch / len(val_dataset)
            val_mae_avg = val_mae_epoch / len(val_dataset)

            if epoch >= warmup_epochs:
                scheduler.step(val_loss_avg)

            if val_loss_avg < best_val_mse:
                best_val_mse = val_loss_avg
                best_epoch = epoch + 1
                best_model_state = copy.deepcopy(model.state_dict())
                early_stop_count = 0
            else:
                early_stop_count += 1

            history["loss"].append(train_loss_avg)
            history["val_loss"].append(val_loss_avg)
            history["mae"].append(train_mae_avg)
            history["val_mae"].append(val_mae_avg)

            if (epoch + 1) % 10 == 0 or epoch == 0:
                current_lr = optimizer.param_groups[0]["lr"]
                print(
                    f"Epoch {epoch + 1}/{args.epochs} | "
                    f"Train MSE: {train_loss_avg:.6f} | Val MSE: {val_loss_avg:.6f} | "
                    f"Train MAE: {train_mae_avg:.6f} | Val MAE: {val_mae_avg:.6f} | "
                    f"Best Val MSE: {best_val_mse:.6f} (epoch {best_epoch}) | LR: {current_lr:.2e}"
                )

            if args.early_stop_patience > 0 and early_stop_count >= args.early_stop_patience:
                print(f"Early stopped at epoch {epoch + 1} (no Val MSE improvement).")
                break

        model_path = os.path.normpath(
            os.path.join(save_dir, f"forward_transformer_{i}.pth")
        )
        if best_model_state is not None:
            torch.save(
                {
                    "model_state_dict": best_model_state,
                    "scaler_x": scaler_x,
                    "scaler_y": scaler_y,
                    "input_cols": input_cols,
                    "best_epoch": best_epoch,
                    "best_val_mse": best_val_mse,
                    "config": vars(args),
                },
                model_path,
            )
            print(
                f"Best model saved: {model_path} "
                f"(Val MSE: {best_val_mse:.6f}, Epoch: {best_epoch})"
            )

        df_log = pd.DataFrame(history)
        log_path = os.path.normpath(
            os.path.join(save_dir, f"log_forward_transformer_{i}.xlsx")
        )
        df_log.to_excel(log_path, index=False)
        plot_training_curves(history, i, save_dir)

    print(f"\nAll {args.pipelines} transformer pipelines completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_path",
        type=str,
        default=DEFAULT_TRAIN_DATA_PATH,
    )
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--pipelines", type=int, default=6)

    # Transformer capacity (increased vs previous run)
    parser.add_argument("--hidden_dim", type=int, default=256)
    parser.add_argument("--num_heads", type=int, default=8)
    parser.add_argument("--num_layers", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.10)

    # Optimization
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--weight_decay", type=float, default=1e-4)
    parser.add_argument("--warmup_epochs", type=int, default=10)
    parser.add_argument("--lr_patience", type=int, default=20)
    parser.add_argument("--grad_clip", type=float, default=0.8)
    parser.add_argument("--early_stop_patience", type=int, default=80)

    # Noise reduced for Transformer stability
    parser.add_argument("--noise_start", type=float, default=0.004)
    parser.add_argument("--noise_min", type=float, default=0.0)

    # Tail control (s16~s20 and high-stress samples)
    parser.add_argument("--tail_dim_weight", type=float, default=1.8)
    parser.add_argument("--high_stress_weight", type=float, default=1.5)
    parser.add_argument("--high_stress_quantile", type=float, default=0.90)

    args = parser.parse_args()

    torch.manual_seed(42)
    np.random.seed(42)
    train_pipeline(args)
