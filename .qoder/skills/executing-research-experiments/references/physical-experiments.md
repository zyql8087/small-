# Physical Experiments Execution Checklist

Use this checklist when manufacturing, inspecting, testing, processing, reviewing, or handing off physical specimens. A checked item means that the named direct evidence exists and is linked from the physical-experiment manifest. A single specimen, a smooth curve, or agreement with one simulation is never formal validation evidence.

## Applicability and N/A

- Execute only checklist items applicable to the resolved task contract and current stage.
- Mark an item N/A only with the exact contract, design, or stage basis and handoff-reviewer agreement.
- Evidence that the resolved physical design or current stage is designed not to produce may be N/A. Evidence expected by the resolved contract but missing is a stop condition.
- A staged physical-validation program may legitimately remain at pilot stage. Label pilot evidence explicitly and do not represent it as confirmatory repeatability, agreement, or acceptance.
- N/A cannot waive the current stage's specimen identity, manufacturing provenance, applicable calibration and protocol records, raw machine exports, processing provenance, individual outcomes, failures, or exclusions.
- N/A cannot waive the confirmatory specimen-and-test seal, confirmatory event ledger, or fresh-test-or-exploratory rule when the resolved contract or current stage makes a confirmatory claim.

## Specimen Traceability

- [ ] Assign an immutable specimen ID before manufacture and use it in every file name, label, image, inspection record, test record, processed curve, and disposition.
- [ ] Map each specimen ID to the exact CAD or STL artifact and content hash, design-parameter record, geometry revision, coordinate convention, scale and units, and build orientation.
- [ ] Record printer or manufacturing-system identity, material identity and batch or lot, feedstock condition where relevant, build job or process run, process configuration, and operator or execution identity.
- [ ] Preserve a traceable identity map between simulation design, manufactured specimen, inspection record, physical test, raw machine export, processed result, and statistical observation.
- [ ] Assign related-specimen, batch, build, and test-session identifiers needed to distinguish independent replication from nested or correlated replication.
- [ ] Photograph or otherwise document each specimen with its ID visible before testing and after failure or termination, while preserving the unedited source images.
- [ ] Record every relabeling, replacement, remanufacture, or duplicate identifier in an append-only mapping rather than reusing or silently changing an ID.

## Manufacturing and Inspection

- [ ] Freeze the applicable manufacturing recipe before producing confirmatory specimens, including orientation, placement or nesting rule, supports, process settings, post-processing, and acceptance inspection.
- [ ] Define, freeze, and content-hash the a priori specimen eligibility, inclusion, allocation, manufacturing-quality-control, and exclusion rules before accessing specimen-specific inspection, defect, eligibility, or confirmatory outcome information. State the required attributes, frozen measurement procedure and timing, mechanical decision logic, allocator blinding, batch and blocking constraints, and every possible disposition.
- [ ] Record the actual manufacturing configuration and deviations for each build and specimen; do not substitute nominal settings for observed provenance.
- [ ] Measure and record contract-required dimensions, mass, density or other derived quantities, measurement units, instrument identity, resolution, calibration status, and measurement procedure.
- [ ] Record conditioning, storage, drying, curing, aging, temperature or humidity exposure, and elapsed-time requirements where applicable to the contract.
- [ ] Inspect and record visible defects, incomplete features, warping, delamination, support damage, surface anomalies, contamination, and other contract-defined defect classes before testing.
- [ ] Preserve inspection photographs, measurement exports, notes, pass/fail outcomes, and the predeclared disposition for every specimen, including specimens never tested.
- [ ] Classify manufacturing or printing failures separately from test failures. Preserve the attempted specimen identity, process evidence, failure stage, and reason in both cases.
- [ ] Do not discard a specimen because its measured dimensions, mass, appearance, or likely performance are unfavorable unless the frozen exclusion rule requires that disposition.

## Test Protocol

- [ ] Before the first access to any confirmatory outcome, freeze and content-hash the protocol; manufacturing acceptance and quality-control rules; processing, filtering, and smoothing rules; exclusion and outlier rules; metrics and aggregation; simulation-experiment alignment; analysis and statistical procedures; and acceptance, claim, and reporting rules.
- [ ] Define and record each specimen-manufacture event as production of a physical specimen from the identified frozen CAD or design revision under a frozen manufacturing recipe, process configuration, and print or build orientation.
- [ ] Define and record each specimen-allocation-and-sealing event as the pre-outcome assignment of an immutable specimen ID to the confirmatory test set or a named confirmatory-reserve stratum, with eligibility, independence, batch and blocking role, intended protocol, storage controls, and seal status fixed.
- [ ] Define and record each specimen-handling event as any conditioning, storage change, transport, post-processing, inspection, preparation, mounting, or other physical interaction after manufacture, including actor, time, purpose, condition, and deviation.
- [ ] Define and record each test-execution event as the first or subsequent application or attempted application of a test protocol to a specimen, including setup, preload, loading or stimulation, acquisition, interruption, termination, and produced raw artifacts.
- [ ] Define outcome access as any human or adaptive-system exposure to a confirmatory raw export, processed value, curve, image, failure state, disposition, comparison, statistic, or other result capable of informing a frozen rule or claim. Seal the confirmatory specimen and test identities under the contract before the first such access.
- [ ] Define qualification-information access as any human or adaptive-system exposure to specimen-specific inspection, defect, measured-attribute, eligibility, inclusion, manufacturing-quality-control, exclusion, or disposition information, whether or not a test outcome has been accessed.
- [ ] Enter every specimen manufacture, allocation and sealing, handling, test execution, qualification-information-access, and outcome-access event in the append-only confirmatory event ledger with time, actor or execution identity, purpose, specimen and test identities, event-specific state, frozen-rule hashes, command or viewing route where applicable, and input and produced-artifact hashes. Any outcome-access listing is a subset or view of this event ledger, not a separate mutable ledger.
- [ ] After any confirmatory outcome is exposed, route every change to or selection among the protocol, manufacturing acceptance or quality control, processing, filtering, smoothing, exclusions, outliers, metrics, aggregation, alignment, analysis, statistics, acceptance, claims, or reporting through a fresh confirmatory set or an explicit exploratory downgrade.
- [ ] If post-outcome adaptation changes a manufacturing recipe or process, print or build orientation, physical handling, or any manufacturing acceptance, quality-control, eligibility, inclusion, allocation, or exclusion rule that can affect how the physical article is produced or physically treated, renew confirmation only with independent specimens manufactured under the newly frozen rules and independently allocated under the contract's batch and independence design.
- [ ] Do not choose from a sealed reserve by using inspection, defect, eligibility, manufacturing-quality-control, exclusion, disposition, or outcome information observed before or after a rule change.
- [ ] If a new or changed eligibility, inclusion, allocation, manufacturing-quality-control, or exclusion rule depends on an attribute not completely recorded before outcome access under the frozen measurement procedure, or cannot be applied to the sealed reserve without revealing specimen outcomes or comparison-group selection information, renew confirmation only with independent specimens manufactured and allocated under the newly frozen rules.
- [ ] A sealed reserve may remain eligible after such a rule change only when every required attribute was completely recorded before outcome access under the frozen measurement procedure and an independent blinded allocator, with no outcome or comparison-group selection information, can apply the frozen rule mechanically to all reserve specimens. Record every included and excluded reserve specimen and the rule-based reason while preserving the contract's independence, batch, and blocking design.
- [ ] A reserve specimen whose inspection, defect, eligibility, manufacturing-quality-control, exclusion, disposition, or outcome information informed post hoc selection cannot serve as fresh evidence for the affected claim.
- [ ] If post-outcome adaptation changes only processing, analysis, statistics, or reporting and cannot affect physical manufacture or a priori specimen inclusion, a previously manufactured specimen is eligible only when it was allocated to a named confirmatory-reserve stratum and sealed before outcome access, remains untested and outcome-unaccessed, was not used for adaptation or selection, and satisfies the contract's independence and batch design.
- [ ] If post-outcome adaptation changes the test protocol, fixture, preload, loading, acquisition, termination, or another test-execution rule without changing the physical article or a priori inclusion, a sealed eligible reserve specimen may support renewed confirmation only through its first test execution under the newly frozen protocol. A previously tested specimen cannot be fresh evidence for the affected claim.
- [ ] An assertion that a post-outcome change is unrelated to the observed result does not restore the prior confirmatory seal or relax the applicable manufacturing, reserve, or first-test requirement.
- [ ] Record the testing-machine identity, controller and acquisition software versions, load-cell or force-sensor identity and range, displacement source, and any extensometer or auxiliary sensor used.
- [ ] Verify and archive calibration status and applicable pre-test checks for the machine, load cell, displacement channel, and auxiliary sensors without inventing missing calibration evidence.
- [ ] Define and record fixture, platen, alignment, contact, lubrication or friction treatment, preload or seating procedure, control mode, loading rate, and sign convention.
- [ ] Define force, displacement, stress, strain, energy, stiffness, plateau, peak, densification, or other curve quantities with units, reference geometry, and computation windows before confirmatory testing.
- [ ] Predefine acquisition channels, sampling policy, synchronization, zeroing, filtering policy, termination criteria, safety limits, and operator interventions.
- [ ] Record the actual environmental conditions required by the contract, including temperature and humidity where applicable, together with test date, time, operator, and session identity.
- [ ] Predefine the specimen order and any blocking, randomization, or blinding procedure applicable to manufacture, inspection, testing, processing, or outcome assessment. Record deviations and unblinding events.
- [ ] Use blind labels or randomized test order when the contract identifies operator, sequence, batch, warm-up, drift, or analysis bias as a relevant risk; otherwise record the exact basis for N/A.
- [ ] Run protocol qualification or pilot tests under explicit pilot labels. Freeze any confirmatory protocol changes before confirmatory specimen outcomes are inspected.

## Raw Data and Processing

- [ ] Preserve the original machine export for every attempted test as immutable, read-only or content-addressed raw evidence, including headers, channel names, units, timestamps, and acquisition metadata.
- [ ] Compute and record cryptographic hashes, storage locations, file sizes, and specimen-to-file mappings for raw exports and unedited photographs.
- [ ] Never replace a raw export with a cleaned, cropped, zeroed, smoothed, resampled, or manually edited curve.
- [ ] Implement processing as a reproducible script or declared pipeline with version, environment, resolved configuration, command, input hashes, and output hashes.
- [ ] Predefine zero correction, compliance correction, baseline removal, alignment, resampling, smoothing, filtering, truncation, segmentation, and derived-metric rules before confirmatory outcome inspection.
- [ ] Retain noise, spikes, dropouts, outliers, and anomalous segments in the immutable raw data. Apply only the preregistered processing or exclusion rule and report the affected points, intervals, and specimens.
- [ ] Preserve both individual raw and processed curves. Show processing effects and do not present a smoothed aggregate as if it were a raw or individual result.
- [ ] Record every manual action or override with actor, time, reason, affected specimen and interval, before-and-after artifact hashes, and contract authorization.
- [ ] Validate the processing script on known or independently checked cases for units, signs, zeroing, integration, window boundaries, and derived quantities required by the contract.

## Repeats Exclusions and Statistics

- [ ] Predefine the independent specimen unit, repeat design, blocking factors, batch structure, failure categories, retry or replacement policy, exclusion rules, and statistical aggregation before confirmatory testing.
- [ ] Report every manufactured specimen and attempted test, including untested, interrupted, invalid, manufacturing-failed, test-failed, excluded, and successfully completed specimens.
- [ ] Give every exclusion the frozen rule, direct evidence, decision time, decision maker or process identity, and effect on denominators. Preserve excluded raw data.
- [ ] Distinguish manufacturing failure, fixture or alignment failure, acquisition failure, protocol deviation, safety termination, and specimen mechanical failure.
- [ ] Treat each independently manufactured specimen as one experimental observation when that is the causal unit. Time-series points, curve samples, repeated derived metrics, photographs, or reprocessed versions are not repeats.
- [ ] Treat repeated tests on the same specimen according to the predeclared repeated-measure or damage-history rule; do not relabel them as independent specimens.
- [ ] Compute specimen-level metrics first and estimate uncertainty across independent specimens under the contract-approved hierarchical or paired design.
- [ ] Report individual specimen curves and outcomes before aggregate center, dispersion, intervals, effect sizes, or formal tests required by the contract.
- [ ] Do not infer repeatability or formal acceptance from a single specimen, an aggregate curve without individual traces, visually smooth behavior, or deletion of noisy segments.
- [ ] Keep pilot results separate from confirmatory repeats. Pilot specimens may inform a later frozen protocol only when the later confirmatory sample and analysis remain independent as specified by the contract.
- [ ] Keep pilot and protocol-qualification specimen IDs, test IDs, artifacts, and access histories isolated from the confirmatory set. Never relabel, promote, or reuse a pilot specimen, test, or outcome as confirmatory evidence.

## Simulation-Experiment Alignment

- [ ] Map each physical specimen and test to the exact simulation geometry, mesh or model revision, configuration, job identity, and output artifacts used for comparison.
- [ ] Verify common units, coordinate axes, loading direction, sign convention, reference area and length, displacement or strain definition, force or stress definition, and energy normalization.
- [ ] Reconcile as-designed, as-manufactured, and simulated geometry. Record whether simulation uses nominal geometry, measured dimensions, inspected geometry, or another contract-approved representation.
- [ ] Align boundary conditions, fixture contact, platen motion, constraints, preload, loading rate or rate assumption, termination, and environmental assumptions to the physical protocol, and document unavoidable mismatches.
- [ ] Predefine curve registration, zero alignment, interpolation, comparison window, characteristic points, error metrics, and failure or termination treatment before confirmatory comparison.
- [ ] Preserve one-to-one or declared group-level pairing identity between simulation and experimental observations; do not pair by post hoc visual similarity or favorable outcome.
- [ ] Report individual paired curves and metrics, mismatch sources, failed simulations, solver rejections, physical failures, and missing pairs before aggregate agreement claims.
- [ ] Do not claim validation from visually similar or smoothed curves without traceable identity, compatible definitions, quantitative metrics, uncertainty, and the contract-defined acceptance rule.

## Handoff Evidence

- [ ] Provide the specimen manifest linking IDs to CAD or STL hashes, design parameters, orientation, machine, material batch, process run, conditioning, inspection, test, raw exports, processed outputs, and simulation pairing.
- [ ] Provide actual manufacturing records, dimensional and mass measurements, defect records, conditioning history, photographs, and the disposition of every specimen.
- [ ] Provide calibration certificates or status evidence, test-machine and sensor identities, fixture and alignment records, full protocol, environmental log, test order, blinding or randomization record where applicable, and deviations.
- [ ] Provide immutable raw machine exports and source photographs with hashes, together with the versioned processing script, environment, configuration, exact regeneration command, and processed-output hashes.
- [ ] Provide individual raw and processed curves, per-specimen metrics, aggregate statistics and uncertainty, all failures and exclusions, denominators, and the complete disposition ledger.
- [ ] Provide simulation-experiment mapping, common unit and definition table, geometry and boundary-condition alignment, individual paired curves, quantitative comparison results, and unresolved mismatches.
- [ ] Label each result as pilot, protocol qualification, exploratory, or confirmatory and state the exact claims the current stage does and does not support.
- [ ] Provide the confirmatory freeze package and seal, including hashes of every frozen rule family, the sealed specimen and test identities, and the complete event ledger with manufacture, allocation and sealing, handling, test execution, qualification-information access, and the first outcome-access event identified.
- [ ] Disclose every post-access rule change or selection, its affected claims, and whether it changes the physical article, a priori eligibility or inclusion, test execution, or only processing, analysis, statistics, or reporting. For each, identify the newly manufactured independent specimens or eligible sealed reserve specimens and first-test events used for renewed confirmation, or record the explicit exploratory downgrade.
- [ ] For every changed eligibility, inclusion, allocation, manufacturing-quality-control, or exclusion rule, provide the frozen attribute definitions and measurement records, rule and revision hash, allocation and seal history, allocator identity and blinding evidence, mechanical decision output for every reserve specimen, all inclusion and exclusion reasons, and preservation of the independence, batch, and blocking design.
- [ ] Record each N/A decision with its precise contract, design, or stage basis and handoff-reviewer agreement. List missing future-stage evidence without implying present acceptance.

## Stop Conditions

Stop manufacturing, testing, processing, handoff, or formal acceptance as appropriate; preserve all existing evidence and mark affected claims unresolved when any of the following occurs:

- [ ] A specimen cannot be traced to its CAD or STL hash, design parameters, orientation, manufacturing system, material batch, process record, inspection, test, raw export, or simulation pairing required by the contract.
- [ ] Required actual dimensions, mass, conditioning history, defect inspection, manufacturing deviations, or specimen photographs are missing or silently replaced by nominal values.
- [ ] Applicable machine, load-cell, displacement, or sensor calibration evidence is missing, expired under the contract, or contradicted by pre-test checks.
- [ ] Fixture, preload, loading rate, sampling policy, termination criteria, environment, units, signs, or curve definitions required for interpretation are absent, ambiguous, or changed after outcome inspection.
- [ ] Raw machine exports or source photographs are missing, mutable, overwritten, manually edited, or cannot be mapped to specimen IDs.
- [ ] Processed results cannot be regenerated from immutable raw inputs by the versioned script and resolved configuration, or undocumented manual processing affected an outcome.
- [ ] Noise, outliers, curve segments, specimens, failures, or exclusions are deleted or hidden instead of preserved and handled by the preregistered rule.
- [ ] Manufacturing failures and test failures are conflated, or any attempted specimen or test is omitted from the manifest, denominator, and disposition ledger.
- [ ] Time-series or curve points are counted as specimen repeats, repeat tests on one specimen are treated as independent without authority, or specimen-level uncertainty is absent where required.
- [ ] A single specimen, smooth or aggregate-only curve, favorable pair, or noise-segment deletion is offered as formal repeatability, agreement, validation, or acceptance evidence.
- [ ] Simulation and experiment use incompatible or undocumented units, geometry, boundary conditions, loading definitions, curve definitions, comparison windows, or pairing identities.
- [ ] Pilot or protocol-qualification evidence is represented as confirmatory, or confirmatory protocol, exclusion, processing, or analysis rules were selected after inspecting outcomes.
- [ ] A confirmatory specimen-and-test seal, required frozen-rule hash, first-access record, or complete event ledger for manufacture, allocation and sealing, handling, test execution, qualification-information access, and outcome access is missing, ambiguous, or inconsistent with the evidence.
- [ ] After outcome access, a manufacturing recipe or process, print or build orientation, physical handling, or a rule affecting how the physical article is produced or treated is changed, but the affected claim relies on specimens not independently manufactured and allocated under the newly frozen rules and contract-defined batch design, without an explicit exploratory downgrade.
- [ ] After outcome or qualification information is accessed, eligibility, inclusion, allocation, manufacturing-quality-control, or exclusion rules are changed and reserve specimens are chosen using observed inspection, defect, eligibility, disposition, comparison-group selection, or outcome information, without an explicit exploratory downgrade.
- [ ] A changed eligibility, inclusion, allocation, manufacturing-quality-control, or exclusion rule depends on an attribute not completely recorded before outcome access under the frozen measurement procedure, or cannot be applied by an independent blinded allocator without outcome or comparison-group selection information, but the affected claim uses the existing reserve rather than newly manufactured and independently allocated specimens or an explicit exploratory downgrade.
- [ ] A reserve specimen whose inspection, defect, eligibility, manufacturing-quality-control, exclusion, disposition, or outcome information informed post hoc selection is presented as fresh evidence for an affected claim.
- [ ] After outcome access, a processing, analysis, statistics, or reporting rule is changed and the affected claim relies on a previously manufactured specimen that was not allocated and sealed as confirmatory reserve before access, was already tested or outcome-accessed, informed adaptation or selection, or violates the contract's independence or batch design, without an explicit exploratory downgrade.
- [ ] After outcome access, a test protocol, fixture, preload, loading, acquisition, termination, or other test-execution rule is changed and the affected claim reuses an already tested specimen or lacks an eligible sealed reserve specimen's first test under the newly frozen protocol, without an explicit exploratory downgrade.
- [ ] After confirmatory outcome access, any affected rule is changed or selected and the same accessed results remain the basis of a confirmatory claim without the applicable fresh evidence and new seal, or without an explicit exploratory downgrade.
- [ ] A post-outcome adaptation is treated as harmless or outcome-independent to bypass the fresh-test-or-exploratory rule, or pilot specimens, tests, or outcomes are relabeled, promoted, or reused as confirmatory evidence.
- [ ] N/A is used to bypass a confirmatory specimen-and-test seal, event-ledger entry, fresh confirmatory set, or exploratory downgrade required for the current-stage claim.
- [ ] Applicable blinding, randomized order, or bias-control evidence required by the contract is absent without an exact N/A basis and reviewer agreement.
- [ ] Evidence required by the resolved contract for the current stage is missing. Design-inapplicable evidence may be N/A only with its exact basis and handoff-reviewer agreement; current-stage raw data, traceability, or protocol evidence cannot be waived.
