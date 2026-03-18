import os
import argparse
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score

# 导入模型定义
from GNN_module import GNNForwardNetwork

# ----------------------------------------------------------------
# 1. 配置
# ----------------------------------------------------------------
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"[Test] Running on device: {device}")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEST_DATA_PATH = os.path.join(SCRIPT_DIR, "dataset used for training", "test.xlsx")
DEFAULT_GNN_MODEL_DIR = os.path.join(SCRIPT_DIR, "forward_gnn_checkpoints")


# ----------------------------------------------------------------
# 2. 数据加载
# ----------------------------------------------------------------
def load_test_data(excel_path):
    print(f"Loading Test Data from: {excel_path}")
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Test file not found at: {excel_path}")

    columns = [
        "V1a", "V1v", "V1c", "w",
        "relativeVolume", "relativeArea", "thickness", "poreDiameter", "areaMean",
        "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10",
        "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20"
    ]
    input_cols = columns[:9]

    dfs = []
    try:
        for sheet in ['class1', 'class2', 'class12']:
            try:
                df = pd.read_excel(excel_path, sheet_name=sheet, names=columns)
                dfs.append(df)
            except ValueError:
                continue
        if not dfs:
            df = pd.read_excel(excel_path, names=columns)
            dfs.append(df)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return None, None, None

    df_all = pd.concat(dfs, axis=0).reset_index(drop=True)
    X_raw = df_all[input_cols].values.astype(np.float32)
    y_raw = df_all.iloc[:, 9:].values.astype(np.float32)

    return X_raw, y_raw


# ----------------------------------------------------------------
# 3. 集成推理核心
# ----------------------------------------------------------------
def ensemble_predict(model_dir, X_raw, num_pipelines=6):
    print(f"\nStarting Ensemble Prediction with {num_pipelines} models...")

    # 准备图结构
    adj = torch.ones((9, 9), dtype=torch.float32).to(device)

    # 存储所有模型的预测结果
    all_preds = []

    # 用于反标准化的 Scaler (只需加载一次，假设所有 pipeline 用的是同一套数据分布)
    scaler_y = None

    for i in range(num_pipelines):
        model_path = os.path.join(model_dir, f'forward_gnn_{i}.pth')
        if not os.path.exists(model_path):
            print(f"Warning: Model {i} not found, skipping.")
            continue

        # 加载 Checkpoint
        # weights_only=False 解决 PyTorch 2.6+ 安全报错
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)

        if scaler_y is None:
            scaler_y = checkpoint['scaler_y']
            scaler_x = checkpoint['scaler_x']

        # 数据预处理 (标准化)
        X_scaled = scaler_x.transform(X_raw)
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32).to(device)

        # 初始化模型 (保持与训练一致的配置: Bottleneck 架构)
        model = GNNForwardNetwork(
            units_layer1=512,
            units_layer2=256,
            units_layer3=128,
            units_layer4=64,
            gnn_hidden_dim=256,
            gnn_heads=8,
            dropout_rate=0.0  # 测试模式关闭 Dropout
        ).to(device)

        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()

        # 批量推理
        batch_size = 512
        y_pred_pipe = []
        with torch.no_grad():
            for idx in range(0, len(X_tensor), batch_size):
                batch_x = X_tensor[idx:idx + batch_size]
                batch_adj = adj.unsqueeze(0).repeat(batch_x.size(0), 1, 1)
                out = model(batch_x, batch_adj)
                y_pred_pipe.append(out.cpu().numpy())

        # 反标准化并加入集合
        y_pred_pipe = np.concatenate(y_pred_pipe, axis=0)
        y_pred_raw = scaler_y.inverse_transform(y_pred_pipe)
        all_preds.append(y_pred_raw)

        print(f"  Model {i} loaded and predicted.")

    # 【核心】计算平均值 (Ensemble Averaging)
    if not all_preds:
        return None

    ensemble_prediction = np.mean(np.array(all_preds), axis=0)
    return ensemble_prediction


# ----------------------------------------------------------------
# 4. 主程序
# ----------------------------------------------------------------
def main(args):
    # 1. 加载数据
    X_raw, y_true = load_test_data(args.test_data_path)
    if X_raw is None: return

    # 2. 执行集成推理
    y_pred = ensemble_predict(args.model_dir, X_raw)

    # 3. 计算最终指标
    mse = np.mean((y_true - y_pred) ** 2)
    mae = np.mean(np.abs(y_true - y_pred))
    r2 = r2_score(y_true, y_pred)

    data_range = np.max(y_true) - np.min(y_true)
    rmse = np.sqrt(mse)
    nrmse = (rmse / data_range) * 100

    print(f"\n{'=' * 40}")
    print(f"FINAL ENSEMBLE RESULTS (Average of 6 Models)")
    print(f"{'=' * 40}")
    print(f"  MSE  : {mse:.4f}")
    print(f"  MAE  : {mae:.4f}")
    print(f"  R2   : {r2:.4f}")
    print(f"  NRMSE: {nrmse:.2f}% (Paper Baseline: 2.49%)")
    print(f"{'=' * 40}")

    # 4. 绘图：随机抽取 4 个样本
    indices = np.random.choice(len(y_true), 4, replace=False)
    plt.figure(figsize=(12, 10))

    # 统一坐标轴范围 (基于数据的最大值)
    y_max = np.max(y_true) * 1.1

    for idx, sample_idx in enumerate(indices):
        plt.subplot(2, 2, idx + 1)

        true_curve = np.concatenate(([0], y_true[sample_idx]))
        pred_curve = np.concatenate(([0], y_pred[sample_idx]))
        x_axis = np.linspace(0, 25, 21)

        plt.plot(x_axis, true_curve, 'k-', linewidth=2.5, label='Ground Truth')
        plt.plot(x_axis, pred_curve, 'r--', linewidth=2, marker='o', markersize=4, label='Ensemble Pred')

        # 计算单个样本的误差
        sample_nrmse = (np.sqrt(np.mean((true_curve - pred_curve) ** 2)) / data_range) * 100

        plt.title(f'Sample {sample_idx} (NRMSE: {sample_nrmse:.2f}%)')
        plt.xlabel('Strain (%)')
        plt.ylabel('Stress (kPa)')
        plt.ylim(0, y_max)
        plt.legend()
        plt.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    save_path = os.path.join(args.model_dir, 'final_ensemble_result.png')
    plt.savefig(save_path, dpi=300)
    print(f"Final visualization saved to: {save_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--test_data_path', type=str, default=DEFAULT_TEST_DATA_PATH)
    parser.add_argument('--model_dir', type=str, default=DEFAULT_GNN_MODEL_DIR)
    args = parser.parse_args()

    main(args)
