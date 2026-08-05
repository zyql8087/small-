# M04 Dual Descriptor Calibration and Abaqus Gate-0 Interface Design

**Date:** 2026-08-05

**Status:** Approved design; implementation not started

**Parent baseline:** M03 continuous-CSG compiler at commit `be24186`

**Target branch:** `paper-a/matlab-gyroid-m04-descriptors-interface`

## 1. Objective and scope

M04 shall add two explicitly separated geometry-descriptor profiles to the
validated M03 geometry compiler:

1. `legacy_small`, which reproduces the algorithms used by TPMS-Designer and
   is used only to compare against the archived Small dataset; and
2. `physical_m04`, which reports finite-specimen descriptors with explicit SI-
   compatible millimetre units for Paper A's new geometries.

M04 shall also publish a hash-verified exchange package for a later Abaqus
Gate-0. The package is preparation evidence only. This stage shall not launch
Abaqus, generate a solver-ready volume mesh, submit a job, or claim Abaqus
compatibility.

The M04 boundary is:

```text
validated M03 request + response + STL
    |-- legacy sampler --> legacy_small descriptors --> Small descriptor Gate-0
    |-- physical sampler --> physical_m04 descriptors --> Paper A dataset fields
    `-- verified artifacts + physical metadata --> Abaqus package (not run)
```

The Graph Transformer, diffusion model, mechanical labels, printability model,
and formal Abaqus dataset are outside this specification.

## 2. Evidence requiring a versioned descriptor correction

The M01 candidate descriptor contract does not reproduce the implementation
in the open-source software cited by the Small paper. The comparison is:

| Descriptor | M01 candidate | TPMS-Designer source behavior |
|---|---|---|
| `relativeVolume` | cell-centred solid fraction | solid occupancy excluding the final sample plane in each direction |
| `relativeArea` | surface area / reference volume | surface area / bounding-box surface area |
| `thickness` | median solid-skeleton local thickness | maximum solid inscribed diameter after circular padding |
| `poreDiameter` | largest finite-domain connected-void sphere | maximum void inscribed diameter after circular padding |
| `areaMean` | mean largest connected void area over 26 slices | mean solid cross-sectional area over all z sample planes |

The source-of-record implementation is TPMS-Designer commit
`a5f7d59b59f5c00e0f50c0bc3675f38f553454eb`, specifically
`classes/metrics.m`, `classes/v3Field.m`, and `classes/UnitCell.m` in the
[official repository](https://github.com/Alistairj43/TPMS-Designer/tree/a5f7d59b59f5c00e0f50c0bc3675f38f553454eb).

The correction shall be versioned rather than silently rewriting history:

- preserve the existing file byte-for-byte as
  `configs/descriptor_definition.v1_candidate.json`;
- require its preserved SHA-256 to equal
  `2f59976c74cc88eac66c43a56e242f50f28aff0e71be8d752a481c05a4a2d9c9`;
- create `configs/descriptor_definition.v2.json` as the active dual-profile
  contract;
- update the compiler configuration and immutable hashes explicitly;
- bump the compiler version because descriptor provenance and geometry
  identities currently include the descriptor-definition hash.

No archived Small value may be copied into a computed result or used to train a
descriptor correction model.

## 3. Descriptor profile contracts

### 3.1 Shared output envelope

Each profile result shall contain:

```json
{
  "profile": "legacy_small",
  "definition_sha256": "<64 lowercase hex characters>",
  "sampling": {},
  "units": {},
  "values": {
    "relativeVolume": 0.0,
    "relativeArea": 0.0,
    "thickness": 0.0,
    "poreDiameter": 0.0,
    "areaMean": 0.0
  },
  "diagnostics": {}
}
```

The descriptor order is permanently
`[relativeVolume, relativeArea, thickness, poreDiameter, areaMean]`.
All values must be real, finite scalars. A missing, empty, complex, infinite, or
NaN result is a structural failure, not a value to impute.

### 3.2 `legacy_small`

The legacy profile is an independent compatibility implementation. It shall
not reuse the finite-boundary definitions from `physical_m04`.

The sampler uses an endpoint grid compatible with TPMS-Designer:

```matlab
x = 0:voxel_size_mm:Lx_mm;
y = 0:voxel_size_mm:Ly_mm;
z = 0:voxel_size_mm:Lz_mm;
solid = legacy_field(x, y, z) <= 0;
```

The grid span divided by `voxel_size_mm` must be an integer in every direction.
The five algorithms are:

```matlab
[sx, sy, sz] = size(solid);
relativeVolume = sum(solid(1:sx-1, 1:sy-1, 1:sz-1), 'all') ...
    / ((sx-1)*(sy-1)*(sz-1));

relativeArea = surfaceArea_mm2 ...
    / (2*(Lx_mm*Ly_mm + Ly_mm*Lz_mm + Lz_mm*Lx_mm));

solidPeriodic = padarray(solid, size(solid,1), 'circular', 'both');
solidBarrier = padarray(~solidPeriodic, [1 1 1], true, 'both');
thickness = 2 * voxel_size_mm * max(bwdist(solidBarrier), [], 'all');

voidPeriodic = padarray(solid, size(solid,1), 'circular', 'both');
voidBarrier = padarray(voidPeriodic, [1 1 1], true, 'both');
poreDiameter = 2 * voxel_size_mm * max(bwdist(voidBarrier), [], 'all');

sliceArea = squeeze(sum(solid, [1 2])) * voxel_size_mm^2;
areaMean = mean(sliceArea);
```

The implementation shall be verified against the exact array operations in
the pinned TPMS-Designer source. If MATLAB expression shape or padding
semantics differ from the pseudocode above, source parity wins and the v2 JSON
shall record the executable expression used.

Legacy units are recorded as:

- `relativeVolume`: dimensionless;
- `relativeArea`: dimensionless ratio to bounding-box surface area;
- `thickness`: legacy length unit, converted to mm by the frozen global scale;
- `poreDiameter`: legacy length unit, converted to mm by the frozen global scale;
- `areaMean`: legacy area unit, converted to mm2 by the square of the frozen
  global scale.

### 3.3 `physical_m04`

The physical profile uses the validated M03 finite specimen and cell-centred
interior mask. It preserves the M01 candidate definitions with explicit names,
units, and boundary policies:

- `relativeVolume`: interior solid-cell count / interior cell count;
- `relativeArea`: validated closed-surface area / physical bounding-box volume,
  in `mm^-1`;
- `thickness`: twice the median Euclidean distance from solid-skeleton voxels to
  void, multiplied by isotropic voxel spacing, in mm;
- `poreDiameter`: twice the maximum finite-domain distance in the largest
  26-connected interior void component, in mm; the exterior is a non-void
  barrier;
- `areaMean`: mean largest 8-connected void-region area over 26 uniformly
  selected z slices including endpoints, in `mm2`; empty slices are excluded.

The profile shall report solid and void component counts, skeleton voxel count,
selected void-component size, slice indices, nonempty slice count, voxel
spacing, physical bounds, and surface triangle count.

The physical profile is not compared numerically to the archived Small
descriptors. Its purpose is the new Paper A dataset and downstream finite-
element provenance.

## 4. Small source data and immutable case selection

The source workbook is the unaugmented Small test split named `test.xlsx`, with
SHA-256:

```text
b4544b09c2688af8bc7aeeca5140a5d4c1cfc1c5b262709c9618c030d90fa561
```

The required sheets and method mapping are:

| Sheet | Method | Data rows |
|---|---:|---:|
| `class1` | M1 | 1423 |
| `class2` | M2 | 1910 |
| `class12` | M3 | 1778 |

Each sheet must have exactly these first nine columns:

```text
V1a,V1b,V1c,w,relativeVolume,relativeArea,thickness,poreDiameter,areaMean
```

Selection eligibility requires finite numeric values, a valid method mapping,
the frozen method constraint, and parameters within the compiler bounds.
Selection order is the ascending lowercase hexadecimal value of:

```text
SHA256(source_workbook_sha256 | sheet_name | excel_row_number |
       "M04-v2-selection")
```

For each method, the first two eligible rows form the discovery set and the
next ten form the confirmation set. Therefore:

- discovery: 2 x 3 = 6 cases;
- confirmation: 10 x 3 = 30 cases;
- total locked rows: 36;
- discovery and confirmation are disjoint.

The selection manifest stores the workbook hash, sheet, Excel row number,
method, raw parameters, archived descriptors, selection digest, and manifest
hash. It is written before any selected geometry is evaluated. The full source
workbook remains read-only and is not committed.

## 5. Discovery calibration and freeze protocol

The six discovery cases may identify only global legacy sampling and scale
parameters. They may not alter a descriptor formula per method or per case.

### 5.1 Sampling-density identification

The preregistered samples-per-reference-length candidates are:

```text
20, 24, 30, 32, 40, 48, 60, 64, 80, 96
```

For every candidate, compute the six discovery geometries at unit reference
length and compare only the scale-independent `relativeVolume` and
`relativeArea` results with the archive. Rank candidates by:

1. pooled median relative error;
2. pooled 95th-percentile relative error;
3. lower sampling density as a deterministic final tie-break.

Relative error is:

```text
abs(computed - archived) / max(abs(archived), descriptor_absolute_tolerance)
```

The selected density must achieve median error at most 2% and 95th-percentile
error at most 5% on both scale-independent descriptors. Otherwise the status is
`M04_SCALE_NOT_IDENTIFIED`.

### 5.2 Global physical-scale identification

At the selected density and unit reference length, independently estimate a
reference-length scale from every discovery case:

```text
L_thickness = archived_thickness / computed_thickness_at_L1
L_pore      = archived_poreDiameter / computed_poreDiameter_at_L1
L_area      = sqrt(archived_areaMean / computed_areaMean_at_L1)
```

This produces 18 estimates. The frozen reference length is their median,
serialized with `%.17g` precision. Identification succeeds only if:

- all estimates are finite and positive;
- median absolute relative deviation from the frozen value is at most 2%;
- the 95th percentile absolute relative deviation is at most 5%; and
- the medians of the thickness, pore, and area estimate groups each differ
  from the frozen value by at most 2%.

The archive suggests a reference length near 30 mm, but the implementation
must not hard-code that value. Failure of the three independent scale laws to
agree produces `M04_SCALE_NOT_IDENTIFIED` and stops the workflow.

### 5.3 Freeze artifact

The atomic freeze JSON records:

- selection-manifest SHA-256;
- source-workbook SHA-256;
- TPMS-Designer commit;
- compiler version and geometry-definition hash;
- descriptor-contract and profile hashes;
- selected sampling density and global reference length;
- every discovery result and error statistic;
- the confirmation row identities, without confirmation results;
- freeze SHA-256 and status.

The confirmation runner accepts no sampling or scale override. Any hash or
parameter disagreement yields `M04_GATE0_NOT_FROZEN`.

## 6. Confirmation Gate-0

Only a valid freeze artifact may unlock the 30 confirmation cases. The runner
processes cases in selection order, writes one atomic result per case, and may
resume only by verifying every existing case hash. It may never skip a failed
case.

Gate-0 passes only when:

- all 30 cases complete M03 and legacy descriptor calculation;
- all computed descriptor values are finite;
- repeated execution is byte-deterministic at the JSON canonical-value level;
- for every descriptor, median relative error is at most 2% and the 95th
  percentile is at most 5%;
- pooled over all 150 descriptor comparisons, median relative error is at most
  2% and the 95th percentile is at most 5%.

The report also provides method x descriptor counts, median, 95th percentile,
maximum, signed bias, RMSE, and rank correlation. These stratified statistics
are diagnostics and do not replace the preregistered pass criteria.

Confirmation outcomes are exactly:

- `M04_GATE0_PASSED`;
- `M04_GATE0_FAILED`;
- `M04_SCALE_NOT_IDENTIFIED`;
- `M04_GATE0_NOT_FROZEN`.

After any confirmation result is observed, the freeze is immutable. A changed
formula, scale, density, case set, or tolerance requires a new contract version
and a new untouched confirmation set. The six discovery rows and 30
confirmation rows shall be tagged as calibration/confirmation records and
excluded from later claims of independent Small++ model evaluation.

## 7. M04 compiler integration

M03 remains independently executable. The M04 entry point is:

```matlab
response = run_descriptor_compiler( ...
    requestPath, m03ResponsePath, m04ResponsePath)
```

It shall:

1. parse and validate the original request with the active configuration;
2. read the M03 response and manifest without trusting embedded paths;
3. verify request hash, geometry identity, STL SHA-256, manifest hash, units,
   bounds, resolution, and compiler compatibility;
4. deterministically rebuild the required legacy and physical sampled fields;
5. compute and validate both profiles;
6. write an M04 result manifest before publishing the response;
7. atomically publish without overwriting any existing file or directory.

The response contains `descriptors.legacy_small` and
`descriptors.physical_m04`. It shall not flatten the profiles into five
ambiguous scalar fields. M04 failure must not delete or modify M03 artifacts.

Stable M04 failure codes include:

```text
DESCRIPTOR_DEPENDENCY_MISSING
DESCRIPTOR_CONTRACT_MISMATCH
DESCRIPTOR_NONFINITE
DESCRIPTOR_PROFILE_INVALID
M03_ARTIFACT_MISMATCH
M04_SCALE_NOT_IDENTIFIED
M04_GATE0_NOT_FROZEN
M04_GATE0_FAILED
OUTPUT_CONFLICT
INTERNAL_ERROR
```

## 8. Abaqus Gate-0 exchange package

### 8.1 Package contents

For a valid M03 geometry with valid M04 descriptors, the MATLAB packager writes
an immutable directory:

```text
abaqus_gate0/<package_sha256>/
|-- geometry.stl
|-- geometry.manifest.json
|-- descriptors.json
|-- abaqus_gate0_request.json
`-- checksums.sha256
```

The package identifier is the SHA-256 of canonical lines containing the
geometry identity, STL digest, geometry-manifest digest, descriptor-result
digest, Abaqus request-schema version, and material-profile identifier.

The request records:

- geometry identity and every artifact digest;
- length unit `mm` and no other accepted unit;
- physical bounding box and positive specimen dimensions;
- x/y/z axis definitions and compression direction `z`;
- bottom and top z coordinates;
- plane-selection tolerance derived from the M03 physical mesh spacing;
- representation `closed_surface_stl`;
- `volume_mesh_status: not_generated`;
- `solver_ready: false`;
- intended solver `Abaqus/Explicit`;
- target nominal compression strain `0.25`;
- required x/y periodicity;
- bottom six-degree-of-freedom constraint intent;
- top constraint intent allowing z translation only;
- a versioned material-profile reference;
- `execution_status: prepared_not_run`.

The plane-selection tolerance is
`max(0.25 * spacing_mm, 1e-9 * specimen_height_mm)`. It is a later adapter
input, not evidence that an Abaqus node set has already been created.

### 8.2 Offline preflight

`abaqus/preflight_gate0_package.py` shall use only the Python standard library.
It validates schemas, relative package paths, exact file digests, binary STL
header/count/length, finite facet payload, physical bounds, units, identities,
and status fields. It must reject absolute artifact paths, `..` path escape,
symlink escape, missing files, extra checksum entries, and tampering.

This stage shall contain no call to `job.submit()` and no execution path that
launches Abaqus. Source scanning shall enforce this constraint.

The only successful package status is:

```text
ABAQUS_PACKAGE_PREPARED_NOT_RUN
```

The package is not solver-ready because a closed surface STL is not a volume
finite-element mesh. M05 must separately demonstrate Abaqus import, volume
meshing, element-quality gates, TOP/BOTTOM set construction, periodic
constraints, input writing, and small-scale execution.

## 9. File boundaries

Planned files are:

```text
geometry_compiler_matlab/
|-- configs/
|   |-- descriptor_definition.v1_candidate.json
|   |-- descriptor_definition.v2.json
|   `-- abaqus_gate0_request.schema.json
|-- core/
|   |-- build_legacy_descriptor_field.m
|   |-- compute_legacy_small_descriptors.m
|   |-- compute_physical_m04_descriptors.m
|   |-- compute_descriptor_profiles.m
|   |-- validate_descriptor_result.m
|   |-- build_abaqus_gate0_package.m
|   `-- validate_abaqus_gate0_package.m
|-- gate0/
|   |-- prepare_small_gate0_selection.m
|   |-- calibrate_legacy_scale.m
|   |-- freeze_legacy_calibration.m
|   `-- run_small_descriptor_gate0.m
|-- abaqus/
|   `-- preflight_gate0_package.py
|-- tests/
|   |-- TestLegacyDescriptors.m
|   |-- TestPhysicalDescriptors.m
|   |-- TestDescriptorGate0.m
|   `-- TestAbaqusGate0Package.m
|-- run_descriptor_compiler.m
`-- run_abaqus_gate0_packager.m
```

Each file owns one responsibility. The M03 meshing and STL validators remain
the source of geometry validity and shall not be duplicated in M04.

## 10. Verification matrix

### 10.1 Unit and contract tests

Tests shall cover:

1. byte preservation of the v1 candidate definition;
2. strict v2 schema, order, hashes, profile names, units, and algorithms;
3. exact TPMS-Designer parity on small synthetic binary volumes;
4. circular-padding cases whose extrema cross an x, y, or z boundary;
5. analytic all-solid, all-void, slab, cylindrical-pore, and box fixtures;
6. physical scale laws: length metrics scale by `k`, area by `k^2`, and
   dimensionless metrics remain unchanged;
7. profile determinism for representative M1, M2, and M3 cases;
8. nonfinite, empty-support, anisotropic-grid, missing-toolbox, and malformed
   contract failures;
9. deterministic 6+30 selection and exact Excel row provenance from a compact
   committed fixture;
10. freeze tampering and forbidden confirmation overrides;
11. per-case checkpoint integrity and fail-closed resume behavior;
12. Abaqus package determinism, overwrite refusal, hash mismatch, unit error,
    path escape, missing artifact, symlink escape, and STL tampering;
13. Python preflight under normal Python without Abaqus modules;
14. source scan proving no `job.submit()` token exists in an Abaqus Python
    adapter outside tests that assert its absence;
15. all existing M01-M03 tests remain green.

External `test.xlsx` is not required by ordinary unit tests. A compact fixture
contains only selected row values, original row identifiers, and the source
workbook hash. A separate release command re-audits those rows against the
actual workbook before discovery or confirmation.

### 10.2 Release verification

Release verification runs in this order:

1. MATLAB Code Analyzer over all compiler `.m` files;
2. complete M01-M04 unit suite;
3. source-workbook hash/header/row audit;
4. deterministic selection-manifest regeneration;
5. six-case discovery calibration;
6. calibration freeze and digest verification;
7. 30-case confirmation run;
8. independent summary recomputation from per-case JSON;
9. one representative offline Abaqus package per method;
10. Python package preflight and tamper-negative tests;
11. `git diff --check` and clean-worktree verification.

Large sampled fields, caches, generated STL collections, and Abaqus packages
remain outside Git. The selection manifest, calibration freeze, 30-case result
summary, compact row fixture, schemas, and concise QA report are committed.

## 11. Completion and stop conditions

M04 implementation is complete only when:

- both descriptor profiles are versioned, finite, deterministic, and tested;
- v1 candidate history is preserved;
- the discovery workflow either identifies one globally consistent scale or
  stops explicitly;
- the confirmation workflow either passes the preregistered criteria or emits
  a complete immutable failure report;
- the Abaqus package is offline-preflighted and explicitly marked not run;
- all prior tests remain green and static analysis reports no issue.

The workflow must stop without entering formal Abaqus generation when:

- the source workbook or any selected row cannot be authenticated;
- scale-independent descriptor parity fails;
- the three physical scale laws disagree;
- a confirmation threshold fails;
- any result is nonfinite or nondeterministic;
- an Abaqus package cannot be reproduced byte-for-byte.

No result may be described as "approximately passed". The four externally
visible terminal states are:

```text
M04_GATE0_PASSED
M04_GATE0_FAILED
M04_SCALE_NOT_IDENTIFIED
ABAQUS_PACKAGE_PREPARED_NOT_RUN
```

## 12. Approval record

The user approved:

- serial execution: complete M04 and implement the Abaqus exchange interface
  without running Abaqus;
- preservation of the v1 candidate descriptor definition;
- the dual `legacy_small` / `physical_m04` descriptor architecture;
- deterministic 6-case discovery plus 30-case confirmation;
- fail-closed, hash-verified Abaqus packaging with `solver_ready=false`;
- the file boundaries, verification matrix, and non-goals in this document.
