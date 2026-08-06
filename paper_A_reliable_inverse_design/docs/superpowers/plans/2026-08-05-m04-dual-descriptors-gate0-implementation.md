# M04 Dual Descriptors and Abaqus Gate-0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add versioned `legacy_small` and `physical_m04` descriptor profiles, preregistered Small 6+30 calibration/confirmation, and a tamper-evident Abaqus exchange package that is explicitly prepared but not run.

**Architecture:** Keep M03 geometry construction, meshing, and QC behavior unchanged; add only an explicit manifest digest to its response. Build M04 as a downstream consumer that re-authenticates all M03 artifacts before recomputing two independent descriptor samplings. Gate-0 freezes one global legacy sampling density and scale before touching the 30 confirmation cases. The Abaqus boundary publishes only an immutable surface-STL package and validates it offline; volume meshing and solver execution remain M05 work.

**Tech Stack:** MATLAB R2023b, MATLAB Unit Test, Image Processing Toolbox, JSON, SHA-256, Python 3 standard library, Git.

**Handoff memory:** `paper_A_reliable_inverse_design/geometry_compiler_matlab/docs/SIMULATION_EXPERIMENT_MEMORY.md`

---

## Execution rules and file map

Run every command from:

```text
F:\small++\.worktrees\m03-continuous-csg-impl
```

Use this MATLAB executable:

```text
F:\MATLAB\R2023b\bin\matlab.exe
```

Do not edit `run_geometry_compiler.m` except where this plan explicitly says to update contract provenance. Do not run Abaqus, import `abaqus`, create a volume mesh, generate an `.inp`, or submit a job.

The implementation adds these focused units:

```text
paper_A_reliable_inverse_design/geometry_compiler_matlab/
|-- configs/
|   |-- descriptor_definition.v1_candidate.json
|   |-- descriptor_definition.v2.json
|   |-- material_profile.gate0.reference.json
|   `-- abaqus_gate0_request.schema.json
|-- core/
|   |-- build_legacy_descriptor_field.m
|   |-- compute_legacy_small_descriptors.m
|   |-- compute_physical_m04_descriptors.m
|   |-- compute_descriptor_profiles.m
|   |-- validate_descriptor_result.m
|   |-- read_and_verify_m03_artifacts.m
|   |-- canonical_descriptor_text.m
|   |-- build_abaqus_gate0_package.m
|   `-- validate_abaqus_gate0_package.m
|-- gate0/
|   |-- prepare_small_gate0_selection.m
|   |-- calibrate_legacy_scale.m
|   |-- freeze_legacy_calibration.m
|   |-- run_small_descriptor_gate0.m
|   |-- summarize_descriptor_errors.m
|   |-- recompute_descriptor_summary_independent.m
|   `-- package_representative_gate0_cases.m
|-- abaqus/
|   `-- preflight_gate0_package.py
|-- tests/
|   |-- fixtures/small_gate0_rows.json
|   |-- TestLegacyDescriptors.m
|   |-- TestPhysicalDescriptors.m
|   |-- TestDescriptorCompiler.m
|   |-- TestDescriptorGate0.m
|   `-- TestAbaqusGate0Package.m
|-- run_descriptor_compiler.m
`-- run_abaqus_gate0_packager.m
```

The three hard checkpoints are:

1. **D:** both descriptor profiles pass unit, scale-law, determinism, and M03 provenance tests;
2. **G:** the discovery artifact is frozen and the independent confirmation report reaches one declared terminal state;
3. **A:** one package per method passes MATLAB and ordinary-Python preflight while remaining `solver_ready=false`.

Do not proceed from D to G, or G to A, if the prior checkpoint fails.

### Task 1: Preserve v1 and activate the dual-profile v2 contract

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/descriptor_definition.v1_candidate.json`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/descriptor_definition.v2.json`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/compiler_config.example.json`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compiler_contract.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/load_compiler_config.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/validate_descriptor_definition.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compiler_version.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestBootstrap.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestContractHardening.m`

- [x] **Step 1: Write failing contract-migration tests**

Add tests that demand byte preservation, exact profile order, exact descriptor order, and distinct units:

```matlab
function testV1CandidateBytesArePreserved(testCase)
    p = fullfile(testCase.BaseDir, 'configs', ...
        'descriptor_definition.v1_candidate.json');
    testCase.verifyEqual(sha256_file(p, 'MATLABGyroid:InvalidConfig', 'v1'), ...
        '2f59976c74cc88eac66c43a56e242f50f28aff0e71be8d752a481c05a4a2d9c9');
end

function testV2HasSeparatedProfiles(testCase)
    p = fullfile(testCase.BaseDir, 'configs', 'descriptor_definition.v2.json');
    d = jsondecode(fileread(p));
    testCase.verifyEqual(string({d.profiles.name}), ...
        ["legacy_small", "physical_m04"]);
    testCase.verifyEqual(string(d.descriptor_order), ...
        ["relativeVolume"; "relativeArea"; "thickness"; ...
         "poreDiameter"; "areaMean"]);
    testCase.verifyEqual(d.profiles(1).units.relativeArea, 'dimensionless');
    testCase.verifyEqual(d.profiles(2).units.relativeArea, 'mm^-1');
end
```

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); r=runtests({'tests/TestBootstrap.m','tests/TestContractHardening.m'}); assertSuccess(r)"
```

Expected: failure because `descriptor_definition.v1_candidate.json` and `descriptor_definition.v2.json` do not exist.

- [x] **Step 3: Preserve v1, create v2, and update immutable hashes**

Rename `descriptor_definition.json` to `descriptor_definition.v1_candidate.json` without changing its bytes, verify its fixed hash, and ensure the old filename no longer exists. Then write v2 with this mandatory shape:

```json
{
  "schema_version": "2.0",
  "descriptor_order": ["relativeVolume", "relativeArea", "thickness", "poreDiameter", "areaMean"],
  "source_of_record": {
    "repository": "https://github.com/Alistairj43/TPMS-Designer",
    "commit": "a5f7d59b59f5c00e0f50c0bc3675f38f553454eb"
  },
  "profiles": [
    {
      "name": "legacy_small",
      "grid_convention": "endpoint_grid",
      "units": {"relativeVolume":"dimensionless","relativeArea":"dimensionless","thickness":"mm","poreDiameter":"mm","areaMean":"mm2"},
      "algorithms": {"relativeVolume":"drop_final_plane_occupancy","relativeArea":"surface_area_over_bbox_surface_area","thickness":"periodic_maximum_solid_inscribed_diameter","poreDiameter":"periodic_maximum_void_inscribed_diameter","areaMean":"mean_solid_z_slice_area"}
    },
    {
      "name": "physical_m04",
      "grid_convention": "m03_cell_centered_interior",
      "units": {"relativeVolume":"dimensionless","relativeArea":"mm^-1","thickness":"mm","poreDiameter":"mm","areaMean":"mm2"},
      "algorithms": {"relativeVolume":"interior_solid_fraction","relativeArea":"closed_surface_area_over_bbox_volume","thickness":"median_skeleton_local_thickness","poreDiameter":"largest_finite_void_component_inscribed_diameter","areaMean":"mean_largest_void_region_over_26_z_slices"}
    }
  ]
}
```

Set `descriptor_definition_path` to `descriptor_definition.v2.json`, calculate its lowercase SHA-256, and put that same value in `compiler_config.example.json` and `compiler_contract.m`. Retain the v1 hash separately as `contract.legacyCandidateDescriptorDefinitionSha256`. Bump `compiler_version()` by one minor stage. Keep `contract.validationStage = 'M03_GEOMETRY_MESH'` for the existing M03 runner and add `contract.descriptorValidationStage = 'M04_DUAL_DESCRIPTORS'` for the new M04 response; do not relabel M03 output as M04.

Update validation so it rejects profile reordering, descriptor reordering, unknown fields that affect algorithms, wrong units, duplicate names, and any hash mismatch. Return parsed profile definitions on `config.descriptor_profiles`. Compute each profile's definition hash from fixed-order canonical lines containing its name, grid convention, five units, and five algorithm identifiers; expose them as `config.descriptor_profile_sha256.legacy_small` and `config.descriptor_profile_sha256.physical_m04`. These per-profile hashes populate the result envelope's `definition_sha256`; the full v2-file hash remains the compiler contract hash.

- [x] **Step 4: Run focused and full regression tests**

Run the Step 2 command, then:

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); run_tests"
```

Expected: all existing M01-M03 tests plus the new migration tests pass.

- [x] **Step 5: Commit the contract migration**

```powershell
git add paper_A_reliable_inverse_design/geometry_compiler_matlab/configs paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compiler_contract.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compiler_version.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/load_compiler_config.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/validate_descriptor_definition.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestBootstrap.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestContractHardening.m
git commit -m "feat(descriptors): version dual-profile M04 contract"
```

### Task 2: Implement `legacy_small` sampling and exact descriptor algorithms

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_legacy_descriptor_field.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compute_legacy_small_descriptors.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/validate_descriptor_result.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestLegacyDescriptors.m`

- [x] **Step 1: Write failing synthetic parity tests**

Test endpoint counts, final-plane exclusion, bounding-box surface normalization, periodic extrema across all three axes, and mean solid slice area. The central fixture must use exact arrays, not generated TPMS data:

```matlab
function testLegacyArrayOperations(testCase)
    solid = false(4,4,4);
    solid(1:3,1:3,1:3) = true;
    field = struct('solid',solid,'voxel_size_mm',1, ...
        'surface_area_mm2',12, ...
        'bounds_mm',struct('x',[0 3],'y',[0 3],'z',[0 3]), ...
        'samples_per_reference_length',1,'reference_length_mm',1);
    r = compute_legacy_small_descriptors(field, ...
        repmat('a',1,64));
    testCase.verifyEqual(r.values.relativeVolume, 1, 'AbsTol', 0);
    testCase.verifyEqual(r.values.relativeArea, 12/54, 'AbsTol', 1e-15);
    testCase.verifyEqual(r.values.areaMean, mean([9 9 9 0]), 'AbsTol', 0);
    testCase.verifyEqual(string(r.profile), "legacy_small");
end

function testLegacyRejectsNonIntegralSpan(testCase)
    projected = struct('method','M1','c0',.1,'c1',.1,'c2',.1,'w',0);
    config = TestLegacyDescriptors.loadConfig(testCase.BaseDir);
    f = @() build_legacy_descriptor_field(projected, config, 31, 1.01);
    testCase.verifyError(f, 'MATLABGyroid:DescriptorProfileInvalid');
end
```

Add one fixture where the maximum solid distance crosses x, one across y, and one across z. Calculate the expected maximum from a manually circularly tiled mask, then assert exact equality with the implementation.

- [x] **Step 2: Run the test and verify RED**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); r=runtests('tests/TestLegacyDescriptors.m'); assertSuccess(r)"
```

Expected: undefined-function failures for the two new core functions.

- [x] **Step 3: Implement the endpoint sampler**

Use one explicit contract: `samplesPerReferenceLength` is intervals per normalized reference length and `referenceLengthMm` supplies physical scale.

```matlab
function field = build_legacy_descriptor_field(projected, config, ...
        samplesPerReferenceLength, referenceLengthMm)
    validateattributes(samplesPerReferenceLength, {'numeric'}, ...
        {'scalar','real','finite','integer','positive'});
    validateattributes(referenceLengthMm, {'numeric'}, ...
        {'scalar','real','finite','positive'});
    d = config.geometry_parameters.domain_over_l;
    spans = [diff(d.x), diff(d.y), diff(d.z)];
    counts = spans .* double(samplesPerReferenceLength);
    if any(abs(counts-round(counts)) > 16*eps(max(1,max(abs(counts)))))
        throw(MException('MATLABGyroid:DescriptorProfileInvalid', ...
            'legacy endpoint-grid spans must contain integer intervals'));
    end
    axes = {linspace(d.x(1),d.x(2),round(counts(1))+1), ...
            linspace(d.y(1),d.y(2),round(counts(2))+1), ...
            linspace(d.z(1),d.z(2),round(counts(3))+1)};
    sampled = evaluate_continuous_graded_gyroid(projected, config, ...
        axes{1}, axes{2}, axes{3});
    field.solid = abs(sampled.G) <= reshape(sampled.threshold,1,1,[]);
    field.axes_over_l = axes;
    field.voxel_size_mm = referenceLengthMm/double(samplesPerReferenceLength);
    field.bounds_mm = struct('x',d.x*referenceLengthMm, ...
        'y',d.y*referenceLengthMm,'z',d.z*referenceLengthMm);
    field.samples_per_reference_length = double(samplesPerReferenceLength);
    field.reference_length_mm = double(referenceLengthMm);
end
```

Before returning, extract the legacy endpoint-grid isosurface at level zero and compute triangle area in physical coordinates. Store it as `field.surface_area_mm2`. Match the pinned TPMS-Designer surface extraction convention; do not reuse the finite hard-box M03 STL area because that is a different boundary protocol.

The field passed to `isosurface` is `abs(sampled.G)-reshape(sampled.threshold,1,1,[])`; the coordinate axes are multiplied by `referenceLengthMm` exactly once. Reject an empty surface or any nonfinite vertex/facet area.

- [x] **Step 4: Implement the five source-parity metrics**

The production body must implement these exact operations and store the global scale in `sampling.reference_length_mm`; it must not use archived target values:

```matlab
[sx,sy,sz] = size(solid);
values.relativeVolume = nnz(solid(1:sx-1,1:sy-1,1:sz-1)) / ...
    ((sx-1)*(sy-1)*(sz-1));
dims = [diff(bounds.x),diff(bounds.y),diff(bounds.z)];
values.relativeArea = surfaceAreaMm2 / ...
    (2*(dims(1)*dims(2)+dims(2)*dims(3)+dims(3)*dims(1)));
padWidth = size(solid,1);
solidPeriodic = padarray(solid,padWidth,'circular','both');
solidBarrier = padarray(~solidPeriodic,[1 1 1],true,'both');
values.thickness = 2*voxelSizeMm*max(bwdist(solidBarrier),[],'all');
voidPeriodic = padarray(solid,padWidth,'circular','both');
voidBarrier = padarray(voidPeriodic,[1 1 1],true,'both');
values.poreDiameter = 2*voxelSizeMm*max(bwdist(voidBarrier),[],'all');
sliceArea = squeeze(sum(solid,[1 2]))*voxelSizeMm^2;
values.areaMean = mean(sliceArea);
```

Before finalizing, compare the padding dimensions and boolean conventions line-by-line with TPMS-Designer commit `a5f7d59b59f5c00e0f50c0bc3675f38f553454eb` `classes/metrics.m`. If source parity requires a syntax adjustment, update both MATLAB and the v2 JSON formula together and record the pinned source lines in a code comment.

Use the exact public signature `compute_legacy_small_descriptors(field, definitionSha256)`. Return the shared envelope and validate it through:

```matlab
function result = validate_descriptor_result(result, expectedProfile, expectedHash)
    names = {'relativeVolume','relativeArea','thickness','poreDiameter','areaMean'};
    if ~isstruct(result) || ~isscalar(result) || ...
            ~all(isfield(result,{'profile','definition_sha256','sampling', ...
            'units','values','diagnostics'}))
        throw(MException('MATLABGyroid:DescriptorProfileInvalid', ...
            'descriptor result envelope is incomplete'));
    end
    if ~strcmp(result.profile,expectedProfile) || ...
            ~strcmp(result.definition_sha256,expectedHash)
        throw(MException('MATLABGyroid:DescriptorContractMismatch', ...
            'descriptor profile identity does not match the active contract'));
    end
    for k = 1:numel(names)
        v = result.values.(names{k});
        if ~isnumeric(v) || ~isscalar(v) || ~isreal(v) || ~isfinite(v)
            throw(MException('MATLABGyroid:DescriptorNonfinite', ...
                'descriptor %s must be a finite real scalar',names{k}));
        end
    end
end
```

- [x] **Step 5: Run legacy tests, analyzer, and regressions**

Run:

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); r=runtests('tests/TestLegacyDescriptors.m'); assertSuccess(r); files=dir(fullfile(pwd,'core','*.m')); for k=1:numel(files), assert(isempty(checkcode(fullfile(files(k).folder,files(k).name),'-id'))); end; run_tests"
```

Expected: legacy suite and all regressions pass; analyzer returns no issues.

- [x] **Step 6: Commit the legacy profile**

```powershell
git add paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_legacy_descriptor_field.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compute_legacy_small_descriptors.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/validate_descriptor_result.m paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/descriptor_definition.v2.json paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestLegacyDescriptors.m
git commit -m "feat(descriptors): reproduce Small legacy geometry metrics"
```

### Task 3: Implement finite-specimen `physical_m04` descriptors

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compute_physical_m04_descriptors.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestPhysicalDescriptors.m`

- [x] **Step 1: Write failing analytic and scale-law tests**

Build in-memory masks for all-solid, all-void, a slab, a cylindrical void, and a box. Test all failure branches explicitly. The scale-law test uses one fixed mask and two physical scales:

```matlab
function testPhysicalScaleLaws(testCase)
    solid = true(21,21,21);
    solid(7:15,7:15,:) = false;
    mesh = TestPhysicalDescriptors.boxMesh([0 1],[0 1],[0 1]);
    definitionHash = repmat('b',1,64);
    r1 = compute_physical_m04_descriptors(solid,.05,mesh,[0 1;0 1;0 1],definitionHash);
    mesh.vertices = 3*mesh.vertices;
    r3 = compute_physical_m04_descriptors(solid,.15,mesh,[0 3;0 3;0 3],definitionHash);
    testCase.verifyEqual(r3.values.relativeVolume,r1.values.relativeVolume,'AbsTol',0);
    testCase.verifyEqual(r3.values.relativeArea,r1.values.relativeArea/3,'RelTol',1e-12);
    testCase.verifyEqual(r3.values.thickness,3*r1.values.thickness,'RelTol',1e-12);
    testCase.verifyEqual(r3.values.poreDiameter,3*r1.values.poreDiameter,'RelTol',1e-12);
    testCase.verifyEqual(r3.values.areaMean,9*r1.values.areaMean,'RelTol',1e-12);
end
```

Also assert 26 selected slice indices include endpoints, duplicates are retained when `Nz < 26`, empty slices are excluded, and anisotropic spacing is rejected.

- [x] **Step 2: Run the test and verify RED**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); r=runtests('tests/TestPhysicalDescriptors.m'); assertSuccess(r)"
```

Expected: undefined `compute_physical_m04_descriptors`.

- [x] **Step 3: Implement the physical algorithms and diagnostics**

Use the exact public signature `compute_physical_m04_descriptors(solid, spacingMm, mesh, boundsMm, definitionSha256)`, where `boundsMm` is a finite `3x2` matrix ordered x/y/z. Use validated M03 interior data only. Surface area is the sum of triangle cross-product areas; reference volume is the finite bounding-box volume:

```matlab
tri = mesh.vertices(mesh.faces(:,2),:) - mesh.vertices(mesh.faces(:,1),:);
trj = mesh.vertices(mesh.faces(:,3),:) - mesh.vertices(mesh.faces(:,1),:);
surfaceArea = .5*sum(vecnorm(cross(tri,trj,2),2,2));
dimensions = boundsMm(:,2)-boundsMm(:,1);
values.relativeVolume = nnz(solid)/numel(solid);
values.relativeArea = surfaceArea/prod(dimensions);
Dsolid = bwdist(~solid);
skel = bwskel(solid);
values.thickness = 2*median(Dsolid(skel))*spacingMm;
voidMask = ~solid;
padded = padarray(voidMask,[1 1 1],false,'both');
Dpad = bwdist(~padded);
Dvoid = Dpad(2:end-1,2:end-1,2:end-1);
cc = bwconncomp(voidMask,26);
counts = cellfun(@numel,cc.PixelIdxList);
[largestCount,largestIndex] = max(counts);
values.poreDiameter = 2*max(Dvoid(cc.PixelIdxList{largestIndex}))*spacingMm;
sliceIndices = round(linspace(1,size(solid,3),26));
areas = zeros(1,0);
for k = 1:numel(sliceIndices)
    c2 = bwconncomp(voidMask(:,:,sliceIndices(k)),8);
    if c2.NumObjects > 0
        areas(end+1) = max(cellfun(@numel,c2.PixelIdxList))*spacingMm^2; %#ok<AGROW>
    end
end
values.areaMean = mean(areas);
```

Reject all-solid, all-void, empty skeleton, empty area list, nonfinite mesh, non-watertight upstream status, and unequal x/y/z spacing using `MATLABGyroid:DescriptorProfileInvalid`. Store component counts, skeleton count, `largestCount`, slice indices, nonempty count, spacing, bounds, surface area, and triangle count in `diagnostics`.

- [x] **Step 4: Run physical tests and regressions**

Use the focused command from Step 2 followed by `run_tests`. Expected: all pass.

- [x] **Step 5: Commit the physical profile**

```powershell
git add paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compute_physical_m04_descriptors.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestPhysicalDescriptors.m
git commit -m "feat(descriptors): add finite physical M04 metrics"
```

### Task 4: Add fail-closed M04 compiler integration

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/read_and_verify_m03_artifacts.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compute_descriptor_profiles.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/canonical_descriptor_text.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/run_descriptor_compiler.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestDescriptorCompiler.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/run_geometry_compiler.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestCompilerPipeline.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/run_tests.m`

- [x] **Step 1: Write failing provenance and publication tests**

Create a valid M03 artifact in `TestMethodSetup`, then test success, request mutation, response mutation, manifest mutation, STL mutation, wrong units/bounds/resolution/compiler version, response-file conflict, response-directory conflict, and M03 preservation after M04 failure. The success assertion is:

```matlab
r = run_descriptor_compiler(requestPath,m03ResponsePath,m04ResponsePath);
testCase.verifyTrue(r.valid);
testCase.verifyEqual(string(fieldnames(r.descriptors))', ...
    ["legacy_small","physical_m04"]);
testCase.verifyFalse(isfield(r,'relativeVolume'));
testCase.verifyTrue(isfile(r.artifacts.manifest_path));
```

- [x] **Step 2: Run the test and verify RED**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); r=runtests('tests/TestDescriptorCompiler.m'); assertSuccess(r)"
```

Expected: undefined `run_descriptor_compiler`.

- [x] **Step 3: Implement dependency authentication**

First extend M03 publication so `response.artifacts.manifest_sha256` is computed from the final manifest file after atomic publication. Add a regression assertion that it equals a fresh `sha256_file` result. This changes M03 provenance only; it must not change meshing behavior or make M03 depend on M04.

Then `read_and_verify_m03_artifacts(request,m03ResponsePath,config)` must independently resolve the manifest and STL from the response, require both paths to be ordinary files, verify their hashes, verify binary STL, and cross-check these exact fields:

```matlab
requiredEqual = {
    m03.request_id, request.request_id, 'request_id';
    manifest.geometry_identity_sha256, m03.geometry_identity_sha256, 'geometry identity';
    manifest.artifact.sha256, sha256_file(stlPath,'MATLABGyroid:M03ArtifactMismatch','STL'), 'STL hash';
    manifest.compiler_version, m03.compiler_version, 'compiler version';
    manifest.discretization.units, 'mm', 'length unit';
    manifest.discretization.resolution, request.resolution, 'resolution'};
```

Also recompute the request hash, require the fresh manifest-file digest to equal `m03.artifacts.manifest_sha256`, validate physical bounds against configuration times reference length, and reject embedded paths that resolve outside the request output directory. Require filenames equal to `sprintf('geometry_%s.stl',m03.geometry_identity_sha256)` and `sprintf('geometry_%s.manifest.json',m03.geometry_identity_sha256)`. Return only authenticated values; never trust a second read of an embedded path.

- [x] **Step 4: Implement orchestration and atomic output**

Use this public signature and stable mapping:

```matlab
function response = run_descriptor_compiler(requestPath,m03ResponsePath,m04ResponsePath)
%RUN_DESCRIPTOR_COMPILER Compute authenticated dual M04 descriptors.
```

On success, build both fields deterministically, compute both profiles, serialize `canonical_descriptor_text` in fixed profile/descriptor order using `%.17g`, hash it, atomically write a descriptor manifest, then atomically write the response. On failure, preserve every M03 file, remove only M04-owned partial artifacts, and map errors to exactly:

```matlab
codes = {'DESCRIPTOR_DEPENDENCY_MISSING','DESCRIPTOR_CONTRACT_MISMATCH', ...
    'DESCRIPTOR_NONFINITE','DESCRIPTOR_PROFILE_INVALID', ...
    'M03_ARTIFACT_MISMATCH','M04_SCALE_NOT_IDENTIFIED', ...
    'M04_GATE0_NOT_FROZEN','M04_GATE0_FAILED','OUTPUT_CONFLICT','INTERNAL_ERROR'};
```

The response must contain `descriptors.legacy_small` and `descriptors.physical_m04`; never publish five flattened descriptor fields.

For ordinary M04 compilation, use the authenticated M03 `resolution` as the legacy endpoint intervals per reference length and the authenticated M03 `reference_length_mm` as its physical scale. For Small Gate-0 only, Tasks 6-7 call the same lower-level legacy functions with the separately frozen density and scale. Thus the public three-argument compiler stays deterministic and does not silently read or tune against archived Small values.

Build the physical mask from the authenticated rebuilt M03 field using the same strict interior selection as M03:

```matlab
d = config.geometry_parameters.domain_over_l;
xInside = field.x_over_l > d.x(1) & field.x_over_l < d.x(2);
yInside = field.y_over_l > d.y(1) & field.y_over_l < d.y(2);
zInside = field.z_over_l > d.z(1) & field.z_over_l < d.z(2);
physicalSolid = field.F(xInside,yInside,zInside) <= 0;
```

Pass the verified STL mesh, physical bounds, and isotropic `field.spacing_mm` to `compute_physical_m04_descriptors`. Pass `build_legacy_descriptor_field(...)` directly to `compute_legacy_small_descriptors`.

Use the orchestration signature:

```matlab
function profiles = compute_descriptor_profiles(projected,config, ...
        resolution,validatedMesh,physicalBoundsMm)
    legacyField = build_legacy_descriptor_field(projected,config, ...
        resolution,config.reference_length_mm);
    profiles.legacy_small = compute_legacy_small_descriptors( ...
        legacyField,config.descriptor_profile_sha256.legacy_small);
    finiteField = build_finite_csg_field(projected,config,resolution,true);
    d = config.geometry_parameters.domain_over_l;
    inside = {finiteField.x_over_l>d.x(1) & finiteField.x_over_l<d.x(2), ...
        finiteField.y_over_l>d.y(1) & finiteField.y_over_l<d.y(2), ...
        finiteField.z_over_l>d.z(1) & finiteField.z_over_l<d.z(2)};
    solid = finiteField.F(inside{1},inside{2},inside{3}) <= 0;
    profiles.physical_m04 = compute_physical_m04_descriptors( ...
        solid,finiteField.spacing_mm,validatedMesh,physicalBoundsMm, ...
        config.descriptor_profile_sha256.physical_m04);
end
```

- [x] **Step 5: Run compiler tests twice and compare canonical hashes**

Run the focused suite and `run_tests`. Expected: both executions produce equal canonical descriptor hashes even though output directories differ.

- [x] **Step 6: Commit Checkpoint D**

```powershell
git add paper_A_reliable_inverse_design/geometry_compiler_matlab/core/read_and_verify_m03_artifacts.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compute_descriptor_profiles.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/canonical_descriptor_text.m paper_A_reliable_inverse_design/geometry_compiler_matlab/run_descriptor_compiler.m paper_A_reliable_inverse_design/geometry_compiler_matlab/run_geometry_compiler.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestDescriptorCompiler.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestCompilerPipeline.m paper_A_reliable_inverse_design/geometry_compiler_matlab/run_tests.m
git commit -m "feat(m04): integrate authenticated dual descriptor compiler"
```

### Task 5: Authenticate the Small workbook and freeze deterministic 6+30 selection

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/prepare_small_gate0_selection.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/fixtures/small_gate0_rows.json`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestDescriptorGate0.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/run_tests.m`

- [x] **Step 1: Write failing selection tests using a compact synthetic workbook**

Construct three temporary sheets named `class1`, `class2`, `class12`, with headers exactly:

```matlab
headers = {'V1a','V1b','V1c','w','relativeVolume','relativeArea', ...
    'thickness','poreDiameter','areaMean'};
```

Assert method mapping, eligibility, deterministic ordering, 2 discovery plus 10 confirmation rows per method, disjoint row IDs, and exact digest input:

```matlab
expected = sha256_text(sprintf('%s|%s|%d|M04-v2-selection', ...
    workbookHash,'class1',excelRow));
testCase.verifyEqual(selection.rows(i).selection_digest,expected);
```

Add rejection tests for wrong workbook hash, sheet count, header order, missing/nonfinite cell, invalid method constraints, and out-of-domain parameters.

- [x] **Step 2: Run Gate-0 tests and verify RED**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); r=runtests('tests/TestDescriptorGate0.m'); assertSuccess(r)"
```

Expected: undefined `prepare_small_gate0_selection`.

- [x] **Step 3: Implement authenticated selection**

Use `readcell` only after verifying the workbook SHA-256 equals:

```text
b4544b09c2688af8bc7aeeca5140a5d4c1cfc1c5b262709c9618c030d90fa561
```

Map `class1->M1`, `class2->M2`, and `class12->M3`. Preserve Excel row numbers starting at 2. Apply `project_method_constraints` and the active compiler bounds before computing the digest. Sort eligible rows by lowercase digest, select `[1:2]` and `[3:12]`, and atomically publish the manifest before evaluating geometry. Compute the manifest identity from fixed canonical lines rather than pretty-printed JSON bytes. The selection loop must have this structure:

```matlab
sheetNames = {'class1','class2','class12'};
methods = {'M1','M2','M3'};
selected = repmat(struct(),0,1);
for s = 1:3
    raw = readcell(workbookPath,'Sheet',sheetNames{s});
    assert_exact_headers(raw(1,1:9));
    eligible = collect_eligible_rows(raw(2:end,1:9),methods{s},config,2);
    for k = 1:numel(eligible)
        eligible(k).selection_digest = sha256_text(sprintf( ...
            '%s|%s|%d|M04-v2-selection',workbookHash,sheetNames{s}, ...
            eligible(k).excel_row));
    end
    [~,order] = sort({eligible.selection_digest});
    eligible = eligible(order);
    for k = 1:12
        if k <= 2
            eligible(k).role = 'discovery';
        else
            eligible(k).role = 'confirmation';
        end
    end
    selected = [selected; eligible(1:12)]; %#ok<AGROW>
end
```

- [x] **Step 4: Audit the real workbook and create the committed compact fixture**

Run:

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); addpath('gate0'); prepare_small_gate0_selection('F:\demo_TPMS\xiedian\Inverse-design-of-graded-TPMS-main\Inverse-design-of-graded-TPMS-main\dataset used for training\test.xlsx','tests\fixtures\small_gate0_rows.json')"
```

Expected: exactly 36 rows, 12 per method, with six tagged `discovery` and 30 tagged `confirmation`; the source workbook remains unchanged and outside Git.

- [x] **Step 5: Re-run tests and commit selection provenance**

```powershell
git add paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/prepare_small_gate0_selection.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/fixtures/small_gate0_rows.json paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestDescriptorGate0.m paper_A_reliable_inverse_design/geometry_compiler_matlab/run_tests.m
git commit -m "feat(gate0): freeze deterministic Small descriptor cases"
```

### Task 6: Implement discovery calibration and immutable freeze

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/calibrate_legacy_scale.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/freeze_legacy_calibration.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/canonical_legacy_calibration_freeze.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/verify_legacy_calibration_freeze.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/legacy_calibration_contract.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/legacy_case_identity_sha256.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/validate_legacy_calibration_payload.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/canonical_small_gate0_selection.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/verify_small_gate0_selection.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/select_small_gate0_rows.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestDescriptorGate0.m`

- [x] **Step 1: Write failing density, scale-law, and tamper tests**

Use injected descriptor-computation functions so unit tests do not require 60 full TPMS evaluations. Assert the preregistered candidate order exactly `20, 24, 30, 32, 40, 48, 60, 64, 80, 96`; rank by pooled median, pooled p95, then lower density. Test threshold boundary equality, all three scale laws, nonpositive estimates, group disagreement, altered selection hash, confirmation override, and freeze mutation.

```matlab
fake = @(row,n,L) TestDescriptorGate0.fakeLegacy(row,n,L);
cal = calibrate_legacy_scale(selection,fake,1e-12);
testCase.verifyEqual(cal.status,'M04_CALIBRATION_IDENTIFIED');
testCase.verifyEqual(cal.samples_per_reference_length,30);
testCase.verifyLessThanOrEqual(cal.scale_statistics.mard,0.02);
testCase.verifyLessThanOrEqual(cal.scale_statistics.p95,0.05);
```

- [x] **Step 2: Run focused tests and verify RED**

Use the Task 5 test command. Expected: undefined calibration/freezing functions.

- [x] **Step 3: Implement preregistered error statistics and density selection**

Use one relative-error implementation everywhere:

```matlab
function e = relative_error(computed,archived,absoluteTolerance)
    e = abs(computed-archived) ./ max(abs(archived),absoluteTolerance);
end
```

For each density, pool only `relativeVolume` and `relativeArea` across six discovery cases. Compute percentile by a documented deterministic linear interpolation function, not a release-dependent default. A density is eligible only when each of the two descriptors independently has median `<=.02` and p95 `<=.05`. If none is eligible, return `M04_SCALE_NOT_IDENTIFIED` and do not produce a freeze.

- [x] **Step 4: Implement the single global scale and atomic freeze**

At unit reference length calculate exactly:

```matlab
estimates = [archivedThickness./computedThickness, ...
             archivedPore./computedPore, ...
             sqrt(archivedArea./computedArea)];
frozenLength = median(estimates,'all');
relativeDeviation = abs(estimates-frozenLength)/frozenLength;
```

Require all 18 estimates positive/finite, overall median deviation `<=.02`, deterministic p95 `<=.05`, and each group median within `.02` of `frozenLength`. Serialize the length with `sprintf('%.17g',frozenLength)`. The freeze includes selection/workbook/profile/compiler hashes, pinned TPMS-Designer commit, every discovery result, confirmation row identities without results, and `freeze_sha256` calculated over a canonical representation that excludes only the `freeze_sha256` field.

`freeze_legacy_calibration` must refuse any existing file or directory. Its reader must recompute the digest and reject any override of scale, density, formulas, case identities, or tolerances with `M04_GATE0_NOT_FROZEN`.

- [x] **Step 5: Run focused tests and commit discovery freeze logic**

Run Gate-0 tests plus `run_tests`, then:

```powershell
git add paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/calibrate_legacy_scale.m paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/freeze_legacy_calibration.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestDescriptorGate0.m
git commit -m "feat(gate0): preregister and freeze legacy calibration"
```

### Task 7: Implement resumable 30-case confirmation and terminal report

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/summarize_descriptor_errors.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/run_small_descriptor_gate0.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestDescriptorGate0.m`

- [ ] **Step 1: Write failing confirmation-state tests**

Use fake case runners to cover all-pass, one threshold failure, nonfinite output, nondeterminism, mid-run interruption/resume, corrupted checkpoint, missing checkpoint, changed freeze, and forbidden overrides. Assert no failed case can be skipped.

```matlab
report = run_small_descriptor_gate0(freezePath,outputDir,fakeRunner);
testCase.verifyEqual(report.case_count,30);
testCase.verifyEqual(report.comparison_count,150);
testCase.verifyEqual(report.status,'M04_GATE0_PASSED');
testCase.verifyTrue(all([report.per_descriptor.median] <= .02));
testCase.verifyTrue(all([report.per_descriptor.p95] <= .05));
```

- [ ] **Step 2: Run Gate-0 tests and verify RED**

Expected: undefined confirmation runner and summarizer.

- [ ] **Step 3: Implement verified checkpoint/resume semantics**

For each frozen confirmation row in order, derive a case identity from the freeze hash plus selection digest. Before reusing a checkpoint, authenticate its identity, inputs, computed descriptor hash, and JSON canonical-value hash. If missing, run M03 and legacy descriptors twice into separate temporary directories and compare canonical descriptor text. Publish one atomic case JSON only after equality. Stop immediately on any failure; never advance the next case index.

```matlab
caseId = sha256_text(sprintf('freeze=%s\nselection=%s\n', ...
    freeze.freeze_sha256,row.selection_digest));
casePath = fullfile(outputDir,['case_',caseId,'.json']);
if exist(casePath,'file') == 2
    checkpoint = verify_case_checkpoint(casePath,freeze,row,caseId);
else
    first = caseRunner(row,freeze,1);
    second = caseRunner(row,freeze,2);
    if ~strcmp(canonical_descriptor_text(first), ...
            canonical_descriptor_text(second))
        throw(MException('MATLABGyroid:M04Gate0Failed', ...
            'confirmation case is nondeterministic: %s',caseId));
    end
    checkpoint = build_case_checkpoint(first,freeze,row,caseId);
    write_json_atomic(checkpoint,casePath);
end
verifiedCases(end+1) = checkpoint; %#ok<AGROW>
```

- [ ] **Step 4: Implement exact pass/fail statistics**

Produce, for each descriptor and each method脳descriptor group: count, median relative error, deterministic p95, maximum, signed bias, RMSE, and Spearman rank correlation with tied-rank handling. Pass only when all 30 cases are finite/deterministic, every descriptor median `<=.02` and p95 `<=.05`, and the pooled 150 median `<=.02` and p95 `<=.05`.

If either ranked vector is constant, serialize `rank_correlation` as JSON `null` and set `rank_correlation_status` to `undefined_constant_input`; do not serialize NaN or invent a numeric correlation.

Return exactly one of:

```matlab
terminal = {'M04_GATE0_PASSED','M04_GATE0_FAILED', ...
    'M04_SCALE_NOT_IDENTIFIED','M04_GATE0_NOT_FROZEN'};
```

The report records the six discovery and 30 confirmation row IDs under `excluded_from_independent_model_evaluation`.

- [ ] **Step 5: Independently recompute the summary in the test**

Load the 30 per-case JSON files without calling `summarize_descriptor_errors`, recompute the 150 errors in test code, and assert exact equality with the report's stored count, median, p95, and status. This prevents a shared production bug from validating itself.

- [ ] **Step 6: Run tests and commit Checkpoint G implementation**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); r=runtests('tests/TestDescriptorGate0.m'); assertSuccess(r); run_tests"
git add paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0 paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestDescriptorGate0.m
git commit -m "feat(gate0): add immutable Small confirmation gate"
```

### Task 8: Build the MATLAB Abaqus Gate-0 package contract

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/abaqus_gate0_request.schema.json`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/material_profile.gate0.reference.json`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_abaqus_gate0_package.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/validate_abaqus_gate0_package.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/run_abaqus_gate0_packager.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestAbaqusGate0Package.m`

- [ ] **Step 1: Write failing package-contract tests**

Test deterministic package identity, exact five-file inventory, overwrite refusal, changed material profile, hash mismatch, wrong unit, wrong status, negative dimension, absolute path, `..` escape, missing artifact, extra checksum entry, STL tampering, and M03/M04 identity mismatch.

```matlab
r = run_abaqus_gate0_packager(m03Path,m04Path,materialPath,outRoot);
testCase.verifyEqual(r.status,'ABAQUS_PACKAGE_PREPARED_NOT_RUN');
q = jsondecode(fileread(fullfile(r.package_path,'abaqus_gate0_request.json')));
testCase.verifyEqual(q.representation,'closed_surface_stl');
testCase.verifyEqual(q.volume_mesh_status,'not_generated');
testCase.verifyFalse(q.solver_ready);
testCase.verifyEqual(q.execution_status,'prepared_not_run');
testCase.verifyEqual(q.target_nominal_compression_strain,.25);
```

- [ ] **Step 2: Run package tests and verify RED**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); r=runtests('tests/TestAbaqusGate0Package.m'); assertSuccess(r)"
```

Expected: missing schema and package functions.

- [ ] **Step 3: Define and validate the request schema**

The JSON schema and MATLAB validator must require these invariant values:

```json
{
  "length_unit": "mm",
  "compression_direction": "z",
  "representation": "closed_surface_stl",
  "volume_mesh_status": "not_generated",
  "solver_ready": false,
  "intended_solver": "Abaqus/Explicit",
  "target_nominal_compression_strain": 0.25,
  "periodicity": {"x": true, "y": true},
  "bottom_constraint_intent": "all_6_dof_fixed",
  "top_constraint_intent": "z_translation_only",
  "execution_status": "prepared_not_run"
}
```

Also require finite positive dimensions, bounds, axes, top/bottom z, artifact hashes, geometry identity, material profile ID/version/hash, and `plane_selection_tolerance_mm = max(.25*spacing_mm,1e-9*height_mm)`.

The material reference is deliberately non-solver-ready and contains no invented constitutive constants:

```json
{
  "schema_version": "1.0",
  "material_profile_id": "paper-a-material-pending-m05-calibration",
  "status": "reference_only_not_solver_ready",
  "unit_system": "mm-MPa-s",
  "constitutive_model": "deferred_to_m05",
  "parameter_source": "not_assigned"
}
```

- [ ] **Step 4: Implement immutable staging and publication**

Compute the package ID from newline-terminated canonical key/value lines containing geometry identity, STL digest, geometry-manifest digest, descriptor-result digest, request-schema version, and material-profile identifier. Stage the five files in a sibling temporary directory, copy authenticated bytes, write `checksums.sha256` with exactly four entries for the other files, validate the staged package, and rename it atomically to `fullfile(outputRoot,'abaqus_gate0',packageSha256)`. Refuse an existing leaf or directory.

The successful runner response contains only:

```matlab
response = struct('status','ABAQUS_PACKAGE_PREPARED_NOT_RUN', ...
    'package_sha256',packageSha,'package_path',finalPath, ...
    'solver_ready',false,'execution_status','prepared_not_run');
```

- [ ] **Step 5: Run MATLAB package tests and commit**

Run the focused suite and `run_tests`, then:

```powershell
git add paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/abaqus_gate0_request.schema.json paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/material_profile.gate0.reference.json paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_abaqus_gate0_package.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/validate_abaqus_gate0_package.m paper_A_reliable_inverse_design/geometry_compiler_matlab/run_abaqus_gate0_packager.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestAbaqusGate0Package.m
git commit -m "feat(abaqus): prepare immutable Gate-0 exchange package"
```

### Task 9: Implement ordinary-Python offline preflight and solver-execution guard

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/abaqus/preflight_gate0_package.py`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestAbaqusGate0Package.m`

- [ ] **Step 1: Add failing Python-preflight integration tests**

From MATLAB, call normal Python with a known-good package and assert exit 0/status JSON. Copy that package and independently mutate one condition per test: checksum, STL length/count, NaN facet payload, path escape, symlink escape where supported, missing file, extra checksum entry, wrong bounds/unit/status.

- [ ] **Step 2: Implement standard-library preflight**

The CLI is:

```python
def main(argv: list[str]) -> int:
    package = pathlib.Path(argv[1]).resolve(strict=True)
    validate_inventory(package)
    expected = parse_checksums(package / "checksums.sha256")
    validate_relative_members(package, expected)
    validate_digests(package, expected)
    request = json.loads((package / "abaqus_gate0_request.json").read_text("utf-8"))
    validate_request(request)
    validate_binary_stl(package / "geometry.stl", request)
    print(json.dumps({"status":"ABAQUS_PACKAGE_PREPARED_NOT_RUN", ...
                      "solver_ready":False}, sort_keys=True))
    return 0
```

Use only `hashlib`, `json`, `math`, `pathlib`, `struct`, and `sys`. Require exactly the five package files. For every relative member, reject absolute paths, `..`, symlinks, and any resolved path outside the package. For binary STL, require byte length `84 + 50*triangle_count`, unpack all 12 facet floats, reject nonfinite floats, and compare mesh bounds with the request within the declared plane tolerance.

- [ ] **Step 3: Add a source guard that proves Abaqus cannot run**

Add this test over all production `.py` files under `abaqus/`:

```matlab
files = dir(fullfile(testCase.BaseDir,'abaqus','*.py'));
for k = 1:numel(files)
    source = lower(fileread(fullfile(files(k).folder,files(k).name)));
    testCase.verifyFalse(contains(source,'job.submit('));
    testCase.verifyFalse(contains(source,'import abaqus'));
    testCase.verifyFalse(contains(source,'from abaqus'));
end
```

- [ ] **Step 4: Run normal-Python and full regression tests**

```powershell
$packagePath = (Get-ChildItem -LiteralPath 'F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab\release_artifacts\abaqus_gate0' -Directory | Sort-Object Name | Select-Object -First 1).FullName
python paper_A_reliable_inverse_design/geometry_compiler_matlab/abaqus/preflight_gate0_package.py $packagePath
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); r=runtests('tests/TestAbaqusGate0Package.m'); assertSuccess(r); run_tests"
```

Expected Python JSON contains `ABAQUS_PACKAGE_PREPARED_NOT_RUN` and `solver_ready:false`; all MATLAB tests pass. The directory must contain exactly one package for this focused manual check; otherwise select the intended package by its recorded SHA-256 instead of using `Select-Object -First 1`.

- [ ] **Step 5: Commit the offline preflight**

```powershell
git add paper_A_reliable_inverse_design/geometry_compiler_matlab/abaqus/preflight_gate0_package.py paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestAbaqusGate0Package.m
git commit -m "test(abaqus): enforce offline Gate-0 package preflight"
```

### Task 10: Run release calibration, confirmation, and package evidence

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/recompute_descriptor_summary_independent.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/package_representative_gate0_cases.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/release/m04_selection_manifest.json`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/release/m04_calibration_freeze.json`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/release/m04_confirmation_summary.json`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/release/M04_QA_REPORT.md`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/docs/M04_USAGE.md`

- [ ] **Step 1: Run static analysis and the complete unit suite**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); files=dir(fullfile(pwd,'**','*.m')); for k=1:numel(files), issues=checkcode(fullfile(files(k).folder,files(k).name),'-id'); assert(isempty(issues),strjoin({issues.message},newline)); end; run_tests"
```

Expected: zero analyzer issues and every M01-M04 unit test passes.

- [ ] **Step 2: Re-audit the real workbook and regenerate selection**

Run `prepare_small_gate0_selection` against the authenticated external workbook and compare the regenerated canonical manifest hash to the committed compact fixture:

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); addpath('core','gate0'); prepare_small_gate0_selection('F:\demo_TPMS\xiedian\Inverse-design-of-graded-TPMS-main\Inverse-design-of-graded-TPMS-main\dataset used for training\test.xlsx','release\m04_selection_manifest.json')"
```

Expected: workbook hash matches, headers match, and all 36 row identities/values match exactly.

- [ ] **Step 3: Run six-case discovery and freeze before confirmation**

Run `calibrate_legacy_scale` over exactly the six discovery rows and preregistered density list, then call `freeze_legacy_calibration`:

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); addpath('core','gate0'); config=load_compiler_config(fullfile('configs','compiler_config.example.json')); selection=jsondecode(fileread(fullfile('release','m04_selection_manifest.json'))); runner=@(row,n,L) compute_legacy_small_descriptors(build_legacy_descriptor_field(project_method_constraints(row.method,row.raw_parameters,config),config,n,L),config.descriptor_profile_sha256.legacy_small); calibration=calibrate_legacy_scale(selection,runner,1e-12); freeze_legacy_calibration(calibration,selection,fullfile('release','m04_calibration_freeze.json'));"
```

Inspect the freeze before any confirmation call. Continue only if the status is identified, both scale-free descriptor thresholds pass, and all 18 scale estimates satisfy the global consistency gates. Commit the freeze before executing confirmation:

```powershell
git add paper_A_reliable_inverse_design/geometry_compiler_matlab/release/m04_selection_manifest.json paper_A_reliable_inverse_design/geometry_compiler_matlab/release/m04_calibration_freeze.json
git commit -m "data(gate0): freeze M04 discovery calibration"
```

- [ ] **Step 4: Run the untouched 30-case confirmation once**

The production signature is `run_small_descriptor_gate0(freezePath,outputDir)`; only tests may provide the optional third injected runner. Call it with the committed freeze and no overrides:

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); addpath('core','gate0'); report=run_small_descriptor_gate0(fullfile('release','m04_calibration_freeze.json'),fullfile('release_artifacts','m04_confirmation')); write_json_atomic(report,fullfile('release','m04_confirmation_summary.json'));"
```

Preserve all per-case outputs outside Git; commit only the summary. If any case fails, keep the complete failure evidence and report `M04_GATE0_FAILED`; do not tune density, scale, formulas, or thresholds on these rows.

- [ ] **Step 5: Independently recompute the confirmation summary**

Implement `recompute_descriptor_summary_independent(caseDirectory,summaryPath)` without calling production summary functions, then run:

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); addpath('core','gate0'); independent=recompute_descriptor_summary_independent(fullfile('release_artifacts','m04_confirmation'),fullfile('release','m04_confirmation_summary.json')); assert(independent.case_count==30); assert(independent.comparison_count==150);"
```

Confirm per-descriptor and pooled metrics, terminal status, and exclusion tags. Record both production and independent hashes in `M04_QA_REPORT.md`.

- [ ] **Step 6: Produce three representative offline packages**

Proceed only when the immutable confirmation summary status is exactly `M04_GATE0_PASSED`. Implement `package_representative_gate0_cases(caseDirectory,packageRoot,materialPath)` to choose the lowest selection digest among successful confirmation cases for each of M1, M2, and M3, package each with the same versioned material reference, and invoke ordinary Python preflight. Run:

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); addpath('core','gate0'); packages=package_representative_gate0_cases(fullfile('release_artifacts','m04_confirmation'),fullfile('release_artifacts','abaqus_gate0'),fullfile('configs','material_profile.gate0.reference.json')); assert(numel(packages)==3); assert(all(strcmp({packages.status},'ABAQUS_PACKAGE_PREPARED_NOT_RUN')));"
```

Record package SHA-256 and `ABAQUS_PACKAGE_PREPARED_NOT_RUN`; do not commit large STL/package directories.

- [ ] **Step 7: Write usage and boundary documentation**

`M04_USAGE.md` must show exact commands for descriptor compilation, workbook audit, discovery, freeze, confirmation, packaging, and Python preflight. State prominently:

```text
legacy_small is for historical Small compatibility only.
physical_m04 is for the new finite-specimen Paper A dataset.
The two profiles must not be flattened or mixed without profile name, hash, and units.
A closed surface STL is not a solver-ready Abaqus volume mesh.
M04 does not run Abaqus.
```

- [ ] **Step 8: Final verification and release commit**

Run:

```powershell
git diff --check
git status --short
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'); run_tests"
```

Expected before staging: only the planned release evidence and documentation are untracked/modified, no large generated fields/STLs/packages are present, and all tests pass. Then commit:

```powershell
git add paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/recompute_descriptor_summary_independent.m paper_A_reliable_inverse_design/geometry_compiler_matlab/gate0/package_representative_gate0_cases.m paper_A_reliable_inverse_design/geometry_compiler_matlab/release paper_A_reliable_inverse_design/geometry_compiler_matlab/docs/M04_USAGE.md
git commit -m "docs(m04): publish descriptor Gate-0 evidence"
```

## Final acceptance checklist

- [ ] The preserved v1 file still hashes to `2f59976c74cc88eac66c43a56e242f50f28aff0e71be8d752a481c05a4a2d9c9`.
- [ ] M03 remains independently executable and all pre-M04 tests pass.
- [ ] Results contain two named profiles, two definition hashes, and unambiguous units; no flattened descriptor vector is published.
- [ ] Legacy algorithms match pinned TPMS-Designer array and padding semantics.
- [ ] Physical algorithms pass analytic fixtures and exact scaling laws.
- [ ] All M04 dependencies are re-authenticated and failures preserve M03 artifacts.
- [ ] The selection is authenticated, deterministic, and exactly 6+30 disjoint cases.
- [ ] One density and one global scale are frozen before confirmation.
- [ ] Confirmation returns exactly one declared terminal state and no threshold is described as approximately passing.
- [ ] Calibration and confirmation rows are marked as excluded from independent model-evaluation claims.
- [ ] Abaqus packages contain exactly five files, pass MATLAB/Python validation, and remain `solver_ready=false` / `prepared_not_run`.
- [ ] Production Python contains no Abaqus import and no solver submission token.
- [ ] Analyzer is clean, full MATLAB suite passes, `git diff --check` passes, and generated large artifacts remain outside Git.

