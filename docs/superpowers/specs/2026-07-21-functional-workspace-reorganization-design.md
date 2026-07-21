# Functional Workspace Reorganization

## Goal

Organize the `small++` workspace by function without deleting original source,
data, models, reports, or the user's existing uncommitted work. Consolidate
scratch material, logs, and Python bytecode under one ignored workspace cache.

## Scope

### Cache and transient material

Create a root-level `.workspace_cache/` directory and ignore it in Git.

- `scratch/` receives the existing root `tmp/` material.
- `logs/` receives historical run logs and standalone training logs that are
  not source or published evidence.
- `bytecode/` receives the existing `__pycache__` trees. Future bytecode is
  directed there by the validation commands when possible; Python may recreate
  local bytecode during ordinary interactive runs.

No files are deleted. Existing historical logs are moved intact with their
relative source paths encoded beneath `.workspace_cache/logs/`.

### Source layout

Keep `origami_experiments/` as the package root and introduce these functional
areas:

```text
origami_experiments/
  models/                 # former modules/ neural-network definitions
  workflows/
    data/                 # data preparation and split creation
    training/             # model-training entry points
    evaluation/           # model evaluation and loading smoke checks
    analysis/             # audit, summary, and showcase utilities
    publishing/           # report, slide, and checkpoint-export utilities
  curve_dataset/
    probes/snap_probe/    # reusable nonlinear-curve exploratory experiment
  tests/
```

`curve_dataset/` remains a distinct functional subsystem. Its self-contained
`snap_probe` experiment moves to `curve_dataset/probes/snap_probe/` rather
than to the cache because it contains source, MATLAB tooling, and validation
plans in addition to generated results.

## Compatibility and safety

- All source relocation is performed as a move, preserving file content and
  Git rename detection. No algorithmic changes are in scope.
- Imports change from the former `modules` package to the new `models` package
  and use package-root imports so module execution is reliable from the repo
  root.
- Script-internal path constants are updated only where a move changes their
  semantic location. README commands and the training shell entry point are
  updated to the new paths.
- Existing uncommitted changes are neither reset nor overwritten. The final
  Git diff is inspected to ensure all moved content remains present.

## Validation

1. Record a before/after inventory of moved paths and file hashes.
2. Search for stale `modules`, old workflow script paths, and old
   `snap_probe` paths.
3. Compile moved Python sources with bytecode directed to `.workspace_cache`.
4. Run the repository's lightweight import/shape tests where dependencies are
   available.
5. Confirm the cache is ignored and that no tracked source or user-modified
   content was removed.

## Out of scope

- Deleting data, checkpoints, reports, figures, or historical experimental
  outputs.
- Changing model behavior, data processing, or experiment configuration.
- Moving the third-party `external/` repositories.
