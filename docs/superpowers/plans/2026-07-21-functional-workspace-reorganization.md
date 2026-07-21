# Functional Workspace Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate transient workspace material and reorganize the Origami experiment source by function without deleting source, data, models, reports, or existing user changes.

**Architecture:** Keep `origami_experiments` as the package root. Relocate neural-network definitions to `models`, place runnable scripts below `workflows/<function>`, and retain `curve_dataset` as its own subsystem with `snap_probe` as a reusable probe. All current scratch material, logs, and bytecode move intact to the ignored root `.workspace_cache` tree; data and experiment outputs retain their current semantic locations.

**Tech Stack:** Python 3, unittest, PowerShell, Git, Bash launcher, Markdown.

---

## Target file structure

```text
.workspace_cache/
  scratch/                         # former tmp/
  logs/                             # relocated historical logs
  bytecode/                         # relocated existing __pycache__ trees
origami_experiments/
  __init__.py
  models/                           # former modules/
  workflows/
    __init__.py
    data/                           # prepare_data.py, prepare_validation_splits.py
    training/                       # train_*.py, run_all_training.sh
    evaluation/                     # evaluate_*.py, smoke_load_portable_models.py
    analysis/                       # audit_*, summarize_*, plot_*, showcase
    publishing/                     # create_*, generate_*, export_*
  curve_dataset/
    probes/snap_probe/              # former curve_dataset/snap_probe/
  tests/test_workspace_layout.py
```

### Task 1: Record the baseline and add a relocation contract test

**Files:**
- Create: `docs/superpowers/reports/2026-07-21-workspace-reorganization-before.json`
- Create: `origami_experiments/tests/test_workspace_layout.py`
- Modify: `.gitignore`

- [ ] **Step 1: Record file paths and SHA-256 hashes before any move**

Run from `F:\small++`:

```powershell
New-Item -ItemType Directory -Force 'docs/superpowers/reports' | Out-Null
$paths = @(
  'tmp',
  'origami_experiments/modules',
  'origami_experiments/curve_dataset/snap_probe',
  'origami_experiments/training_log.txt',
  'origami_experiments/curve_dataset/logs',
  'origami_experiments/curve_dataset/miura_nonlinear_v2/logs',
  'origami_experiments/curve_dataset/miura_nonlinear_v2/pre_physics_50/logs',
  'origami_experiments/__pycache__',
  'origami_experiments/modules/__pycache__',
  'origami_experiments/tests/__pycache__',
  'origami_experiments/curve_dataset/__pycache__',
  'origami_experiments/curve_dataset/snap_probe/__pycache__',
  'origami_experiments/curve_dataset/miura_nonlinear_v2/scripts/__pycache__',
  'origami_experiments/curve_dataset/miura_nonlinear_v2/tests/__pycache__',
  'output/figures/__pycache__'
)
$files = foreach ($path in $paths) {
  if (Test-Path -LiteralPath $path -PathType Leaf) {
    Get-FileHash -Algorithm SHA256 -LiteralPath $path | Select-Object Path, Algorithm, Hash
  } elseif (Test-Path -LiteralPath $path -PathType Container) {
    Get-ChildItem -LiteralPath $path -Force -Recurse -File | Get-FileHash -Algorithm SHA256 | Select-Object Path, Algorithm, Hash
  }
}
$files | ConvertTo-Json -Depth 3 | Set-Content -Encoding utf8 'docs/superpowers/reports/2026-07-21-workspace-reorganization-before.json'
```

Expected: a non-empty JSON inventory containing every file to be relocated.

- [ ] **Step 2: Add the failing standard-library layout test**

Create `origami_experiments/tests/test_workspace_layout.py`:

```python
"""Regression checks for the functional workspace layout."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


class WorkspaceLayoutTests(unittest.TestCase):
    def test_functional_packages_are_discoverable(self) -> None:
        expected_modules = [
            "origami_experiments.models.origami_forward_gnn",
            "origami_experiments.workflows.data.prepare_data",
            "origami_experiments.workflows.training.train_taskfit",
            "origami_experiments.workflows.evaluation.evaluate_taskfit",
            "origami_experiments.workflows.analysis.audit_trained_models",
            "origami_experiments.workflows.publishing.export_portable_checkpoints",
        ]
        for module_name in expected_modules:
            with self.subTest(module_name=module_name):
                self.assertIsNotNone(importlib.util.find_spec(module_name))

    def test_snap_probe_is_classified_as_curve_dataset_probe(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "curve_dataset" / "probes" / "snap_probe").is_dir())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the layout test before implementation**

Run:

```powershell
python -m unittest origami_experiments.tests.test_workspace_layout -v
```

Expected: FAIL because `models` and `workflows` do not yet exist.

- [ ] **Step 4: Ignore the central cache without changing existing ignore policy**

Append these exact entries to `.gitignore` below the `# ── Logs & scratch ──` heading:

```gitignore
.workspace_cache/
docs/superpowers/reports/*-workspace-reorganization-before.json
```

- [ ] **Step 5: Confirm no pre-existing user work was staged**

Run:

```powershell
git status --short
git diff --cached --name-status
```

Expected: no pre-existing source edits are staged. Do not commit the reorganization because the current worktree already contains user modifications in files that will move.

### Task 2: Consolidate current transient files in the central cache

**Files:**
- Create: `.workspace_cache/scratch/`
- Create: `.workspace_cache/logs/`
- Create: `.workspace_cache/bytecode/`
- Move: `tmp/` → `.workspace_cache/scratch/root-tmp/`
- Move: `origami_experiments/training_log.txt` → `.workspace_cache/logs/origami_experiments/training_log.txt`
- Move: three curve-dataset `logs/` trees → corresponding `.workspace_cache/logs/` paths
- Move: existing project-local `__pycache__/` trees → corresponding `.workspace_cache/bytecode/` paths

- [ ] **Step 1: Create cache category directories**

```powershell
New-Item -ItemType Directory -Force '.workspace_cache/scratch', '.workspace_cache/logs', '.workspace_cache/bytecode' | Out-Null
```

- [ ] **Step 2: Move scratch and historical logs intact**

```powershell
Move-Item -LiteralPath 'tmp' -Destination '.workspace_cache/scratch/root-tmp'
New-Item -ItemType Directory -Force '.workspace_cache/logs/origami_experiments', '.workspace_cache/logs/origami_experiments/curve_dataset/miura_nonlinear_v2/pre_physics_50' | Out-Null
Move-Item -LiteralPath 'origami_experiments/training_log.txt' -Destination '.workspace_cache/logs/origami_experiments/training_log.txt'
Move-Item -LiteralPath 'origami_experiments/curve_dataset/logs' -Destination '.workspace_cache/logs/origami_experiments/curve_dataset/logs'
Move-Item -LiteralPath 'origami_experiments/curve_dataset/miura_nonlinear_v2/logs' -Destination '.workspace_cache/logs/origami_experiments/curve_dataset/miura_nonlinear_v2/logs'
Move-Item -LiteralPath 'origami_experiments/curve_dataset/miura_nonlinear_v2/pre_physics_50/logs' -Destination '.workspace_cache/logs/origami_experiments/curve_dataset/miura_nonlinear_v2/pre_physics_50/logs'
$probeRoot = (Resolve-Path 'origami_experiments/curve_dataset/snap_probe').Path
Get-ChildItem -LiteralPath $probeRoot -Recurse -File -Filter '*.log' | ForEach-Object {
  $relativePath = $_.FullName.Substring($probeRoot.Length).TrimStart('\\')
  $destination = Join-Path '.workspace_cache/logs/origami_experiments/curve_dataset/snap_probe' $relativePath
  New-Item -ItemType Directory -Force (Split-Path -Parent $destination) | Out-Null
  Move-Item -LiteralPath $_.FullName -Destination $destination
}
```

Expected: all historical log files are preserved below `.workspace_cache/logs`; no current source file changes.

- [ ] **Step 3: Move only project-owned existing bytecode, never external or Git metadata**

```powershell
$pycacheDirs = @(
  'origami_experiments/__pycache__',
  'origami_experiments/modules/__pycache__',
  'origami_experiments/tests/__pycache__',
  'origami_experiments/curve_dataset/__pycache__',
  'origami_experiments/curve_dataset/snap_probe/__pycache__',
  'origami_experiments/curve_dataset/miura_nonlinear_v2/scripts/__pycache__',
  'origami_experiments/curve_dataset/miura_nonlinear_v2/tests/__pycache__',
  'output/figures/__pycache__'
)
foreach ($dir in $pycacheDirs) {
  if (Test-Path -LiteralPath $dir) {
    $target = Join-Path '.workspace_cache/bytecode' ($dir -replace '[\\/:]', '__')
    Move-Item -LiteralPath $dir -Destination $target
  }
}
```

Expected: `external/**/__pycache__` and all `.git/**/logs` remain untouched.

- [ ] **Step 4: Verify cache confinement and source preservation**

```powershell
git check-ignore -v .workspace_cache/scratch/root-tmp/analyze_origami.py
Get-ChildItem -LiteralPath '.workspace_cache' -Force -Recurse -File | Measure-Object
Test-Path 'external/OrigamiSimulator/.git'
Test-Path 'external/GenerateOrigamiDataSet/.git'
```

Expected: cache path is ignored, file count is nonzero, and both external nested repositories still exist.

### Task 3: Move models and workflows into functional packages

**Files:**
- Create: `origami_experiments/__init__.py`
- Create: `origami_experiments/workflows/__init__.py`
- Create: `origami_experiments/workflows/{data,training,evaluation,analysis,publishing}/__init__.py`
- Move: `origami_experiments/modules/` → `origami_experiments/models/`
- Move: top-level workflow scripts to their matching `workflows/` category
- Move: `origami_experiments/run_all_training.sh` → `origami_experiments/workflows/training/run_all_training.sh`
- Modify: every moved workflow script that imports `modules` or derives paths from `__file__`

- [ ] **Step 1: Create packages and relocate files with `git mv`**

```powershell
New-Item -ItemType Directory -Force 'origami_experiments/workflows/data', 'origami_experiments/workflows/training', 'origami_experiments/workflows/evaluation', 'origami_experiments/workflows/analysis', 'origami_experiments/workflows/publishing' | Out-Null
New-Item -ItemType File -Force 'origami_experiments/__init__.py', 'origami_experiments/workflows/__init__.py', 'origami_experiments/workflows/data/__init__.py', 'origami_experiments/workflows/training/__init__.py', 'origami_experiments/workflows/evaluation/__init__.py', 'origami_experiments/workflows/analysis/__init__.py', 'origami_experiments/workflows/publishing/__init__.py' | Out-Null
git mv origami_experiments/modules origami_experiments/models
git mv origami_experiments/prepare_data.py origami_experiments/prepare_validation_splits.py origami_experiments/workflows/data/
git mv origami_experiments/train_forward_gnn.py origami_experiments/train_forward_transformer.py origami_experiments/train_inverse_resnet.py origami_experiments/train_inverse_cvae.py origami_experiments/train_inverse_diffusion.py origami_experiments/train_taskfit.py origami_experiments/run_all_training.sh origami_experiments/workflows/training/
git mv origami_experiments/evaluate_all.py origami_experiments/evaluate_all_final_models.py origami_experiments/evaluate_taskfit.py origami_experiments/smoke_load_portable_models.py origami_experiments/workflows/evaluation/
git mv origami_experiments/audit_trained_models.py origami_experiments/make_prediction_showcase.py origami_experiments/plot_final_model_losses.py origami_experiments/summarize_diffusion_iterations.py origami_experiments/workflows/analysis/
git mv origami_experiments/create_experiment_report_docx.py origami_experiments/create_origami_dataset_intro_ppt.py origami_experiments/export_portable_checkpoints.py origami_experiments/generate_ppt.py origami_experiments/workflows/publishing/
```

- [ ] **Step 2: Preserve each script's semantic output root and use package imports**

In every moved workflow script that currently sets `SCRIPT_DIR = Path(__file__).resolve().parent`, replace the root setup with:

```python
EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = EXPERIMENT_ROOT.parent
SCRIPT_DIR = EXPERIMENT_ROOT
```

For scripts importing a model, add this immediately before the import and use the listed package import:

```python
sys.path.insert(0, str(REPO_ROOT))
from origami_experiments.models.origami_taskfit_models import load_test_raw, load_train_val
```

Use the model module that matches each existing import:

```python
from origami_experiments.models.origami_forward_gnn import OrigamiGNNForward
from origami_experiments.models.origami_forward_transformer import OrigamiForwardTransformer
from origami_experiments.models.origami_inverse_resnet import OrigamiResNet1DInverse
from origami_experiments.models.origami_inverse_cvae import OrigamiCVAE
from origami_experiments.models.origami_inverse_diffusion import OrigamiConditionalDenoisingMLP
from origami_experiments.models.origami_taskfit_models import load_test_raw, load_train_val
```

For `prepare_data.py`, use this exact root derivation instead of its former two `Path(__file__)` expressions:

```python
EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = EXPERIMENT_ROOT.parent
DATA_ROOT = PROJECT_ROOT / "external" / "GenerateOrigamiDataSet"
OUTPUT_DIR = EXPERIMENT_ROOT / "data"
```

For `prepare_validation_splits.py`, use:

```python
EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = EXPERIMENT_ROOT.parent
SCRIPT_DIR = EXPERIMENT_ROOT
DATA_ROOT = PROJECT_ROOT / "external" / "GenerateOrigamiDataSet"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "demo_data" / "data_validation_splits"
```

For `create_origami_dataset_intro_ppt.py`, replace its absolute `F:\\small++` root with:

```python
ROOT = Path(__file__).resolve().parents[2]
```

- [ ] **Step 3: Make the training launcher location independent**

Replace the setup portion of `origami_experiments/workflows/training/run_all_training.sh` with:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPERIMENT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONDA="${CONDA:-python}"

"$CONDA" "$SCRIPT_DIR/train_forward_gnn.py" --epochs 500 --batch_size 256
"$CONDA" "$SCRIPT_DIR/train_forward_transformer.py" --epochs 500 --batch_size 256
"$CONDA" "$SCRIPT_DIR/train_inverse_resnet.py" --epochs 300 --batch_size 512
"$CONDA" "$SCRIPT_DIR/train_inverse_cvae.py" --epochs 400 --batch_size 256
"$CONDA" "$SCRIPT_DIR/train_inverse_diffusion.py" --epochs 1200 --batch_size 4096 --val_batch_size 8192 --amp
```

Expected: the launcher does not depend on its current working directory and each invoked Python script resolves data/output roots to `origami_experiments/`.

- [ ] **Step 4: Update test imports for the renamed model package**

In `origami_experiments/tests/test_curve_model_shapes.py`, replace:

```python
from origami_experiments.modules.origami_curve_models import (
```

with:

```python
from origami_experiments.models.origami_curve_models import (
```

- [ ] **Step 5: Run the layout test and syntax compilation**

```powershell
$env:PYTHONPYCACHEPREFIX = (Resolve-Path '.workspace_cache/bytecode').Path
python -m unittest origami_experiments.tests.test_workspace_layout -v
python -m compileall -q origami_experiments
Remove-Item Env:PYTHONPYCACHEPREFIX
```

Expected: the layout test passes and `compileall` has no output.

- [ ] **Step 6: Inspect source moves without staging user modifications**

```powershell
git status --short
git diff --name-status -- origami_experiments
```

Expected: moved source paths and the user's pre-existing edits remain unstaged. Do not commit this task because several moved source files were already modified before reorganization.

### Task 4: Classify the curve probe without discarding its experiment material

**Files:**
- Create: `origami_experiments/curve_dataset/probes/`
- Move: `origami_experiments/curve_dataset/snap_probe/` → `origami_experiments/curve_dataset/probes/snap_probe/`
- Modify: Markdown and source files under the relocated probe that contain the old absolute probe path

- [ ] **Step 1: Move the probe as a single directory**

```powershell
New-Item -ItemType Directory -Force 'origami_experiments/curve_dataset/probes' | Out-Null
git mv origami_experiments/curve_dataset/snap_probe origami_experiments/curve_dataset/probes/snap_probe
```

- [ ] **Step 2: Replace the two documented absolute probe paths**

In `origami_experiments/curve_dataset/probes/snap_probe/仿真实验计划指导.md`, replace both occurrences of:

```text
F:\small++\origami_experiments\curve_dataset\snap_probe
```

with:

```text
F:\small++\origami_experiments\curve_dataset\probes\snap_probe
```

- [ ] **Step 3: Check for stale references and preserve raw-curve results**

```powershell
rg -n 'curve_dataset[/\\]snap_probe|curve_dataset\\snap_probe' .
Test-Path 'origami_experiments/curve_dataset/probes/snap_probe/raw_curves'
Test-Path 'origami_experiments/curve_dataset/probes/snap_probe/abaqus_validation/abaqus_validation_manifest.csv'
```

Expected: `rg` reports no old probe path, and both paths return `True`.

- [ ] **Step 4: Confirm the probe remains an unstaged, recoverable move**

```powershell
git status --short 'origami_experiments/curve_dataset'
```

Expected: the relocated probe remains visible as an uncommitted move or untracked content; do not stage it automatically.

### Task 5: Update project documentation and command entry points

**Files:**
- Modify: `README.md`
- Modify: `origami_experiments/实验总结报告.md` only if it is intended to be a living layout document; otherwise leave its historical directory snapshot unchanged

- [ ] **Step 1: Replace the README tree with the target functional structure**

Update the section beginning at `## 4. 目录结构` to list `models/`, all five `workflows/` categories, `curve_dataset/probes/snap_probe/`, and `.workspace_cache/` as an ignored cache. Retain the existing descriptions of `data/`, checkpoints, results, `output/`, `evidence/`, and `external/`.

- [ ] **Step 2: Update runnable README commands**

Replace the existing scalar-task commands with these exact PowerShell commands:

```powershell
python origami_experiments\workflows\data\prepare_data.py
python origami_experiments\workflows\training\train_taskfit.py
python origami_experiments\workflows\training\train_taskfit.py --stages forward_gat inverse_cvae --gat_graph physical_sparse
python origami_experiments\workflows\training\train_forward_gnn.py
python origami_experiments\workflows\training\train_forward_transformer.py
python origami_experiments\workflows\training\train_inverse_resnet.py
python origami_experiments\workflows\training\train_inverse_cvae.py
python origami_experiments\workflows\training\train_inverse_diffusion.py
python origami_experiments\workflows\evaluation\evaluate_taskfit.py
python origami_experiments\workflows\evaluation\evaluate_all.py
python origami_experiments\workflows\data\prepare_validation_splits.py --split group_pattern_mn
```

- [ ] **Step 3: Add the cache policy to the README Git section**

Add this sentence to the list of ignored artifacts:

```markdown
- `.workspace_cache/`：统一存放临时脚本、历史运行日志和可再生成的 Python 字节码；不含源码、训练数据、模型或正式报告。
```

- [ ] **Step 4: Verify no stale documentation commands remain**

```powershell
rg -n 'origami_experiments\\(prepare_|train_|evaluate_)|modules/' README.md
```

Expected: no output except historical prose deliberately retained in the immutable experiment summary.

- [ ] **Step 5: Inspect the README diff without staging it**

```powershell
git diff --check -- README.md
git diff -- README.md
```

Expected: no whitespace errors and only the documented layout/command/cache-policy changes. Do not stage or commit automatically.

### Task 6: Run regression checks and prove relocations are lossless

**Files:**
- Create: `docs/superpowers/reports/2026-07-21-workspace-reorganization-after.json`
- Modify: no source files expected

- [ ] **Step 1: Record an after-move hash inventory for every cache and relocated source file**

```powershell
$roots = @('.workspace_cache', 'origami_experiments/models', 'origami_experiments/workflows', 'origami_experiments/curve_dataset/probes/snap_probe')
$files = foreach ($root in $roots) {
  Get-ChildItem -LiteralPath $root -Force -Recurse -File | Get-FileHash -Algorithm SHA256 | Select-Object Path, Algorithm, Hash
}
$files | ConvertTo-Json -Depth 3 | Set-Content -Encoding utf8 'docs/superpowers/reports/2026-07-21-workspace-reorganization-after.json'
```

- [ ] **Step 2: Compare all baseline hashes to the appropriate new roots**

```powershell
$before = Get-Content -Raw 'docs/superpowers/reports/2026-07-21-workspace-reorganization-before.json' | ConvertFrom-Json
$after = Get-Content -Raw 'docs/superpowers/reports/2026-07-21-workspace-reorganization-after.json' | ConvertFrom-Json
$afterHashes = @($after | ForEach-Object Hash)
$missing = @($before | Where-Object { $_.Hash -notin $afterHashes })
if ($missing.Count -gt 0) { $missing | Format-Table -AutoSize; throw 'A baseline file hash is absent after reorganization.' }
```

Expected: command exits successfully; each baseline artifact survives at a new categorized location.

- [ ] **Step 3: Run standard-library and existing model-shape tests**

```powershell
$env:PYTHONPYCACHEPREFIX = (Resolve-Path '.workspace_cache/bytecode').Path
python -m unittest origami_experiments.tests.test_workspace_layout -v
python -m unittest origami_experiments.tests.test_curve_model_shapes -v
Remove-Item Env:PYTHONPYCACHEPREFIX
```

Expected: both test commands pass. If model dependencies are unavailable, retain the exact error and still require successful `compileall` and layout test before handoff.

- [ ] **Step 4: Inspect final Git state without altering the user's pre-existing changes**

```powershell
git status --short
git diff --check
git diff --name-status
```

Expected: user changes remain in the diff, moved paths appear as renames where Git can detect them, and no whitespace errors are reported.

- [ ] **Step 5: Leave verification reports unstaged for user review**

```powershell
git status --short docs/superpowers/reports
```

Expected: the reports are available for inspection but remain unstaged until the user explicitly requests a commit.
