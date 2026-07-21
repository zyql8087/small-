# Snap-Probe Simulation Report

Run window: 2026-06-29 to 2026-06-30 local time.

## Executive Decision

Do not retrofit the production Miura curve generator yet.

The corrected DC probes fail the diversity gate. MGDCM produces a raw PASS, but the margin is small and several nonlinear labels are driven by numerical-scale artifacts. Treat MGDCM as a provisional source of candidate curves for Abaqus validation, not as sufficient evidence for full dataset generation.

## Tool Fixes Made Before Final Classification

- `detect_curve_diversity.py`: fixed `snap_back` detection so monotone motion in the negative coordinate direction is not mislabeled as displacement reversal.
- `select_abaqus_validation_samples.py`: fixed validation selection so it only picks samples with completed probe labels and fills to the requested `--n-samples` count when enough labeled samples exist.

Regression tests:

```powershell
& 'F:\Anaconda\envs\GMM\python.exe' -m unittest test_detect_curve_diversity.py test_select_abaqus_validation_samples.py
```

Result: 3 tests passed.

## Probe Runs

### DC, LambdaBar=0.5

Output: `raw_curves/`

- Attempted rows: 1-50
- Completed sample CSVs: 49
- Timeout: `miura_00013`
- Classified curves: 294
- Interesting fraction: 4.1%
- Result: FAIL

Summary: `raw_curves/curve_diversity_summary.json`

### DC, LambdaBar=1.0

Output: `raw_curves_lambda1/`

- Attempted rows: 1-50
- Completed sample CSVs: 45
- Timeouts: `miura_00013`, `miura_00019`, `miura_00023`, `miura_00038`, `miura_00050`
- Classified curves: 270
- Interesting fraction: 10.0%
- Result: FAIL

Summary: `raw_curves_lambda1/curve_diversity_summary.json`

### MGDCM, LambdaBar=0.5, IterMax=80

Output: `raw_curves_mgdcm/`

- Attempted rows: 1-50
- Completed sample CSVs: 49
- Timeout: `miura_00013`
- Classified curves: 294
- Raw interesting fraction: 25.85%
- Raw result: PASS
- Sanity-filtered result with max absolute signed displacement <= 0.5 m: 22.97%

Raw summary: `raw_curves_mgdcm/curve_diversity_summary.json`

Sanity summary: `raw_curves_mgdcm/curve_diversity_summary_sanity_cap_0p5m.json`

## Caveat

MGDCM creates some apparent snap-back and plateau curves, but visual and range audits show numerical spikes and very large forces in part of the nonlinear set. This is exactly the class of result that needs Abaqus validation before any production retrofit or large-scale dataset generation.

## Abaqus Validation Artifacts

Generated from the MGDCM per-curve labels:

- `abaqus_validation/abaqus_validation_manifest.csv`: 10 samples x 4 conditions = 40 curves
- `abaqus_validation/abaqus_validation_plan.md`

The manifest should be treated as a high-fidelity validation queue, not as proof that SWOMPS/MGDCM curves are already physically reliable.

## Representative Figures

Generated under `representative_curves_mgdcm/`:

- `miura_00047_curve3_monotone_hardening.png`
- `miura_00005_curve1_monotone_softening.png`
- `miura_00014_curve4_plateau.png`
- `miura_00050_curve2_snap_back.png`
