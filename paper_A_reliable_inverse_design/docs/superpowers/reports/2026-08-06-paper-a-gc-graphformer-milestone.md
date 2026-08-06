# Paper A GC-GraphFormer first algorithm milestone

Date: 2026-08-06 (Asia/Shanghai)

## Delivered

The isolated branch `codex/paper-a-gc-graphformer` now contains a runnable
Python contract layer because this worktree had no Small++, PyG, Graph
Transformer, or diffusion implementation to extend.

- `gc_graphformer/graph_builder.py` builds a real homogeneous PyG `Data` graph
  with exactly 11 semantic nodes, explicit `node_type`/`edge_type`, continuous
  eight-column edge attributes, compiler finite-difference edges, bidirectional
  axial edges, method-to-variable constraint edges, and directed readout edges.
  It projects M1/M2/M3 parameters and preserves profile IDs.
- `gc_graphformer/compiler.py` defines the read-only M03/M04 callback contract
  and finite/one-sided sensitivity calculation. `SyntheticM04Compiler` is a
  deterministic smoke fixture only; it is labelled `synthetic_smoke` and never
  runs Abaqus.
- `gc_graphformer/geometry_dataset.py` writes canonical JSON records into
  compressed NPZ shards with seed/config/compiler/profile/record/shard/manifest
  SHA-256 provenance. The loader refuses profile mixing, tampering, path escape,
  solver-ready claims, and mechanics/Abaqus claims.
- `gc_graphformer/model.py` implements GC-GraphFormer with edge-aware
  `TransformerConv(edge_dim=8)`, strain-query cross-attention, positive
  amplitude and non-negative unit-RMS shape decoding, plus the
  parameter-matched fully-connected all-ones PyG ablation.
- `gc_graphformer/baselines.py` retains explicit ResMLP, parameter-token
  Transformer, and dense all-ones GAT baselines. The dense GAT is labelled as a
  baseline, not physical topology.
- `gc_graphformer/diffusion_interface.py` defines only the method-conditioned
  interface and differentiable padded `[c0,c1,c2,w]` projection. M1/M2/M3
  constraints and the open `(2,8)` width interval are enforced in both training
  projection and decode projection.

`legacy_small` and `physical_m04` remain separate profile identifiers. The
geometry-only records are explicitly `original_auxiliary_geometry_dataset` with
`mechanical_labels=false`, `abaqus_executed=false`, and `solver_ready=false`.

## Verification evidence

Environment: `F:\Anaconda\envs\GMM\python.exe`, Python 3.9.25, Torch 2.7.0+cu128,
PyG 2.6.1. The base Anaconda Python had a Torch DLL initialization failure, so
all Torch/PyG verification used the working GMM environment; no dependency was
downloaded.

Commands and results:

```text
python -m compileall -q gc_graphformer tests                 exit 0
python -m unittest discover -s tests -p 'test_*.py' -v       23 tests, 0 failures
import + Batch isolation + forward/backward smoke            output shape (2, 20), gradients present
git diff --check                                             exit 0
```

The focused tests cover graph counts/directions/attributes, method constraints,
determinism, PyG Batch isolation, geometry manifest recovery and profile
separation, model shape/gradient/determinism/one-step overfit behavior, the
retained baselines, and diffusion interface constraints.

## Boundaries and known limitations

- The active repository did not contain the legacy algorithm source, Small
  workbook loader, or diffusion training code; this milestone supplies stable
  adapters and baselines rather than claiming to reproduce unavailable code.
- The synthetic compiler is not M03/M04 scientific geometry and must not be
  used for mechanics claims. Production generation must inject a validated
  MATLAB M03/M04 callback and retain its hashes.
- No MATLAB compiler run, Abaqus run, volume mesh, STL, checkpoint, formal
  10k/50k/100k dataset, 225-run budget, or physical experiment was started.
- Pytest is not installed in the GMM environment; tests use standard-library
  `unittest` and remain pytest-compatible.

## Next-stage dry-run command and resource estimate

For a contract-only smoke shard, run from the repository root:

```powershell
& 'F:\Anaconda\envs\GMM\python.exe' -c "from pathlib import Path; from gc_graphformer import SyntheticM04Compiler, GeometryOnlyGenerator, write_dataset; c=SyntheticM04Compiler(profile='physical_m04'); r=GeometryOnlyGenerator(c, seed=20260806, profile='physical_m04').generate(32); write_dataset(Path('external_smoke_geometry_32'), r, seed=20260806, profile='physical_m04', shard_size=16)"
```

Delete that external smoke directory after inspection; it is intentionally not
tracked. For physical geometry pretraining, replace the synthetic compiler with
the authenticated M03/M04 callback, begin with 10k, and gate 50k/100k only after
hash, storage, and acceptance review. The finite-difference contract requires
approximately 5, 7, or 9 compiler evaluations per M1, M2, or M3 sample
respectively (base plus valid central-difference sides; boundary fallbacks can
reduce this). A 50k run is therefore a compiler-throughput and storage task,
not a neural-network-only task. Planning estimate: 4–16 GB working storage for
50k compressed records plus temporary compiler artifacts, CPU parallelism subject
to MATLAB licensing, and one 12–24 GB GPU for the first graph pretraining smoke;
these are estimates, not measured performance claims.

