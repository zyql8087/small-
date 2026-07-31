---
name: executing-research-experiments
description: Use when planning, implementing, running, handing off, or reviewing Paper A research tasks involving MATLAB geometry, Abaqus simulation, datasets, machine learning, OOD or statistical evaluation, 3D printing, compression tests, experiment evidence, or milestone acceptance.
---

# Executing Research Experiments

## Overview

Execute Paper A work as an auditable chain from an approved requirement to direct evidence. Preserve scientific meaning, isolate authorized changes, and make every acceptance decision reproducible.

**Core principle:** Evidence must be direct, requirement-specific, and independently reproducible.

```text
implemented != verified != accepted
```

Never collapse these states. Future-milestone code does not satisfy the current task and does not pre-accept a later task.

## Before Work

1. Read the task brief, approved specification, scientific contract, active configuration, adjacent implementation, and recent commits before planning edits.
2. Discover available facts from the repository before asking questions. Record exact source paths and revisions.
3. Run `git status --short`; identify every dirty file. Preserve user and unrelated changes. Do not overwrite, reformat, stage, or clean them.
4. Resolve authority in this order unless the task contract states otherwise: approved specification and scientific contract, task brief, active configuration, accepted interfaces, adjacent implementation, comments or prior reports.
5. If authoritative sources conflict on scientific meaning, stop scientific implementation, quote the conflict, and request a decision.
6. Build and maintain a requirement-to-implementation-to-verification table before editing:

| Requirement ID | Authority | Implementation path/symbol | Verification command | Direct evidence | State |
|---|---|---|---|---|---|
| `REQ-001` | approved specification section 2.1 | `src/module.m:functionName` | `powershell -File tests/run.ps1` | `logs/REQ-001.txt`; exit `0` | verified |

7. For a behavioral change (new feature, bug fix, or behavioral refactor), run a focused baseline that fails for the correct missing behavior. Capture the command, version, exit code, and failure text; a crash, environment error, or unrelated failure is invalid. For planning, review, handoff, read-only diagnosis, or verification of existing results, capture applicable current-state baseline evidence; it may succeed or only produce observations. Never manufacture a failure.

## Task Contract

Write the contract in the task record before implementation. Include all fields below; use repository evidence first and mark unresolved fields explicitly.

| Contract field | Required content |
|---|---|
| Identity | Task ID, task type, and milestone |
| Scope | Goal and explicit non-goals |
| Authorization | Allowed paths, allowed Git actions, and protected changes |
| Authority | Source precedence and conflict owner |
| Data contract | Inputs, outputs, schema, units, coordinates, naming, and serialization |
| Constraints | Parameter domain, dataset, randomness/seeds, hardware, software, and versions |
| Interfaces | Shape, type, ordering, sign, tolerance, compatibility, and other invariants |
| Acceptance | Requirement matrix, exact commands, expected results, and required evidence |
| Prohibitions | Forbidden shortcuts, proxy claims, and out-of-scope changes |
| Handoff | Artifacts, raw logs, reviewer needs, unresolved issues, and Git state |

Do not change formulas, units, coordinate systems, parameter domains, data splits, or thresholds without explicit authority. If authorization is absent, preserve them exactly and report the limitation.

## Execution Gates

Proceed only when the current gate is satisfied.

1. **Contract gate:** Scope, authorities, invariants, acceptance evidence, and authorized paths are explicit.
2. **Isolation gate:** Dirty-worktree ownership is understood and unrelated changes are protected.
3. **Traceability gate:** Every requirement has an implementation location and a direct verification method.
4. **Baseline gate:** For a behavioral change, the focused baseline fails for the intended missing behavior before implementation, and the same check passes after it. For planning, review, handoff, read-only diagnosis, or verification of existing results, capture applicable current-state baseline evidence; success or observation-only output is valid. Never manufacture a failure.
5. **Implementation gate:** Make the smallest authorized change; keep configuration and scientific assumptions visible.
6. **Diagnosis gate:** When results differ from expectations, diagnose the root cause from raw inputs, intermediates, logs, and versions. Do not edit tests or relax thresholds merely to obtain green output.
7. **Validation gate:** Complete the applicable validation matrix and record raw evidence.
8. **Review gate:** Pass Stage 1 before Stage 2. Do not accept with unresolved Critical or Important findings.
9. **Handoff gate:** Load `references/review-and-git.md`, reconcile the traceability table, and report exact repository state.

## Validation Matrix

Run every applicable class. Mark a class `N/A` only with a contract-based reason and reviewer agreement.

| Class | Required question and evidence |
|---|---|
| Normal | Do representative in-domain inputs produce the specified schema, behavior, and metrics? |
| Boundary | Do extrema, empty/minimal cases, tolerances, and domain boundaries behave explicitly? |
| Invalid | Are malformed, nonphysical, out-of-range, missing, and incompatible inputs rejected clearly? |
| Determinism | With locked seeds, versions, hardware policy, and inputs, are outputs repeatable within approved tolerance? |
| Regression | Do previously accepted cases and interfaces remain unchanged where required? |
| Scientific-numerical | Do units, coordinates, signs, conservation/symmetry, convergence, and numerical anchors match the contract? |
| Tool-quality | Do linters, schema checks, build/import checks, `git diff --check`, and artifact integrity checks pass? |

Record the exact command, tool version, exit code, pass/fail/skip counts, numerical anchors with tolerances, and output paths for each row.

## Two-Stage Review

Classify every finding as **Critical**, **Important**, or **Minor**. The implementer's self-review supplements but never replaces an independent reviewer.

### Stage 1: Specification Compliance

Review the approved requirements against the traceability table and changed behavior. Verify scope, authorities, contracts, invariants, acceptance mapping, and forbidden shortcuts. Stop while any Critical or Important finding remains unresolved; do not begin quality acceptance.

### Stage 2: Evidence and Quality

Independently rerun the acceptance commands from a known state. Inspect raw logs and artifacts, numerical results, test quality, maintainability, reproducibility, and Git cleanliness. Record reviewer identity/context, versions, commands, exit codes, statistics, artifact hashes, and findings.

Only explicit reviewer conclusions backed by direct evidence may change a requirement state to accepted.

## Domain Routing

Load every reference whose signals apply; multiple signals require multiple references. Keep domain detail in the references. Before every handoff, always load `references/review-and-git.md`.

| Signals | Load |
|---|---|
| MATLAB / implicit surface / TPMS / mesh / STL / descriptor | `references/matlab-geometry.md` |
| Abaqus / CAE / INP / ODB / HPC / convergence | `references/abaqus-simulation.md` |
| dataset / split / duplicate / leakage / provenance | `references/dataset-quality.md` |
| GNN / Transformer / Diffusion / training / checkpoint | `references/machine-learning.md` |
| ablation / OOD / robustness / uncertainty / statistics | `references/evaluation-statistics.md` |
| printing / specimen / compression / testing machine | `references/physical-experiments.md` |
| review / acceptance / handoff / commit | `references/review-and-git.md` |

Retain these cross-domain safeguards while routing details:

- Prevent structure-level leakage. Row-level disjointness is insufficient when structures, parents, augmentations, specimens, or derived records are related.
- Define and freeze the OOD axis and separation rule before evaluation. Randomly selected rows are not OOD evidence.
- Preserve Abaqus solver/job logs and raw outputs. An ODB alone is not convergence or correctness evidence.
- Treat a single specimen as a single observation, not repeatability evidence. Preserve raw force-displacement data, specimen metadata, exclusions, and processing history; a smoothed curve is not raw evidence.

## Stop Conditions

Stop, preserve evidence, and report instead of improvising when:

- authoritative scientific sources conflict;
- required inputs, units, coordinate definitions, schemas, provenance, or permissions are missing;
- the requested edit exceeds authorized paths, Git actions, or milestone scope;
- the worktree contains overlapping changes whose ownership cannot be established;
- for a behavioral change, the expected failing baseline is absent, irrelevant, or caused by the environment; or, for planning, review, handoff, read-only diagnosis, or verification of existing results, applicable current-state baseline evidence was not captured;
- data leakage, invalid OOD construction, corrupted artifacts, nonconvergence, or irreproducibility is suspected;
- a formula, threshold, split, or acceptance criterion would need unauthorized alteration;
- Critical or Important review findings remain open;
- required commands, raw logs, versions, exit codes, statistics, artifacts, or direct evidence cannot be produced.

## Evidence and Definition of Done

Completion requires one evidence bundle containing:

- change summary linked to requirement IDs;
- raw commands, tool/software versions, full logs, and exit codes;
- test totals with pass, fail, and skip counts for every validation class;
- scientific numerical anchors, units, expected values, actual values, and tolerances;
- artifact paths, sizes where relevant, and cryptographic hashes;
- unresolved items, assumptions, deviations, and their authorization status;
- fresh `git diff --check`, `git status --short`, and scoped diff results;
- Stage 1 and Stage 2 conclusions, finding severities, reviewer context, and direct acceptance mapping.

The following are not completion evidence: code written, script finished, file generated, tests should pass.

A downstream artifact does not prove an upstream milestone. A solid volume does not prove that the scalar-field contract was exposed, independently tested, or accepted.

Saying evidence is missing and then marking the task complete is still false acceptance.

Never infer acceptance transitively; map direct evidence to every accepted requirement.

## Red Flags and Rationalization Counters

| Red flag | Counter-action |
|---|---|
| "tests should pass" | Run the exact tests and report fresh totals and exit codes. |
| "an ODB exists" | Inspect convergence, solver/job logs, fields, and contract-specific outputs. |
| "curve looks smooth" | Inspect raw data, processing history, replicates, units, and quantitative checks. |
| "best seed is enough" | Apply the predeclared seed and aggregation policy; report all required runs. |
| "random rows are OOD" | Enforce the frozen OOD definition and separation evidence. |
| "change threshold until green" | Diagnose the discrepancy; change criteria only with explicit authority. |
| "ignore dirty files" | Identify ownership and protect unrelated work before editing or staging. |
| "future code already exists" | Verify and accept only the current milestone's direct requirements. |
| "previous agent says tests pass" | Independently rerun commands and inspect raw evidence. |
| "the file/artifact exists" | Validate content, provenance, hashes, numerical anchors, and requirement mapping. |
| "self-review found no issues" | Obtain both review stages; self-review cannot confer acceptance. |

Any red flag means pause the acceptance claim, return to the relevant gate, and produce direct evidence.
