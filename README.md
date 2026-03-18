# TPMS Modeling Workspace

This repository contains forward and inverse modeling scripts for TPMS data.

## Canonical Script Location

- The repository root (`F:\TPMS`) is the canonical source of truth.
- The `F:\TPMS\code` directory now contains compatibility wrappers only.
- If you have old commands like `python code/train_forward_gnn.py`, they still work and forward to root scripts.

## Data and Checkpoints

- Training and test data are expected in:
  - `dataset used for training/train.xlsx`
  - `dataset used for training/test.xlsx`
- By default, scripts resolve these paths relative to their own file location.

## Environment Setup

1. Create and activate a Python environment (Python 3.9+ recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

If `torch-geometric` installation fails on your platform/CUDA combo, install PyTorch and torch-geometric using their official wheel instructions first, then re-run `pip install -r requirements.txt`.

## Quick Start

Forward GNN training:

```bash
python train_forward_gnn.py
```

Forward Transformer training:

```bash
python train_forward_transformer.py
```

Inverse CVAE training:

```bash
python train_inverse_cvae.py
```

Inverse ResNet (curve -> params) training:

```bash
python train_inverse_gnn.py
```

Evaluate GNN ensemble:

```bash
python test_ensemble.py
```

Evaluate Transformer models:

```bash
python forward_test.py
```

Run inverse-design verification:

```bash
python verify_inverse_design_final.py
```

## Notes

- `train_inverse_gnn.py` now uses `ResNet1DInverse` defined in `GNN_module.py`.
- Checkpoints are written under root-level checkpoint directories (for example `forward_gnn_checkpoints`, `forward_transformer_checkpoints`, `cvae_checkpoints`).
