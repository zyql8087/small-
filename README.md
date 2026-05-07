# TPMS Modeling Workspace

本仓库用于 TPMS（Triply Periodic Minimal Surface）结构的应力曲线预测与逆向参数设计。项目包含两类核心任务：

- **Forward modeling**：由 9 个 TPMS 几何/形态参数预测 20 点应力曲线。
- **Inverse design**：由目标 20 点应力曲线生成或回归 9 个 TPMS 参数，并用前向代理模型对候选参数排序。

仓库已经整理为 `GAT`、`GNNTransform`、`CVAE`、`diffusion` 和 `demo` 五个主要区域，并保留了训练数据、已训练 checkpoint、评估结果和对比图，便于直接复现实验结果或继续训练。

## Repository Layout

```text
TPMS/
├── README.md
├── requirements.txt
├── dataset used for training/
│   ├── train.xlsx
│   ├── test.xlsx
│   ├── train-4canshu.xlsx
│   └── test-4canshu.xlsx
├── GAT/
│   ├── GAT_module.py
│   ├── train_forward_gnn.py
│   ├── train_inverse_gnn.py
│   └── forward_gnn_checkpoints/
├── GNNTransform/
│   ├── GNNtransformer_module.py
│   ├── train_forward_transformer.py
│   ├── test_forward_ensemble.py
│   ├── forward_transformer_checkpoints/
│   └── forward_test_results/
├── CVAE/
│   ├── CVAE_module.py
│   ├── train_inverse_cvae.py
│   └── cvae_checkpoints/
├── diffusion/
│   ├── diffusion_module.py
│   ├── train_inverse_diffusion.py
│   ├── test_inverse_ensemble.py
│   ├── inverse_diffusion_checkpoints/
│   └── inverse_test_results/
└── demo/
    ├── compare_experiment_metrics.py
    ├── compare_with_paper_baseline.py
    ├── reproduce_inverse_paper_baseline_5fold.py
    ├── graph_modeling.py
    ├── generate_ppt_outline_docx.py
    └── comparison_results/
```

## Data Format

默认训练和测试脚本读取：

- `dataset used for training/train.xlsx`
- `dataset used for training/test.xlsx`

两个 Excel 文件默认包含 `class1`、`class2`、`class12` 三个 sheet。脚本会把三个 sheet 合并后使用。

每行样本共有 29 列：

| Column group | Columns | Meaning |
| --- | --- | --- |
| TPMS parameters | `V1a`, `V1v`, `V1c`, `w`, `relativeVolume`, `relativeArea`, `thickness`, `poreDiameter`, `areaMean` | 9 维结构参数 |
| Stress curve | `s1` 到 `s20` | 20 点应力曲线 |

当前主要脚本使用 9 参数版本的 `train.xlsx` 和 `test.xlsx`。`train-4canshu.xlsx` 与 `test-4canshu.xlsx` 已保留在仓库中，可作为其他实验的数据源，但不是默认入口。

## Environment Setup

推荐使用 Python 3.10 或 3.11。GPU 不是强制要求，但完整训练会明显受益于 CUDA。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` 包含：

- `numpy`
- `pandas`
- `matplotlib`
- `scikit-learn`
- `torch`
- `torch-geometric`
- `networkx`
- `tqdm`
- `openpyxl`

如果 `torch-geometric` 安装失败，通常是 PyTorch/CUDA 轮子版本不匹配。先确认本机 PyTorch、CUDA 和 Python 版本，再安装匹配的 PyG wheel。

## Model Families

| Module | Task | Main model | Input | Output |
| --- | --- | --- | --- | --- |
| `GAT/` | Forward prediction | `GNNForwardNetwork` with dense GAT parameter graph | 9 TPMS parameters | 20 stress points |
| `GAT/` | Inverse baseline | `ResNet1DInverse` | 20 stress points | 9 TPMS parameters |
| `GNNTransform/` | Forward prediction | `TPMSForwardTransformer` | 9 TPMS parameters | 20 stress points |
| `CVAE/` | Inverse generation | Conditional VAE | 20 stress points + latent noise | 9 TPMS parameters |
| `diffusion/` | Inverse generation | Conditional denoising diffusion MLP | noisy 9 parameters + timestep + target curve | denoised 9 parameters |

## Quick Start

From the repository root:

```powershell
python GAT\train_forward_gnn.py
python GNNTransform\train_forward_transformer.py
python GNNTransform\test_forward_ensemble.py
python CVAE\train_inverse_cvae.py
python diffusion\train_inverse_diffusion.py
python diffusion\test_inverse_ensemble.py
```

The repository already includes checkpoints and result files, so evaluation scripts can be run before retraining if the default checkpoint paths exist.

## Forward Modeling

### GAT Forward Model

Training command:

```powershell
python GAT\train_forward_gnn.py --data_path "dataset used for training\train.xlsx" --epochs 500 --batch_size 256 --pipelines 1
```

Default behavior:

- reads `train.xlsx`
- uses the first 9 columns as input parameters
- uses `s1` to `s20` as the target curve
- splits data into train/validation with `test_size=0.2` and `random_state=42`
- builds a fully connected 9-node parameter graph
- trains with AdamW, MSE loss, MAE monitoring, warmup, input noise, gradient clipping, and ReduceLROnPlateau

Outputs are written to `GAT/forward_gnn_checkpoints/`:

- `forward_gnn_0.pth`
- `log_forward_gnn_0.xlsx`
- `training_curves_pipeline_0.png`

### Transformer Forward Model

Training command:

```powershell
python GNNTransform\train_forward_transformer.py --data_path "dataset used for training\train.xlsx" --epochs 500 --batch_size 256 --pipelines 1
```

Useful options:

```powershell
python GNNTransform\train_forward_transformer.py --pipelines 5 --hidden_dim 256 --num_heads 8 --num_layers 4 --early_stop_patience 80
```

Default behavior:

- tokenizes the 9 scalar parameters
- adds learnable parameter-type embeddings and a CLS token
- predicts the full 20-point stress curve from the CLS representation
- uses weighted MSE to emphasize tail stress points `s16` to `s20`
- gives extra weight to high-stress samples above the configured quantile

Outputs are written to `GNNTransform/forward_transformer_checkpoints/`:

- `forward_transformer_0.pth`, `forward_transformer_1.pth`, ...
- `log_forward_transformer_0.xlsx`, ...
- `training_curves_transformer_pipeline_0.png`, ...

### Forward Evaluation

Evaluation command:

```powershell
python GNNTransform\test_forward_ensemble.py
```

Default inputs:

- test data: `dataset used for training/test.xlsx`
- GAT checkpoint: `GAT/forward_gnn_checkpoints/forward_gnn_0.pth`
- Transformer checkpoint directory: `GNNTransform/forward_transformer_checkpoints/`
- Transformer ensemble indices: `0,1,2,3,4`

Outputs are written to `GNNTransform/forward_test_results/`:

- `forward_test_metrics.csv`
- `forward_test_comparison.png`
- `forward_test_comparison_stratified.png`

Current committed forward metrics:

| Model | MSE | MAE | R2 | NRMSE (%) |
| --- | ---: | ---: | ---: | ---: |
| GAT | 11.4840 | 1.0618 | 0.97595 | 2.31875 |
| Transformer ensemble 5 | 7.2574 | 0.7951 | 0.98465 | 1.84330 |

## Inverse Design

### ResNet Inverse Baseline

Training command:

```powershell
python GAT\train_inverse_gnn.py --data_path "dataset used for training\train.xlsx" --epochs 300 --batch_size 512
```

This script trains a deterministic inverse baseline from stress curve to TPMS parameters. It writes outputs to `GAT/inverse_resnet_checkpoints/`. This folder is generated by the script and is not part of the current committed checkpoint set.

### CVAE Inverse Model

Training command:

```powershell
python CVAE\train_inverse_cvae.py --data_path "dataset used for training\train.xlsx" --epochs 400 --batch_size 256 --pipelines 1
```

Default behavior:

- encodes the 20-point target curve with a 1D residual convolution encoder
- learns a latent distribution for 9-parameter reconstruction
- uses KL warmup, free-bits regularization, condition dropout, AdamW, and cosine annealing

Outputs are written to `CVAE/cvae_checkpoints/`:

- `cvae_0.pth`
- `log_cvae_0.xlsx`
- `cvae_curve_0.png`

### Diffusion Inverse Model

Training command:

```powershell
python diffusion\train_inverse_diffusion.py --data_path "dataset used for training\train.xlsx" --epochs 1200 --batch_size 4096 --pipelines 1
```

Useful options:

```powershell
python diffusion\train_inverse_diffusion.py --run_name single_pipeline_YYYYMMDD --amp --val_every 10 --early_stop_patience 300
```

Default behavior:

- trains a conditional denoising MLP
- conditions on the 20-point target curve
- denoises the 9-dimensional parameter vector over a diffusion schedule
- supports EMA model selection, optional AMP, optional `torch.compile`, validation repeats, x0 reconstruction loss, and early stopping

Outputs are written to `diffusion/inverse_diffusion_checkpoints/` or a named run folder:

- `inverse_diffusion_0.pth`
- `log_inverse_diffusion_0.xlsx`
- `inverse_diffusion_curve_0.png`

The committed default diffusion checkpoint is:

```text
diffusion/inverse_diffusion_checkpoints/single_pipeline_20260319/inverse_diffusion_0.pth
```

### Inverse Evaluation

Evaluation command:

```powershell
python diffusion\test_inverse_ensemble.py
```

Default inputs:

- test data: `dataset used for training/test.xlsx`
- CVAE checkpoint: `CVAE/cvae_checkpoints/cvae_0.pth`
- Diffusion checkpoint: `diffusion/inverse_diffusion_checkpoints/single_pipeline_20260319/inverse_diffusion_0.pth`
- forward GAT checkpoint: `GAT/forward_gnn_checkpoints/forward_gnn_0.pth`
- forward Transformer checkpoint directory: `GNNTransform/forward_transformer_checkpoints/`

Evaluation flow:

1. Generate candidate TPMS parameters from CVAE and diffusion.
2. Use the forward GAT and Transformer ensemble to predict stress curves for each candidate.
3. Rank candidates by curve reconstruction error against the target curve.
4. Report top-k parameter and curve metrics.
5. Save top-k candidates for later comparison.

Outputs are written to `diffusion/inverse_test_results/`:

- `inverse_test_metrics.csv`
- `inverse_test_comparison.png`
- `cvae_topk_candidates.npz`
- `diffusion_topk_candidates.npz`

Current committed inverse metrics:

| Model | Top-k | Param MSE | Param MAE | Curve MSE | Curve MAE | Curve NRMSE (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CVAE | 3 | 133.0156 | 3.6545 | 28.8452 | 2.0193 | 3.67489 |
| Diffusion | 3 | 46.8414 | 1.1496 | 2.5386 | 0.7309 | 1.09019 |

## Experiment Comparison

`demo/compare_experiment_metrics.py` compares the committed forward and inverse result CSV files:

```powershell
python demo\compare_experiment_metrics.py
```

Inputs:

- `GNNTransform/forward_test_results/forward_test_metrics.csv`
- `diffusion/inverse_test_results/inverse_test_metrics.csv`

Outputs:

- `demo/comparison_results/metrics_comparison_summary.csv`
- `demo/comparison_results/metrics_comparison_visualization.png`

Current summary:

- Transformer ensemble reduces forward MSE by about 36.80% vs GAT.
- Transformer ensemble reduces forward NRMSE by about 20.50% vs GAT.
- Diffusion reduces inverse parameter MSE by about 64.79% vs CVAE.
- Diffusion reduces inverse curve NRMSE by about 70.33% vs CVAE.

`demo/compare_with_paper_baseline.py` and `demo/reproduce_inverse_paper_baseline_5fold.py` are paper-baseline comparison utilities. They expect the supplementary file `smll202500634-sup-0001-suppmat.docx` under `C:\Users\48186\Desktop` and parse Table S1/S2 scores from the document.

## Common Workflows

### Re-run forward experiments

```powershell
python GAT\train_forward_gnn.py --pipelines 1
python GNNTransform\train_forward_transformer.py --pipelines 5
python GNNTransform\test_forward_ensemble.py --transformer_ensemble_indices 0,1,2,3,4
python demo\compare_experiment_metrics.py
```

### Re-run inverse experiments

```powershell
python CVAE\train_inverse_cvae.py --pipelines 1
python diffusion\train_inverse_diffusion.py --run_name single_pipeline_custom --pipelines 1
python diffusion\test_inverse_ensemble.py --diffusion_checkpoint diffusion\inverse_diffusion_checkpoints\single_pipeline_custom\inverse_diffusion_0.pth
python demo\compare_experiment_metrics.py
```

### Use a single Transformer checkpoint instead of an ensemble

```powershell
python GNNTransform\test_forward_ensemble.py --transformer_checkpoint GNNTransform\forward_transformer_checkpoints\forward_transformer_0.pth
```

### Change inverse candidate sampling

```powershell
python diffusion\test_inverse_ensemble.py --cvae_candidates_per_sample 50 --diffusion_candidates_per_sample 12 --top_k 5 --diffusion_steps 50
```

## Reproducibility Notes

- Training scripts set deterministic seeds such as `42`, but GPU kernels can still introduce small numeric differences.
- All scripts auto-select CUDA when available and fall back to CPU otherwise.
- Checkpoints store fitted `StandardScaler` objects. Use the matching checkpoint scaler for inference.
- Evaluation scripts rely on relative paths resolved from each script location, so run commands from the repository root unless you pass explicit paths.
- Some source comments contain mojibake from older encoding conversions. The executable logic is unaffected, but comments may need cleanup in a future documentation pass.

## Generated Artifacts

The repository tracks selected `.pth`, `.xlsx`, `.csv`, `.png`, and `.npz` artifacts so the included results can be inspected without retraining. For long-term collaboration, consider moving larger model artifacts to Git LFS or an external artifact store.

The `.gitignore` excludes:

- IDE settings such as `.idea/` and `.cursor/`
- Python bytecode and `__pycache__/`
- runtime logs such as `*.log` and `*.err.log`
- ad-hoc temporary artifacts under `tmp_artifacts/`

## Troubleshooting

### `FileNotFoundError` for Excel data

Check that the file path exists and includes the space in `dataset used for training`. You can also pass an explicit path:

```powershell
python GAT\train_forward_gnn.py --data_path "F:\TPMS\dataset used for training\train.xlsx"
```

### Missing Transformer checkpoints

`test_forward_ensemble.py` defaults to indices `0,1,2,3,4`. If only one checkpoint exists, run:

```powershell
python GNNTransform\test_forward_ensemble.py --transformer_ensemble_indices 0
```

### Missing paper supplementary DOCX

Paper-baseline scripts look for:

```text
C:\Users\48186\Desktop\**\smll202500634-sup-0001-suppmat.docx
```

Place the supplementary file under Desktop or edit the path in the demo script before running.

### Out-of-memory during diffusion training

Reduce batch sizes:

```powershell
python diffusion\train_inverse_diffusion.py --batch_size 1024 --val_batch_size 2048
```

## Suggested Development Order

1. Confirm data schema and sheet names in `train.xlsx` and `test.xlsx`.
2. Train or reuse the forward models.
3. Run `GNNTransform/test_forward_ensemble.py` to validate forward prediction quality.
4. Train or reuse inverse models.
5. Run `diffusion/test_inverse_ensemble.py` to evaluate inverse candidates.
6. Run `demo/compare_experiment_metrics.py` to regenerate summary tables and figures.

