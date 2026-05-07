# TPMS Modeling Workspace

This workspace is organized into four model families plus a `demo` area for one-off analysis and temporary scripts.

## Structure

- `GAT/`: GAT forward model, inverse ResNet baseline, and GAT checkpoints
- `GNNTransform/`: transformer forward model, forward ensemble test script, and transformer results
- `CVAE/`: CVAE inverse model and checkpoints
- `diffusion/`: diffusion inverse model, inverse ensemble test script, and diffusion results
- `demo/`: comparison, reproduction, graph exploration, and PPT-outline helper scripts
- `dataset used for training/`: shared training and test Excel files

## Quick Start

```bash
python GAT/train_forward_gnn.py
python GAT/train_inverse_gnn.py
python GNNTransform/train_forward_transformer.py
python GNNTransform/test_forward_ensemble.py
python CVAE/train_inverse_cvae.py
python diffusion/train_inverse_diffusion.py
python diffusion/test_inverse_ensemble.py
```

## Notes

- Shared datasets stay in `dataset used for training/`.
- Temporary comparison outputs are grouped under `demo/comparison_results/`.
- Default checkpoint and result paths are now resolved from the reorganized directory layout.
