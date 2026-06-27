# Miura Nonlinear V2 Simulation Workspace

This folder contains the Miura-only large-load nonlinear force-displacement
simulation workflow.

## Layout

- `jobs_miura/`: local copy of the Miura-only parameter and condition tables.
- `matlab/`: MATLAB/SWOMPS curve generator with physical summary columns.
- `scripts/`: batch simulation, audit, packing, plotting, and smoke-training scripts.
- `raw_curves/`: production CSV output for the next optimized run.
- `data/`: production NPZ output for the next optimized run.
- `smoke_results/`: production audit, plots, and smoke-training output.
- `logs/`: production batch logs.
- `validation/physics_smoke/`: two-sample validation of the physical-summary schema.
- `pre_physics_50/`: archived 50-sample run from before physical summary columns were added.

## Job Tables

- `jobs_miura/parameters.csv`: one row per Miura sample. This is the model
  input table and keeps the six original stiffness columns only for QC.
- `jobs_miura/simulation_jobs.csv`: one row per sample-condition pair
  (`6 rows/sample`). It documents the six loading conditions and is validated
  for consistency, but it is not used as the ML input table.
- `jobs_miura/dataset_spec.json`: v2 default metadata. `curve_points` is `80`
  and must stay aligned with the nonlinear batch script.

## Current Optimized CSV Schema

Each sample CSV contains six loading conditions with 80 loading steps each.
In addition to force-displacement fields, each step includes:

- `strain_energy_total`
- `strain_energy_crease`
- `strain_energy_panel`
- `max_bar_stress`
- `max_bar_strain`
- `max_crease_moment`
- `max_crease_rotation`

These physical columns are required for new v2 runs. Archived pre-physics CSVs
can still be packed only when `--allow-missing-physics` is passed explicitly.

## Recommended Production Run

Run the full optimized dataset from this folder's self-contained scripts:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\scripts\run_swomps_miura_nonlinear_batch.ps1 -StartIndex 1 -EndIndex 2000 -CurvePoints 80 -TargetLinearDisplacement 0.015 -MaxFinalLoad 10000 -Overwrite
```

Audit after each milestone, for example at 200 samples:

```powershell
F:\Anaconda\envs\GMM\python.exe F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\scripts\audit_curve_batch.py --job-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\jobs_miura --curves-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\raw_curves --output-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\smoke_results --curve-points 80 --final-load 3 --expected-samples 200 --audit-mode nonlinear --min-mean-secant-change-ratio 0.08 --min-max-secant-change-ratio 0.25 --min-mean-linearity-error 0.08
```

Pack the completed dataset:

```powershell
F:\Anaconda\envs\GMM\python.exe F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\scripts\build_curve_dataset_npz.py --allow-partial --curve-points 80
```

Run the protocol smoke training with displacement plus physical-history targets:

```powershell
F:\Anaconda\envs\GMM\python.exe F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\scripts\smoke_train_curve_dataset.py --epochs 5 --target-mode displacement_physics
```
