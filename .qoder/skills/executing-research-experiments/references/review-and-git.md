# Review and Git Handoff Checklist

Use this checklist for independent review, milestone acceptance, evidence handoff, staging, commit preparation, or push preparation. Review establishes only what direct evidence supports at the identified revision or snapshot. It does not inherit acceptance from an executor, a previous agent, or a downstream artifact.

```text
implemented != verified != accepted
```

## Review Target and Evidence Boundary

- [ ] Identify the review target as either one exact commit SHA or one explicit dirty-worktree snapshot. A branch name, task name, latest state, or executor summary is not a stable target.
- [ ] For a commit review, record the full base SHA, full head SHA, branch name if any, and the exact comparison range.
- [ ] For a dirty-worktree review, record the full `HEAD` SHA, timestamp and time zone, working directory, exact capture commands, path scope, and `git status --short --untracked-files=all`. Preserve the complete byte streams, byte lengths, and cryptographic hashes of both `git diff --cached --binary --full-index --no-ext-diff -- path/to/task-a path/to/task-b` and `git diff --binary --full-index --no-ext-diff -- path/to/task-a path/to/task-b`; substitute the complete authorized path list. A patch hash or summary without the patch bytes is not reconstructable evidence.
- [ ] Preserve every authorized, readable, in-scope untracked object as raw bytes, a controlled archive, or content-addressed blobs. Record its repository-relative path, object type, file mode or symlink target, byte length, and cryptographic hash. For inaccessible or unauthorized paths, record only their existence and the access blocker; do not read, hash, or copy them, and mark any dependent review claim `blocked` or `partial`.
- [ ] Verify dirty-snapshot reconstruction in a temporary clone or isolated worktree created from the recorded base: check both patches, apply staged then unstaged binary patches in the recorded order, restore the preserved untracked objects, and compare hashes, modes, the authorized-path scoped-status projection, and scoped diffs with the capture manifest. The global status is a boundary inventory only; unrelated, protected, inaccessible, and out-of-scope paths are neither copied into the isolated tree nor required to match. Record the reconstruction commands and result.
- [ ] Record the allowed paths and allowed Git actions from the task authorization. Identify protected paths and explicit non-goals.
- [ ] Classify every dirty or changed path before review:

| Path | Ownership | In review target? | Allowed action | Evidence |
|---|---|---:|---|---|
Field specifications:

- `Path` field: record one exact repository-relative path per row.
- `Ownership` field: record `user pre-existing`, `task change`, `unrelated`, or `unresolved`, supported by repository history, the task record, or user direction.
- `In review target?` field: record `yes` or `no` for the identified commit or dirty-worktree snapshot.
- `Allowed action` field: record only the authorized action set, such as `inspect`, `edit`, `stage`, or `none`.
- `Evidence` field: cite the exact status entry, scoped diff, history record, task authorization, or provenance observation supporting the row.

- [ ] Treat ownership as unresolved until repository history, the task record, or the user establishes it. A dirty file is not automatically part of the task.
- [ ] Preserve user pre-existing and unrelated changes. Do not reformat, clean, overwrite, stage, or use them as task evidence unless the user explicitly adds them to scope.
- [ ] Declare the reviewer identity or execution context and the independence boundary. The implementer's self-review can supply observations but cannot confer independent acceptance.
- [ ] Prefer evidence in this order: raw command output and exit status; raw logs and immutable artifacts; inspected source and tests at the target; derived summaries with traceable inputs. Executor summaries and previous-agent claims are navigation aids, not evidence.
- [ ] Keep evidence requirement-specific. A downstream artifact proves only the facts directly inspected about that artifact; it does not prove the upstream contract, implementation route, or milestone.
- [ ] Track `implemented`, `verified`, and `accepted` separately. Implementation means the target contains a change; verification means a named check produced direct evidence; acceptance requires both review stages and closure of blocking findings.

## Stage 1 — Specification Compliance

Complete Stage 1 against the approved specification, task contract, scientific contract, and authorization before issuing any Stage 2 quality endorsement.

- [ ] Resolve the authoritative requirement sources and their precedence. Quote and stop on unresolved conflict rather than choosing a convenient interpretation.
- [ ] Reconstruct the complete current-milestone requirement set, including scientific meaning, scope, interfaces, outputs, tolerances, acceptance rules, authorized paths, and forbidden changes.
- [ ] Map every requirement to direct evidence:

| Requirement ID | Required behavior or invariant | Direct implementation evidence | Direct verification evidence | State | Finding |
|---|---|---|---|---|---|
Field specifications:

- `Requirement ID` field: record the stable identifier from the authoritative requirement source.
- `Required behavior or invariant` field: quote or precisely restate the complete contract, including applicable units, tolerances, scope, and acceptance rule.
- `Direct implementation evidence` field: cite an exact repository path and symbol, configuration key, schema field, or immutable artifact field inspected at the review target.
- `Direct verification evidence` field: cite the exact command, raw-log location, exit status, and relevant output or numerical anchor.
- `State` field: record exactly one of `implemented`, `verified`, `accepted`, or `not met`, using the state boundaries defined in this checklist.
- `Finding` field: record the stable finding ID and severity, or `none` only when no mismatch was observed.

- [ ] Inspect source, configuration, interfaces, tests, raw logs, and artifacts named in the table. Do not accept a row from a prose claim or a file-existence check.
- [ ] Verify the scientific contract directly: formulas, units, coordinates, signs, parameter domains, data identities, split rules, randomness policy, numerical tolerances, and approved assumptions.
- [ ] Verify scope directly: all required paths and behaviors are covered, non-goals remain untouched, and every changed path is authorized.
- [ ] Verify interface and output contracts directly: type, shape, schema, ordering, naming, serialization, versioning, compatibility, required fields, units, and artifact identity.
- [ ] Search explicitly for forbidden changes and shortcuts, including relaxed thresholds, altered scientific definitions, hidden data substitutions, test weakening, proxy acceptance, and unauthorized future-milestone work.
- [ ] Record each state transition separately. Code present is `implemented`; a direct check that passed is `verified`; only an independent two-stage decision with no open blocking finding is `accepted`.
- [ ] Reject transitive proof. A generated solid, mesh, ODB, dataset row, checkpoint, plot, or physical curve cannot establish an upstream scalar-field, geometry, solver, data, training, statistical, or protocol contract without direct upstream evidence.
- [ ] Keep future preimplementation outside current acceptance. It may be inventoried as unaccepted preimplementation, but it neither completes the current milestone nor pre-accepts a future milestone.
- [ ] Classify every mismatch before leaving Stage 1. If any Critical or Important finding remains open, stop the acceptance path and do not issue a Stage 2 quality endorsement. Read-only diagnosis may continue if clearly labeled as diagnosis rather than acceptance.

Stage 1 output must state `pass` or `fail`, list the reviewed requirements, cite the direct evidence for each decision, and enumerate every finding with severity, owner, disposition, and closure evidence.

## Stage 2 — Implementation and Experiment Quality

Begin quality acceptance only after Stage 1 passes with no open Critical or Important finding.

- [ ] Independently rerun the contract's key commands from the identified commit or reconstructable snapshot. Record the exact command, working directory, tool and dependency versions, resolved configuration, environment constraints, exit code, and raw output path.
- [ ] Inspect the implementation source, tests, raw logs, intermediate outputs, and final artifacts. Do not substitute executor-selected excerpts for the underlying evidence.
- [ ] Verify that tool calls return the real data structure expected by downstream code. Inspect nested fields, dimensions, types, emptiness, status values, warning payloads, and error elements rather than trusting container truthiness, display formatting, or a wrapper's success status.
- [ ] Execute every applicable validation class:

| Class | Minimum independent review |
|---|---|
| Normal | Representative in-domain inputs meet the exact behavior, schema, units, metrics, and output contract. |
| Boundary | Extrema, tolerances, empty or minimal cases, domain edges, and resource limits behave explicitly. |
| Invalid | Malformed, nonphysical, out-of-range, missing, incompatible, and corrupted inputs are rejected or classified as specified. |
| Deterministic | Locked seeds, inputs, configuration, versions, and hardware policy reproduce results within the approved tolerance. |
| Regression | Previously accepted behaviors, interfaces, anchors, and artifacts remain unchanged where required. |
| Scientific anchors | Units, coordinates, signs, conservation or symmetry, convergence, analytical cases, and approved numerical anchors agree within named tolerances. |

- [ ] For each class, report pass, fail, and skip counts. A skip requires a contract-based reason and reviewer disposition; it is not silently equivalent to a pass.
- [ ] Check test quality: requirements are asserted directly, failures are diagnostic, fixtures preserve scientific meaning, negative cases fail for the intended reason, and tests do not merely duplicate the implementation.
- [ ] Check maintainability: assumptions and configuration are visible, interfaces are narrow and documented, error paths are actionable, and unrelated complexity or duplicated logic was not introduced.
- [ ] Check performance against the approved envelope using representative evidence. Do not generalize from a smoke test to production scale, hardware, memory, wall time, solver convergence, or throughput.
- [ ] Check reproducibility: immutable input identities, seeds, versions, environment, commands, configuration, ordering, artifact hashes, and nondeterminism tolerances are sufficient for an independent rerun.
- [ ] Check evidence integrity: logs are raw and complete, artifacts map to run identities, hashes match, failures and exclusions remain visible, and summaries reconcile to their source counts.
- [ ] Record all observed warnings and explain their disposition. A clean exit code does not erase scientific, numerical, or data-quality warnings.
- [ ] Require an independent reviewer conclusion. Implementer self-review, automated self-critique, or a prior agent's approval can supplement but cannot replace Stage 2.

Stage 2 output must state `pass` or `fail`, list commands and results, identify inspected sources and artifacts, report validation-class counts and numerical anchors, and link every conclusion to direct evidence.

## Severity and Closure

Classify findings by impact on validity and acceptance, not by how easy they are to fix.

| Severity | Definition | Acceptance effect | Closure requirement |
|---|---|---|---|
| Critical | Invalid science, corrupted or irrecoverable evidence, data loss, leakage that invalidates a claim, unsafe destructive behavior, or a false completion or acceptance claim. | Reject and stop acceptance immediately. | Correct the cause, regenerate affected evidence when necessary, independently rerun applicable checks, and link direct closure evidence. |
| Important | Required behavior, interface, scientific invariant, validation class, reproducibility record, raw evidence, or authorization control is missing, wrong, or unverified. | Reject; Stage 1 or Stage 2 cannot pass. | Supply or correct the requirement-specific evidence and obtain independent re-review. |
| Minor | A bounded defect or documentation gap with no effect on the scientific conclusion, required behavior, evidence integrity, or reproducibility of the accepted scope. | May remain only in an accepted Minor ledger. | Record owner, explicit disposition, scope of non-impact, evidence for that judgment, and follow-up state. |

- [ ] Give every finding a stable ID, severity, affected requirement or claim, evidence, owner, disposition, and closure evidence.
- [ ] Do not downgrade a finding to make a gate pass. Changes in severity require new direct evidence and reviewer rationale.
- [ ] Reopen related acceptance decisions when a fix changes scientific behavior, data, interfaces, tests, thresholds, or artifacts.
- [ ] Require zero open Critical and zero open Important findings before any task is accepted.
- [ ] Carry every open Minor item in a ledger. `Minor` without owner, disposition, and evidence is unresolved, not harmless.
- [ ] Treat false completion itself as Critical when it asserts validity or acceptance that the evidence does not support.

## Evidence Bundle

Create one immutable or content-hashed bundle for the exact review target. Include:

- [ ] target identity: base and head SHAs or the complete dirty-snapshot manifest;
- [ ] reviewer identity or execution context, review time, authority sources, allowed paths, protected changes, and scope decisions;
- [ ] changed-file inventory classified as user pre-existing, task change, or unrelated;
- [ ] exact commands, working directories, tool and dependency versions, resolved configuration, exit codes, and raw stdout and stderr;
- [ ] test totals with pass, fail, and skip counts per command and per applicable validation class;
- [ ] scientific anchors with names, units, expected values, actual values, tolerances, and pass or fail decisions;
- [ ] raw-log, intermediate, and artifact paths with run or sample identity, size where relevant, and cryptographic hash;
- [ ] failures, warnings, exclusions, retries, diagnosis, remediation, and evidence retained from failed attempts;
- [ ] unresolved items, assumptions, deviations, limitations, authorization status, and affected claims;
- [ ] fresh `git status --short --untracked-files=all`, scoped tracked and staged diffs, scoped whitespace checks, the review-start index manifest, retained staged and unstaged binary patches, retained authorized in-scope untracked objects, and the dirty-snapshot reconstruction manifest and result;
- [ ] complete Stage 1 and Stage 2 decisions, requirement states, finding ledger, closure evidence, and reviewer conclusions;
- [ ] unaccepted preimplementation and future-stage artifacts, clearly separated from accepted current-task evidence.

Previous-agent claims, executor summaries, screenshots without source identity, and the mere existence of a file are not evidence. They may point to evidence that the reviewer then inspects directly.

The bundle index should make each claim auditable without guessing:

| Evidence ID | Requirement or finding | Source type | Exact path or command | Hash or exit | Reviewer observation |
|---|---|---|---|---|---|
Field specifications:

- `Evidence ID` field: assign a stable identifier unique within the evidence bundle.
- `Requirement or finding` field: record the exact requirement ID or finding ID supported by the evidence.
- `Source type` field: record `source`, `test`, `log`, `artifact`, or `git`.
- `Exact path or command` field: record the repository-relative or bundle-relative path, or the complete command and working directory.
- `Hash or exit` field: record the cryptographic hash for a file or the command exit code, as applicable.
- `Reviewer observation` field: state only the direct fact observed in the cited source, without inferred or transitive conclusions.

## Git Safety

- [ ] Run `git status --short --untracked-files=all` before editing, before staging, and at handoff. Reconcile every path with the ownership table.
- [ ] At review start, resolve and record the real index path, its byte hash, and the complete staged path/status baseline. Classify staged entries as pre-existing or task-owned from direct evidence before any staging action.
- [ ] Protect user pre-existing and unrelated changes. Never use destructive `reset`, `checkout`, clean, restore, or bulk overwrite to obtain a clean-looking tree.
- [ ] Treat overlap between an authorized task path and pre-existing staged user content as an ownership conflict: stop staging or committing and request direction. Do not overwrite, unstage, restore, or rewrite the user's index entry.
- [ ] Stage only after explicit authorization and only with exact task paths, for example `git add -- path/to/file-a path/to/file-b`. Exact-path staging does not clear unrelated staged content or transfer ownership of pre-existing staged entries. Never use broad pathspecs, directory-wide staging, `git add .`, or `git add -A`.
- [ ] Inspect only authorized task paths with scoped `git diff --cached --name-status -- path/to/task-a path/to/task-b`, `git diff --cached --full-index --binary -- path/to/task-a path/to/task-b`, and `git diff --cached --check -- path/to/task-a path/to/task-b`; substitute the complete authorized path list. Record unrelated staged warnings separately; do not read protected cached content or let unrelated warnings contaminate the task gate.
- [ ] If the baseline index contains any non-task staged entry, prohibit a normal commit from the real worktree and current ref. Stop and request direction, or use an explicitly approved isolated worktree or clone and commit on a detached HEAD or temporary ref. A temporary index must be initialized from the reviewed base with `read-tree` semantics, never copied from a mixed real index, and may create a commit only through plumbing such as `write-tree` plus `commit-tree` that does not move the real HEAD or ref; add only authorized task paths.
- [ ] Immediately before a commit, enumerate the prospective parent-to-commit name/status and full diff without broadening the review scope; the changed path set must be a subset of authorized task paths. Immediately after an isolated or plumbing commit, prove that the real worktree's symbolic ref and resolved HEAD SHA, real index byte hash and staged inventory, and global and authorized-path status projections are unchanged. If no isolation was needed, prove that every pre-existing staged entry is byte-for-byte unchanged.
- [ ] Also inspect unstaged and untracked task files so a clean scoped cached diff is not mistaken for a complete handoff.
- [ ] Do not stage caches, temporary files, generated bulk artifacts, solver scratch, large raw outputs outside the approved artifact route, credentials, tokens, secrets, personal data, or unrelated changes.
- [ ] Bind acceptance to the reviewed commit SHA or explicit dirty snapshot. Any content change after review invalidates the affected acceptance until the new target is reviewed.
- [ ] Commit or push only when the user has explicitly authorized that Git action. Review approval is not authorization to commit, rewrite history, merge, or push.
- [ ] Before an authorized commit, record the exact staged paths, cached diff, cached whitespace check, commit identity policy, and message. Before an authorized push, verify the destination remote, branch, upstream, and reviewed commit SHA.
- [ ] Explain Git-only warnings such as line-ending conversion, file-mode behavior, ignore rules, or permissions in their actual scope. Investigate them, but do not automatically convert them into source-code, scientific, or experiment failures without direct impact evidence.
- [ ] If ignore behavior or permissions hide an expected file, report the visibility and access limitation. Do not bypass protection, copy secrets, or declare the source invalid solely because Git does not track it.

## Completion Statement

Issue one conclusion per task or requirement group. Use only `accepted`, `rejected`, or `conditional`.

Every completion statement must include:

- `Task`: the stable task ID and exact title;
- `Review target`: the full commit SHA or reconstructable dirty-snapshot ID;
- `Allowed paths`: every exact authorized path and the authorized Git actions;
- `Stage 1`: `pass` or `fail`, with the direct evidence IDs supporting the decision;
- `Stage 2`: `pass`, `fail`, or `not entered`, with the direct evidence IDs supporting the decision;
- `Tests`: each exact command, working directory, passed, failed, and skipped counts, and exit code;
- `Scientific anchors`: each anchor name, expected value, actual value, units, tolerance, and decision;
- `Findings`: every stable finding ID, severity, open or closed state, owner, disposition, and closure evidence;
- `Unaccepted preimplementation`: exact paths or features and the future milestone to which they belong;
- `Remaining boundaries`: every explicitly unreviewed or unsupported scope item;
- `Decision`: exactly one of `accepted`, `rejected`, or `conditional`;
- `Decision basis`: requirement-specific direct evidence IDs and the facts they establish.

A completion statement must not use a branch name, task name alone, `latest`, or an executor summary as the review target; omit failed or skipped checks, open findings, limitations, or unsupported scope; use inferred or transitive proof as direct evidence; claim acceptance beyond the reviewed target; or combine tasks whose evidence or decisions differ.

- [ ] Use `accepted` only when both stages pass and no Critical or Important finding remains open.
- [ ] Use `rejected` when a required behavior or evidence item fails, a blocking finding remains, or the target cannot be reproduced.
- [ ] Use `conditional` only to express clear, bounded, and explicitly unaccepted scope outside the accepted claim. It cannot conceal or waive any open Critical or Important finding in the task being judged.
- [ ] State exact test counts and commands, including failures and skips. Do not report a partial suite as the total suite.
- [ ] List future code and preimplementation as unaccepted. State which future requirement still lacks direct evidence.
- [ ] Name remaining work, assumptions, unsupported environments, non-applicable classes with rationale, and every Minor ledger item.
- [ ] Never combine several tasks into a blanket completion statement when their evidence or decisions differ.

## Rationalization Counters

Apply these counters to what the captured baseline and review evidence actually show. Do not invent failures, successes, stability, or generality that were not observed.

| Rationalization | Required counter |
|---|---|
| "A solid volume exists, so the scalar-field milestone is complete." | The downstream solid proves only its inspected existence and properties. Require direct evidence for the upstream scalar-field interface, values, coordinates, tests, and acceptance contract. |
| "I noted missing evidence, so I can still mark complete." | A caution followed by acceptance is still false acceptance. Keep the affected requirement unverified and reject until direct evidence closes it. |
| "The previous agent says tests pass." | Independently rerun the exact commands at the identified target and inspect raw output, or mark the tests unverified. |
| "`checkcode` returned an outer cell or container, so MATLAB analysis passed." | Inspect every inner result and finding, including nested messages, severity, file, and location. Container return, non-emptiness, or wrapper success alone is not a clean result. |
| "B/C passed, so the capability is stable and safeguards can be removed." | Any captured B/C pass is only a single-baseline positive control. It does not prove repeated stability, broad capability, negative-case safety, or permission to remove safeguards. Preserve the contract and rerun requirements. |
| "The ODB exists, so the Abaqus run is valid." | Route to `abaqus-simulation.md`; inspect job and solver status, convergence, warnings, steps, frames, fields, numerical and energy checks, extraction identity, and required raw files. |
| "The curve is smooth, so physical validation passed." | Route to `physical-experiments.md`; inspect immutable raw machine exports, identities, calibration, protocol, processing history, units, replicates, failures, exclusions, and preregistered comparison rules. |
| "The best seed meets the metric, so the model is accepted." | Apply the predeclared seed, repetition, aggregation, uncertainty, and failure-accounting policy. Report every required run; a selected best seed is selection evidence, not robust performance. |
| "Random held-out rows are OOD." | Route to `dataset-quality.md` and `evaluation-statistics.md`; require a frozen OOD axis, support boundary, separation rule, group identity, leakage audit, and evaluation envelope. Random row holdout is not OOD evidence. |
| "Changing the threshold makes the test pass." | Diagnose the discrepancy against the approved contract. Change thresholds, tolerances, metrics, or acceptance rules only with explicit authority, versioning, and re-review. |
| "Dirty files can be ignored because they are unrelated." | Establish ownership and scope from evidence, protect user changes, and record every dirty path. Unknown ownership is a stop condition, not permission to ignore or stage. |
| "A patch hash and untracked inventory are enough to reconstruct the dirty snapshot." | Retain the complete binary full-index staged and unstaged patch bytes plus authorized in-scope untracked object bytes, then reconstruct the snapshot in isolation and verify hashes, modes, status, and diffs. |
| "Exact-path staging makes a normal commit safe even when the user index is already staged." | Detect overlap and stop on ownership conflict. Otherwise use an approved isolated worktree or a temporary index initialized from the reviewed base, prove the commit changes only authorized paths, and leave the real index unchanged. |
| "Future code is already present, so the future task is complete." | Record it as unaccepted preimplementation. Review and accept only the current milestone; the future task still needs its own direct requirement mapping, baseline, validation, and review. |
| "One clean artifact proves the whole pipeline." | Trace every upstream and downstream contract independently. Keep leakage and OOD review, Abaqus evidence, and physical-experiment evidence routed to their dedicated references whenever those domains apply. |

The red-baseline record may include genuine positive controls. Preserve those observations exactly, including B/C if present, but describe them only as single-baseline positive controls. Do not infer stability, general coverage, safeguard removal, scientific validity, or milestone acceptance beyond the observed command and target.

## Stop Conditions

Stop acceptance, preserve all evidence already collected, and report when:

- the review target, base/head pair, dirty snapshot, authority order, allowed paths, or Git authorization conflicts or cannot be fixed precisely;
- raw commands, versions, exit codes, logs, source, tests, artifacts, hashes, or requirement-specific evidence required for a decision are missing or inaccessible;
- dirty-worktree ownership or the boundary among user pre-existing, task, and unrelated changes is unclear;
- the reviewer is not independent where independent acceptance is required;
- any Critical or Important finding remains open;
- a required command cannot be independently reproduced from the identified target and environment;
- a scientific definition, threshold, split, unit, interface, or acceptance rule would need unauthorized change;
- evidence indicates leakage, invalid OOD construction, corrupted or overwritten artifacts, nonconvergence, irreproducibility, data loss, or a false acceptance claim;
- staging, commit, push, cleanup, history rewriting, or access to protected material exceeds authorization.

When safe and within authorization, continue read-only diagnosis to identify the blocker, retain raw outputs and failed attempts, and report the narrowest supported conclusion. A stop condition is not permission to discard evidence, clean the worktree, hide failures, or substitute a summary for missing proof.
