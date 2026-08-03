# M02 Graded-Gyroid Field Kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify the deterministic MATLAB kernel that projects M1/M2/M3 controls, evaluates the Small threshold and cell-size profiles, samples the normalized graded-Gyroid field, and converts it to a finite sheet-band voxel volume.

**Architecture:** Keep the M01 configuration loader as the trusted contract boundary. Implement five focused pure functions under `core/`: method projection, threshold profile, cell-size profile, field sampling, and sheet-band voxelization. The kernel works in normalized coordinates; millimetres are derived exactly once from `reference_length_mm` and recorded as spacing metadata.

**Tech Stack:** MATLAB R2023b, `matlab.unittest`, Image Processing Toolbox inventory from M01, JSON configuration frozen by commit `960e1c5`.

---

## 1. Frozen decisions and non-goals

1. The branch starts at M01 commit `960e1c5` and is named `paper-a/matlab-gyroid-m02-field-kernel`.
2. `M1` uses active `c0,c1,c2`; its supplied `w` must equal the frozen value `0` and is never silently changed.
3. `M2` performs the documented orthogonal projection `c_projected=mean([c0,c1,c2])`, then returns `c0=c1=c2=c_projected`; `w` remains active.
4. `M3` passes all four controls through unchanged.
5. Bounds come only from `config.method_bounds`; inclusive and open endpoints are enforced exactly.
6. Threshold interpolation is piecewise linear through `z/l = 0,1,2`.
7. `M1` uses constant normalized z cell size `Lz0_over_l=1.5`. `M2` and `M3` use `gamma(z)=1.5+(z/l)/w`.
8. The normalized field is

   ```text
   G = sin(2*pi*x/Lx)*cos(2*pi*y/Ly)
     + sin(2*pi*y/Ly)*cos(2*pi*z/gamma(z))
     + sin(2*pi*z/gamma(z))*cos(2*pi*x/Lx)
   ```

9. A resolution `r` means `r` intervals per reference length. Endpoint-inclusive axes therefore contain `span*r+1` samples.
10. The solid convention is exactly `abs(G)<=t(z)`.
11. Meshing, STL export, descriptor computation, Gate 0 selection, Abaqus submission, and Graph Transformer/Diffusion code are outside M02.

Stable M02 error identifiers:

| Identifier | Meaning |
|---|---|
| `MATLABGyroid:InvalidRequest` | Wrong method/parameter structure or non-finite scalar |
| `MATLABGyroid:MethodConstraint` | A fixed method variable is violated |
| `MATLABGyroid:OutOfBounds` | A projected active variable violates its frozen interval |
| `MATLABGyroid:InvalidGeometry` | Invalid coordinate vector, resolution, convention, or non-finite field |
| `MATLABGyroid:EmptySolid` | Sheet-band voxelization contains no material |
| `MATLABGyroid:FullSolid` | Sheet-band voxelization contains no void |

## 2. File map

### Create

- `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/project_method_constraints.m` — canonicalize method controls and enforce frozen intervals.
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/validate_normalized_z.m` — share strict normalized z-vector validation across both profile evaluators.
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/evaluate_threshold_profile.m` — evaluate the M1/M2/M3 threshold profile on normalized z coordinates.
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/evaluate_cell_size_profile.m` — evaluate constant or denominator-form normalized z cell size.
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_graded_gyroid_field.m` — create endpoint-inclusive axes and sample `G` without retaining full coordinate grids.
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_solid_volume.m` — apply the frozen sheet-band convention and return occupancy diagnostics.
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestFieldKernel.m` — all M02 unit, contract, determinism, and integration tests.

### Modify

- `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compiler_contract.m` — add the exact M02 error identifiers and formula labels used in provenance.

### Do not modify

- M01 JSON hashes or descriptor definitions.
- Archived Small workbooks or code under `F:/demo_TPMS`.
- `run_geometry_compiler.m`, mesh/STL code, metrics, Abaqus, Python training, or paper text.

---

### Task 1: Method projection and bounds

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestFieldKernel.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/project_method_constraints.m`

- [ ] **Step 1: Write the failing projection tests**

Create `TestFieldKernel.m` with a `TestClassSetup` that adds `core/`, loads `configs/compiler_config.example.json`, and stores the result. Add tests with these exact assertions:

```matlab
function testM1PassesThresholdControlsAndRequiresZeroW(testCase)
    raw = struct('c0', 0.04, 'c1', 0.10, 'c2', 0.20, 'w', 0);
    p = project_method_constraints('M1', raw, testCase.Config);
    testCase.verifyEqual([p.c0,p.c1,p.c2,p.w], [0.04,0.10,0.20,0]);
    testCase.verifyFalse(p.projection_applied);
    raw.w = 4;
    testCase.verifyError(@() project_method_constraints('M1', raw, testCase.Config), ...
        'MATLABGyroid:MethodConstraint');
end

function testM2UsesOrthogonalMeanProjection(testCase)
    raw = struct('c0', 0.04, 'c1', 0.10, 'c2', 0.16, 'w', 4);
    p = project_method_constraints('M2', raw, testCase.Config);
    testCase.verifyEqual([p.c0,p.c1,p.c2,p.c_projected], [0.10,0.10,0.10,0.10], ...
        'AbsTol', 10*eps);
    testCase.verifyEqual(p.projection_l2, norm([-0.06,0,0.06]), 'AbsTol', 10*eps);
    testCase.verifyTrue(p.projection_applied);
end

function testM3PassesAllControls(testCase)
    raw = struct('c0', 0.03, 'c1', 0.10, 'c2', 0.20, 'w', 4);
    p = project_method_constraints('M3', raw, testCase.Config);
    testCase.verifyEqual([p.c0,p.c1,p.c2,p.w], [0.03,0.10,0.20,4]);
    testCase.verifyFalse(p.projection_applied);
end
```

Also test wrong method, missing/extra parameter fields, non-scalar/non-finite controls, `c<0.03`, `c>0.20`, and open `w=2`/`w=8` endpoints. Every negative test must assert the exact error identifier and a method/variable message fragment.

- [ ] **Step 2: Run the RED test**

```powershell
F:\MATLAB\R2023b\bin\matlab.exe -batch "cd('F:/small++/paper_A_reliable_inverse_design/geometry_compiler_matlab'); r=runtests('tests/TestFieldKernel.m','Name','*M1*|*M2*|*M3*'); assertSuccess(r);"
```

Expected: FAIL because `project_method_constraints` is undefined.

- [ ] **Step 3: Implement exact projection**

`project_method_constraints(method, raw, config)` must:

1. validate `method` with `validate_text_scalar` and require `M1|M2|M3`;
2. require `raw` to be a scalar struct with exactly `{c0,c1,c2,w}`;
3. require every value to be a finite real numeric scalar;
4. apply the method rule stated in section 1;
5. validate each active/projected value against `config.method_bounds.(method).bounds` using both inclusivity flags;
6. return fields `method,c0,c1,c2,w,c_projected,projection_applied,projection_l2,raw_parameters` in that order of meaning; use `[]` for non-M2 `c_projected` so JSON provenance contains no non-finite sentinel.

The interval predicate is exactly:

```matlab
below = value < bound.lower || ...
    (value == bound.lower && ~bound.lower_inclusive);
above = value > bound.upper || ...
    (value == bound.upper && ~bound.upper_inclusive);
```

- [ ] **Step 4: Run projection tests GREEN**

Run all tests in `TestFieldKernel.m`. Expected: projection tests PASS; later profile tests do not exist yet.

- [ ] **Step 5: Commit projection slice**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/project_method_constraints.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestFieldKernel.m
git commit -m "feat(geometry): project graded Gyroid method controls"
```

---

### Task 2: Threshold and cell-size profiles

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/validate_normalized_z.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/evaluate_threshold_profile.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/evaluate_cell_size_profile.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestFieldKernel.m`

- [ ] **Step 1: Write failing profile tests**

Add exact-knot, vector-orientation, denominator, and invalid-z tests:

```matlab
function testThresholdProfileHitsAllKnotsExactly(testCase)
    p = project_method_constraints('M1', ...
        struct('c0',0.04,'c1',0.10,'c2',0.20,'w',0), testCase.Config);
    z = [0, 1, 2];
    testCase.verifyEqual(evaluate_threshold_profile(z, p), [0.04,0.10,0.20], ...
        'AbsTol', 10*eps);
    testCase.verifyEqual(evaluate_threshold_profile(z', p), [0.04;0.10;0.20], ...
        'AbsTol', 10*eps);
end

function testM2ThresholdIsProjectedConstant(testCase)
    p = project_method_constraints('M2', ...
        struct('c0',0.04,'c1',0.10,'c2',0.16,'w',4), testCase.Config);
    testCase.verifyEqual(evaluate_threshold_profile([0,0.5,1,2], p), ...
        0.10*ones(1,4), 'AbsTol', 10*eps);
end

function testDenominatorCellSizeProfileIsExact(testCase)
    p = project_method_constraints('M3', ...
        struct('c0',0.04,'c1',0.10,'c2',0.16,'w',4), testCase.Config);
    gamma = evaluate_cell_size_profile([0,1,2], p, testCase.Config);
    testCase.verifyEqual(gamma, [1.5,1.75,2.0], 'AbsTol', 10*eps);
end
```

Also prove M1 returns constant `1.5`, values immediately on both sides of `z=1` are continuous, z outside `[0,2]` is rejected, and NaN/Inf/complex z is rejected as `MATLABGyroid:InvalidGeometry`.

- [ ] **Step 2: Run profile tests RED**

Expected: FAIL with undefined `evaluate_threshold_profile` and `evaluate_cell_size_profile`.

- [ ] **Step 3: Implement profile functions**

Use logical masks without reshaping the caller's z vector:

```matlab
threshold = zeros(size(zOverL), 'like', zOverL);
lowerHalf = zOverL <= 1;
threshold(lowerHalf) = projected.c0 + ...
    (projected.c1-projected.c0).*zOverL(lowerHalf);
upperHalf = ~lowerHalf;
threshold(upperHalf) = projected.c1 + ...
    (projected.c2-projected.c1).*(zOverL(upperHalf)-1);
```

For M2 return `projected.c_projected + zeros(size(zOverL))`. For cell size, M1 returns `config.geometry_parameters.Lz0_over_l`; M2/M3 return `Lz0_over_l + zOverL./projected.w`. Reject any non-finite or non-positive result.

- [ ] **Step 4: Run `TestFieldKernel` and the complete suite GREEN**

Expected: all profile tests and the M01 suite pass.

- [ ] **Step 5: Commit profile slice**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/evaluate_threshold_profile.m paper_A_reliable_inverse_design/geometry_compiler_matlab/core/evaluate_cell_size_profile.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestFieldKernel.m
git commit -m "feat(geometry): evaluate Small grading profiles"
```

---

### Task 3: Endpoint-inclusive graded-Gyroid field

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_graded_gyroid_field.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestFieldKernel.m`

- [ ] **Step 1: Write failing field tests**

Use resolution `8` for mathematical unit tests and assert:

```matlab
function testFieldGridIncludesDomainEndpoints(testCase)
    p = project_method_constraints('M1', ...
        struct('c0',0.04,'c1',0.10,'c2',0.20,'w',0), testCase.Config);
    f = build_graded_gyroid_field(p, testCase.Config, 8);
    testCase.verifySize(f.G, [9,9,17]);
    testCase.verifyEqual(f.x_over_l([1,end]), [0,1], 'AbsTol', eps);
    testCase.verifyEqual(f.y_over_l([1,end]), [0,1], 'AbsTol', eps);
    testCase.verifyEqual(f.z_over_l([1,end]), [0,2], 'AbsTol', eps);
    testCase.verifyEqual(f.spacing_over_l, 1/8, 'AbsTol', eps);
    testCase.verifyEqual(f.spacing_mm, testCase.Config.reference_length_mm/8, ...
        'AbsTol', eps);
end

function testKnownGyroidPointEqualsOne(testCase)
    p = project_method_constraints('M1', ...
        struct('c0',0.10,'c1',0.10,'c2',0.10,'w',0), testCase.Config);
    f = build_graded_gyroid_field(p, testCase.Config, 8);
    testCase.verifyEqual(f.G(3,1,1), 1, 'AbsTol', 100*eps);
end

function testFieldIsDeterministic(testCase)
    p = project_method_constraints('M3', ...
        struct('c0',0.04,'c1',0.10,'c2',0.16,'w',4), testCase.Config);
    a = build_graded_gyroid_field(p, testCase.Config, 8);
    b = build_graded_gyroid_field(p, testCase.Config, 8);
    testCase.verifyEqual(a.G, b.G);
    testCase.verifyEqual(a.threshold, b.threshold);
    testCase.verifyEqual(a.cell_size_over_l, b.cell_size_over_l);
end
```

Also assert all values are real/finite, M2/M3 cell-size arrays equal the profile helper, noninteger/zero/NaN resolution is rejected, and a span/resolution combination that cannot produce an integer interval count is rejected.

- [ ] **Step 2: Run field tests RED**

Expected: FAIL because `build_graded_gyroid_field` is undefined.

- [ ] **Step 3: Implement memory-bounded field sampling**

Construct row-vector axes using `linspace`. Compute the field by implicit expansion, not full `ndgrid` storage:

```matlab
xPhase = 2*pi*field.x_over_l/config.geometry_parameters.Lx_over_l;
yPhase = 2*pi*field.y_over_l/config.geometry_parameters.Ly_over_l;
zPhase = 2*pi*field.z_over_l./field.cell_size_over_l;

sinX = reshape(sin(xPhase), [], 1, 1);
cosX = reshape(cos(xPhase), [], 1, 1);
sinY = reshape(sin(yPhase), 1, [], 1);
cosY = reshape(cos(yPhase), 1, [], 1);
sinZ = reshape(sin(zPhase), 1, 1, []);
cosZ = reshape(cos(zPhase), 1, 1, []);
field.G = sinX.*cosY + sinY.*cosZ + sinZ.*cosX;
```

Return `x_over_l,y_over_l,z_over_l,spacing_over_l,spacing_mm,threshold,cell_size_over_l,G,method,resolution`. Do not convert axes to millimetres inside the trigonometric formula.

- [ ] **Step 4: Run field tests and M01 regression GREEN**

Expected: exact point, dimensions, determinism, profile, and all 97 M01 tests pass.

- [ ] **Step 5: Commit field slice**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_graded_gyroid_field.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestFieldKernel.m
git commit -m "feat(geometry): sample deterministic graded Gyroid field"
```

---

### Task 4: Sheet-band voxel volume

**Files:**
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_solid_volume.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestFieldKernel.m`

- [ ] **Step 1: Write failing solid tests**

For valid M1/M2/M3 examples at resolution `16`, call the field builder then assert:

```matlab
volume = build_solid_volume(field, testCase.Config);
testCase.verifyClass(volume.solid, 'logical');
testCase.verifySize(volume.solid, size(field.G));
testCase.verifyGreaterThan(volume.solid_fraction, 0);
testCase.verifyLessThan(volume.solid_fraction, 1);
testCase.verifyEqual(volume.solid, abs(field.G) <= reshape(field.threshold,1,1,[]));
```

Add direct synthetic-field cases that produce no solid and full solid, and assert `MATLABGyroid:EmptySolid` and `MATLABGyroid:FullSolid`. Add wrong convention and non-finite field cases expecting `MATLABGyroid:InvalidGeometry`.

- [ ] **Step 2: Run solid tests RED**

Expected: FAIL because `build_solid_volume` is undefined.

- [ ] **Step 3: Implement sheet-band voxelization**

Require `config.solid_convention` to equal `sheet_band`, require real finite `field.G`, require threshold length to equal `size(G,3)`, and compute:

```matlab
threshold3d = reshape(field.threshold, 1, 1, []);
solid = abs(field.G) <= threshold3d;
solidCount = nnz(solid);
voxelCount = numel(solid);
```

Return `solid,solid_count,void_count,voxel_count,solid_fraction,convention`. Reject `solidCount==0` and `solidCount==voxelCount` before returning.

- [ ] **Step 4: Run complete suite GREEN**

Expected: all M01 and M02 tests pass from the project directory and an unrelated temporary directory.

- [ ] **Step 5: Commit solid slice**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/build_solid_volume.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestFieldKernel.m
git commit -m "feat(geometry): build finite sheet Gyroid voxels"
```

---

### Task 5: Freeze kernel provenance labels

**Files:**
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compiler_contract.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestFieldKernel.m`

- [ ] **Step 1: Write failing contract-label test**

Assert these exact values:

```matlab
contract.thresholdProfile = 'piecewise_linear_knots_z_over_l_0_1_2';
contract.cellSizeProfile = 'gamma(z_over_l)=1.5+z_over_l/w';
contract.gyroidFieldVersion = 'small-si-s6-s9-candidate-v1';
contract.solidConvention = 'sheet_band';
```

- [ ] **Step 2: Run RED**

Expected: FAIL because the four fields do not yet exist.

- [ ] **Step 3: Add the four immutable fields to `compiler_contract.m`**

Use the exact strings above. Do not change the M01 descriptor or manifest hashes.

- [ ] **Step 4: Run GREEN and commit**

```powershell
git add -- paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compiler_contract.m paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestFieldKernel.m
git commit -m "chore(geometry): freeze M02 kernel provenance"
```

---

### Task 6: Final M02 evidence and self-review

**Files:** No production additions. Any black-box script is temporary and must be deleted before commit.

- [ ] **Step 1: Run all tests from the project directory**

```powershell
F:\MATLAB\R2023b\bin\matlab.exe -batch "cd('F:/small++/paper_A_reliable_inverse_design/geometry_compiler_matlab'); run_tests"
```

Expected: zero failures.

- [ ] **Step 2: Run all tests from a temporary external directory**

Add only the project root to the MATLAB path, call `run_tests`, return to a safe directory, then remove the temporary directory. Expected: the same test count and zero failures.

- [ ] **Step 3: Run Code Analyzer**

Run `checkcode(...,'-id')` over every `.m` file in `core/`, `tests/`, and `run_tests.m`. Expected: zero issues or a written justification for each nonzero issue; M02 acceptance target is zero.

- [ ] **Step 4: Run independent mathematical probes**

Print and assert:

- M1 threshold at `[0,1,2]` equals `[c0,c1,c2]`;
- M2 projection of `[0.04,0.10,0.16]` equals `[0.10,0.10,0.10]`;
- M3 `gamma([0,1,2])` at `w=4` equals `[1.5,1.75,2]`;
- `G(0.25,0,0)=1` on the resolution-8 grid;
- three representative sheet-band volumes are nonempty and nonfull;
- repeated field construction is bitwise identical.

- [ ] **Step 5: Review the exact Git scope**

Run `git diff --check`, `git status --short`, `git diff --stat`, and inspect every changed file. Do not stage `.qoder/`, archived data, PDFs, preview images, temporary scripts, or the untracked M01 plan.

- [ ] **Step 6: Record residual scientific status**

The final report must state that the field formula and sheet convention remain `candidate_pending_gate0`. M02 proves deterministic implementation of the approved equations; it does not prove agreement with archived five-descriptor values, watertight STL generation, Abaqus importability, or manufacturability.

## 3. Reviewer acceptance checklist

- [ ] M01 commit `960e1c5` remains an ancestor and all 97 M01 tests still pass.
- [ ] M1 rejects nonzero fixed `w`; M2 uses an orthogonal mean projection; M3 passes four controls.
- [ ] All projected active variables obey the versioned bounds and endpoint semantics.
- [ ] Threshold knots are exact and continuous at `z/l=1`.
- [ ] M2/M3 use division by `w`, never multiplication or reciprocal reparameterization.
- [ ] Axes include both domain endpoints with `span*r+1` samples.
- [ ] Field construction is finite, real, deterministic, and uses normalized coordinates.
- [ ] Millimetre spacing equals `reference_length_mm/resolution` and is not used inside normalized trigonometric phases.
- [ ] Sheet volume is exactly `abs(G)<=t(z)` and valid examples contain both solid and void.
- [ ] Project and external-directory suites pass; Code Analyzer is clean.
- [ ] No M02 claim exceeds `candidate_pending_gate0`.
