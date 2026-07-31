# Evidence Report: EXAMPLE-001

This is a non-acceptable template example. After copying, replace every `EXAMPLE` value, `SNAPSHOT` value, and zero hash with task-specific direct evidence before execution or review.

## Identity and Scope

- Task ID: EXAMPLE-001
- Task title: Demonstrate the research-task contract
- Milestone: example
- Task type: example
- Executor identity or context: example-agent in isolated worktree
- Evidence captured at: example timestamp; replace before use
- Review target mode: dirty_snapshot
- Implementation snapshot ID: SNAPSHOT-EXAMPLE-001
- Base repository revision for reconstruction: `0000000000000000000000000000000000000000`
- Full binary patch bundle: `delivery/snapshots/SNAPSHOT-EXAMPLE-001/full-binary.patch`
- Authorized untracked-object bundle: `delivery/snapshots/SNAPSHOT-EXAMPLE-001/authorized-untracked-objects/`
- Reconstruction manifest: `delivery/snapshots/SNAPSHOT-EXAMPLE-001/reconstruction-manifest.yaml`
- Snapshot definition: the three records above jointly and exclusively define the reviewed implementation state
- Authorized Git action: none
- In-scope paths: `path/to/output`, `delivery/evidence-report.md`, `delivery/review-ledger.md`, `delivery/experiment-manifest.yaml`
- Protected paths: `path/to/input`, `path/to/protected`
- Explicit non-goals: scientific-rule changes, threshold changes, split changes, commit, push, cleanup, and history rewriting

## Facts and Interpretations

### Observed Facts

| Fact ID | Direct source | Observation |
|---|---|---|
| FACT-001 | EVD-TEST-001 | The recorded command exited 0 and reported one passing check. |
| FACT-002 | EVD-ANCHOR-001 | The observed example value matched the expected value within 1e-8. |
| FACT-003 | EVD-GIT-001 | The scoped Git check reported no whitespace error. |

### Executor Interpretations

| Interpretation ID | Based on facts | Interpretation | Acceptance boundary |
|---|---|---|---|
| INFER-001 | FACT-001, FACT-002 | REQ-001 and REQ-002 appear verified at the recorded target. | Independent review is still required. |

## Unresolved issues

| Item ID | Type | Description | Impacted requirement or claim | Owner | Required resolution |
|---|---|---|---|---|---|
| UNRESOLVED-001 | future scope | Production-scale performance was not assessed. | Production performance claim | example-owner | Run the separately authorized production benchmark. |

## Authority Resolution

| Priority | Authority ID | Source | Immutable identity | Resolution |
|---:|---|---|---|---|
| 1 | AUTH-001 | Current user instruction | recorded task message | Applied to scope and Git authorization |
| 2 | AUTH-002 | Approved project specification | `docs/specification.md` | Applied to behavior and acceptance |
| 3 | AUTH-003 | Scientific contract | `configs/scientific-contract.yaml` | Applied to units, domain, and tolerance |

- Conflicts observed: none recorded
- Deviations authorized: none recorded

## Changed Files and Ownership

| Path | Ownership | Change summary | Requirement IDs | Allowed action |
|---|---|---|---|---|
| `path/to/output` | task change | Added the example output. | REQ-001, REQ-002 | modify and generate |
| `delivery/evidence-report.md` | task change | Recorded executor evidence and direct observations. | REQ-003 | generate |
| `delivery/review-ledger.md` | task change | Prepared the independent review record. | REQ-003 | generate |
| `delivery/experiment-manifest.yaml` | task change | Recorded machine-readable identity and provenance. | REQ-003 | generate |
| `path/to/input` | project input | No change observed. | REQ-001 | read only |
| `path/to/protected` | user pre-existing | Excluded from task evidence and left untouched. | REQ-003 | none |

## Environment

| Category | Name | Version or value | Identity evidence |
|---|---|---|---|
| Platform | Operating system | example OS 1.0 | EVD-ENV-001 |
| Runtime | Primary software | example 1.0 | EVD-ENV-001 |
| Hardware | Execution device | one CPU, 1 GB memory | EVD-ENV-001 |
| Configuration | Resolved configuration | `configs/example.yaml` | SHA-256 `0000000000000000000000000000000000000000000000000000000000000000` |
| Dataset | Dataset version | example-dataset 1.0 | SHA-256 `0000000000000000000000000000000000000000000000000000000000000000` |
| Split | Split manifest | grouped-example-split 1.0 | SHA-256 `0000000000000000000000000000000000000000000000000000000000000000` |
| Metric | Frozen metric | per-sample absolute error | EVD-CONFIG-001 |

- Random seeds or replay states: seed 0
- Determinism policy: identical input, configuration, software, and seed must reproduce the output hash
- Independent unit: one example sample
- Failure and exclusion policy: retain every attempt; no outcome-based exclusion
- Final-test access state: no locked final test accessed

## Baseline

- Baseline ID: BASELINE-001
- Baseline type: behavioral-change RED baseline
- Working directory: repository root
- Exact command: `command --example`
- Environment identity: EVD-ENV-001
- Exit code: 1
- Expected failure: missing example behavior
- Observed failure: command reported that example behavior was unavailable
- Failure attribution: intended missing behavior
- Raw stdout: `evidence/raw/baseline.stdout.log`
- Raw stderr: `evidence/raw/baseline.stderr.log`
- Baseline validity: valid focused failure

## Implementation Summary and Traceability

| Requirement ID | Implementation evidence | Verification evidence | State | Executor observation |
|---|---|---|---|---|
| REQ-001 | `path/to/output` | EVD-TEST-001 | verified | The declared normal case passed. |
| REQ-002 | `path/to/output` | EVD-ANCHOR-001, EVD-INVALID-001, EVD-DETERMINISM-001, EVD-TRACE-001 | verified | Schema, identity trace, anchor, invalid-input, and replay checks passed. |
| REQ-003 | Scoped worktree state | EVD-GIT-001, EVD-GIT-002 | verified | Scoped status and diff checks found no out-of-scope task change. |

Implementation was limited to the authorized output and delivery paths. Scientific definitions, thresholds, data splits, and protected files were not changed.

## Commands and exit codes

| Evidence ID | Validation class | Working directory | Exact command | Version or configuration | Exit code | Passed | Failed | Skipped | Duration | Raw log | Result |
|---|---|---|---|---|---:|---:|---:|---:|---|---|---|
| EVD-TEST-001 | Normal | repository root | `command --example` | example 1.0, seed 0 | 0 | 1 | 0 | 0 | 1 s | `evidence/raw/normal.log` | pass |
| EVD-BOUNDARY-001 | Boundary | repository root | `command --example-boundary` | example 1.0 | 0 | 2 | 0 | 0 | 1 s | `evidence/raw/boundary.log` | pass |
| EVD-INVALID-001 | Invalid | repository root | `command --example-invalid` | example 1.0 | 0 | 2 | 0 | 0 | 1 s | `evidence/raw/invalid.log` | pass |
| EVD-DETERMINISM-001 | Determinism | repository root | `command --example-replay --seed 0` | example 1.0, seed 0 | 0 | 1 | 0 | 0 | 1 s | `evidence/raw/determinism.log` | pass |
| EVD-REGRESSION-001 | Regression | repository root | `command --example-regression` | example 1.0 | 0 | 1 | 0 | 0 | 1 s | `evidence/raw/regression.log` | pass |
| EVD-GIT-001 | Tool quality | repository root | `git diff --check` | Git example | 0 | 1 | 0 | 0 | 1 s | `evidence/raw/git-diff-check.log` | pass |
| EVD-GIT-002 | Tool quality | repository root | `git status --short --untracked-files=all` | Git example | 0 | 1 | 0 | 0 | 1 s | `evidence/raw/git-status.log` | pass |

### Validation-Class Totals

| Class | Passed | Failed | Skipped | N/A basis |
|---|---:|---:|---:|---|
| Normal | 1 | 0 | 0 | not applicable |
| Boundary | 2 | 0 | 0 | not applicable |
| Invalid | 2 | 0 | 0 | not applicable |
| Determinism | 1 | 0 | 0 | not applicable |
| Regression | 1 | 0 | 0 | not applicable |
| Scientific-numerical | 1 | 0 | 0 | not applicable |
| Tool quality | 2 | 0 | 0 | not applicable |

## Numerical and Scientific Anchors

| Evidence ID | Anchor | Source | Input | Expected | Observed | Units | Tolerance | Difference | Decision |
|---|---|---|---|---:|---:|---|---:|---:|---|
| EVD-ANCHOR-001 | Asymmetric example anchor | AUTH-003 | example scalar 0.25 | 0.5 | 0.5 | dimensionless | 1e-8 absolute | 0 | pass |

## Artifacts and hashes

| Evidence ID | Artifact or log path | Kind | Parent identity | Size | SHA-256 | Direct observation |
|---|---|---|---|---:|---|---|
| EVD-ARTIFACT-001 | `path/to/output` | output | INPUT-001 and source commit | 1 byte | `0000000000000000000000000000000000000000000000000000000000000000` | Schema-valid finite example value |
| EVD-HANDOFF-001 | `delivery/evidence-report.md` | report | EXAMPLE-001 | 1 byte | `0000000000000000000000000000000000000000000000000000000000000000` | Evidence sections are present |
| EVD-MANIFEST-001 | `delivery/experiment-manifest.yaml` | manifest | EXAMPLE-001 | 1 byte | `0000000000000000000000000000000000000000000000000000000000000000` | Task and provenance fields are present |

Provenance chain: INPUT-001 → SNAPSHOT-EXAMPLE-001 and resolved configuration → EVD-TEST-001 → EVD-ARTIFACT-001.

## Failures, Warnings, Anomalies, and Exclusions

| Record ID | Attempt or artifact | Classification | Direct evidence | Diagnosis | Disposition | Retained evidence |
|---|---|---|---|---|---|---|
| EVENT-001 | BASELINE-001 | expected baseline failure | baseline raw logs and exit 1 | Intended behavior was not implemented at baseline | Closed by the verified implementation | Both baseline logs retained |
| EVENT-002 | Production benchmark | not run | task scope | Outside the current milestone | Remains unaccepted | UNRESOLVED-001 |

- Warnings observed: none recorded
- Retries observed: none recorded
- Exclusions observed: none recorded
- Failed or interrupted formal runs: none recorded

## Git state

### Fresh Status

Command: `git status --short --untracked-files=all`

Evidence ID: EVD-GIT-002

```text
 M path/to/output
```

### Scoped Diff and Ownership

- Scoped tracked diff command: `git diff -- path/to/output`
- Scoped staged diff command: `git diff --cached -- path/to/output`
- Staged task paths: none
- Out-of-scope staged paths: none
- Untracked task artifacts: `delivery/evidence-report.md`, `delivery/review-ledger.md`, `delivery/experiment-manifest.yaml`
- User pre-existing and unrelated changes: `path/to/protected`, preserved and excluded
- `git diff --check` exit code: 0
- Git authorization followed: yes; no staging, commit, push, cleanup, or history action performed

## Evidence Index

| Evidence ID | Requirement or finding | Source type | Exact path or command | Hash or exit | Direct fact supported |
|---|---|---|---|---|---|
| EVD-TEST-001 | REQ-001 | test | `command --example`, repository root | exit 0 | One normal case passed. |
| EVD-BOUNDARY-001 | REQ-002 | test | `command --example-boundary`, repository root | exit 0 | Both contract boundaries passed. |
| EVD-INVALID-001 | REQ-002 | test | `command --example-invalid`, repository root | exit 0 | Nonfinite and out-of-domain inputs were rejected. |
| EVD-ANCHOR-001 | REQ-002 | test | `command --example-anchor`, repository root | exit 0 | The anchor difference was zero. |
| EVD-DETERMINISM-001 | REQ-002 | test | `command --example-replay --seed 0`, repository root | exit 0 | Replay output matched. |
| EVD-REGRESSION-001 | REQ-003 | test | `command --example-regression`, repository root | exit 0 | Previously accepted behavior remained passing. |
| EVD-GIT-001 | REQ-003 | git | `git diff --check`, repository root | exit 0 | No whitespace error was reported. |
| EVD-GIT-002 | REQ-003 | git | `git status --short --untracked-files=all`, repository root | exit 0 | The recorded worktree state was available for ownership review. |
| EVD-ARTIFACT-001 | REQ-001 | artifact | `path/to/output` | recorded SHA-256 | The artifact is finite and schema-valid. |
| EVD-ENV-001 | REQ-001, REQ-002 | source | environment capture in this report | recorded environment identity | Platform, runtime, and hardware values are recorded. |
| EVD-CONFIG-001 | REQ-002 | source | `configs/example.yaml` and frozen metric record | recorded SHA-256 | The resolved configuration and metric identity are recorded. |
| EVD-TRACE-001 | INV-002, REQ-002 | artifact | `delivery/experiment-manifest.yaml` provenance section | recorded manifest SHA-256 | INPUT-001 and OUTPUT-001 retain the declared sample and causal-group lineage. |
| EVD-HANDOFF-001 | OUTPUT-002, REQ-003 | artifact | `delivery/evidence-report.md` | recorded SHA-256 | The executor evidence record contains the required delivery sections. |
| EVD-MANIFEST-001 | OUTPUT-004, REQ-003 | artifact | `delivery/experiment-manifest.yaml` | recorded SHA-256 | The machine-readable run identity and provenance fields are present. |

## Executor Completion Claim

- Implemented: not claimed by this template example
- Verified by executor: not claimed by this template example
- Independent review status: not_reviewed
- Requested independent review: Stage 1 specification compliance followed by Stage 2 evidence and quality after all example identities and hashes are replaced
- Remaining boundary: every scientific, implementation, performance, and future-milestone claim remains unaccepted
- Executor claim: not_issued
