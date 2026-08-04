# M03 Continuous-CSG Meshing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, fail-closed MATLAB R2023b compiler path that converts an M1/M2/M3 graded sheet-Gyroid request into a continuous hard-box CSG surface, audited watertight binary STL, response JSON, and manifest.

**Architecture:** Preserve the M01/M02 contracts and refactor their Gyroid evaluation into a reusable continuous-coordinate kernel. M03 samples a cell-centred continuous CSG field, extracts a shared-index mesh, validates geometry/topology/self-intersection before serialization, and publishes artifacts atomically. Binary occupancy remains diagnostic only and never replaces a rejected continuous-CSG result.

**Tech Stack:** MATLAB R2023b, Image Processing Toolbox for diagnostic connectivity, `matlab.unittest`, `isosurface`, `triangulation`, Java SHA-256 already used by the repository, Git.

---

## Scope and file map

All paths below are relative to `paper_A_reliable_inverse_design/geometry_compiler_matlab`.

**Existing files to modify**

- `core/compiler_version.m` — bump the compiler version for the M03 contract.
- `core/compiler_contract.m` — freeze the continuous-CSG identity, beta, grid convention, level, and validation stage.
- `core/build_graded_gyroid_field.m` — delegate numerical field evaluation to the new arbitrary-axis kernel without changing its public outputs.
- `tests/TestBootstrap.m` — lock the M03 compiler constants and version.
- `tests/TestFieldKernel.m` — prove backward compatibility and arbitrary-axis equivalence.

**New production files**

- `core/evaluate_continuous_graded_gyroid.m` — evaluate Gyroid, threshold, and cell-size profiles on arbitrary normalized axes.
- `core/build_finite_csg_field.m` — build the staggered physical/normalized sampling grid and authoritative hard-box CSG scalar field.
- `core/compose_hard_box_csg.m` — pure field-level CSG composition used by production and truth-table tests.
- `core/extract_isosurface_mesh.m` — convert the CSG zero set to a correctly oriented coordinate mesh.
- `core/validate_surface_mesh.m` — basic, two-manifold, orientation, connected-component, and mesh-quality gate.
- `core/detect_mesh_self_intersections.m` — deterministic sweep-and-prune broad phase and exact triangle-pair narrow phase.
- `core/triangles_intersect_3d.m` — tested non-coplanar and coplanar triangle intersection predicate.
- `core/export_binary_stl.m` — write a request-scoped temporary binary STL and atomically publish it.
- `core/verify_binary_stl.m` — verify header/count/byte length/finite payload and return an artifact summary.
- `core/sha256_text.m` — SHA-256 for canonical UTF-8 text.
- `core/parse_and_validate_request.m` — strict public JSON request boundary and semantic hash.
- `core/build_geometry_manifest.m` — stable manifest structure and geometry-identity hash.
- `core/write_json_atomic.m` — deterministic JSON write to temporary file followed by atomic publication.
- `core/compare_mesh_convergence.m` — volume, area, topology, and deterministic bidirectional surface-distance proxy.
- `run_geometry_compiler.m` — public two-argument orchestration boundary.

**New tests**

- `tests/TestContinuousCSG.m` — staggered grid, CSG truth table, exterior margin, and M1/M2/M3 field smoke tests.
- `tests/TestSurfaceMesh.m` — coordinate order, degeneracy, manifold, orientation, components, and self-intersection tests.
- `tests/TestBinarySTL.m` — binary writer/verifier, hash, conflict, and corruption tests.
- `tests/TestCompilerPipeline.m` — strict request, failure response, deterministic integration, manifest, and artifact tests.
- `tests/TestMeshConvergence.m` — convergence metric and surface-distance proxy tests.
- `docs/M03_USAGE.md` — exact request, command, artifact, failure-code, and validity-boundary documentation.

Do not modify descriptor formulas or claim M04/Abaqus/print validity in this plan.

## Test command convention

Run focused tests from repository root with this PowerShell pattern:

```powershell
$compilerDir = (Resolve-Path 'paper_A_reliable_inverse_design\geometry_compiler_matlab').Path.Replace('\','/')
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('$compilerDir'); addpath('core'); r=runtests('tests/TestContinuousCSG.m'); assert(all([r.Passed]));"
```

Run the complete suite from the compiler directory:

```powershell
$compilerDir = (Resolve-Path 'paper_A_reliable_inverse_design\geometry_compiler_matlab').Path.Replace('\','/')
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('$compilerDir'); run_tests;"
```

If MATLAB does not reach batch execution within 120 seconds, record the launcher/license/startup failure separately. Do not reinterpret an environment timeout as a test failure or a passing result.

### Task 1: Freeze the M03 compiler contract

**Files:**

- Modify: `core/compiler_version.m`
- Modify: `core/compiler_contract.m`
- Modify: `tests/TestBootstrap.m`

- [ ] **Step 1: Write failing version and contract tests**

Add these test methods to `TestBootstrap`:

```matlab
function testCompilerVersion(testCase)
    testCase.verifyEqual(compiler_version(), 'matlab-gyroid-0.2.0');
end

function testM03ContinuousCsgContract(testCase)
    contract = compiler_contract();
    testCase.verifyEqual(contract.geometryDefinition, ...
        'continuous_sheet_gyroid_intersect_hard_box');
    testCase.verifyEqual(contract.validationStage, 'M03_GEOMETRY_MESH');
    testCase.verifyEqual(contract.betaBox, 1.0);
    testCase.verifyEqual(contract.isosurfaceLevel, 0.0);
    testCase.verifyEqual(contract.gridConvention, ...
        'cell_centered_half_step_exterior');
end
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
$compilerDir = (Resolve-Path 'paper_A_reliable_inverse_design\geometry_compiler_matlab').Path.Replace('\','/')
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('$compilerDir'); addpath('core'); r=runtests('tests/TestBootstrap.m'); assert(all([r.Passed]));"
```

Expected: FAIL because the version is `0.1.0` and the new contract fields do not exist.

- [ ] **Step 3: Implement the frozen constants**

Change the version return value and add these fields to `compiler_contract`:

```matlab
version = 'matlab-gyroid-0.2.0';
```

```matlab
contract.geometryDefinition = ...
    'continuous_sheet_gyroid_intersect_hard_box';
contract.validationStage = 'M03_GEOMETRY_MESH';
contract.betaBox = 1.0;
contract.isosurfaceLevel = 0.0;
contract.gridConvention = 'cell_centered_half_step_exterior';
contract.requestSchemaVersion = '1.0';
contract.requestFields = {'schema_version', 'request_id', 'method', ...
    'c0', 'c1', 'c2', 'w', 'resolution', 'output_dir'};
```

- [ ] **Step 4: Run focused and complete tests**

Expected: focused tests PASS; all pre-existing tests PASS with only the intentional version assertion changed.

- [ ] **Step 5: Commit**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compiler_version.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compiler_contract.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestBootstrap.m
git commit -m "feat(geometry): freeze M03 continuous CSG contract"
```

### Task 2: Extract an arbitrary-axis continuous Gyroid evaluator

**Files:**

- Create: `core/evaluate_continuous_graded_gyroid.m`
- Modify: `core/build_graded_gyroid_field.m`
- Modify: `tests/TestFieldKernel.m`

- [ ] **Step 1: Write equivalence and exterior-axis tests**

Add tests that call the new evaluator on the axes returned by the old wrapper and on half-step exterior axes:

```matlab
function testContinuousEvaluatorMatchesLegacyGrid(testCase)
    projected = project_method_constraints('M3', ...
        struct('c0',0.04,'c1',0.10,'c2',0.16,'w',4), testCase.Config);
    legacy = build_graded_gyroid_field(projected, testCase.Config, 8);
    direct = evaluate_continuous_graded_gyroid(projected, ...
        testCase.Config, legacy.x_over_l, legacy.y_over_l, legacy.z_over_l);
    testCase.verifyEqual(direct.G, legacy.G);
    testCase.verifyEqual(direct.threshold, legacy.threshold);
    testCase.verifyEqual(direct.cell_size_over_l, legacy.cell_size_over_l);
end

function testContinuousEvaluatorClampsOnlyExteriorProfileInput(testCase)
    projected = project_method_constraints('M3', ...
        struct('c0',0.04,'c1',0.10,'c2',0.16,'w',4), testCase.Config);
    sample = evaluate_continuous_graded_gyroid(projected, testCase.Config, ...
        [-0.0625,0.5,1.0625], [-0.0625,0.5,1.0625], ...
        [-0.0625,1,2.0625]);
    testCase.verifyEqual(sample.profile_z_over_l, [0,1,2]);
    testCase.verifyTrue(all(isfinite(sample.G(:))));
    testCase.verifyEqual(sample.threshold, [0.04,0.10,0.16], ...
        'AbsTol',100*eps);
end
```

- [ ] **Step 2: Run the focused test and verify RED**

Expected: FAIL with `Undefined function 'evaluate_continuous_graded_gyroid'`.

- [ ] **Step 3: Create the evaluator**

Implement this public shape. Keep validation local so malformed axes cannot reach implicit expansion:

```matlab
function sample = evaluate_continuous_graded_gyroid( ...
        projected, config, xOverL, yOverL, zOverL)
%EVALUATE_CONTINUOUS_GRADED_GYROID Evaluate the M02 field on arbitrary axes.
    errorId = 'MATLABGyroid:InvalidGeometry';
    xOverL = validate_axis(xOverL, 'x_over_l', errorId);
    yOverL = validate_axis(yOverL, 'y_over_l', errorId);
    zOverL = validate_axis(zOverL, 'z_over_l', errorId);
    domain = config.geometry_parameters.domain_over_l;
    profileZ = min(max(zOverL, domain.z(1)), domain.z(2));
    threshold = evaluate_threshold_profile(profileZ, projected);
    cellSize = evaluate_cell_size_profile(profileZ, projected, config);

    xPhase = 2*pi*xOverL/config.geometry_parameters.Lx_over_l;
    yPhase = 2*pi*yOverL/config.geometry_parameters.Ly_over_l;
    zPhase = 2*pi*zOverL./cellSize;
    sinX = reshape(sin(xPhase), [], 1, 1);
    cosX = reshape(cos(xPhase), [], 1, 1);
    sinY = reshape(sin(yPhase), 1, [], 1);
    cosY = reshape(cos(yPhase), 1, [], 1);
    sinZ = reshape(sin(zPhase), 1, 1, []);
    cosZ = reshape(cos(zPhase), 1, 1, []);
    G = sinX.*cosY + sinY.*cosZ + sinZ.*cosX;
    if ~isreal(G) || any(~isfinite(G(:)))
        throw(MException(errorId, 'continuous Gyroid field must be finite and real'));
    end
    sample = struct('G',G,'threshold',threshold, ...
        'cell_size_over_l',cellSize,'profile_z_over_l',profileZ);
end

function axisValue = validate_axis(value, label, errorId)
    if ~isnumeric(value) || ~isvector(value) || isempty(value) || ...
            ~isreal(value) || any(~isfinite(value(:)))
        throw(MException(errorId, ...
            '%s must be a non-empty finite real numeric vector', label));
    end
    axisValue = double(value(:)');
    if numel(axisValue) > 1 && any(diff(axisValue) <= 0)
        throw(MException(errorId, '%s must be strictly increasing', label));
    end
end
```

Replace only the phase/profile calculation block in `build_graded_gyroid_field` with a call to this function and assign its fields to the existing result structure. Do not change its endpoint grid or low-resolution test behavior.

- [ ] **Step 4: Run `TestFieldKernel` and the complete suite**

Expected: direct/legacy equality PASS and all current numerical fixtures remain unchanged.

- [ ] **Step 5: Commit**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/evaluate_continuous_graded_gyroid.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_graded_gyroid_field.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestFieldKernel.m
git commit -m "refactor(geometry): expose continuous graded Gyroid evaluator"
```

### Task 3: Build the staggered hard-box CSG field

**Files:**

- Create: `core/compose_hard_box_csg.m`
- Create: `core/build_finite_csg_field.m`
- Create: `tests/TestContinuousCSG.m`

- [ ] **Step 1: Write CSG truth-table and staggered-grid tests**

Create `TestContinuousCSG` with class setup matching `TestFieldKernel`, then add:

```matlab
function testHardBoxCsgTruthTable(testCase)
    fSheet = reshape([-1,-1,1,1],2,2);
    fBox = reshape([-1,1,-1,1],2,2);
    F = compose_hard_box_csg(fSheet, fBox, 1.0);
    testCase.verifyEqual(F <= 0, (fSheet <= 0) & (fBox <= 0));
    testCase.verifyEqual(F, max(fSheet,fBox));
end

function testFiniteGridIsHalfStepStaggered(testCase)
    projected = project_method_constraints('M1', ...
        struct('c0',0.10,'c1',0.10,'c2',0.10,'w',0), testCase.Config);
    field = build_finite_csg_field(projected, testCase.Config, 8, false);
    h = 1/8;
    testCase.verifyEqual(field.x_over_l([1,end]), [-h/2,1+h/2], ...
        'AbsTol',eps);
    testCase.verifyEqual(field.z_over_l([1,end]), [-h/2,2+h/2], ...
        'AbsTol',eps);
    testCase.verifyFalse(any(field.x_over_l == 0 | field.x_over_l == 1));
    testCase.verifyTrue(all(field.F([1,end],:,:) > 0,'all'));
    testCase.verifyTrue(all(field.F(:,[1,end],:) > 0,'all'));
    testCase.verifyTrue(all(field.F(:,:,[1,end]) > 0,'all'));
end
```

The fourth argument is a test-only `enforceAllowedLevel` switch. Production calls pass `true`; low-resolution unit tests pass `false`.

- [ ] **Step 2: Run `TestContinuousCSG` and verify RED**

Expected: FAIL because both production functions are absent.

- [ ] **Step 3: Implement the pure CSG composition**

```matlab
function F = compose_hard_box_csg(fSheet, fBox, betaBox)
%COMPOSE_HARD_BOX_CSG Hard intersection of sheet and finite box fields.
    errorId = 'MATLABGyroid:InvalidGeometry';
    if ~isequal(size(fSheet),size(fBox)) || ~isreal(fSheet) || ...
            ~isreal(fBox) || any(~isfinite(fSheet(:))) || ...
            any(~isfinite(fBox(:)))
        throw(MException(errorId, ...
            'f_sheet and f_box must be same-sized finite real arrays'));
    end
    if ~isnumeric(betaBox) || ~isscalar(betaBox) || ~isreal(betaBox) || ...
            ~isfinite(betaBox) || betaBox <= 0
        throw(MException(errorId, 'beta_box must be a finite positive scalar'));
    end
    F = max(double(fSheet), double(betaBox).*double(fBox));
end
```

- [ ] **Step 4: Implement the finite field builder**

Use `hOverL=1/resolution`, build every axis from `min-h/2:h:max+h/2`, evaluate the continuous Gyroid, and construct the dimensionless box field by implicit expansion:

```matlab
xBox = max(domain.x(1)-reshape(x,[],1,1), ...
           reshape(x,[],1,1)-domain.x(2));
yBox = max(domain.y(1)-reshape(y,1,[],1), ...
           reshape(y,1,[],1)-domain.y(2));
zBox = max(domain.z(1)-reshape(z,1,1,[]), ...
           reshape(z,1,1,[])-domain.z(2));
fBox = max(max(xBox,yBox),zBox);
fSheet = abs(sample.G)-reshape(sample.threshold,1,1,[]);
F = compose_hard_box_csg(fSheet,fBox,contract.betaBox);
```

Return `method`, `resolution`, normalized and millimetre axes, `spacing_over_l`, `spacing_mm`, `exterior_margin_mm`, `F`, interior solid/void counts, and the contract identifiers. Check in this order: throw `MATLABGyroid:NonfiniteField` when any `F` value is non-finite; locate the interior cells from the staggered axes; throw `MATLABGyroid:EmptySolid` when their solid count is zero; throw `MATLABGyroid:FullSolid` when their void count is zero; then require all six outermost planes to be strictly positive.

- [ ] **Step 5: Add M1/M2/M3 deterministic smoke tests and run the suite**

At resolution 16 with `enforceAllowedLevel=false`, verify each method returns finite `F`, mixed interior phases, correct physical scaling, and identical repeated output.

- [ ] **Step 6: Commit**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compose_hard_box_csg.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_finite_csg_field.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestContinuousCSG.m
git commit -m "feat(geometry): build finite continuous CSG field"
```

### Task 4: Extract a coordinate-correct shared-index surface mesh

**Files:**

- Create: `core/extract_isosurface_mesh.m`
- Create: `tests/TestSurfaceMesh.m`

- [ ] **Step 1: Write a coordinate-order regression test**

Use unequal x/y spans so an unnoticed MATLAB row/column swap cannot pass:

```matlab
function testIsosurfacePreservesPhysicalCoordinateOrder(testCase)
    field = struct();
    field.x_mm = -0.1:0.1:1.1;
    field.y_mm = -0.1:0.1:2.1;
    field.z_mm = -0.1:0.1:0.9;
    [X,Y,Z] = ndgrid(field.x_mm,field.y_mm,field.z_mm);
    field.F = X-0.35;
    mesh = extract_isosurface_mesh(field,0);
    testCase.verifyEqual(mesh.vertices(:,1), ...
        0.35*ones(size(mesh.vertices,1),1),'AbsTol',1e-12);
    testCase.verifyGreaterThan(range(mesh.vertices(:,2)),1.9);
    testCase.verifyGreaterThan(range(mesh.vertices(:,3)),0.8);
end
```

- [ ] **Step 2: Run the test and verify RED**

Expected: FAIL because `extract_isosurface_mesh` is absent.

- [ ] **Step 3: Implement extraction with explicit dimension mapping**

```matlab
function mesh = extract_isosurface_mesh(field, isoLevel)
%EXTRACT_ISOSURFACE_MESH Extract shared-index XYZ mesh from [X,Y,Z] field.
    errorId = 'MATLABGyroid:InvalidGeometry';
    required = {'x_mm','y_mm','z_mm','F'};
    if ~isstruct(field) || ~isscalar(field) || ...
            ~all(isfield(field,required))
        throw(MException(errorId,'field lacks x_mm, y_mm, z_mm, or F'));
    end
    if ~isequal(size(field.F), ...
            [numel(field.x_mm),numel(field.y_mm),numel(field.z_mm)])
        throw(MException(errorId,'F dimensions do not match XYZ axes'));
    end
    volumeYXZ = permute(field.F,[2,1,3]);
    [faces,vertices] = isosurface(field.x_mm,field.y_mm, ...
        field.z_mm,volumeYXZ,isoLevel);
    if isempty(faces) || isempty(vertices)
        throw(MException('MATLABGyroid:EmptyMesh', ...
            'zero isosurface produced an empty mesh'));
    end
    mesh = struct('faces',double(faces),'vertices',double(vertices), ...
        'iso_level',double(isoLevel),'global_orientation_flip',false);
end
```

- [ ] **Step 4: Add a real CSG smoke extraction and run tests**

Verify that a low-resolution M1 CSG field yields finite vertices contained within the configured physical hard-box bounds to a spacing-scaled tolerance.

- [ ] **Step 5: Commit**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/extract_isosurface_mesh.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestSurfaceMesh.m
git commit -m "feat(geometry): extract continuous CSG surface mesh"
```

### Task 5: Implement the strict shared-index topology gate

**Files:**

- Create: `core/validate_surface_mesh.m`
- Modify: `tests/TestSurfaceMesh.m`

- [ ] **Step 1: Add valid and invalid mesh fixtures**

Use a consistently oriented tetrahedron as the valid fixture. Add separate tests that mutate it into an open mesh, duplicate-index face, duplicate face, non-manifold edge, two disconnected tetrahedra, and locally reversed face. Each test must assert one exact `failure_code`.

```matlab
function mesh = tetrahedronFixture()
    mesh.vertices = [0 0 0;1 0 0;0 1 0;0 0 1];
    mesh.faces = [1 3 2;1 2 4;2 3 4;3 1 4];
end

function testOpenMeshRejected(testCase)
    mesh = TestSurfaceMesh.tetrahedronFixture();
    mesh.faces(end,:) = [];
    report = validate_surface_mesh(mesh,0.1,struct( ...
        'min_edge_length_ratio',0.01,'self_intersect_check',false));
    testCase.verifyFalse(report.valid);
    testCase.verifyEqual(report.failure_code,'OPEN_MESH');
end
```

- [ ] **Step 2: Run focused tests and verify RED**

Expected: FAIL because the validator is absent.

- [ ] **Step 3: Implement deterministic integrity and topology checks**

The validator shall return, never hide, these metrics:

```matlab
report = struct('valid',false,'failure_code','INTERNAL_ERROR', ...
    'vertex_count',size(V,1),'face_count',size(F,1), ...
    'boundary_edge_count',NaN,'nonmanifold_edge_count',NaN, ...
    'component_count',NaN,'duplicate_face_count',NaN, ...
    'degenerate_face_count',NaN,'minimum_edge_mm',NaN, ...
    'surface_area_mm2',NaN,'signed_volume_mm3',NaN, ...
    'global_orientation_flip',false);
```

Build directed edges as `[F(:,[1 2]);F(:,[2 3]);F(:,[3 1])]`, sort each row for undirected grouping, and use `unique(...,'rows')` plus `accumarray` for incidence. Require incidence exactly two. For each two-use edge, require opposite directed order. Construct face adjacency from the two owner faces and use `conncomp(graph(...))` for face components. Calculate triangle cross products, areas, three edge lengths, surface area, and signed volume. Fail in this order: invalid indices, degenerate faces, duplicate faces, short edges, open edges, non-manifold edges, inconsistent orientation, disconnected components.

If all local orientations are consistent and signed volume is negative, reverse every face using `F(:,[1 3 2])`, recompute signed volume, and set `global_orientation_flip=true`. Do not reverse individual faces.

- [ ] **Step 4: Run invalid-fixture tests and real CSG mesh test**

Expected: every invalid fixture reaches its exact failure code; the tetrahedron passes; real CSG results report all raw counts even when a low test resolution is rejected.

- [ ] **Step 5: Commit**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/validate_surface_mesh.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestSurfaceMesh.m
git commit -m "feat(geometry): enforce closed two-manifold mesh gate"
```

### Task 6: Add deterministic self-intersection rejection

**Files:**

- Create: `core/detect_mesh_self_intersections.m`
- Create: `core/triangles_intersect_3d.m`
- Modify: `core/validate_surface_mesh.m`
- Modify: `tests/TestSurfaceMesh.m`

- [ ] **Step 1: Write narrow-phase and mesh-level failing tests**

Cover a proper crossing, separated triangles, coplanar overlap, coplanar separation, and adjacent faces sharing a declared mesh edge. At mesh level, two closed tetrahedra that geometrically penetrate each other must return `SELF_INTERSECTION`; a single tetrahedron must pass.

```matlab
function testCrossingTrianglesDetected(testCase)
    A = [0 0 0;1 0 0;0 1 0];
    B = [0.25 0.25 -1;0.25 0.25 1;0.75 0.25 0];
    testCase.verifyTrue(triangles_intersect_3d(A,B,1e-12));
end

function testCoplanarSeparatedTrianglesNotDetected(testCase)
    A = [0 0 0;1 0 0;0 1 0];
    B = [2 2 0;3 2 0;2 3 0];
    testCase.verifyFalse(triangles_intersect_3d(A,B,1e-12));
end
```

- [ ] **Step 2: Run tests and verify RED**

Expected: FAIL because the intersection functions are absent.

- [ ] **Step 3: Implement the triangle predicate**

`triangles_intersect_3d(A,B,tol)` shall:

1. compute normalized plane normals and reject degenerate input;
2. reject if all signed distances of either triangle lie strictly on one side of the other plane;
3. if normals are parallel and both triangles are coplanar, drop the coordinate corresponding to the largest normal component and test all 2-D edge pairs plus point-in-triangle containment;
4. otherwise test all six finite segments against the opposite triangle using the Möller–Trumbore barycentric predicate with `-tol <= u,v,u+v <= 1+tol` and segment parameter in `[-tol,1+tol]`.

Use explicit local helpers named `segment_hits_triangle`, `coplanar_overlap_2d`, `segments_intersect_2d`, `orient2d`, and `point_in_triangle_2d`. Every comparison must use the caller-provided tolerance; do not add random jitter.

- [ ] **Step 4: Implement sweep-and-prune broad phase**

`detect_mesh_self_intersections(mesh,tol)` shall calculate triangle AABBs, sort faces by minimum X, and for each face consider only later faces whose minimum X is not greater than its maximum X plus tolerance. Filter those candidates by Y and Z AABB overlap, skip pairs sharing any vertex index, and call the narrow phase. Return a lexicographically sorted `N x 2` face-pair array. Do not stop at the first pair so diagnostics remain reproducible.

- [ ] **Step 5: Wire the self-intersection result into the validator**

When `mesh_qc.self_intersect_check` is true, populate `self_intersection_pair_count` and up to the first 20 face pairs. Return `SELF_INTERSECTION` when the count is nonzero. Convert runtime inability to perform the check into `SELF_INTERSECTION_CHECK_UNAVAILABLE`; never treat an unexecuted check as passing.

- [ ] **Step 6: Run focused tests, then run the complete suite twice**

Expected: all intersection fixtures PASS and repeated reports list face pairs in identical order.

- [ ] **Step 7: Commit**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/detect_mesh_self_intersections.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/triangles_intersect_3d.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/validate_surface_mesh.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestSurfaceMesh.m
git commit -m "feat(geometry): reject self-intersecting surface meshes"
```

### Task 7: Write and verify binary STL without topology repair

**Files:**

- Create: `core/export_binary_stl.m`
- Create: `core/verify_binary_stl.m`
- Create: `tests/TestBinarySTL.m`

- [ ] **Step 1: Write binary round-trip and corruption tests**

Use the tetrahedron fixture. Verify expected byte length `84 + 50*face_count`, triangle count, finite payload, stable SHA-256, and refusal to overwrite an existing final path. Copy and truncate the STL by one byte and require `MATLABGyroid:STLVerificationError`.

- [ ] **Step 2: Run tests and verify RED**

Expected: FAIL because exporter and verifier are absent.

- [ ] **Step 3: Implement the binary writer**

Open the temporary file with `fopen(path,'w','ieee-le')`. Write exactly:

```matlab
header = zeros(1,80,'uint8');
label = uint8('MATLABGyroid continuous CSG STL');
header(1:numel(label)) = label;
fwrite(fileId,header,'uint8');
fwrite(fileId,uint32(size(faces,1)),'uint32');
for faceIndex = 1:size(faces,1)
    triangle = single(vertices(faces(faceIndex,:),:));
    normal = cross(double(triangle(2,:)-triangle(1,:)), ...
        double(triangle(3,:)-triangle(1,:)));
    normal = single(normal./norm(normal));
    fwrite(fileId,normal,'single');
    fwrite(fileId,triangle','single');
    fwrite(fileId,uint16(0),'uint16');
end
```

Write to `tempname(outputDirectory) + ".stl"`, protect it through `onCleanup`, explicitly call `fclose(fileId)` and clear the file cleanup before verification, call the verifier, then publish with `movefile`. Refuse an existing final path before opening the temporary artifact. Delete only the known request-scoped temporary file on failure.

- [ ] **Step 4: Implement the independent binary verifier**

Read the 80-byte header and little-endian `uint32` triangle count. Require exact byte length `84+50*N`. Read all remaining records as bytes, decode every normal/vertex `single`, reject non-finite coordinates or normals, and return:

```matlab
summary = struct('byte_length',fileInfo.bytes, ...
    'triangle_count',double(triangleCount), ...
    'all_finite',true,'sha256',sha256_file(path, ...
    'MATLABGyroid:STLVerificationError','binary STL'));
```

The verifier must not weld vertices or infer repaired topology from STL triangle duplication.

- [ ] **Step 5: Run tests and commit**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/export_binary_stl.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/verify_binary_stl.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestBinarySTL.m
git commit -m "feat(geometry): publish verified binary STL artifacts"
```

### Task 8: Add strict request parsing and canonical hashes

**Files:**

- Create: `core/sha256_text.m`
- Create: `core/parse_and_validate_request.m`
- Create: `tests/TestCompilerPipeline.m`

- [ ] **Step 1: Write strict-schema tests**

Create temporary JSON fixtures for one valid request and separate missing-field, extra-field, wrong-type, non-finite, invalid-method, disallowed-resolution, unsafe request ID, and relative-output cases. Assert every invalid request throws `MATLABGyroid:InvalidRequest`, `MATLABGyroid:MethodConstraint`, or `MATLABGyroid:OutOfBounds` with a stable message fragment.

Use this valid fixture:

```matlab
request = struct('schema_version','1.0','request_id','m03-m1-001', ...
    'method','M1','c0',0.10,'c1',0.10,'c2',0.10,'w',0, ...
    'resolution',96,'output_dir','outputs');
```

- [ ] **Step 2: Verify RED**

Expected: FAIL because request parsing and text hashing are absent.

- [ ] **Step 3: Implement UTF-8 text hashing**

```matlab
function digestHex = sha256_text(value)
    value = validate_text_scalar(value,'value', ...
        'MATLABGyroid:InvalidRequest');
    digest = javaMethod('getInstance', ...
        'java.security.MessageDigest','SHA-256');
    bytes = unicode2native(value,'UTF-8');
    digest.update(typecast(uint8(bytes),'int8'));
    bytes = typecast(digest.digest(),'uint8');
    digestHex = lower(reshape(dec2hex(bytes,2).',1,[]));
end
```

- [ ] **Step 4: Implement exact request validation**

`parse_and_validate_request(requestPath,config)` shall:

- require a scalar decoded JSON object whose sorted field set exactly equals `compiler_contract().requestFields`;
- validate all text with `validate_text_scalar` and all numerics as finite real scalars;
- restrict `request_id` to `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`;
- anchor relative `output_dir` to the request file directory and return a normalized absolute path;
- require resolution membership in `config.method_bounds.(method).levels`;
- call `project_method_constraints` with exactly `c0,c1,c2,w`;
- produce a canonical request-semantic string using `%.17g` values in the fixed order `schema_version,method,c0,c1,c2,w,resolution`, excluding `request_id` and `output_dir`;
- return raw request SHA-256, request-semantic SHA-256, requested parameters, effective parameters, resolution, resolved output directory, and request ID.

- [ ] **Step 5: Prove path/ID independence and commit**

Write two request files with different IDs and output directories but identical geometry inputs. Verify their request-semantic hashes match while raw file hashes differ.

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/sha256_text.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/parse_and_validate_request.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestCompilerPipeline.m
git commit -m "feat(geometry): validate compiler requests and canonicalize hashes"
```

### Task 9: Build manifest, atomic JSON output, and end-to-end compiler

**Files:**

- Create: `core/build_geometry_manifest.m`
- Create: `core/write_json_atomic.m`
- Create: `run_geometry_compiler.m`
- Modify: `tests/TestCompilerPipeline.m`

- [ ] **Step 1: Write failure-response tests before orchestration**

For malformed JSON and an invalid M1 `w`, call `run_geometry_compiler(requestPath,responsePath)`. Verify response JSON exists, `valid=false`, `validation_stage="M03_GEOMETRY_MESH"`, the exact failure code is present, and no STL or manifest exists.

- [ ] **Step 2: Run pipeline tests and verify RED**

Expected: FAIL because the entry point is absent.

- [ ] **Step 3: Implement deterministic manifest construction**

The geometry-identity canonical string shall contain fixed-order lines for compiler version, geometry definition, effective method/parameters, physical domain bounds, reference length, resolution, beta, isosurface level, and the immutable config/manifest/descriptor hashes. Hash it with `sha256_text`.

Return a manifest with these top-level fields:

```matlab
manifest = struct('schema_version','1.0', ...
    'validation_stage',contract.validationStage, ...
    'compiler_version',compiler_version(), ...
    'geometry_definition',contract.geometryDefinition, ...
    'request',requestSummary, ...
    'geometry_identity_sha256',geometryIdentityHash, ...
    'discretization',discretization, ...
    'mesh_qc',meshReport, ...
    'artifact',artifactSummary, ...
    'deferred_stages',{{'M04_DESCRIPTORS','ABAQUS_GATE0', ...
        'PRINTABILITY','EXPERIMENT'}});
```

- [ ] **Step 4: Implement atomic JSON writing**

Encode with `jsonencode(value,'PrettyPrint',true)`, write UTF-8 to a temporary file in the target directory, close and reread it with `jsondecode` to verify syntactic validity, reject an existing final path, and atomically move the temporary file. Do not recursively delete or clean the output directory.

- [ ] **Step 5: Implement `run_geometry_compiler` orchestration**

Use the compiler file location to resolve `configs/compiler_config.example.json`; never depend on the current working directory. Execute in this order:

```text
load config
parse request and project parameters
build continuous finite CSG field
extract zero isosurface
validate shared-index mesh including self-intersection
build geometry identity and final artifact names
export and verify binary STL
build and atomically write manifest
atomically write success response
```

Use filenames `geometry_<geometry_identity_sha256>.stl` and `geometry_<geometry_identity_sha256>.manifest.json`. On caught errors, map known MATLAB identifiers to the design failure codes and atomically write a failure response to the caller-provided response path. Do not include stack traces or machine-specific temporary paths in semantic hashes.

The success response shall contain requested/effective parameters, `valid=true`, `failure_code=""`, mesh QC, geometry identity, STL/manifest paths, and artifact SHA-256. It shall set all later stages to `not_computed`.

- [ ] **Step 6: Add one production-level M1 integration test**

Run a valid resolution-96 request in a fresh temporary directory twice using two separate output directories. Verify both runs succeed and produce byte-identical STL SHA-256 values and identical geometry identities. Verify different request IDs do not alter the STL bytes.

- [ ] **Step 7: Run pipeline and complete tests, then commit**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_geometry_manifest.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/write_json_atomic.m paper_A_reliable_inverse_design/geometry_compiler_matlab/run_geometry_compiler.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestCompilerPipeline.m
git commit -m "feat(geometry): integrate fail-closed M03 compiler pipeline"
```

### Task 10: Add convergence evidence and perform final acceptance

**Files:**

- Create: `core/compare_mesh_convergence.m`
- Create: `tests/TestMeshConvergence.m`
- Modify: `tests/TestCompilerPipeline.m`
- Create: `docs/M03_USAGE.md`

- [ ] **Step 1: Write convergence metric tests**

Use identical tetrahedra, a translated copy, and a uniformly scaled copy. Assert identical meshes give zero bidirectional proxy distance and zero relative area/volume change; translation yields the known vertex-distance proxy; scaling changes area and volume by the expected square/cube factors.

- [ ] **Step 2: Run tests and verify RED**

Expected: FAIL because `compare_mesh_convergence` is absent.

- [ ] **Step 3: Implement convergence metrics without optional toolboxes**

Compute mesh surface area and absolute signed volume from faces. For each mesh, deterministically select at most 5,000 vertices using rounded `linspace` indices. Compute directed vertex-distance proxies in chunks of 250 query vertices using implicit expansion against the other sampled vertex set. Return directed maximum/RMS values, bidirectional maximum/RMS values, relative area/volume changes, component counts, and topology-stability boolean.

The function returns measurements only. It shall not hard-code universal publication tolerances; callers compare metrics to validated configuration values later.

- [ ] **Step 4: Add M1/M2/M3 resolution-evidence smoke tests**

For archived-valid parameters, generate low test levels 12 and 16 through internal functions and verify deterministic metric structures and topology reporting. Mark production evidence as requiring the configured method levels 96/128/160 and, for M3, 192. Do not make the full unit suite generate all four production meshes on every run.

- [ ] **Step 5: Write the usage and validity-boundary documentation**

Document the exact request example, PowerShell/MATLAB command, output files, failure-code behavior, and this warning verbatim:

```text
M03 valid=true confirms request, continuous geometry, surface topology,
self-intersection, STL serialization, and artifact integrity only. It does
not confirm descriptor calibration, Abaqus Gate 0, printability, or
experimental performance.
```

- [ ] **Step 6: Run the complete suite from the project directory**

```powershell
$compilerDir = (Resolve-Path 'paper_A_reliable_inverse_design\geometry_compiler_matlab').Path.Replace('\','/')
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('$compilerDir'); run_tests;"
```

Expected: every test passes and MATLAB exits zero.

- [ ] **Step 7: Run the complete suite from an unrelated directory**

```powershell
$compilerDir = (Resolve-Path 'paper_A_reliable_inverse_design\geometry_compiler_matlab').Path.Replace('\','/')
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "addpath('$compilerDir'); cd(tempdir); run_tests;"
```

Expected: the same total/pass count and zero failures.

- [ ] **Step 8: Run Code Analyzer on every changed MATLAB file**

Use a MATLAB batch script that enumerates the exact changed `.m` files with `dir`, calls `checkcode(path,'-id')`, prints all messages, and throws if any actionable message remains. Do not suppress messages globally; justify any line-level suppression adjacent to the code.

- [ ] **Step 9: Verify repository scope**

Run:

```powershell
git diff --check
git status --short
git diff --name-only <implementation-base>..HEAD
```

Expected: no whitespace errors; only M03/M01-M02 integration files and the approved documentation are changed; user-owned untracked files remain untouched.

- [ ] **Step 10: Commit final convergence and documentation work**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compare_mesh_convergence.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestMeshConvergence.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestCompilerPipeline.m paper_A_reliable_inverse_design/geometry_compiler_matlab/docs/M03_USAGE.md
git commit -m "test(geometry): close M03 convergence and acceptance gates"
```

## Final evidence checklist

- [ ] Existing M01/M02 tests pass unchanged except the intentional compiler-version expectation.
- [ ] Continuous evaluator reproduces the archived M02 field values exactly on the legacy grid.
- [ ] M03 grid is half-step staggered and every exterior plane is positive.
- [ ] `F<=0` matches sheet/box logical intersection on all tested points.
- [ ] Production mesh comes only from continuous `F=0` extraction.
- [ ] Open, non-manifold, disconnected, degenerate, inconsistently oriented, and self-intersecting meshes fail closed.
- [ ] No automatic welding, filling, smoothing, component deletion, or candidate substitution exists.
- [ ] Binary STL round trip, length, triangle count, finiteness, and SHA-256 pass.
- [ ] Semantic and geometry hashes exclude request ID, output path, and timestamps.
- [ ] Identical geometry identities produce identical STL bytes on MATLAB R2023b.
- [ ] Response and manifest label later stages `not_computed`.
- [ ] Project-directory and unrelated-directory full suites both pass.
- [ ] Code Analyzer and `git diff --check` pass.
