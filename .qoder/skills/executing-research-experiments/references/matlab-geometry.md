# MATLAB Geometry Execution Checklist

Use this checklist for MATLAB geometry generation, field evaluation, voxelization, meshing, and descriptor calculation. A checked item means that the named evidence exists and is linked from the run manifest. A verbal assurance is not evidence.

## Applicability and N/A

- Execute only checklist items applicable to the task contract and current stage.
- N/A is not a shortcut: record the exact contract/design basis and require reviewer agreement at handoff.
- Evidence that the selected method/stage/tool configuration is designed not to produce is legitimately N/A; evidence expected by the resolved contract but missing is a stop condition.
- Do not demand downstream mesh/STL/descriptor evidence for a field-only stage, but do record downstream work as unaccepted/not assessed.
- Apply N/A only to stage-inapplicable evidence. It cannot waive source authority, contract identity, input validity, finite-value checks, provenance, determinism, or other evidence required for the current stage.

## Read First

- [ ] Read the approved experiment specification and record its immutable identifier or archived path in the run manifest.
- [ ] Read the scientific contract that defines the geometry and record its version or content hash.
- [ ] Read the input manifest and verify that every sample ID maps to one parameter record and one intended output location. Save the validation report.
- [ ] Recompute and compare the descriptor and configuration hashes before execution. Save both expected and observed hashes; do not silently refresh a mismatch.
- [ ] Read the tests that encode accepted behavior and save the test file hashes or repository revision used by the run.
- [ ] When a paper or supporting information is an authoritative source under the contract, or the task explicitly requires it, read the sections that define equations, parameter domains, normalization, and validation targets. Record page, equation, figure, or table anchors so another person can trace each implemented rule. Otherwise record the contract basis for N/A.
- [ ] Produce a source map from every implemented scientific rule to the applicable approved specification, contract, test, paper, or supporting-information anchor. If authoritative sources disagree, stop rather than choosing one implicitly.

## Scientific Contract

- [ ] Transcribe the implicit equation exactly, including signs, coefficients, exponents, trigonometric arguments, offsets, and parameter placement. Preserve a source anchor and an equation hash or canonical text snapshot.
- [ ] Record the normalization convention, including the reference length and the precise transformation from physical coordinates to normalized coordinates.
- [ ] Record coordinate order and axis meaning explicitly, for example whether arrays and functions consume `x,y,z` or another order. Save at least one asymmetric anchor case that would expose an axis swap.
- [ ] Record units for coordinates, lengths, fields, descriptors, and output geometry. Save the conversion table used at interfaces.
- [ ] Record the solid convention as an executable predicate, including whether solid is `f <= c`, `f >= c`, or another approved relation, and define the treatment of equality.
- [ ] Classify each manifest field as either an independent input or a derived descriptor. Save the dependency mapping and reject attempts to supply a derived descriptor as an independent degree of freedom unless the contract explicitly permits inversion.
- [ ] Record the approved method projection from the full parameter record to the method-specific parameter set. Mark every parameter active or inactive for that method and test that inactive parameters cannot change its geometry.
- [ ] Parse anchors and knots according to the approved schema, preserving ordering, multiplicity, boundary behavior, and interpolation convention. Save the parsed representation and round-trip or anchor-evaluation evidence.
- [ ] Never infer a formula, unit, axis, sign, interpolation rule, or parameter role from a variable name. Missing semantics require a source citation or a stop decision.
- [ ] Treat `gamma(z/l)=1.5+(z/l)/w` only as the M01/M02 project case. The authoritative contract takes precedence, and this expression must not be generalized to other methods or tasks.

## Implementation Gates

- [ ] Gate input parsing before geometry evaluation: validate required fields, types, shapes, coordinate order, units, domain constraints, sample IDs, duplicate IDs, and expected hashes. Save accepted and rejected case results.
- [ ] Gate method dispatch: log the selected method, projected active parameters, explicitly ignored inactive parameters, and the contract version that authorized the projection.
- [ ] Gate field evaluation: evaluate preserved numerical anchors before a production batch and compare them with contract-derived expectations using the approved tolerance policy. Save inputs, expected values, observed values, and differences.
- [ ] When voxelization belongs to the current stage, gate it by recording domain bounds, resolution, sampling locations, solid predicate, boundary treatment, data type, occupancy, memory estimate, and measured runtime. A field-only stage records voxelization as unaccepted and not assessed.
- [ ] When surface extraction, STL, or mesh export belongs to the current stage, gate it by recording algorithm and options, coordinate scaling, face orientation convention, component policy, and the input field or voxel artifact hash. Earlier stages record these downstream outputs as unaccepted and not assessed.
- [ ] When descriptor calculation belongs to the current stage, gate it by recording descriptor implementation version, configuration hash, geometry hash, dependency mapping, numerical settings, and whether the descriptor is measured from the field, voxels, or mesh. Earlier stages record descriptors as unaccepted and not assessed.
- [ ] Gate output publication: write outputs to a run-specific location, produce hashes after successful validation, and update the manifest atomically only after every required check passes.

## Minimum Verification

- [ ] Run normal cases and save exact inputs, output summaries, test assertions, and pass counts.
- [ ] Run boundary cases at every contract-defined parameter and spatial boundary. Save which boundaries were exercised and the observed boundary behavior.
- [ ] Run invalid-value cases and confirm that each is rejected with an attributable error: out-of-domain values, malformed anchors or knots, unknown methods, duplicate IDs, and incompatible units where applicable.
- [ ] Inject `NaN` and `Inf` into every numeric input class and verify rejection before artifact publication. Save the rejection results.
- [ ] Test wrong scalar, vector, matrix, and coordinate-array shapes, including transposed or permuted coordinate layouts, and save the error evidence.
- [ ] Repeat identical evaluations and artifact generation under recorded settings. Compare deterministic values or hashes and document any contract-approved nondeterminism.
- [ ] Verify provenance by tracing every output artifact back to sample ID, input record, method projection, contract version, configuration hash, code revision, and parent artifact hashes.
- [ ] Check that every evaluated field used downstream is finite. Save finite-value counts and extrema; any nonfinite value is a failed gate.
- [ ] For a voxel-producing stage, record voxel occupancy and independently confirm that the solid convention produces the intended phase. Empty and full volumes must be explicit tested outcomes: either valid contract cases with documented meaning or rejected degeneracies. For a field-only stage, record this check as downstream, unaccepted, and not assessed.
- [ ] Evaluate resolution effects applicable to the current stage using the contract-approved sequence. Save memory and runtime for each resolution and preserve the measured field, voxel, descriptor, or geometric convergence data required by that stage without inventing an acceptance threshold.
- [ ] For an STL- or mesh-producing stage, check each mesh for manifoldness, watertightness, consistent orientation, degenerate entities, and connected-component count. Save tool output and the approved disposition of every component. Do not make this a field- or voxel-only acceptance gate.
- [ ] When the current stage requires descriptor convergence, evaluate it against resolution or mesh refinement using the predefined metric and tolerance from the approved contract. Save the table, calculation, and decision. Otherwise record descriptor convergence as downstream, unaccepted, and not assessed.
- [ ] Run all applicable automated tests and save command, MATLAB release, test counts, failures, skips, and duration.

## MATLAB Tool Trap

`checkcode` can return a cell array for multiple files whose individual cells contain empty finding structs. In that case, the outer cell is nonempty even though there are no findings. Conversely, checking only outer `isempty` does not count findings correctly.

- [ ] Flatten or iterate over the per-file results and count the inner finding structs.
- [ ] Report findings by file, identifier, line, and message, plus a total inner finding count.
- [ ] Preserve the exact `checkcode` invocation and raw result summary as evidence; do not claim a clean result from the outer container alone.

## Handoff Evidence

- [ ] Record MATLAB release, platform, and all required toolbox names and versions.
- [ ] Record the exact noninteractive or batch command, working directory, environment inputs, and exit status.
- [ ] Report automated test totals: passed, failed, incomplete or skipped, and duration.
- [ ] Report `checkcode` per-file findings and the total inner finding count.
- [ ] Provide numerical anchors with source references, inputs, expected values, observed values, differences, and the applied approved tolerance.
- [ ] Provide the run manifest and hashes for the contract, configuration, code revision, and every artifact produced by the current stage. Include descriptor, voxel, STL, and mesh hashes only when those outputs are applicable and produced.
- [ ] State tested parameter, domain, and resolution limits; memory and runtime observations; known unsupported cases; and any approved deviations.
- [ ] Include the convergence and quality evidence required for the current stage, failure records, and the command needed to reproduce the handoff package. List downstream voxel, STL, mesh, and descriptor work not executed in this stage as unaccepted and not assessed, with the N/A basis and reviewer agreement.

## Stop Conditions

Stop the run, preserve diagnostics, and do not publish affected outputs when any of the following occurs:

- [ ] The specification, contract, tests, or any contract-authoritative or task-required paper or supporting information conflict and no approved resolution is recorded.
- [ ] An expected contract, configuration, descriptor, code, or parent-artifact hash drifts.
- [ ] A formula, normalization, coordinate order, unit, solid convention, parameter role, anchor, or knot rule lacks an authoritative source.
- [ ] Input-to-sample mapping is ambiguous, duplicated, missing, or non-bijective where bijection is required.
- [ ] Field evaluation produces `NaN`, `Inf`, or another nonfinite value.
- [ ] In a contract-required voxel stage, empty or full occupancy occurs without an explicit contract-approved interpretation.
- [ ] In a contract-required STL or mesh stage, the mesh is non-manifold, not watertight, inconsistently oriented, unexpectedly disconnected, or otherwise fails the approved mesh contract.
- [ ] Numerical anchors, determinism, provenance, resolution behavior, or any convergence check required for the current stage fails the approved checks.
- [ ] Estimated or observed memory or runtime exceeds the approved execution envelope.
- [ ] Required evidence cannot be reproduced or tied to the run manifest.
- [ ] Evidence required by the resolved contract for the current stage is missing; stage-inapplicable downstream evidence may be N/A only with its exact basis and reviewer agreement.
