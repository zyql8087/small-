# Abaqus Simulation Execution Checklist

Use this checklist for Abaqus model construction, job submission, monitoring, extraction, and acceptance. A checked item means that the named record is archived and linked from the run manifest. An ODB or a smooth curve alone is never acceptance evidence.

## Applicability and N/A

- Execute only checklist items applicable to the task contract and current stage.
- N/A is not a shortcut: record the exact contract/design basis and require reviewer agreement at handoff.
- Evidence that the selected solver/procedure/stage/launcher is designed not to produce is legitimately N/A; evidence expected by the resolved contract but missing is a stop condition.
- Do not demand downstream submission/ODB/extraction/convergence evidence for a model/preflight-only stage, but do record downstream work as unaccepted/not assessed.
- Apply N/A only to evidence the resolved task configuration does not require or produce. It cannot waive model identity, input validity, solver completion, provenance, physics checks, or other evidence required for the current stage.

## Model Contract

- [ ] Record the approved Abaqus release, solver product and procedure, platform, and any user subroutine compiler/runtime requirements.
- [ ] Record one coherent unit system and the units of every geometry, material, load, output, and extracted quantity. Save the interface conversion table.
- [ ] Record material models, constants, dependencies, orientations, sections, and assignment regions with their approved source and version.
- [ ] Record all independent parameters, derived parameters, admissible domains, and the method used to instantiate them. Preserve the resolved parameter record per sample.
- [ ] Record the source geometry artifact hash and the geometry import, healing, partitioning, and assembly settings.
- [ ] Record element family, formulation, order, integration choice, hourglass or locking controls where relevant, section controls, and mesh-generation settings.
- [ ] Record interaction, contact formulation, surface definitions, enforcement method, friction law and coefficients, clearance or overclosure handling, and any contact controls.
- [ ] Record analysis steps, time periods, increment controls, solver controls, stabilization settings, and nonlinear geometry setting. Record restart policy only when restart or recovery is enabled or required by the task configuration; otherwise preserve the N/A basis.
- [ ] Record boundary conditions, constraints, couplings, loads, amplitudes, reference points, coordinate systems, and sign conventions with region identities.
- [ ] Record requested field and history outputs, regions, variables, frequency, precision, and the downstream quantity each output supports.
- [ ] Prove a bijection among job ID, sample ID, and produced artifact IDs. When the task generates a dataset and its contract requires a dataset ID, include dataset ID in the bijection; otherwise do not fabricate a dataset identity. Save forward and reverse mapping checks and reject duplicates, omissions, or aliases.

## Preflight

- [ ] Validate the resolved parameter record against the approved schema and hashes before generating an input deck.
- [ ] Run geometry quality checks for scale, units, invalid or sliver entities, gaps, intersections, normals, component count, and region or set integrity. Save the report and disposition.
- [ ] Run mesh quality checks using the predefined project metrics, including element count by type, connectivity, free or duplicate entities, distorted elements, aspect or angle measures, Jacobian-related measures where applicable, and set or surface coverage. Save raw results and the approved decision.
- [ ] Verify material, section, orientation, interaction, boundary-condition, load, output, and step assignments against expected entity counts and named regions.
- [ ] Verify that loads and constraints do not unintentionally under-constrain, over-constrain, or suppress the intended response. Save model-check output and an annotated region summary.
- [ ] Perform Abaqus input or data checks under the target release. Archive warnings and errors with their disposition; do not suppress unexplained warnings.
- [ ] Archive the fully resolved INP and resolved configuration used for submission, together with their hashes and the generation code revision.
- [ ] Estimate CPU, memory, wall time, output size, and scratch demand from a documented basis and compare them with the approved execution envelope.

## Submission and HPC

- [ ] Record requested CPUs, memory, accelerators if used, wall time, scratch path and capacity, environment modules or container identity, and any launcher-specific settings. For scheduler execution, also record queue or partition and host constraints; for local execution, record the host and process limits.
- [ ] When the task configuration depends on managed license checkout, confirm required Abaqus license features and the token availability policy, and archive license checkout failures rather than repeatedly resubmitting without classification. Otherwise record why license evidence is not applicable.
- [ ] Record the exact Abaqus submission command and the scheduler command or local-launcher command or script hash, working directory, environment, and returned scheduler job ID or process ID.
- [ ] Preserve scheduler status or local-launcher/process status transitions, timestamps, assigned host or node information, resource usage, and final exit status.
- [ ] When restart or recovery is enabled or required by the task configuration, record restart write frequency, restart source job and increment, and the relationship between original and restarted job IDs. Otherwise record the configuration basis for N/A.
- [ ] Isolate each job's working, scratch, and output paths so concurrent jobs cannot overwrite or consume another sample's files.
- [ ] Record every resubmission, changed resource request, restart, or model modification as a new attempt linked to the same sample, never as an overwritten history.

## Completion Is Not File Existence

- [ ] Require agreement among scheduler status or local-launcher/process status, Abaqus process exit status, and terminal solver status. Archive disagreements as failures needing investigation.
- [ ] Before submission, list the solver status files expected from the selected Abaqus release, solver, procedure, and launcher. For each applicable produced status file, including `.sta`, `.msg`, or `.dat` when generated, parse and preserve completion markers, errors, warnings, cutbacks, numerical difficulties, and termination reason. Record a contract or design explanation for each expected file that is not produced; an unexplained missing contract-required file is a stop condition.
- [ ] Confirm that all required steps and frames completed and that requested history and field outputs are present and readable.
- [ ] Treat an ODB as potentially partial: its existence or openability does not establish successful completion.
- [ ] Inspect element distortion, excessive deformation, contact convergence or penetration, zero pivots, negative eigenvalues where relevant, numerical singularities, and other solver warnings. Record counts, locations, increments, and dispositions.
- [ ] Inspect increment history, attempted and completed increments, cutbacks, equilibrium iterations, and termination point. Save the summary rather than reporting only elapsed time.
- [ ] Classify each attempt as successful, failed, aborted, preempted, timed out, resource-exhausted, extraction-failed, license-blocked when license management applies, or another approved category, with evidence for the classification.

## Convergence and Reproducibility

- [ ] When mesh convergence is required by the resolved contract, define the response metric, comparison method, refinement sequence, and acceptance tolerance before evaluating production results. Otherwise record the contract basis for N/A and reviewer agreement.
- [ ] For a contract-required convergence study, preserve a table containing mesh identity and hash, element counts, relevant mesh scale, response metric, relative or absolute comparison as defined, solver status, and resource cost.
- [ ] For a contract-required convergence study, apply the predefined metric and tolerance without selecting a more favorable measure after seeing results. Archive both passing and failing refinements.
- [ ] Re-run designated reproducibility cases under recorded settings and compare inputs, solver version, model hashes, status, response metrics, and extracted artifact hashes using the approved policy.
- [ ] Explain and quantify any contract-approved nondeterminism, parallel-order effect, or solver-platform difference; unexplained differences remain unresolved.
- [ ] Preserve failed jobs and their inputs, partial outputs, logs, resource records, and failure classifications. Do not delete them from the convergence or reproducibility history.

## Extraction and Physics Checks

- [ ] Record the extraction script version or code revision, configuration hash, interpreter and Abaqus release, command, and input ODB hash.
- [ ] Validate job ID, sample ID, produced artifact IDs, step, frame, region, variable, component, coordinate system, sign convention, and units during extraction. Validate dataset ID only when dataset generation is required by the resolved contract.
- [ ] Save extraction logs, output schema validation, row or point counts, missing-data checks, finite-value checks, and hashes of extracted tables and curves.
- [ ] Verify force-displacement sign and units against the model contract using named reference points or regions. Preserve the raw components and the transformation used to form the reported curve.
- [ ] Check curve ordering, duplicate abscissae, discontinuities, unexpected reversals, and whether the endpoint corresponds to the actual completed increment rather than the requested step end.
- [ ] Evaluate the predefined energy-balance quantities appropriate to the procedure, including external work, internal energy, kinetic energy, artificial or stabilization energy, and dissipative terms where requested. Save histories, ratios or residual calculations defined by the contract, and the decision.
- [ ] Cross-check extracted quantities against independent solver totals or reactions where available. Preserve values, differences, and the approved tolerance.
- [ ] Reject acceptance based only on ODB existence, successful plotting, or a visually smooth force-displacement curve.

## Handoff Evidence

- [ ] Provide the run manifest with the job-sample-artifact bijection, attempt history, model and configuration identifiers, statuses, and links to all evidence. Include dataset ID only for a contract-required dataset-generation task.
- [ ] Provide the resolved INP and configuration archive, geometry and mesh hashes, generation and extraction code revisions, and output artifact hashes.
- [ ] Provide scheduler logs or local-launcher/process logs, submission and solver logs, the expected solver-status-file list, all applicable produced status files, and extraction logs with commands and exit statuses. Include license and restart evidence only when the task configuration makes them applicable; for N/A items include the exact basis and reviewer agreement.
- [ ] When mesh convergence is required, provide its table with the predefined metric, tolerance, refinement identities, results, and acceptance decision. Otherwise provide the exact N/A basis and reviewer agreement.
- [ ] Provide raw and processed force-displacement data, sign and unit definitions, extraction provenance, physics-check calculations, and plots that link back to source data hashes.
- [ ] Provide geometry, mesh, contact, solver-warning, increment, output-completeness, finite-value, and energy-balance QC reports.
- [ ] Provide a failure ledger containing every failed or incomplete attempt, classification, evidence, retained artifact paths, and any approved remediation.
- [ ] State the Abaqus release, solver, unit system, model limitations, tested parameter range, resource envelope, known unsupported cases, and exact reproduction commands.

## Stop Conditions

Stop submission, extraction, or publication as appropriate; preserve all diagnostics and mark the attempt unresolved when any of the following occurs:

- [ ] The approved model contract is missing, internally inconsistent, or conflicts with the resolved INP or configuration.
- [ ] The contract-required job-sample-artifact mapping is missing, duplicated, ambiguous, or non-bijective; for dataset-generation tasks this also applies to the required dataset ID.
- [ ] A geometry, mesh, model, configuration, code, INP, ODB, or extraction hash required for the current stage differs from the manifest without an approved new attempt.
- [ ] Contract-required geometry or mesh quality fails its predefined acceptance criteria, or required sets, surfaces, orientations, assignments, or components are missing.
- [ ] Units, signs, material data, contact or friction settings, steps, increments, stabilization, boundary conditions, loads, or outputs required by the resolved contract cannot be verified from archived evidence.
- [ ] Scheduler status or local-launcher/process status disagrees with the solver outcome, terminal solver success required by the contract is absent, or contract-required steps, frames, and outputs are incomplete.
- [ ] An ODB required for the current stage is partial, corrupt, unreadable, or inconsistent with the archived logs and status files.
- [ ] Unresolved distortion, contact, convergence, increment, singularity, energy-balance, nonfinite-output, or physics warnings covered by the resolved contract remain.
- [ ] Mesh convergence or reproducibility required by the resolved contract fails the predefined metric and tolerance.
- [ ] CPU, memory, wall-time, scratch, or output capacity is insufficient for the approved run, or required managed-license capacity is insufficient when license management applies.
- [ ] Extraction provenance, output schema, units, signs, or artifact hashes required for the current stage cannot be established.
- [ ] Logs, convergence evidence, QC reports, artifacts, status files, or failure-ledger entries required by the resolved contract are absent. Evidence the configured solver, procedure, stage, or launcher is designed not to produce may be N/A only with its exact basis and reviewer agreement.
