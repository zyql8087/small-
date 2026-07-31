# Task Brief: EXAMPLE-001

This is a non-acceptable template example. After copying, replace every `EXAMPLE` value, `SNAPSHOT` value, and zero hash with task-specific evidence before dispatch or review.

## Identity

- Task ID: EXAMPLE-001
- Task title: Demonstrate the research-task contract
- Milestone: example
- Task type: example
- Task owner: example-owner
- Execution context: isolated worktree
- Authorized Git action: none
- Contract status: template example; not eligible for acceptance
- Review target mode: dirty_snapshot
- Implementation snapshot ID: SNAPSHOT-EXAMPLE-001
- Snapshot definition: full binary patches, authorized untracked objects, and a content-hashed reconstruction manifest

## Goal

Demonstrate a bounded task whose implementation and acceptance can be traced to direct evidence.

## Non-goals

- Do not modify files outside the declared scope.
- Do not change scientific definitions, thresholds, splits, or interfaces.
- Do not claim acceptance from file existence, process completion, or downstream artifacts.
- Do not commit, push, clean, restore, or rewrite history.

## Authority and Precedence

| Priority | Authority ID | Source | Immutable identity | Governs |
|---:|---|---|---|---|
| 1 | AUTH-001 | Current user instruction | recorded task message | Scope and authorization |
| 2 | AUTH-002 | Approved project specification | `docs/specification.md` | Required behavior and acceptance |
| 3 | AUTH-003 | Scientific contract | `configs/scientific-contract.yaml` | Formulae, units, domains, and tolerances |
| 4 | AUTH-004 | Existing implementation | base repository revision recorded in the snapshot reconstruction manifest | Compatibility and current interfaces |

- Conflict owner: example-owner
- Conflict rule: stop scientific implementation, quote the conflicting sources, and request a decision.
- Known authority conflicts: none recorded

## Inputs and Allowed Paths

### Input Contract

| Input ID | Path or identity | SHA-256 | Schema or format | Units | Access |
|---|---|---|---|---|---|
| INPUT-001 | `path/to/input` | `0000000000000000000000000000000000000000000000000000000000000000` | example-schema 1.0 | dimensionless | read |

### Path Authorization

| Path | Allowed action | Ownership | Protection rule |
|---|---|---|---|
| `path/to/input` | read | project input | Do not edit or overwrite |
| `path/to/output` | modify and generate | task change | Keep changes inside this exact path |
| `delivery/evidence-report.md` | generate | task change | Create only the task-specific evidence report |
| `delivery/review-ledger.md` | generate | task change | Create only the task-specific review ledger |
| `delivery/experiment-manifest.yaml` | generate | task change | Create only the task-specific manifest |
| `path/to/protected` | none | user pre-existing | Do not edit, stage, clean, or use as task evidence |

## Scientific and Interface Invariants

| Invariant ID | Required invariant | Authority | Verification evidence |
|---|---|---|---|
| INV-001 | Units, coordinates, parameter domains, and schema remain unchanged. | AUTH-003 | EVD-ANCHOR-001 |
| INV-002 | Inputs and outputs preserve stable sample and causal-group identities. | AUTH-002 | EVD-TRACE-001 |
| INV-003 | Every numeric output is finite and uses the declared shape and dtype. | AUTH-002 | EVD-TEST-001 |
| INV-004 | Random behavior uses the declared seeds or recorded replay state. | AUTH-002 | EVD-DETERMINISM-001 |

## Constraints and Frozen Decisions

- Parameter domain: example scalar in the closed interval 0 to 1
- Dataset identity: example-dataset 1.0
- Split-manifest identity: `0000000000000000000000000000000000000000000000000000000000000000`
- Causal grouping rule: one base structure remains in one partition
- OOD definition: no OOD claim is in scope
- Random seeds: 0
- Software environment: example 1.0
- Hardware envelope: one CPU, 1 GB memory, 10 minutes wall time
- Numerical tolerance: absolute error at most 1e-8
- Frozen metric: absolute error in dimensionless units, aggregated per independent sample
- Failure and exclusion rule: retain and report every failed case; no outcome-based exclusion

## Required Outputs

| Output ID | Path | Format | Required identity or content | Required evidence |
|---|---|---|---|---|
| OUTPUT-001 | `path/to/output` | example-format 1.0 | Finite value linked to INPUT-001 | EVD-TEST-001 |
| OUTPUT-002 | `delivery/evidence-report.md` | Markdown | Complete executor evidence record | EVD-HANDOFF-001 |
| OUTPUT-003 | `delivery/review-ledger.md` | Markdown | Two-stage independent review record | EVD-REVIEW-001 |
| OUTPUT-004 | `delivery/experiment-manifest.yaml` | YAML | Machine-readable run identity and provenance | EVD-MANIFEST-001 |

## Requirement Traceability

| Requirement ID | Authority | Required behavior | Implementation location | Direct verification | Initial state |
|---|---|---|---|---|---|
| REQ-001 | AUTH-002 | Produce the declared finite output without changing the input. | `path/to/output` | `command --example` and raw log | planned |
| REQ-002 | AUTH-003 | Preserve the scientific and interface invariants. | `path/to/output` | Numerical anchor and schema check | planned |
| REQ-003 | AUTH-001 | Restrict changes and Git actions to the authorized scope. | Repository worktree | Scoped status and diff evidence | planned |

## Acceptance Matrix

| Requirement ID | Validation class | Verification command or evidence | Expected result | Required record |
|---|---|---|---|---|
| REQ-001 | Normal | `command --example` | Exit 0; one finite schema-valid output | Raw stdout, stderr, exit code, and counts |
| REQ-002 | Boundary | Contract-defined lower and upper input anchors | Both anchors meet the approved tolerance | Inputs, expected and observed values, units, and differences |
| REQ-002 | Invalid | Nonfinite and out-of-domain input checks | Each invalid input is rejected diagnostically | Exception type, message, and raw log |
| REQ-002 | Determinism | Repeat `command --example` with seed 0 | Outputs match under the frozen comparison policy | Output hashes and numerical comparison |
| REQ-003 | Regression | Approved regression command | Previously accepted behavior remains passing | Test totals and raw log |
| REQ-003 | Tool quality | `git diff --check` | Exit 0 with no whitespace errors | Command output and exit code |

## Baseline Requirement

- Baseline type: behavioral-change RED baseline
- Baseline command: `command --example`
- Required baseline behavior: fail for the intended missing behavior before implementation, not because of environment or unrelated errors
- Required capture: working directory, exact command, environment, exit code, raw stdout and stderr, and diagnosis

## Forbidden Shortcuts

- Do not alter tests, thresholds, formulas, units, splits, metrics, or expected results merely to force a pass.
- Do not catch and discard errors or omit failed, invalid, excluded, interrupted, or nonfinite cases.
- Do not use a selected best seed, smooth curve, ODB existence, file existence, or downstream artifact as transitive proof.
- Do not infer OOD from random held-out rows.
- Do not use final-test information for tuning or post-access selection.
- Do not stage broad path sets or include user, unrelated, cache, credential, or bulk-generated files.

## Stop and Escalation Conditions

- Stop if authority sources conflict or a required scientific definition is missing.
- Stop if dirty-worktree ownership overlaps the task and cannot be established.
- Stop if the baseline fails for an unrelated reason or the required direct evidence cannot be produced.
- Stop if authorization, immutable identities, provenance, units, split rules, or acceptance criteria are ambiguous.
- Stop acceptance while any Critical or Important finding remains open.
- Preserve raw diagnostics, failed attempts, and partial artifacts when stopping.

## Handoff Requirements

- Complete `evidence-report.md`, `experiment-manifest.yaml`, and `review-ledger.md` with task ID EXAMPLE-001.
- Separate observed facts, executor interpretations, and unresolved items.
- Provide exact commands, working directories, versions, resolved configuration, exit codes, raw logs, test counts, and durations.
- Provide scientific anchors, artifact identities, sizes where applicable, and SHA-256 hashes.
- Reconcile every requirement to direct implementation and verification evidence.
- Record every failure, anomaly, warning, retry, exclusion, and approved disposition.
- Record fresh `git status --short --untracked-files=all`, scoped diffs, and `git diff --check`.
- Obtain Stage 1 specification review before Stage 2 quality review.
- Bind any later review only to `SNAPSHOT-EXAMPLE-001`, reconstructed from its full binary patches, authorized untracked objects, and content-hashed reconstruction manifest; do not substitute a commit claim.

## Completion Definition

The executor may claim implementation and verification only for requirements supported by direct evidence. Independent acceptance requires both review stages, zero open Critical findings, zero open Important findings, and a final decision bound to the identified review target.
