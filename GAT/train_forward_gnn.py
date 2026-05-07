import os
import argparse
import logging
import copy
from pathlib import Path
import pandas as pd
import numpy as np
import networkx as nx
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from torch_geometric.nn import DenseGATConv
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt


# 1. 纭欢涓庣幆澧冮厤缃?
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
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_TRAIN_DATA_PATH = str(REPO_ROOT / "dataset used for training" / "train.xlsx")



# 2. 鏁版嵁澶勭悊 (淇濇寔鍏ㄨ繛鎺ュ浘)
def load_raw_data(excel_path):
    print("------------------------------------------------------------------------")
    print(f"Loading raw data from Excel: {excel_path}")

    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Cannot find the training file at: {excel_path}")

    columns = [
        "V1a", "V1v", "V1c", "w",
        "relativeVolume", "relativeArea", "thickness", "poreDiameter", "areaMean",
        "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10",
        "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20"
    ]
    input_cols = columns[:9]

    try:
        df1 = pd.read_excel(excel_path, sheet_name='class1', names=columns)
        df2 = pd.read_excel(excel_path, sheet_name='class2', names=columns)
        df12 = pd.read_excel(excel_path, sheet_name='class12', names=columns)
    except Exception as e:
        raise RuntimeError(f"Error reading Excel sheets: {e}")

    df_all = pd.concat([df1, df2, df12], axis=0).reset_index(drop=True)
    data_x = df_all[input_cols].values.astype(np.float32)
    data_y = df_all.iloc[:, 9:].values.astype(np.float32)

    print(f"Raw Data shape: X {data_x.shape}, Y {data_y.shape}")

    print(f"Generating Graph Structure (Fully Connected)...")
    adj_matrix = np.ones((len(input_cols), len(input_cols)), dtype=np.float32)
    adj_tensor = torch.tensor(adj_matrix, dtype=torch.float32).to(DEVICE)

    return data_x, data_y, adj_tensor, input_cols



# 3. 缁樺浘妯″潡
def plot_training_curves(history, pipeline_idx, save_dir):
    epochs = range(1, len(history['loss']) + 1)
    plt.figure(figsize=(14, 6))

    plt.subplot(1, 2, 1)
    plt.plot(epochs, history['loss'], 'b-', label='Training Loss')
    plt.plot(epochs, history['val_loss'], 'r-', label='Validation Loss')
    plt.title(f'Pipeline {pipeline_idx} - MSE Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)

    plt.subplot(1, 2, 2)
    plt.plot(epochs, history['mae'], 'b-', label='Training MAE')
    plt.plot(epochs, history['val_mae'], 'r-', label='Validation MAE')
    plt.title(f'Pipeline {pipeline_idx} - MAE')
    plt.xlabel('Epochs')
    plt.ylabel('MAE')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)

    plt.tight_layout()
    fig_path = os.path.normpath(os.path.join(save_dir, f'training_curves_pipeline_{pipeline_idx}.png'))
    plt.savefig(fig_path, dpi=300)
    plt.close()
    print(f"Training curves saved to: {fig_path}")


# 4. 璁粌鏍稿績閫昏緫
def train_pipeline(args):
    from GAT_module import GNNForwardNetwork

    excel_path = args.data_path
    X_raw, y_raw, adj_tensor, input_cols = load_raw_data(excel_path)

    X_train_raw, X_val_raw, y_train_raw, y_val_raw = train_test_split(
        X_raw, y_raw, test_size=0.2, random_state=42
    )

    scaler_x = StandardScaler()
    X_train = scaler_x.fit_transform(X_train_raw)
    X_val = scaler_x.transform(X_val_raw)

    scaler_y = StandardScaler()
    y_train = scaler_y.fit_transform(y_train_raw)
    y_val = scaler_y.transform(y_val_raw)

    train_dataset = TensorDataset(torch.tensor(X_train, dtype=torch.float32),
                                  torch.tensor(y_train, dtype=torch.float32))
    val_dataset = TensorDataset(torch.tensor(X_val, dtype=torch.float32), torch.tensor(y_val, dtype=torch.float32))

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, pin_memory=True)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.normpath(os.path.join(script_dir, "forward_gnn_checkpoints"))

    print(f"Checkpoints will be saved to: {save_dir}")

    for i in range(args.pipelines):
        print(f"\n{'=' * 20} Training Pipeline {i + 1}/{args.pipelines} {'=' * 20}")

        # 鍘嬬缉鍨嬫灦鏋?(Bottleneck Architecture)
        # 浠?512 鍘嬬缉鍒?64锛屽己杩ā鍨嬫彁鍙栨渶鏈川鐨勭壒寰?
        model = GNNForwardNetwork(
            units_layer1=512,
            units_layer2=256,
            units_layer3=128,
            units_layer4=64,
            gnn_hidden_dim=256,
            gnn_heads=8,
            dropout_rate=0.1
        ).to(DEVICE)

        # Weight Decay 1e-4
        base_lr = 0.0005
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=1e-4)

        # 淇濇寔 Plateau 璋冨害鍣?
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=20, min_lr=1e-7
        )

        criterion = nn.MSELoss()
        mae_metric = nn.L1Loss()
        history = {'loss': [], 'val_loss': [], 'mae': [], 'val_mae': []}

        best_val_mae = float('inf')
        best_epoch = -1
        best_model_state = None
        warmup_epochs = 10

        # 銆愭牳蹇冧紭鍖?銆戞案鎭掑簳鍣?
        initial_noise = 0.01
        min_noise = 0.002  # 璁粌缁撴潫鏃朵粛淇濈暀寰皬鍣０

        for epoch in range(args.epochs):
            # Warmup
            if epoch < warmup_epochs:
                warmup_lr = base_lr * (epoch + 1) / warmup_epochs
                for param_group in optimizer.param_groups:
                    param_group['lr'] = warmup_lr

            model.train()
            train_loss_epoch = 0.0
            train_mae_epoch = 0.0

            for batch_x, batch_y in train_loader:
                batch_x, batch_y = batch_x.to(DEVICE), batch_y.to(DEVICE)

                # 鍔ㄦ€佸櫔澹帮細绾挎€ц“鍑忓埌搴曞櫔
                if epoch > 0:
                    decay_rate = max(0, (1 - epoch / (args.epochs * 0.9)))
                    current_noise = (initial_noise - min_noise) * decay_rate + min_noise
                    noise = torch.randn_like(batch_x) * current_noise
                    batch_x = batch_x + noise

                optimizer.zero_grad()
                outputs = model(batch_x, adj_tensor)

                loss = criterion(outputs, batch_y)
                loss.backward()

                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=0.5)
                optimizer.step()

                train_loss_epoch += loss.item() * batch_x.size(0)
                train_mae_epoch += mae_metric(outputs, batch_y).item() * batch_x.size(0)

            train_loss_avg = train_loss_epoch / len(train_dataset)
            train_mae_avg = train_mae_epoch / len(train_dataset)

            model.eval()
            val_loss_epoch = 0.0
            val_mae_epoch = 0.0
            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    batch_x, batch_y = batch_x.to(DEVICE), batch_y.to(DEVICE)
                    outputs = model(batch_x, adj_tensor)
                    val_loss_epoch += criterion(outputs, batch_y).item() * batch_x.size(0)
                    val_mae_epoch += mae_metric(outputs, batch_y).item() * batch_x.size(0)

            val_loss_avg = val_loss_epoch / len(val_dataset)
            val_mae_avg = val_mae_epoch / len(val_dataset)

            if epoch >= warmup_epochs:
                scheduler.step(val_loss_avg)

            # 浠?MAE 涓烘寚鏍囦繚瀛樻渶浣虫ā鍨?
            if val_mae_avg < best_val_mae:
                best_val_mae = val_mae_avg
                best_epoch = epoch + 1
                # Use deep copy so later updates do not overwrite the best checkpoint in memory.
                best_model_state = copy.deepcopy(model.state_dict())

            history['loss'].append(train_loss_avg)
            history['val_loss'].append(val_loss_avg)
            history['mae'].append(train_mae_avg)
            history['val_mae'].append(val_mae_avg)

            if (epoch + 1) % 10 == 0 or epoch == 0:
                current_lr = optimizer.param_groups[0]['lr']
                print(
                    f"Epoch {epoch + 1}/{args.epochs} | Loss(MSE): {train_loss_avg:.6f} | Val MSE: {val_loss_avg:.6f} | Val MAE: {val_mae_avg:.6f} | Best MAE: {best_val_mae:.6f} | LR: {current_lr:.2e}")

        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)

        model_path = os.path.normpath(os.path.join(save_dir, f'forward_gnn_{i}.pth'))
        if best_model_state is not None:
            torch.save({
                'model_state_dict': best_model_state,
                'scaler_x': scaler_x,
                'scaler_y': scaler_y,
                'input_cols': input_cols,
                'best_epoch': best_epoch,
                'best_val_mae': best_val_mae
            }, model_path)
            print(f"Best Model (Val MAE: {best_val_mae:.6f}, Epoch: {best_epoch}) saved to {model_path}")

        df_log = pd.DataFrame(history)
        df_log.to_excel(os.path.normpath(os.path.join(save_dir, f'log_forward_gnn_{i}.xlsx')), index=False)
        plot_training_curves(history, i, save_dir)

    print(f"\nAll {args.pipelines} pipelines training completed successfully.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, default=DEFAULT_TRAIN_DATA_PATH)
    parser.add_argument('--epochs', type=int, default=500)
    parser.add_argument('--batch_size', type=int, default=256)
    parser.add_argument('--pipelines', type=int, default=1)
    args = parser.parse_args()

    torch.manual_seed(42)
    np.random.seed(42)
    train_pipeline(args)



