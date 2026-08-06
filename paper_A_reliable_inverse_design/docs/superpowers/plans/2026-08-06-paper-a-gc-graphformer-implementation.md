# Paper A GC-GraphFormer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first verifiable Paper A algorithm milestone: a topology-bearing PyG graph contract, a deterministic geometry-only auxiliary-data generator, a GC-GraphFormer forward model, retained forward baselines, and a method-constrained diffusion interface.

**Architecture:** Add a focused `gc_graphformer/` Python package because the active M04 worktree contains no Small++, PyG, Graph Transformer, or diffusion source. The graph builder consumes compiler-produced padded parameters, profile-separated descriptors, and finite-difference sensitivities; the geometry generator consumes a compiler callback and provides only an explicitly labelled analytic smoke compiler. The model uses PyG `TransformerConv(edge_dim=...)`, strain-query cross-attention, and amplitude–shape reconstruction. M03/M04 MATLAB artifacts remain read-only dependencies and are represented by a validated callback contract.

**Tech Stack:** Python 3.9+, PyTorch, PyTorch Geometric, NumPy, standard-library `unittest` (pytest-compatible tests), JSON/NPZ, SHA-256.

**Authoritative inputs:** `docs/superpowers/specs/2026-07-28-paper-a-gc-graphformer-design.md`, `docs/superpowers/specs/2026-08-05-m04-dual-descriptors-abaqus-interface-design.md`, and `geometry_compiler_matlab/docs/SIMULATION_EXPERIMENT_MEMORY.md`.

---

## Task 1: Add the graph and method contracts

**Files:**
- Create: `gc_graphformer/__init__.py`
- Create: `gc_graphformer/contracts.py`
- Test: `tests/test_contracts.py`

- [ ] **Step 1: Write failing contract tests**

```python
def test_method_projection_enforces_m1_m2_m3():
    assert project_parameters("M1", [0.1, 0.12, 0.14, 7.0]).tolist() == [0.1, 0.12, 0.14, 0.0]
    assert project_parameters("M2", [0.1, 0.12, 0.14, 7.0]).tolist() == [0.12, 0.12, 0.12, 7.0]
    assert project_parameters("M3", [0.1, 0.12, 0.14, 7.0]).tolist() == [0.1, 0.12, 0.14, 7.0]

def test_curve_decomposition_reconstructs_twenty_points():
    curve = np.linspace(1.0, 20.0, 20)
    amplitude, shape = decompose_curve(curve)
    np.testing.assert_allclose(reconstruct_curve(amplitude, shape), curve)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `& 'F:\Anaconda\envs\GMM\python.exe' -m unittest discover -s tests -p 'test_contracts.py' -v`

Expected: collection fails because `gc_graphformer.contracts` does not exist.

- [ ] **Step 3: Implement the minimal contract layer**

Define the fixed method IDs, four padded parameter names, five descriptor names, 20 strain coordinates, profile IDs, method masks/bounds, differentiable parameter projection, finite-value validation, and amplitude/shape helpers. Keep `legacy_small` and `physical_m04` as distinct profile IDs.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the same unittest command. Expected: all contract tests pass.

- [ ] **Step 5: Commit**

```powershell
git add gc_graphformer tests/test_contracts.py
git commit -m "feat: add Paper A graph and curve contracts"
```

## Task 2: Implement the topology-bearing PyG graph builder

**Files:**
- Create: `gc_graphformer/graph_builder.py`
- Test: `tests/test_graph_builder.py`

- [ ] **Step 1: Write failing graph-contract tests**

Test that each graph has exactly 11 nodes; node types are method, four padded variables, five descriptors, and readout; M1/M2/M3 projections and active masks are preserved; M1 has 33 directed edges, M2 has 28, and M3 has 38; compiler edges point from active variable nodes to descriptor nodes; axial edges are bidirectional; readout edges point only to the readout node; all edge attributes are finite continuous tensors with the six compiler sensitivity fields; repeated construction is byte-equivalent; and `Batch.from_data_list` has no cross-graph edge.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `& 'F:\Anaconda\envs\GMM\python.exe' -m unittest discover -s tests -p 'test_graph_builder.py' -v`

Expected: import or attribute failures for the missing builder.

- [ ] **Step 3: Implement the graph builder**

Create a homogeneous `torch_geometric.data.Data` graph with fixed node ordering, explicit `node_type`, `edge_type`, and an eight-column continuous `edge_attr`. The first six edge columns are `[value, abs(value), sign, log1p(abs(value)), valid_mask, confidence]`; axial edges additionally use columns seven/eight for normalized axial separation and local control-field difference. Add compiler edges only for method-active variables, method-to-variable edges carrying validity/equality metadata, and one directed edge from every non-global node to the global readout node. Store `method_id`, `descriptor_profile_id`, `y_curve`, `y_descriptors`, masks, and provenance IDs as tensor attributes.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run: `& 'F:\Anaconda\envs\GMM\python.exe' -m unittest discover -s tests -p 'test_graph_builder.py' -v`

Expected: all graph schema, direction, determinism, constraints, and batch-isolation tests pass.

- [ ] **Step 5: Commit**

```powershell
git add gc_graphformer/graph_builder.py tests/test_graph_builder.py
git commit -m "feat: build compiler-informed PyG relation graphs"
```

## Task 3: Add the compiler callback and deterministic geometry-only shards

**Files:**
- Create: `gc_graphformer/compiler.py`
- Create: `gc_graphformer/geometry_dataset.py`
- Test: `tests/test_geometry_dataset.py`
- Create: `docs/geometry_only_dataset_contract.md`

- [ ] **Step 1: Write failing generator and manifest tests**

Test deterministic records for a fixed seed/config, profile separation, compiler/provenance hashes, no Abaqus marker, atomic shard reload, per-record hashes, and rejection of mixed `legacy_small`/`physical_m04` records. Test that the default smoke compiler is explicitly marked `synthetic_smoke` and never labelled high-fidelity mechanics.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `& 'F:\Anaconda\envs\GMM\python.exe' -m unittest discover -s tests -p 'test_geometry_dataset.py' -v`

Expected: collection fails because the compiler and shard generator do not exist.

- [ ] **Step 3: Implement the callback contract and smoke compiler**

Define a compiler protocol returning method, padded parameters, one descriptor profile, five finite descriptors, compiler sensitivities, geometry/feasibility flags, compiler version, and artifact hashes. Add a deterministic analytic `SyntheticM04Compiler` for tests only, marked `original_auxiliary_geometry_dataset`, `mechanical_labels: false`, `abaqus_executed: false`, and `compiler_mode: synthetic_smoke`. The production path must accept an injected M03/M04 callback and reject unverified profile payloads.

- [ ] **Step 4: Implement deterministic generation and NPZ shards**

Use `numpy.random.Generator(PCG64(seed))`, deterministic method sampling, canonical JSON SHA-256, config/compiler/profile hashes, ordered record hashes, and `manifest.json` plus compressed `shard-XXXX.npz` files. The loader verifies manifest hash, shard hash, record count, profile homogeneity, and provenance before returning records. Do not commit generated data.

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run the same unittest command. Expected: all manifest, determinism, shard, and profile-isolation tests pass.

- [ ] **Step 6: Commit**

```powershell
git add gc_graphformer/compiler.py gc_graphformer/geometry_dataset.py tests/test_geometry_dataset.py docs/geometry_only_dataset_contract.md
git commit -m "feat: add deterministic geometry-only auxiliary dataset contract"
```

## Task 4: Implement GC-GraphFormer and retained baselines

**Files:**
- Create: `gc_graphformer/model.py`
- Create: `gc_graphformer/baselines.py`
- Test: `tests/test_model.py`
- Test: `tests/test_baselines.py`

- [ ] **Step 1: Write failing model tests**

Test primary-model output shape `[batch, 20]`, finite values, gradient flow through node and edge inputs, deterministic evaluation with dropout disabled, amplitude/shape auxiliary outputs, one-step loss decrease on a tiny repeated sample, and construction of a parameter-matched fully-connected PyG graph baseline.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `& 'F:\Anaconda\envs\GMM\python.exe' -m unittest discover -s tests -p 'test_model.py' -v; & 'F:\Anaconda\envs\GMM\python.exe' -m unittest discover -s tests -p 'test_baselines.py' -v`

Expected: import failures for the model modules.

- [ ] **Step 3: Implement the GC-GraphFormer encoder and decoder**

Use three residual `TransformerConv(edge_dim=8)` blocks with four heads, LayerNorm, GELU feed-forward layers, and dropout 0.1. Add node-type embeddings, dense-batch graph states, strain-query embeddings for the fixed 20 coordinates, cross-attention to graph nodes, a positive global-node amplitude head, and a non-negative unit-RMS shape head. Return `curve` and optional amplitude/shape/latent diagnostics without imposing monotonicity.

- [ ] **Step 4: Implement the parameter-matched fully-connected ablation and historical baselines**

Use the same encoder/decoder dimensions for `FullyConnectedPyGGraphTransformer`, but rebuild per-graph all-pairs edges with constant all-ones edge attributes. Separately implement `ResMLPBaseline`, `ParameterTokenTransformerBaseline`, and `DenseAllOnesGATBaseline`; label the last one as a dense all-ones baseline, never as learned physical topology.

- [ ] **Step 5: Run model and baseline tests**

Run the focused command from Step 2. Expected: all shape, gradient, determinism, and tiny overfit tests pass.

- [ ] **Step 6: Commit**

```powershell
git add gc_graphformer/model.py gc_graphformer/baselines.py tests/test_model.py tests/test_baselines.py
git commit -m "feat: implement GC-GraphFormer and retained forward baselines"
```

## Task 5: Add the conditional-diffusion boundary interface

**Files:**
- Create: `gc_graphformer/diffusion_interface.py`
- Test: `tests/test_diffusion_interface.py`

- [ ] **Step 1: Write failing interface tests**

Test method-conditioned inputs containing the target 20-point curve, response descriptors, method token, and variable-validity mask; padded output shape `[batch, 4]`; differentiable training-time projection; exact M1 `w=0`, M2 `c0=c1=c2`, and M3 identity constraints; and bound validation for open `(2, 8)` widths.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `& 'F:\Anaconda\envs\GMM\python.exe' -m unittest discover -s tests -p 'test_diffusion_interface.py' -v`

Expected: missing-module failures.

- [ ] **Step 3: Implement the interface only**

Provide condition construction and a differentiable `project_padded_parameters`/`validate_padded_parameters` pair. Do not add DiT, RL, MCTS, gradient-guided diffusion, or large-scale retraining. Make decoder projection and training projection use the same contract.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the same unittest command. Expected: all interface tests pass.

- [ ] **Step 5: Commit**

```powershell
git add gc_graphformer/diffusion_interface.py tests/test_diffusion_interface.py
git commit -m "feat: add method-constrained diffusion boundary interface"
```

## Task 6: Documentation, imports, and milestone verification

**Files:**
- Modify: `gc_graphformer/__init__.py`
- Create: `docs/superpowers/reports/2026-08-06-paper-a-gc-graphformer-milestone.md`

- [ ] **Step 1: Add public exports and usage commands**

Export graph/model/generator/interface entry points and document the exact smoke commands, compiler callback boundary, `physical_m04` versus `legacy_small` profile rule, and next-stage geometry-pretraining resource estimate without claiming mechanics evidence.

- [ ] **Step 2: Run fresh verification**

Run, using the GMM environment:

```powershell
& 'F:\Anaconda\envs\GMM\python.exe' -m compileall -q gc_graphformer tests
& 'F:\Anaconda\envs\GMM\python.exe' -m unittest discover -s tests -p 'test_*.py' -v
& 'F:\Anaconda\envs\GMM\python.exe' -c "import gc_graphformer; print(gc_graphformer.__all__)"
```

Also run a fresh graph Batch isolation and forward/backward smoke command, then `git diff --check`, `git status --short`, and `git log --oneline -8`.

- [ ] **Step 3: Record evidence and known boundaries**

Record exact test counts and environment versions, state that MATLAB/Abaqus and the absent legacy algorithm sources were not run, and list the next geometry-pretraining command as a dry-run recipe rather than starting a 10k/50k/100k generation.

- [ ] **Step 4: Commit the report**

```powershell
git add docs/superpowers/reports/2026-08-06-paper-a-gc-graphformer-milestone.md gc_graphformer/__init__.py
git commit -m "docs: record first GC-GraphFormer algorithm milestone"
```

## Self-review checklist

- [ ] Every approved A–D requirement maps to a task above.
- [ ] Graphs contain real compiler, axial, method, and readout relations; no nine-column wrapper is used.
- [ ] `legacy_small` and `physical_m04` are profile-separated and cannot be mixed by the loader.
- [ ] Geometry-only data are labelled auxiliary and non-mechanical; no Abaqus path exists in the generator.
- [ ] GC-GraphFormer defaults to edge-aware `TransformerConv`; the dense all-ones graph is an explicit ablation.
- [ ] The diffusion work is an interface-only, method-constrained padded-vector contract.
- [ ] No formal Abaqus runs, large dataset generation, checkpoints, STL files, or caches are produced.
