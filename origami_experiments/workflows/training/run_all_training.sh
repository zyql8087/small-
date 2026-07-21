#!/usr/bin/env bash
# Sequential training of all 5 origami models
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA="${CONDA:-conda run -n DL}"

echo "========================================="
echo "Starting full training pipeline"
echo "Started at: $(date)"
echo "========================================="

echo ""
echo "===== 1/5: Forward GNN (500 epochs) ====="
$CONDA python "$SCRIPT_DIR/train_forward_gnn.py" --epochs 500 --batch_size 256
echo "Forward GNN done at $(date)"

echo ""
echo "===== 2/5: Forward Transformer (500 epochs) ====="
$CONDA python "$SCRIPT_DIR/train_forward_transformer.py" --epochs 500 --batch_size 256
echo "Forward Transformer done at $(date)"

echo ""
echo "===== 3/5: Inverse ResNet (300 epochs) ====="
$CONDA python "$SCRIPT_DIR/train_inverse_resnet.py" --epochs 300 --batch_size 512
echo "Inverse ResNet done at $(date)"

echo ""
echo "===== 4/5: Inverse CVAE (400 epochs) ====="
$CONDA python "$SCRIPT_DIR/train_inverse_cvae.py" --epochs 400 --batch_size 256
echo "Inverse CVAE done at $(date)"

echo ""
echo "===== 5/5: Inverse Diffusion (1200 epochs) ====="
$CONDA python "$SCRIPT_DIR/train_inverse_diffusion.py" --epochs 1200 --batch_size 4096 --val_batch_size 8192 --amp
echo "Inverse Diffusion done at $(date)"

echo ""
echo "========================================="
echo "All training completed at $(date)"
echo "========================================="
