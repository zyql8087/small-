# Dataset Quality Execution Checklist

Use this checklist when constructing, auditing, splitting, or releasing a research dataset. A checked item means that the named evidence exists and is linked from the dataset manifest. A row count or model score alone is never evidence of dataset validity.

## Applicability and N/A

- Execute only checklist items applicable to the task contract and current stage.
- N/A is not a shortcut: record the exact contract/design basis and require reviewer agreement at handoff.
- Evidence that the selected dataset design or current stage is designed not to produce is legitimately N/A; evidence expected by the resolved contract but missing is a stop condition.
- Do not demand downstream training or final-evaluation evidence during a dataset-only stage, but record that downstream work as unaccepted and not assessed.
- Apply N/A only to evidence the resolved dataset design or stage does not require or produce. It cannot waive dataset identity, causal-group identity, split identity, provenance, or validation evidence required for the current stage.

## Identity and Provenance

- [ ] Assign every source sample an immutable sample ID before augmentation, precision expansion, descriptor calculation, filtering, or row duplication. Prove uniqueness and preserve any legacy-ID mapping.
- [ ] Assign every underlying causal entity an immutable base-structure ID before expansion. Where topology family or another grouping hierarchy is part of the contract, assign and validate that identity at the same time.
- [ ] Define the relationship among dataset ID, sample ID, base-structure ID, topology-family ID, solver job ID, raw artifact ID, and processed-row ID. Save forward and reverse mapping checks and reject unexplained aliases, omissions, or duplicates.
- [ ] Record the compiler or generator code commit, fully resolved configuration hash, solver job identity, raw artifact path and content hash, execution environment, and creation time for every source sample.
- [ ] Preserve parent-child provenance from each processed row to its raw artifact, source sample, causal group, expansion or augmentation operation, and processing code revision.
- [ ] Reject identity derived only from mutable row order, filename order, floating-point formatting, or the output of a split operation.
- [ ] Record every identity correction as a new dataset version with an auditable old-to-new mapping; never rewrite a released identity silently.

## Schema and Variable Roles

- [ ] Publish a machine-readable schema containing field name, semantic definition, causal role, dtype, shape, unit, allowed domain, missing-value representation, and source or derivation rule.
- [ ] Classify fields into separate roles and storage namespaces: independent inputs, derived descriptors, prediction targets, and quality-control or status fields. Reject a field that has multiple implicit roles.
- [ ] Record the dependency graph for every derived descriptor and target, including the raw fields, transformations, software revision, and configuration used to calculate it.
- [ ] Verify that quality-control fields, post-outcome diagnostics, target-derived quantities, and target-normalization statistics cannot enter model inputs unless the scientific contract explicitly defines them as inference-time information.
- [ ] Recompute designated features and descriptors from authoritative parent artifacts with an independent or clean-path implementation. Compare values using the contract-approved metric and tolerance and archive discrepancies.
- [ ] Validate units, conversions, sign conventions, coordinate order, value ranges, categorical levels, tensor shapes, and dtype conversions before splitting or release.
- [ ] Detect and classify missing, nonfinite, failed, and censored values separately. Do not encode any of these states as an ordinary physical value or silently impute them.
- [ ] Version schema changes and prove compatibility or provide an explicit migration with input and output hashes, row counts, and validation results.

## Split Before Expansion

- [ ] Define the causal entity that must not cross partitions and obtain contract approval before any split. For each evaluation claim, use the claim-specific minimum sufficient grouping justified by shared causal origin or lack of independent distinguishability at the experimental resolution. Record any coarser grouping only as a sensitivity analysis; do not enlarge the primary leakage group without a causal or resolution-based justification.
- [ ] Split by causal group, base structure, topology family, or the approved hierarchy before augmentation, precision expansion, oversampling, or other row expansion. Save the group-level assignment manifest.
- [ ] Place every precision variant, augmentation, replicate derived from the same causal entity, exact duplicate, and record classified as a leakage-relevant near duplicate in the same partition. Similarity or correlation alone is not leakage; treat records as leakage-relevant near duplicates only when they share a source or cannot be independently distinguished at the experimental resolution defined for the claim.
- [ ] Freeze test identities, group assignments, and the split-manifest hash before model selection. Any correction creates a new version and invalidates prior test access records unless the contract explicitly defines a controlled repair.
- [ ] Prove zero forbidden group overlap across train, validation, and test partitions at every identity level governed by the contract.
- [ ] Treat a row-held-out split as row-level interpolation evidence only. Do not label it topology, structure, family, or causal-entity OOD evidence.
- [ ] For the public Small precision-expanded dataset, explicitly audit whether precision variants of the same base structure cross partitions; this is a project-specific leakage case, not a claim that every dataset is precision-expanded. The general rule is that records from one causal entity cannot cross partitions.
- [ ] Record the rationale for stratification, grouping, temporal ordering, or domain holdout and show that balancing or resampling occurs only within the training partition.
- [ ] For every OOD claim, define three operational input classes before splitting: supported ID inputs; a contract-declared OOD evaluation envelope outside training support that must remain inferable, labeled, traceable, and evaluable; and unsupported inputs outside both approved envelopes that must be rejected.
- [ ] Record each OOD axis, the training-support boundary, OOD-support or evaluation-envelope boundary, gap or separation rule, boundary ownership, and every evaluated cross-axis combination. Preserve those labels and rules in the split manifest.

## Required Audits

- [ ] Detect exact duplicates using canonical records and content hashes before and after processing. Report duplicate clusters, roles, partitions, and dispositions.
- [ ] For each evaluation claim, predefine the minimum sufficient leakage group and its causal basis. Do not use a broader grouping merely because two records are similar or correlated.
- [ ] Detect tolerance-based near duplicates using a scientifically justified representation, distance or comparison metric, experimental resolution, and contract-approved tolerance. Do not select any of these after viewing model performance.
- [ ] Predefine whether near-duplicate clusters use direct-pair assignments, connected components, transitive closure, or another rule. Audit chain merging and maximum within-cluster separation so a sequence of locally close records does not silently merge scientifically distinct endpoints.
- [ ] Repeat leakage conclusions under other reasonable grouping, representation, distance, tolerance, and clustering definitions. Archive the sensitivity audit and explain changes in membership or split validity.
- [ ] Re-run exact-duplicate, near-duplicate, and causal-group-overlap checks after every transformation that can change row multiplicity or identity.
- [ ] Recompute designated features, verify units, and audit ranges independently within each split. Investigate split-specific clipping, scaling, saturation, or conversion behavior.
- [ ] Report missing, nonfinite, failed, censored, excluded, and imputed counts by field, method, causal group, and split, retaining both numerators and denominators.
- [ ] Compare method and split distributions for sample counts, causal-group counts, topology families, independent inputs, derived descriptors, failure status, and other contract-defined non-target strata. Preserve the raw summaries and plots.
- [ ] Assign an independent data-audit role to perform every target-bearing per-split audit. Seal final-test labels, target summaries, target plots, and other target-bearing artifacts from model developers until every model, checkpoint, preprocessing, protocol, analysis plan, hypothesis or claim family, estimand, and outcome-contingent decision or reporting rule is frozen and content-hashed.
- [ ] For an inductive confirmatory evaluation before the final-test seal opens, expose to developers only predeclared information required for independent data-integrity QA and demonstrated not to reveal target distributions. Prohibit that information from influencing any model, architecture, hyperparameter, preprocessing, normalization, selection, analysis, or reporting decision; predeclaration does not make selection use permissible.
- [ ] Predeclare every permitted inductive final-test covariate or non-target QA summary and its exact integrity purpose. Log its producer, recipient, access time, and artifact hash, and verify from the decision record that it was not used for development or selection.
- [ ] If the explicit contract is transductive or domain-adaptation rather than inductive, define the exact independent adaptation set and unlabeled covariates available for adaptation, adaptation algorithm, selection rule, resource budget, stopping rule, and configuration hash before access. Preserve a separate, locked final evaluation set whose records and covariates did not participate in adaptation, tuning, or selection.
- [ ] Preserve the sealed target-audit artifacts and access-control or custody log. If final-test target information was already public or otherwise visible, do not represent that split as untouched final-test evidence; use a new, previously untouched locked test where required or downgrade the affected result to exploratory for `evaluation-statistics` handling.
- [ ] For ordinary inductive evaluation, fit preprocessing statistics and state on training data only, archive their values and hash, and verify that validation and test data are transformed without refitting.
- [ ] For a contract-authorized transductive or domain-adaptation evaluation, fit adaptation-specific preprocessing or adaptation state only from the independent adaptation set and explicitly permitted unlabeled information under the pre-frozen algorithm, budget, stopping rule, and configuration. The locked final evaluation set and its covariates must not participate in fitting, refitting, tuning, adaptation, selection, threshold choice, or any model or preprocessing-state update.
- [ ] Freeze and content-hash the final-evaluation command before opening the final-test seal. Permit only that frozen evaluator to read the locked final evaluation set and its covariates or labels, solely for inference that is stateless with respect to persistent and adaptive state and for pre-frozen metric computation and outcome-contingent reporting.
- [ ] Log every authorized evaluator read with time, person or execution identity, purpose, command and command hash, input identities, frozen configuration and analysis-plan hashes, and produced-artifact hashes. Preserve the label seal outside the evaluator and record the read as a final-test access event.
- [ ] After an authorized final-test read, apply the fresh-test-or-exploratory rule to any change or selection covered by the frozen analysis plan and selection registry. The authorized read itself is not a stop condition when the evaluator is frozen, performs no persistent or adaptive update, computes only pre-frozen metrics, preserves the seal, and writes the complete ledger entry.
- [ ] Trace unexpectedly high validation or test performance through identity overlap, duplicate, provenance, preprocessing, target leakage, and split audits before interpreting it as scientific progress.
- [ ] Distinguish development smoke checks from formal dataset validation. Smoke checks may use small subsets to expose wiring failures; they cannot replace complete manifest, overlap, distribution, and failure audits.
- [ ] Route inferential comparisons, uncertainty intervals, multiplicity handling, and formal statistical repetition to the subsequent `evaluation-statistics` stage. Do not invent seed counts, thresholds, or acceptance criteria that the approved contract has not supplied.

## Failure and Exclusion Accounting

- [ ] Preserve every failed simulation record with sample and base-structure identities, attempted inputs, solver job and raw artifact identities, logs, partial outputs, failure class, and disposition.
- [ ] Never silently delete a failed simulation, nonfinite result, censored result, missing artifact, or rejected geometry from the dataset history.
- [ ] Define exclusion and censoring rules before outcome inspection. Apply them mechanically, record the rule version, and retain both included and excluded identities.
- [ ] Separate generation failure, solver failure, extraction failure, schema failure, physical-quality failure, and administrative cancellation. Do not collapse these into a single missing label.
- [ ] Report attempted, succeeded, failed, censored, excluded, and released counts by method, causal group, topology family, and split, using reconciled denominators.
- [ ] Test whether failure or exclusion rates differ across methods, splits, input domains, or target ranges using the descriptive checks required by the contract; route formal inference to `evaluation-statistics`.
- [ ] Prevent failure status or exclusion decisions computed after observing the target from becoming an unacknowledged selection mechanism. Document any unavoidable selection effect as a release limitation.

## Release Evidence

- [ ] Keep raw artifacts immutable and content-addressed or otherwise protected against silent overwrite. Record storage location, hash algorithm, hashes, and access policy.
- [ ] Assign a version to every processed dataset and link it to the immutable raw inputs, schema version, processing commit, resolved configuration, and regeneration command.
- [ ] Release the exact split manifest containing dataset version, immutable row and group identities, partition assignment, grouping rule, split-generation code revision, configuration, and content hash.
- [ ] Release the machine-readable schema and role definitions together with unit, range, missing-value, censoring, and quality-control semantics.
- [ ] Publish manifest hashes plus reconciled row counts and causal-group counts for the complete dataset and each split. Include method and topology-family counts where applicable.
- [ ] Archive duplicate, near-duplicate, overlap, recomputation, unit, range, missingness, nonfinite, failure, censoring, exclusion, and distribution audit reports with their commands and exit statuses.
- [ ] Archive final-test seal identities, frozen evaluator and command hash, custody and access ledger, independent data-audit outputs, permitted non-target disclosures, their predeclared integrity purposes, and the hashes of every disclosed artifact. For transductive or domain-adaptation contracts, also archive adaptation-data and untouched-final-evaluation identities, configuration, budget, and separation evidence.
- [ ] Provide a regeneration procedure from immutable raw artifacts to the processed dataset and split manifest. Record required environment, dependencies, configuration, command, and expected output hashes or contract-approved comparison policy.
- [ ] State supported claims, known coverage gaps, selection effects, unresolved limitations, and whether each split measures interpolation or a precisely defined OOD condition.

## Stop Conditions

Stop processing, training handoff, or release as appropriate; preserve diagnostics and mark the dataset unresolved when any of the following occurs:

- [ ] Immutable sample IDs or base-structure IDs were assigned only after augmentation, precision expansion, filtering, or row expansion and cannot be reconstructed unambiguously.
- [ ] Compiler or generator commit, resolved configuration hash, solver job identity, raw artifact identity, or processed-row lineage required by the current stage is missing or inconsistent.
- [ ] Independent inputs, derived descriptors, targets, and quality-control fields cannot be separated unambiguously, or target-derived information reaches model inputs without contract approval.
- [ ] A causal entity, base structure, governed topology family, precision variant, augmentation, or forbidden near duplicate crosses partitions.
- [ ] A leakage-relevant near-duplicate rule lacks a claim-specific causal basis, experimental resolution, representation, distance, tolerance, or clustering policy, or chain-merging and reasonable-definition sensitivity remain unresolved.
- [ ] Test identities are not frozen, the split manifest has drifted, or test membership was used for model, preprocessing, threshold, or hyperparameter selection.
- [ ] Final-test labels, targets, target summaries, target plots, or target-bearing audit artifacts are disclosed before the hypothesis or claim family, estimand, outcome-contingent decision or reporting rule, and all other claim-bearing selection objects and hashes are frozen.
- [ ] In an inductive confirmatory evaluation, a final-test covariate or non-target summary exceeds independently required QA information, influences development or selection, or lacks a predeclared integrity purpose and complete access record; predeclaration alone cannot cure such use.
- [ ] A transductive or domain-adaptation evaluation lacks a contract-defined unlabeled-covariate scope, adaptation algorithm, selection rule, budget, stopping rule, or configuration hash, or lacks a separate locked final evaluation set that was untouched by adaptation, tuning, and selection.
- [ ] An ordinary inductive preprocessing state is fitted outside training data, or transductive or domain-adaptation state is fitted outside the independent adaptation set and permitted unlabeled information under the pre-frozen procedure.
- [ ] The locked final evaluation set or its covariates participate in fitting, refitting, tuning, adaptation, selection, threshold choice, or any model or preprocessing-state update.
- [ ] The locked final evaluation set, its covariates, or its labels are read outside the content-hashed frozen evaluator; that evaluator performs non-frozen metric computation or a persistent or adaptive update; the label seal is bypassed; or the access ledger is incomplete. A compliant frozen-evaluator read is not a stop condition.
- [ ] Exact duplicates, tolerance-based near duplicates, group overlap, feature recomputation, unit, range, missingness, nonfinite, failure, censoring, exclusion, or method/split distribution audits required by the contract are absent or unresolved.
- [ ] A high model score is offered as acceptance before leakage, provenance, preprocessing, and split audits pass.
- [ ] Failed simulations or excluded records were deleted, overwritten, or omitted without a complete ledger and approved rule.
- [ ] Raw artifacts are mutable, or the processed version, schema, split manifest, manifest hashes, row/group counts, or regeneration procedure required for release is missing.
- [ ] A row-held-out result is represented as OOD evidence without a contract-defined group or domain holdout that supports that claim.
- [ ] OOD axes, training support, the declared OOD evaluation envelope, gap or separation rules, boundary ownership, or evaluated cross-axis combinations are missing or ambiguous, or a contract-declared OOD input is rejected instead of being labeled, traced, inferred, and evaluated.
- [ ] Evidence required by the resolved contract for the current stage is missing. Design-inapplicable evidence may be N/A only with its exact contract/design basis and handoff-reviewer agreement.
