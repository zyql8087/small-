import os
import argparse
import logging
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

# 瀵煎叆鏂扮殑 ResNet1DInverse
from GNN_module import ResNet1DInverse


# ----------------------------------------------------------------
# 1. 閰嶇疆
# ----------------------------------------------------------------
def setup_device():
    if torch.cuda.is_available():
        device = torch.device('cuda')
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        print(f"[Device] Running on CUDA: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device('cpu')
        print("[Device] Running on CPU")
    return device


DEVICE = setup_device()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TRAIN_DATA_PATH = os.path.join(SCRIPT_DIR, "dataset used for training", "train.xlsx")


# ----------------------------------------------------------------
# 2. 鏁版嵁鍔犺浇
# ----------------------------------------------------------------
def load_inverse_data(excel_path):
    print("------------------------------------------------------------------------")
    print(f"Loading data for INVERSE task: {excel_path}")
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"File not found: {excel_path}")

    columns = [
        "V1a", "V1v", "V1c", "w",
        "relativeVolume", "relativeArea", "thickness", "poreDiameter", "areaMean",
        "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10",
        "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20"
    ]

    try:
        df1 = pd.read_excel(excel_path, sheet_name='class1', names=columns)
        df2 = pd.read_excel(excel_path, sheet_name='class2', names=columns)
        df12 = pd.read_excel(excel_path, sheet_name='class12', names=columns)
    except Exception as e:
        raise RuntimeError(f"Error reading Excel: {e}")

    df_all = pd.concat([df1, df2, df12], axis=0).reset_index(drop=True)

    # 杈撳叆: Curves (20)
    data_x = df_all.iloc[:, 9:].values.astype(np.float32)
    # 杈撳嚭: Params (9)
    data_y = df_all.iloc[:, :9].values.astype(np.float32)

    print(f"Inverse Dataset: Input Curves {data_x.shape} -> Target Params {data_y.shape}")
    return data_x, data_y


# ----------------------------------------------------------------
# 3. 缁樺浘
# ----------------------------------------------------------------
def plot_curves(history, pipeline_idx, save_dir):
    epochs = range(1, len(history['loss']) + 1)
    plt.figure(figsize=(14, 6))

    plt.subplot(1, 2, 1)
    plt.plot(epochs, history['loss'], 'b-', label='Train Loss')
    plt.plot(epochs, history['val_loss'], 'r-', label='Val Loss')
    plt.title(f'Inverse Pipeline {pipeline_idx} - SmoothL1 Loss')
    plt.xlabel('Epochs')
    plt.legend()
    plt.grid(True, alpha=0.5)

    plt.subplot(1, 2, 2)
    plt.plot(epochs, history['mae'], 'b-', label='Train MAE')
    plt.plot(epochs, history['val_mae'], 'r-', label='Val MAE')
    plt.title(f'Inverse Pipeline {pipeline_idx} - MAE')
    plt.xlabel('Epochs')
    plt.legend()
    plt.grid(True, alpha=0.5)

    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, f'inverse_resnet_curve_{pipeline_idx}.png'))
    plt.close()


# ----------------------------------------------------------------
# 4. 璁粌涓绘祦绋?
# ----------------------------------------------------------------
def train_pipeline(args):
    excel_path = args.data_path
    X_raw, y_raw = load_inverse_data(excel_path)

    X_train_raw, X_val_raw, y_train_raw, y_val_raw = train_test_split(
        X_raw, y_raw, test_size=0.2, random_state=42
    )

    scaler_x = StandardScaler()
    X_train = scaler_x.fit_transform(X_train_raw)
    X_val = scaler_x.transform(X_val_raw)

    scaler_y = StandardScaler()
    y_train = scaler_y.fit_transform(y_train_raw)
    y_val = scaler_y.transform(y_val_raw)

    train_ds = TensorDataset(torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train, dtype=torch.float32))
    val_ds = TensorDataset(torch.tensor(X_val, dtype=torch.float32), torch.tensor(y_val, dtype=torch.float32))

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, pin_memory=True)

    save_dir = os.path.join(SCRIPT_DIR, "inverse_resnet_checkpoints")
    os.makedirs(save_dir, exist_ok=True)

    print(f"Checkpoints will be saved to: {save_dir}")

    for i in range(6):
        print(f"\n{'=' * 20} Training Inverse Pipeline {i}/6 {'=' * 20}")

        # 浣跨敤 ResNet1DInverse
        model = ResNet1DInverse(dropout_rate=0.1).to(DEVICE)

        # 绋冲仴浼樺寲鍣?
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.0002, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=20, min_lr=1e-7
        )

        criterion = nn.SmoothL1Loss()  # 鎶楅渿鑽?
        mae_metric = nn.L1Loss()

        history = {'loss': [], 'val_loss': [], 'mae': [], 'val_mae': []}
        best_val_loss = float('inf')

        initial_noise = 0.01
        noise_decay_end = int(args.epochs * 0.6)

        warmup_epochs = 10

        for epoch in range(args.epochs):
            if epoch < warmup_epochs:
                optimizer.param_groups[0]['lr'] = 0.0002 * (epoch + 1) / warmup_epochs

            model.train()
            train_loss = 0.0
            train_mae = 0.0

            for bx, by in train_loader:
                bx, by = bx.to(DEVICE), by.to(DEVICE)

                if epoch < noise_decay_end:
                    curr_noise = initial_noise * (1 - epoch / noise_decay_end)
                    bx = bx + torch.randn_like(bx) * curr_noise

                optimizer.zero_grad()
                out = model(bx)  # 鐩存帴浼犲叆 Tensor锛屼笉闇€瑕?adj
                loss = criterion(out, by)
                loss.backward()

                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=0.1)
                optimizer.step()

                train_loss += loss.item() * bx.size(0)
                train_mae += mae_metric(out, by).item() * bx.size(0)

            train_loss /= len(train_ds)
            train_mae /= len(train_ds)

            model.eval()
            val_loss = 0.0
            val_mae = 0.0
            with torch.no_grad():
                for bx, by in val_loader:
                    bx, by = bx.to(DEVICE), by.to(DEVICE)
                    out = model(bx)
                    val_loss += criterion(out, by).item() * bx.size(0)
                    val_mae += mae_metric(out, by).item() * bx.size(0)

            val_loss /= len(val_ds)
            val_mae /= len(val_ds)

            scheduler.step(val_loss)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save({
                    'model_state': model.state_dict(),
                    'scaler_x': scaler_x,
                    'scaler_y': scaler_y
                }, os.path.join(save_dir, f'inverse_resnet_{i}.pth'))

            history['loss'].append(train_loss)
            history['val_loss'].append(val_loss)
            history['mae'].append(train_mae)
            history['val_mae'].append(val_mae)

            if (epoch + 1) % 10 == 0:
                lr = optimizer.param_groups[0]['lr']
                print(
                    f"Epoch {epoch + 1} | Loss: {train_loss:.5f} | Val Loss: {val_loss:.5f} | Best: {best_val_loss:.5f} | LR: {lr:.2e}")

        pd.DataFrame(history).to_excel(os.path.join(save_dir, f'log_inverse_{i}.xlsx'), index=False)
        plot_curves(history, i, save_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, default=DEFAULT_TRAIN_DATA_PATH)
    parser.add_argument('--epochs', type=int, default=300)
    parser.add_argument('--batch_size', type=int, default=512)
    args = parser.parse_args()

    torch.manual_seed(42)
    train_pipeline(args)
