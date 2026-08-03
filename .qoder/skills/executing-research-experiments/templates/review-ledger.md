# Review Ledger: EXAMPLE-001

This is a non-acceptable template example. After copying, replace every `EXAMPLE` value, `SNAPSHOT` value, and zero hash before review; no decision in this file is issued.

## Review Identity and Target

- Task ID: EXAMPLE-001
- Task title: Demonstrate the research-task contract
- Reviewer identity or context: unassigned example reviewer
- Independence boundary: not evaluated
- Review time: not issued
- Review target type: dirty_snapshot
- Implementation snapshot ID: SNAPSHOT-EXAMPLE-001
- Base repository revision for reconstruction: `0000000000000000000000000000000000000000`
- Full binary patch bundle: `delivery/snapshots/SNAPSHOT-EXAMPLE-001/full-binary.patch`
- Authorized untracked-object bundle: `delivery/snapshots/SNAPSHOT-EXAMPLE-001/authorized-untracked-objects/`
- Reconstruction manifest: `delivery/snapshots/SNAPSHOT-EXAMPLE-001/reconstruction-manifest.yaml`
- Snapshot definition: the full binary patches, authorized untracked objects, and reconstruction manifest jointly and exclusively define the implementation review target
- Review-record artifact: `delivery/review-ledger.md`, generated after snapshot freeze and excluded from the implementation target
- Review-record SHA-256: `0000000000000000000000000000000000000000000000000000000000000000`
- Evidence-bundle identity: SHA-256 `0000000000000000000000000000000000000000000000000000000000000000`

## Authorization and Ownership

- Authorized output paths: `path/to/output`, `delivery/evidence-report.md`, `delivery/review-ledger.md`, `delivery/experiment-manifest.yaml`
- Reviewed implementation target paths: `path/to/output`, `delivery/evidence-report.md`, `delivery/experiment-manifest.yaml`
- Review-record artifact outside implementation target: `delivery/review-ledger.md`
- Authorized Git actions: none
- Protected changes: `path/to/input`, `path/to/protected`

| Path | Ownership | In review target | Allowed action | Direct evidence |
|---|---|---|---|---|
| `path/to/output` | task change | yes | inspect | Scoped comparison |
| `delivery/evidence-report.md` | task change | yes | inspect | Scoped comparison |
| `delivery/review-ledger.md` | review-record artifact | no | generate | Created after snapshot freeze; hash recorded separately from implementation evidence |
| `delivery/experiment-manifest.yaml` | task change | yes | inspect | Scoped comparison |
| `path/to/input` | project input | no | inspect | Task authorization |
| `path/to/protected` | user pre-existing | no | none | Baseline status and task authorization |

## Stage 1

### Requirement Review

| Requirement ID | Required behavior or invariant | Direct implementation evidence | Direct verification evidence | State | Finding |
|---|---|---|---|---|---|
| REQ-001 | Produce the declared finite output without changing the input. | `path/to/output` inspected at head commit | EVD-TEST-001 raw log, exit 0 | not_reviewed | none |
| REQ-002 | Preserve units, domains, schema, identity, and deterministic replay. | Output schema and resolved configuration inspected at head commit | EVD-ANCHOR-001, EVD-INVALID-001, EVD-DETERMINISM-001, EVD-TRACE-001 | not_reviewed | none |
| REQ-003 | Restrict changes and Git actions to authorized scope. | Scoped status and comparison inspected | EVD-GIT-001, EVD-GIT-002 | not_reviewed | none |

### Scope and Prohibition Checks

| Check ID | Direct check | Evidence | Decision |
|---|---|---|---|
| SCOPE-001 | Every changed path is authorized and ownership is resolved. | Scoped status and comparison | pass |
| SCOPE-002 | No formula, unit, threshold, split, metric, or test expectation was relaxed. | Specification-to-source comparison | pass |
| SCOPE-003 | No downstream artifact was used as transitive proof. | Requirement evidence map | pass |
| SCOPE-004 | Future work is separated from current acceptance. | Pre-implementation boundary below | pass |

### Stage 1 Decision

- Decision: not_reviewed
- Requirements reviewed: none; the rows above demonstrate required fields only
- Open Critical findings: not assessed
- Open Important findings: not assessed
- Decision evidence: not issued
- Reviewer conclusion: not issued

## Stage 2

### Independent Commands

| Evidence ID | Validation class | Working directory | Exact command | Environment or configuration | Exit code | Passed | Failed | Skipped | Raw log | Reviewer observation |
|---|---|---|---|---|---:|---:|---:|---:|---|---|
| REVIEW-TEST-001 | Normal | repository root | `command --example` | example 1.0, seed 0 | 0 | 1 | 0 | 0 | `review/raw/normal.log` | The declared normal behavior passed. |
| REVIEW-BOUNDARY-001 | Boundary | repository root | `command --example-boundary` | example 1.0 | 0 | 2 | 0 | 0 | `review/raw/boundary.log` | Both contract boundaries passed. |
| REVIEW-INVALID-001 | Invalid | repository root | `command --example-invalid` | example 1.0 | 0 | 2 | 0 | 0 | `review/raw/invalid.log` | Invalid inputs were rejected diagnostically. |
| REVIEW-DETERMINISM-001 | Determinism | repository root | `command --example-replay --seed 0` | example 1.0, seed 0 | 0 | 1 | 0 | 0 | `review/raw/determinism.log` | Replay matched the frozen policy. |
| REVIEW-REGRESSION-001 | Regression | repository root | `command --example-regression` | example 1.0 | 0 | 1 | 0 | 0 | `review/raw/regression.log` | Accepted behavior remained passing. |
| REVIEW-GIT-001 | Tool quality | repository root | `git diff --check` | Git example | 0 | 1 | 0 | 0 | `review/raw/git-diff-check.log` | No whitespace error was reported. |

### Validation-Class Review

| Class | Passed | Failed | Skipped | Reviewer decision |
|---|---:|---:|---:|---|
| Normal | 1 | 0 | 0 | pass |
| Boundary | 2 | 0 | 0 | pass |
| Invalid | 2 | 0 | 0 | pass |
| Determinism | 1 | 0 | 0 | pass |
| Regression | 1 | 0 | 0 | pass |
| Scientific anchors | 1 | 0 | 0 | pass |
| Tool quality | 1 | 0 | 0 | pass |

### Independent Scientific Anchors

| Evidence ID | Anchor | Expected | Observed | Units | Tolerance | Difference | Decision |
|---|---|---:|---:|---|---:|---:|---|
| REVIEW-ANCHOR-001 | Asymmetric example anchor | 0.5 | 0.5 | dimensionless | 1e-8 absolute | 0 | pass |

### Quality Observations

- Test quality: direct normal, boundary, invalid, deterministic, regression, and scientific checks were independently inspected.
- Maintainability: assumptions and configuration are visible; no unrelated complexity was observed.
- Reproducibility: input, configuration, software, seed, command, log, and output identities are recorded.
- Evidence integrity: raw logs, command exits, test totals, artifact hashes, failures, and exclusions reconcile.
- Performance boundary: only the declared example envelope was reviewed; production-scale behavior was not assessed.
- Warnings: none recorded

### Stage 2 Decision

- Decision: not_reviewed
- Open Critical findings: not assessed
- Open Important findings: not assessed
- Open Minor findings: not assessed
- Decision evidence: not issued; command rows are structural examples, not executed review evidence
- Reviewer conclusion: not issued

## Findings

| Finding ID | Severity | Affected requirement or claim | Status | Direct evidence | Owner | Disposition | Closure evidence |
|---|---|---|---|---|---|---|---|
| FINDING-EXAMPLE-001 | Minor | Production-scale performance | not_reviewed | Illustrative task boundary only | example-owner | Replace with the actual finding disposition after review | No closure evidence issued |

Severity rule: acceptance requires zero open Critical findings and zero open Important findings. An open Minor item additionally requires an owner, explicit disposition, evidence of non-impact, and follow-up state.

## N/A and Skip Ledger

| Item | Basis | Affected scope | Reviewer agreement |
|---|---|---|---|
| OOD evaluation | The task contract contains no OOD claim. | OOD performance remains unassessed. | agreed |
| Physical experiment | The task produces no physical specimen. | Physical validation remains unassessed. | agreed |

## Pre-implementation and Future Boundary

| Path or feature | Status | Future milestone | Evidence needed before acceptance |
|---|---|---|---|
| Production benchmark | unaccepted and not assessed | production-scale evaluation | Authorized benchmark contract, raw runs, resource evidence, and independent review |

No future artifact or implementation is used to accept EXAMPLE-001.

## Final decision

### Review Evidence Definition

| Evidence ID | Source type | Exact path or command | Direct fact supported |
|---|---|---|---|
| EVD-REVIEW-001 | review-record artifact | `delivery/review-ledger.md`, hashed only after review completion and outside SNAPSHOT-EXAMPLE-001 | This template defines the required review record fields; it is not evidence that a review or decision occurred. |

### Completion Statement

- Task: EXAMPLE-001 — Demonstrate the research-task contract
- Review target: dirty snapshot `SNAPSHOT-EXAMPLE-001`, defined only by its full binary patches, authorized untracked objects, and reconstruction manifest
- Reviewed implementation target paths: `path/to/output`, `delivery/evidence-report.md`, `delivery/experiment-manifest.yaml`; Git actions none
- Review-record artifact: `delivery/review-ledger.md`, outside the implementation snapshot and awaiting its post-review hash
- Stage 1: not_reviewed
- Stage 2: not_reviewed
- Tests: not reviewed; all command rows and counts are structural examples only
- Scientific anchors: not reviewed; values are structural examples only
- Findings: not reviewed
- Unaccepted pre-implementation: every example path, value, result, and claim
- Remaining boundaries: all scientific, implementation, performance, OOD, physical-experiment, and future-milestone claims
- Decision: not_issued
- Decision basis: replace every `EXAMPLE` value, `SNAPSHOT` value, and zero hash, reconstruct the implementation snapshot, and complete both independent review stages before issuing a decision.
