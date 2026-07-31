# Evaluation and Statistics Execution Checklist

Use this checklist when designing, running, reviewing, or handing off statistical evaluation, ablation, robustness, ID/OOD, or uncertainty work. A checked item means that the named evidence exists and is linked from the evaluation manifest. A favorable aggregate, one seed, or a visually convincing plot is never formal acceptance evidence.

## Applicability and N/A

- Execute only checklist items applicable to the resolved task contract and current stage.
- Mark an item N/A only with the exact contract, design, or stage basis and handoff-reviewer agreement.
- Evidence that the resolved design or current stage is designed not to produce may be N/A. Evidence expected by the resolved contract but missing is a stop condition.
- Do not demand confirmatory final-test conclusions during a development or pilot stage, but label that work unaccepted and not assessed for confirmatory claims.
- N/A cannot waive the current stage's core statistical design, independence unit, failure accounting, raw run evidence, frozen evaluation evidence, or access history.
- N/A cannot cancel or bypass the dataset and machine-learning final-test seal. A reused, exposed, or selected-on test remains subject to the fresh-test-or-exploratory rule.

## Pre-registration and Freeze

- [ ] Record the task, claim family, estimand, population or evaluation envelope, comparator, and confirmatory or exploratory status before inspecting locked final-test outcomes.
- [ ] Predeclare every primary metric and distinguish secondary, diagnostic, and descriptive metrics. For each metric, define its formula, units, aggregation unit and level, direction of improvement, and contract-authorized decision threshold.
- [ ] Define the hypothesis or decision rule for every formal claim, including permitted outcome-contingent reporting, without inventing an undeclared threshold, significance level, confidence level, seed count, or repeat count.
- [ ] Freeze and content-hash the analysis plan, resolved configuration, evaluator command, metric implementation, selection registry, subgroup definitions, failure rules, and report template before final-test access.
- [ ] Include in the selection registry every model, checkpoint, seed, retry policy, preprocessing choice, threshold, candidate budget, ablation, metric, aggregation level, subgroup, OOD definition, baseline, statistical procedure, and multiplicity family that can influence a reported claim.
- [ ] Separate validation-based tuning and selection from frozen final evaluation. Use validation information only under the predeclared tuning budget and selection rule.
- [ ] Preserve the dataset and machine-learning access ledger. Log each final-test read with time, actor or execution identity, purpose, command and command hash, input identities, frozen-plan hashes, and produced-artifact hashes.
- [ ] After final-test access, route any affected model, checkpoint, seed, threshold, preprocessing, subgroup, OOD rule, metric, statistical method, exclusion, or reporting-rule change to a new previously untouched locked test or label all affected results and claims exploratory.
- [ ] Treat a compliant, stateless run of the frozen evaluator as an authorized access event, not as permission to tune or select from its outcomes.

## Unit of Independence

- [ ] Name the causal unit that can vary independently for the claim, such as a base structure, independently manufactured specimen, or independently generated experimental unit.
- [ ] Build an identity map from every evaluated row, precision variant, augmentation, curve, time-series point, seed output, and specimen measurement to its causal unit.
- [ ] Compute per-structure or per-specimen summaries first when those are the independent units; aggregate those summaries only at the predeclared next level.
- [ ] Do not count curve points, time-series samples, precision-expanded rows, augmentations, correlated outputs, repeated post-processing, or repeated predictions of one structure as independent observations.
- [ ] Distinguish algorithmic repetition across seeds or retries from independent data or specimen replication. State which source of variability each repetition estimates.
- [ ] Preserve pairing identities for paired comparisons and justify the pairing. When pairing is incomplete, use the predeclared missing-pair rule and report the lost pairs.
- [ ] Model or summarize hierarchy and clustering at the appropriate causal level when structures, specimens, material batches, manufacturing runs, or test sessions are nested.

## ID and OOD Definitions

- [ ] Define ID membership by the frozen causal-group and training-support rule, not merely by row membership or numerical proximity.
- [ ] For every OOD claim, record the OOD axis, training-support boundary, declared OOD evaluation envelope, gap or separation rule, boundary ownership, and permitted cross-axis combinations before evaluation.
- [ ] Prove the required separation at the causal-unit level and link every evaluated unit to its ID, single-axis OOD, cross-axis OOD, or unsupported classification.
- [ ] Keep contract-declared OOD inputs inferable, labeled, traceable, and included in evaluation. Reserve rejection for inputs outside both the supported ID region and declared OOD envelope.
- [ ] Report each OOD axis and predeclared cross-axis subgroup separately before any pooled OOD summary.
- [ ] Do not manufacture OOD evidence by excluding difficult rows, changing decimal precision, holding out derived rows of a seen structure, or selecting post hoc hard cases.
- [ ] Do not redefine support, gaps, boundaries, axes, or subgroups after viewing outcomes. Any affected analysis requires a fresh untouched test or exploratory labeling.

## Fair Comparison

- [ ] Evaluate candidates, baselines, and ablations on the same frozen split identities, causal-unit set, target definitions, units, preprocessing state, metric implementation, and failure policy unless the contract explicitly authorizes and explains a difference.
- [ ] Record all comparison-relevant information: training and inference compute, data exposure, candidate and checkpoint budget, seed and repeat policy, retry policy, tuning space, selection rule, and evaluation command.
- [ ] Apply the same validation-based selection discipline to candidate and baseline methods while permitting predeclared method-appropriate tuning needed for competent baselines.
- [ ] Report trainable parameter counts and other contract-relevant capacity measures. Document rather than conceal unavoidable parameter, capacity, runtime, memory, or budget mismatches.
- [ ] Execute every predeclared ablation under the same applicable split, preprocessing, budget, selection, and evaluation protocol. Record any scientifically required exception and its effect on the claim.
- [ ] Do not strengthen a conclusion by comparing a selected candidate against an untuned, failed, or selectively reported baseline.
- [ ] Preserve every attempted configuration and candidate considered by the selection process so the effective search and selection budget is auditable.

## Metrics and Failure Accounting

- [ ] Compute metric inputs from immutable predictions, targets, identities, units, and validity flags produced by the frozen evaluator.
- [ ] Calculate per-structure or per-specimen results before cross-unit aggregation and retain the individual-unit table underlying every summary.
- [ ] Report every declared seed and repeat, not only the best or successful subset, using the frozen aggregation and retry policy.
- [ ] Include all failed runs, nonfinite outputs, invalid generations, infeasible candidates, missing predictions, solver rejections, and evaluation errors in a disposition ledger.
- [ ] Define denominator, censoring, invalidity, failure, retry, and exclusion rules before outcome inspection. Report counts and rates by method and predeclared subgroup.
- [ ] Distinguish model failure, generation invalidity, simulation or solver rejection, data-quality exclusion, and infrastructure failure; do not silently merge these categories.
- [ ] Apply penalties, worst-case assignments, separate failure-rate reporting, or exclusions only as predeclared by the contract, and show how each disposition changes the estimand.
- [ ] Report primary and secondary metrics with their direction, units, aggregation level, denominators, and threshold status. Keep diagnostic metrics visibly non-confirmatory.

## Uncertainty and Tests

- [ ] Report the contract-required center and dispersion, including mean, median, and an appropriate dispersion summary when those quantities are defined for the estimand.
- [ ] Report confidence intervals and effect sizes using the predeclared methods and contract-supplied confidence level; do not choose the interval level after observing results.
- [ ] Resample or test at the independent structure or specimen level. Never bootstrap curve points, time-series points, precision-expanded rows, or correlated derivatives as if they were independent units.
- [ ] Use paired tests or paired bootstrap only when methods are evaluated on the same independent units and the frozen pairing map supports that estimand.
- [ ] Check and report test assumptions at the appropriate unit. If assumptions fail, use only the predeclared alternative or downgrade the affected inference to exploratory.
- [ ] Report uncertainty and formal comparisons by method and each predeclared OOD subgroup, including cross-axis groups where applicable, rather than relying only on pooled results.
- [ ] Define the multiple-comparison family and contract-approved control procedure before final-test access. Report every comparison in the family, including inconclusive and adverse results.
- [ ] Account for model, checkpoint, hyperparameter, seed, subgroup, metric, and report selection in the inferential claim. Use a selection-aware procedure when predeclared; otherwise narrow or label the selected analysis exploratory.
- [ ] Distinguish statistical uncertainty from variability across seeds, structures, specimens, batches, and measurement or simulation noise rather than collapsing unlike sources without justification.

## Reporting and Handoff

- [ ] State for each claim whether it is confirmatory, exploratory, pilot-only, descriptive, supported, refuted, or inconclusive under the frozen rule.
- [ ] Provide a complete table of per-unit results, all seed and repeat results, subgroup labels, metric inputs, validity flags, failures, exclusions, and dispositions.
- [ ] Report mean, median, dispersion, confidence interval, effect size, formal-test result, denominator, and failure rate as applicable to each predeclared method and subgroup.
- [ ] Link every figure and table to the exact immutable prediction file, unit-identity map, evaluation script and revision, resolved configuration, and regeneration command.
- [ ] Provide ID/OOD support definitions, axis and boundary records, gap evidence, cross-axis labels, and subgroup counts at the independent-unit level.
- [ ] Provide fairness evidence covering split, preprocessing, compute, capacity, tuning, candidate budget, selection, seeds, repeats, ablations, retries, and failures.
- [ ] Provide analysis-plan, selection-registry, evaluator-command, dataset, split, preprocessing, checkpoint, prediction, result, and report hashes.
- [ ] Reconcile the final-test access ledger and state whether evidence remains confirmatory, moved to a new untouched locked test, or was downgraded to exploratory.
- [ ] Record every N/A decision with its precise basis and reviewer agreement, and list unresolved downstream evidence without implying acceptance.

## Stop Conditions

Stop evaluation, handoff, or formal acceptance as appropriate; preserve raw outputs and mark affected claims unresolved when any of the following occurs:

- [ ] A primary or secondary metric, aggregation unit or level, improvement direction, decision threshold, estimand, hypothesis family, or reporting rule required by the contract was not declared before final-test access.
- [ ] A result treats rows, curve points, time-series samples, precision variants, augmentations, or correlated derivatives as independent structures or specimens.
- [ ] ID/OOD causal identity, axis, training support, evaluation envelope, gap or separation rule, boundary ownership, or cross-axis combinations are missing, ambiguous, changed post hoc, or violated.
- [ ] OOD is created by row exclusion, precision changes, derived rows of seen structures, or outcome-selected hard cases, or declared-OOD inputs are rejected rather than evaluated.
- [ ] Candidate and baseline comparisons use incompatible splits, preprocessing, units, targets, metric code, evaluation protocol, failure rules, or undisclosed selection and compute budgets.
- [ ] Required seeds, repeats, candidates, ablations, failed runs, invalid generations, missing predictions, solver rejections, retries, or exclusions are omitted or selectively reported.
- [ ] A bootstrap, paired test, or interval calculation resamples below the independent structure or specimen level, violates the frozen pairing map, or uses a post hoc method or confidence level.
- [ ] Parameter, capacity, data-exposure, compute, tuning, or selection mismatches required for interpretation are unrecorded.
- [ ] Multiple comparisons or outcome-dependent selection affect a formal claim without the predeclared control, selection-aware analysis, claim narrowing, or exploratory label.
- [ ] Final-test information influences tuning, selection, thresholding, exclusions, subgroups, metrics, statistical methods, or reporting without a new untouched locked test or exploratory downgrade.
- [ ] A final-test access event lacks a complete ledger entry, or the evaluator differs from the frozen command, analysis plan, metric implementation, or selection registry.
- [ ] Formal conclusions are drawn from smoke tests, pilot runs, a best seed, favorable subgroups, or aggregate-only evidence.
- [ ] Evidence required by the resolved contract for the current stage is missing. Design-inapplicable evidence may be N/A only with its exact basis and handoff-reviewer agreement; current-stage core statistical or raw run evidence cannot be waived.
