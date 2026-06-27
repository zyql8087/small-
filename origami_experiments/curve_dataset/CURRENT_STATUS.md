# Curve Dataset Workspace Status

Last organized: 2026-05-14

## Current Valid Outputs

- Raw curve CSV files:
  - Miura: 26 samples, `miura_00001` to `miura_00026`
  - TMP: 3 samples, `tmp_00001` to `tmp_00003`
- Packed dataset:
  - `data/origami_curve_train.npz`: 23 samples
  - `data/origami_curve_test.npz`: 6 samples
  - Target shape before flattening: `[N, 6, 30]`
  - Full curve shape: `[N, 6, 30, 2]` for `[displacement, force]`

## Validation State

- `smoke_results/mixed_batch_audit.json` is the latest audit.
- Latest audit found no structural issues:
  - 180 rows per sample
  - `curve_id = 0..5`
  - `step = 1..30` per curve
  - all rows converged
  - force and displacement are monotonic
  - no NaN or Inf values
- Latest simple model smoke test outputs:
  - `smoke_results/curve_smoke_metrics.json`
  - `smoke_results/curve_smoke_history.csv`

## Log Organization

- `logs/completed/`
  - Completed run logs:
    - `swomps_1_20_stdout.log`
    - `swomps_tmp_1_3_stdout.log`
- `logs/aborted/`
  - Long-running exploratory batch logs that were stopped after confirming poor throughput:
    - `swomps_miura_21_200_stdout.log`
    - `swomps_tmp_4_50_stdout.log`
    - `swomps_miura_23_200_stdout.log`
- `logs/empty_stderr/`
  - Empty stderr logs from runs with no MATLAB stderr output.

## Notes For Next Runs

- Do not run multiple MATLAB/SWOMPS instances in parallel on this machine; the observed resource contention made Miura much slower.
- Prefer single-instance staged runs.
- Recommended next staged run:
  - Miura: continue from `StartIndex 27`
  - TMP: continue from `StartIndex 2004`
- Re-run `build_curve_dataset_npz.py --allow-partial` after each staged batch.
