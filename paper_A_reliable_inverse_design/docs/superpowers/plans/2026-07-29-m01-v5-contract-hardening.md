# M01 v5 Scientific Contract Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Do not use a second implementation agent. Mark each checkbox only after the named command has produced the expected result.

**Goal:** Repair commit `087f818a19dd1779521185305964fe175f5e6993` so the MATLAB bootstrap rejects scientifically invalid M1/M2/M3 configurations, uses the actual Small parameterization and parameter domain, freezes descriptor semantics, eliminates false-positive tests, and passes an independent M01 review.

**Architecture:** Keep `load_compiler_config` as the only public configuration entry point. Store immutable Small source facts in a separate parameter-domain manifest, store mutable runtime choices in the compiler configuration, and bind both the parameter manifest and descriptor definition to SHA-256 hashes. Validate generic JSON shape first, then validate the exact method-specific scientific contract.

**Tech Stack:** MATLAB R2023b, `matlab.unittest`, JSON, PowerShell Git/file-hash commands, Image Processing Toolbox.

---

## 0. Non-negotiable instructions

The implementation Agent must obey every rule below.

1. Work from base commit `087f818a19dd1779521185305964fe175f5e6993` on a new branch named `paper-a/matlab-gyroid-m01-bootstrap-v5`.
2. Do not rewrite, amend, rebase, reset, or delete the v4 branch.
3. Do not add `.qoder/`, generated figures, MATLAB preference files, workbooks, PDFs, or temporary scripts to Git.
4. Do not modify either archived Small workbook. They are read-only scientific evidence.
5. Do not invent parameter transformations. The archived `w` column is used directly by the original extraction script.
6. Do not implement the incorrect expression `Lz(z)=1.5+w*z/l` from the current design document. The Small Supporting Information gives `gamma(z)=1.5+z/w`, with `w` corresponding to the published `sigma` and `sigma in (2,8)`.
7. Do not call an error test successful merely because it raised `MATLABGyroid:InvalidConfig`. Every negative test must also assert a message fragment identifying the intended validation failure.
8. Every temporary configuration fixture that reaches descriptor or method validation must contain both `descriptor_definition.json` and `parameter_domain_manifest.json`.
9. Use `git add` with explicit paths. Never use `git add .`.
10. Stop and report the exact command/output if a scientific fact differs from the expected values below. Do not silently change the expected values.

## 1. Scientific facts that are already resolved

Use the following facts. Do not recalculate them differently unless the source files themselves have changed.

### 1.1 Source hashes

| Source | SHA-256 |
|---|---|
| `train-4canshu.xlsx` | `2EBC39E1D99EF0F117223BC7CF5EDB77232EA37E861045B08BC98E52EFB2E30D` |
| `test-4canshu.xlsx` | `D6A5917BED2D9301624D924C16BD430EE9ECDCC7D4A7076F3E904E685BEABB44` |
| `smll202500634-sup-0001-suppmat.pdf` | `6D3B81931AD16EDAEA157F6A32EEB07A6DC47E3DFC49F8002F0FBD050DC2CB7C` |

### 1.2 Pooled archived records

| Method | Workbook sheet | Train | Test | Pooled | `c` domain | Observed `w` |
|---|---:|---:|---:|---:|---:|---:|
| M1 | `class1` | 5,692 | 1,423 | 7,115 | `[0.03,0.20]` | exactly `0` |
| M2 | `class2` | 7,640 | 1,910 | 9,550 | `[0.03,0.20]` | `[2.0019789,7.998]` |
| M3 | `class12` | 7,112 | 1,778 | 8,890 | `[0.03,0.20]` | `[2.0046,7.995]` |

### 1.3 Published equations

Supporting Information page 3, Equations S8-S9:

```text
gamma(z) = 1.5 + z / sigma,    sigma in (2,8)
```

The archived code/data name `sigma` as `w`. Therefore the compiler contract is:

```text
gamma(z) = 1.5 + z / w,        w in (2,8)
```

The open interval is the published sampling domain. The observed archived extrema lie strictly inside it. Represent this explicitly with lower/upper inclusivity flags; do not quietly turn the scientific statement into `[0,2.5]` or a multiplier form.

For `c0,c1,c2`, the SI prose reports random values between `0.04` and `0.20`, while the delivered archived dataset contains valid values down to `0.03`. Because M01 reproduces the archived Small dataset, the compiler domain is `[0.03,0.20]`. Record this discrepancy in provenance instead of hiding it.

## 2. Files in scope

### Create

- `paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/parameter_domain_manifest.json`
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/sha256_file.m`
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compiler_contract.m`
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestContractHardening.m`

### Modify

- `paper_A_reliable_inverse_design/docs/superpowers/specs/2026-07-28-matlab-graded-gyroid-compiler-design.md`
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/compiler_config.example.json`
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/descriptor_definition.json`
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/load_compiler_config.m`
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestBootstrap.m`

### Do not modify

- `core/compiler_version.m` unless the compiler version is intentionally advanced from `0.1.0`; a hash-only correction does not require a version change at M01.
- `run_tests.m`; it already discovers every test file in `tests/`.
- Any Paper A model-training file.
- Any source under `F:\demo_TPMS`.

---

## Task 1: Establish the clean v5 branch and reproduce the evidence

**Files:** No repository file changes in this task.

- [ ] **Step 1: Verify the starting point**

Run from `F:\small++`:

```powershell
git rev-parse HEAD
git status --short --branch
```

Expected HEAD:

```text
087f818a19dd1779521185305964fe175f5e6993
```

Only the two pre-existing `.qoder/` directories may appear as untracked. If a tracked file is dirty, stop.

- [ ] **Step 2: Create the branch**

```powershell
git switch -c paper-a/matlab-gyroid-m01-bootstrap-v5 087f818a19dd1779521185305964fe175f5e6993
```

- [ ] **Step 3: Verify source hashes**

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath `
  'F:\demo_TPMS\xiedian\Inverse-design-of-graded-TPMS-main\Inverse-design-of-graded-TPMS-main\dataset used for training\train-4canshu.xlsx',`
  'F:\demo_TPMS\xiedian\Inverse-design-of-graded-TPMS-main\Inverse-design-of-graded-TPMS-main\dataset used for training\test-4canshu.xlsx',`
  'C:\Users\48186\Desktop\文献\逆向设计优化\smll202500634-sup-0001-suppmat.pdf'
```

Expected hashes are exactly those in Section 1.1, case-insensitively.

- [ ] **Step 4: Re-run the v4 baseline before editing**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\paper_A_reliable_inverse_design\geometry_compiler_matlab'); run_tests"
```

Expected:

```text
Total tests: 37, Passed: 37, Failed: 0
```

This is only the baseline; it is not v5 acceptance.

---

## Task 2: Correct the governing design specification first

**Files:**

- Modify: `paper_A_reliable_inverse_design/docs/superpowers/specs/2026-07-28-matlab-graded-gyroid-compiler-design.md:86-96`

- [ ] **Step 1: Replace the incorrect M2 equation**

Replace the multiplier description with the following exact contract:

```markdown
For `M2`, `t(z)` is uniform after an orthogonal projection onto
`c0=c1=c2`, and the z-direction unit-cell-size profile follows Supporting
Information Equation S8:

\[
\gamma(z)=1.5+\frac{z}{w},\qquad w\in(2,8).
\]

The Small workbooks store the published `sigma` parameter in the column named
`w`; no reciprocal or affine reparameterization is applied at the dataset
boundary. Coordinates and `gamma` use the published normalized convention.
Physical millimetres are introduced once through `reference_length_mm` at the
compiler boundary.
```

- [ ] **Step 2: Correct the M3 statement**

State explicitly that M3 combines the M1 threshold profile with the same denominator form `gamma(z)=1.5+z/w`.

- [ ] **Step 3: Add an erratum note**

Add a short dated note at the bottom of the specification:

```markdown
### 2026-07-29 parameterization correction

Visual verification of Small Supporting Information page 3, Equations S8-S9,
showed that the archived `w` is the denominator parameter `sigma` in
`gamma(z)=1.5+z/w`, with `w in (2,8)`. The earlier multiplier transcription
was incorrect and must not be used by the compiler or its tests.
```

- [ ] **Step 4: Review the diff before committing**

```powershell
git diff -- paper_A_reliable_inverse_design/docs/superpowers/specs/2026-07-28-matlab-graded-gyroid-compiler-design.md
```

The diff must contain no other design changes.

- [ ] **Step 5: Commit the evidence-backed correction**

```powershell
git add paper_A_reliable_inverse_design/docs/superpowers/specs/2026-07-28-matlab-graded-gyroid-compiler-design.md
git commit -m "docs(geometry): correct Small S8-S9 parameterization"
```

---

## Task 3: Add an immutable parameter-domain manifest

**Files:**

- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/parameter_domain_manifest.json`
- Test: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestContractHardening.m`

- [ ] **Step 1: Create the failing provenance test class**

Create `TestContractHardening.m` with this initial structure:

```matlab
classdef TestContractHardening < matlab.unittest.TestCase
    properties (Constant, Access = private)
        ErrorId = 'MATLABGyroid:InvalidConfig'
    end

    properties (Access = private)
        BaseDir
    end

    methods (TestClassSetup)
        function setupClass(testCase)
            testFile = mfilename('fullpath');
            testCase.BaseDir = fileparts(fileparts(testFile));
            addpath(fullfile(testCase.BaseDir, 'core'));
        end
    end

    methods (Test)
        function testParameterManifestExistsAndMatchesSmallSources(testCase)
            path = fullfile(testCase.BaseDir, 'configs', ...
                'parameter_domain_manifest.json');
            testCase.assertEqual(exist(path, 'file'), 2);
            manifest = jsondecode(fileread(path));
            testCase.verifyEqual(char(string(manifest.schema_version)), '1.0');
            testCase.verifyEqual(manifest.methods.M1.row_counts.pooled, 7115);
            testCase.verifyEqual(manifest.methods.M2.row_counts.pooled, 9550);
            testCase.verifyEqual(manifest.methods.M3.row_counts.pooled, 8890);
            testCase.verifyEqual(char(string(manifest.methods.M3.sheet)), 'class12');
            testCase.verifyEqual(manifest.methods.M2.observed.w.lower, 2.0019789, ...
                'AbsTol', 1e-12);
            testCase.verifyEqual(manifest.methods.M2.observed.w.upper, 7.998, ...
                'AbsTol', 1e-12);
            testCase.verifyEqual(manifest.methods.M3.observed.w.lower, 2.0046, ...
                'AbsTol', 1e-12);
            testCase.verifyEqual(manifest.methods.M3.observed.w.upper, 7.995, ...
                'AbsTol', 1e-12);
        end
    end
end
```

- [ ] **Step 2: Run the test and prove it fails for the missing manifest**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\paper_A_reliable_inverse_design\geometry_compiler_matlab'); r=runtests('tests/TestContractHardening.m'); assert(all([r.Passed]))"
```

Expected: failure because `parameter_domain_manifest.json` does not exist.

- [ ] **Step 3: Create the manifest with the exact scientific facts**

The JSON must contain these exact semantic values:

```json
{
  "schema_version": "1.0",
  "contract": "small-archived-parameter-domain",
  "validity_filter": "Exclude header; retain rows whose c0,c1,c2,w cells are finite numeric values",
  "sources": {
    "train": {
      "filename": "train-4canshu.xlsx",
      "sha256": "2EBC39E1D99EF0F117223BC7CF5EDB77232EA37E861045B08BC98E52EFB2E30D"
    },
    "test": {
      "filename": "test-4canshu.xlsx",
      "sha256": "D6A5917BED2D9301624D924C16BD430EE9ECDCC7D4A7076F3E904E685BEABB44"
    },
    "supporting_information": {
      "filename": "smll202500634-sup-0001-suppmat.pdf",
      "sha256": "6D3B81931AD16EDAEA157F6A32EEB07A6DC47E3DFC49F8002F0FBD050DC2CB7C",
      "location": "page 3, equations S8-S9",
      "published_profile": "gamma(z)=1.5+z/w",
      "published_w_interval": "(2,8)"
    }
  },
  "archive_si_discrepancy": "SI prose states c in 0.04-0.20; archived valid records contain 0.03-0.20. Compiler bounds follow archived records for Small reproduction.",
  "methods": {
    "M1": {
      "sheet": "class1",
      "row_counts": {"train": 5692, "test": 1423, "pooled": 7115},
      "compiler_bounds": {
        "c0": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true},
        "c1": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true},
        "c2": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true}
      },
      "fixed": {"w": 0}
    },
    "M2": {
      "sheet": "class2",
      "row_counts": {"train": 7640, "test": 1910, "pooled": 9550},
      "compiler_bounds": {
        "c_projected": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true},
        "w": {"lower": 2.0, "upper": 8.0, "lower_inclusive": false, "upper_inclusive": false}
      },
      "observed": {
        "c_projected": {"lower": 0.03, "upper": 0.20},
        "w": {"lower": 2.0019789, "upper": 7.998}
      }
    },
    "M3": {
      "sheet": "class12",
      "row_counts": {"train": 7112, "test": 1778, "pooled": 8890},
      "compiler_bounds": {
        "c0": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true},
        "c1": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true},
        "c2": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true},
        "w": {"lower": 2.0, "upper": 8.0, "lower_inclusive": false, "upper_inclusive": false}
      },
      "observed": {
        "c0": {"lower": 0.03, "upper": 0.20},
        "c1": {"lower": 0.03, "upper": 0.20},
        "c2": {"lower": 0.03, "upper": 0.20},
        "w": {"lower": 2.0046, "upper": 7.995}
      }
    }
  }
}
```

- [ ] **Step 4: Re-run the focused test**

Expected: the manifest test passes.

- [ ] **Step 5: Do not commit yet**

The manifest must be bound to its SHA-256 in Task 6 before it is committed.

---

## Task 4: Correct the runtime configuration and make the domain explicit

**Files:**

- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/compiler_config.example.json`
- Test: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestContractHardening.m`

- [ ] **Step 1: Add failing tests for the corrected configuration**

Add these test methods to `TestContractHardening`:

```matlab
function testCanonicalBoundsAndPublishedProfile(testCase)
    config = load_compiler_config(fullfile(testCase.BaseDir, 'configs', ...
        'compiler_config.example.json'));
    testCase.verifyEqual(config.method_bounds.M1.fixed_variables.w, 0);
    testCase.verifyEqual(config.method_bounds.M2.bounds.w.lower, 2.0);
    testCase.verifyEqual(config.method_bounds.M2.bounds.w.upper, 8.0);
    testCase.verifyFalse(config.method_bounds.M2.bounds.w.lower_inclusive);
    testCase.verifyFalse(config.method_bounds.M2.bounds.w.upper_inclusive);
    testCase.verifyEqual(config.method_bounds.M3.bounds.w.lower, 2.0);
    testCase.verifyEqual(config.method_bounds.M3.bounds.w.upper, 8.0);
    testCase.verifyEqual(char(string(config.geometry_parameters.cell_size_profile)), ...
        'gamma(z)=1.5+z/w');
end

function testFiniteNormalizedDomainIsExplicit(testCase)
    config = load_compiler_config(fullfile(testCase.BaseDir, 'configs', ...
        'compiler_config.example.json'));
    domain = config.geometry_parameters.domain_over_l;
    testCase.verifyEqual(domain.x(:)', [0, 1]);
    testCase.verifyEqual(domain.y(:)', [0, 1]);
    testCase.verifyEqual(domain.z(:)', [0, 2]);
    testCase.verifyEqual(char(string(config.geometry_parameters.coordinate_units)), ...
        'normalized_by_reference_length');
    testCase.verifyEqual(char(string(config.geometry_parameters.output_units)), 'mm');
end

function testAllMethodsContainRequiredConvergenceLevels(testCase)
    config = load_compiler_config(fullfile(testCase.BaseDir, 'configs', ...
        'compiler_config.example.json'));
    required = [96, 128, 160];
    names = {'M1', 'M2', 'M3'};
    for i = 1:numel(names)
        levels = double(config.method_bounds.(names{i}).levels(:)');
        testCase.verifyTrue(all(ismember(required, levels)), ...
            sprintf('%s must contain 96,128,160', names{i}));
    end
end
```

- [ ] **Step 2: Run the focused tests and confirm failures**

Expected failures include M2/M3 bounds, the cell-size profile, explicit domain fields, and M3 missing level 96.

- [ ] **Step 3: Replace method contracts in the example config**

Use these exact method semantics:

```json
"M1": {
  "description": "Piecewise-linear threshold profile; c0,c1,c2 active; w fixed at 0",
  "active_variables": ["c0", "c1", "c2"],
  "fixed_variables": {"w": 0},
  "projection": null,
  "bounds_manifest_method": "M1",
  "bounds": {
    "c0": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true},
    "c1": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true},
    "c2": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true}
  },
  "levels": [96, 128, 160],
  "convergence_tolerance": 1e-4,
  "max_iterations": 500
},
"M2": {
  "description": "Uniform threshold after L2 projection; published gamma(z)=1.5+z/w profile",
  "active_variables": ["c_projected", "w"],
  "fixed_variables": {},
  "projection": {
    "type": "orthogonal_l2_equal_subspace",
    "variables": ["c0", "c1", "c2"],
    "projected_name": "c_projected",
    "formula": "c_projected=mean([c0,c1,c2]); c0=c1=c2=c_projected"
  },
  "bounds_manifest_method": "M2",
  "bounds": {
    "c_projected": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true},
    "w": {"lower": 2.0, "upper": 8.0, "lower_inclusive": false, "upper_inclusive": false}
  },
  "levels": [96, 128, 160],
  "convergence_tolerance": 1e-5,
  "max_iterations": 1000
},
"M3": {
  "description": "Combined threshold and published gamma(z)=1.5+z/w profiles",
  "active_variables": ["c0", "c1", "c2", "w"],
  "fixed_variables": {},
  "projection": null,
  "bounds_manifest_method": "M3",
  "bounds": {
    "c0": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true},
    "c1": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true},
    "c2": {"lower": 0.03, "upper": 0.20, "lower_inclusive": true, "upper_inclusive": true},
    "w": {"lower": 2.0, "upper": 8.0, "lower_inclusive": false, "upper_inclusive": false}
  },
  "levels": [96, 128, 160, 192],
  "convergence_tolerance": 1e-6,
  "max_iterations": 2000
}
```

- [ ] **Step 4: Replace ambiguous geometry units with an explicit one-time scaling contract**

Use:

```json
"geometry_parameters": {
  "coordinate_units": "normalized_by_reference_length",
  "output_units": "mm",
  "Lx_over_l": 1.0,
  "Ly_over_l": 1.0,
  "Lz0_over_l": 1.5,
  "domain_over_l": {
    "x": [0.0, 1.0],
    "y": [0.0, 1.0],
    "z": [0.0, 2.0]
  },
  "w_units": "normalized_denominator_parameter",
  "cell_size_profile": "gamma(z)=1.5+z/w",
  "physical_conversion": "multiply normalized coordinates by reference_length_mm exactly once",
  "validation_status": "candidate_pending_gate0"
}
```

Also add these top-level path fields. Task 6 adds the two SHA-256 fields after the referenced files are finalized:

```json
"parameter_domain_manifest_path": "parameter_domain_manifest.json",
"descriptor_definition_path": "descriptor_definition.json"
```

- [ ] **Step 5: Keep resolution at 128 and do not alter tolerances in this task**

The method-specific convergence tolerances are not yet scientifically justified, but changing them belongs to the later convergence study. Record this as a residual item rather than inventing replacements.

---

## Task 5: Freeze descriptor boundary and grid semantics before hashing

**Files:**

- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/descriptor_definition.json`
- Test: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestContractHardening.m`

- [ ] **Step 1: Add top-level contract status and grid convention**

Add:

```json
"validation_status": "candidate_pending_gate0",
"grid_convention": {
  "resolution_definition": "voxel-centre samples per reference length",
  "spacing_policy": "isotropic_required",
  "voxel_counts": "Ni=round(domain_length_i/reference_length_mm*resolution)",
  "voxel_spacing": "di=domain_length_i/Ni",
  "coordinate_location": "cell centres",
  "area_element": "dx_mm*dy_mm",
  "volume_element": "dx_mm*dy_mm*dz_mm"
},
"finite_domain_boundary_policy": {
  "outside_domain": "non-void barrier for inscribed-sphere distance",
  "void_connectivity_3d": 26,
  "slice_connectivity_2d": 8
}
```

- [ ] **Step 2: Correct poreDiameter's finite-domain policy**

The descriptor must state that distance is measured to either solid or the finite-domain boundary. Use the following algorithm text:

```matlab
voidMask = ~solid;
paddedVoid = padarray(voidMask, [1 1 1], false, 'both');
Dpad = bwdist(~paddedVoid);
D = Dpad(2:end-1, 2:end-1, 2:end-1);
cc = bwconncomp(voidMask, 26);
if cc.NumObjects == 0
    poreDiameter = NaN;
else
    counts = cellfun(@numel, cc.PixelIdxList);
    [~, largestIdx] = max(counts);
    poreDiameter = 2 * max(D(cc.PixelIdxList{largestIdx})) * voxel_size_mm;
end
```

Add `padarray` to `required_functions`. Keep the definition labelled candidate until Gate 0 verifies it against archived descriptors.

- [ ] **Step 3: Replace scalar area normalization wording**

For `areaMean`, replace `pixel_count * voxel_size_mm^2` with:

```text
pixel_count * dx_mm * dy_mm
```

The coordinate of z slice `k` is:

```text
z_mm = z_min_mm + (k - 0.5) * dz_mm
```

Continue using exactly 26 uniformly indexed slices, endpoints represented by the first and last voxel-centre slices, 8-connectivity, largest connected pore region per slice, empty slices excluded, and `NaN` when all slices are empty.

- [ ] **Step 4: Add candidate-status assertions**

Add:

```matlab
function testDescriptorDefinitionIsExplicitlyCandidate(testCase)
    path = fullfile(testCase.BaseDir, 'configs', 'descriptor_definition.json');
    definition = jsondecode(fileread(path));
    testCase.verifyEqual(char(string(definition.validation_status)), ...
        'candidate_pending_gate0');
    testCase.verifyEqual(char(string(definition.grid_convention.spacing_policy)), ...
        'isotropic_required');
    testCase.verifyEqual(definition.finite_domain_boundary_policy.void_connectivity_3d, 26);
    testCase.verifyEqual(definition.finite_domain_boundary_policy.slice_connectivity_2d, 8);
end
```

- [ ] **Step 5: Verify JSON parses before continuing**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "jsondecode(fileread('F:\small++\paper_A_reliable_inverse_design\geometry_compiler_matlab\configs\descriptor_definition.json')); disp('DESCRIPTOR_JSON_OK')"
```

Expected: `DESCRIPTOR_JSON_OK`.

---

## Task 6: Compute and declare both contract hashes

**Files:**

- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/sha256_file.m`
- Create: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compiler_contract.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/compiler_config.example.json`

- [ ] **Step 1: Create the SHA-256 helper**

Use this complete implementation:

```matlab
function digestHex = sha256_file(filePath, errorId, label)
%SHA256_FILE Returns the lowercase SHA-256 digest of the exact file bytes.
    if nargin ~= 3
        error('MATLABGyroid:ProgrammerError', ...
            'sha256_file requires filePath, errorId, and label.');
    end
    if exist(filePath, 'file') ~= 2
        throw(MException(errorId, '%s not found: %s', label, filePath));
    end
    fileId = fopen(filePath, 'rb');
    if fileId == -1
        throw(MException(errorId, 'Cannot open %s: %s', label, filePath));
    end
    cleanup = onCleanup(@() fclose(fileId));
    try
        bytes = fread(fileId, Inf, '*uint8');
        messageDigest = javaMethod('getInstance', ...
            'java.security.MessageDigest', 'SHA-256');
        messageDigest.update(typecast(bytes, 'int8'));
        digestBytes = typecast(messageDigest.digest(), 'uint8');
        digestHex = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
    catch cause
        wrapped = MException(errorId, ...
            'Cannot hash %s "%s": %s', label, filePath, cause.message);
        wrapped = addCause(wrapped, cause);
        throw(wrapped);
    end
end
```

- [ ] **Step 2: Compute exact final hashes**

Run only after Tasks 3-5 are complete:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath `
  'F:\small++\paper_A_reliable_inverse_design\geometry_compiler_matlab\configs\parameter_domain_manifest.json',`
  'F:\small++\paper_A_reliable_inverse_design\geometry_compiler_matlab\configs\descriptor_definition.json'
```

Copy the exact 64-character digests, converted to lowercase, into the main configuration in the next step. Do not use the workbook hashes here.

- [ ] **Step 3: Add declared hashes to the example config**

Add `parameter_domain_manifest_sha256` and `descriptor_definition_sha256` as top-level JSON string fields. Set each field to the corresponding lowercase digest printed by Step 2. Before continuing, verify both values against `^[0-9a-f]{64}$` and re-run `Get-FileHash` to confirm exact equality.

- [ ] **Step 4: Create `compiler_contract.m` for non-file semantic constants**

Use this complete implementation. File hashes remain declared in the version-controlled main configuration and are checked against the actual bytes at runtime.

```matlab
function contract = compiler_contract()
%COMPILER_CONTRACT Immutable bootstrap contract for schema version 1.0.
    contract = struct();
    contract.schemaVersion = '1.0';
    contract.descriptorNames = {'relativeVolume', 'relativeArea', ...
        'thickness', 'poreDiameter', 'areaMean'};
    contract.requiredLevels = [96, 128, 160];
end
```

- [ ] **Step 5: Add a hash-helper test**

```matlab
function testDeclaredContractHashesMatchFiles(testCase)
    configDir = fullfile(testCase.BaseDir, 'configs');
    config = jsondecode(fileread(fullfile(configDir, ...
        'compiler_config.example.json')));
    manifestHash = sha256_file(fullfile(configDir, ...
        'parameter_domain_manifest.json'), testCase.ErrorId, ...
        'parameter-domain manifest');
    descriptorHash = sha256_file(fullfile(configDir, ...
        'descriptor_definition.json'), testCase.ErrorId, ...
        'descriptor definition');
    testCase.verifyEqual(manifestHash, ...
        lower(char(string(config.parameter_domain_manifest_sha256))));
    testCase.verifyEqual(descriptorHash, ...
        lower(char(string(config.descriptor_definition_sha256))));
end
```

---

## Task 7: Enforce the exact scientific contract in the loader

**Files:**

- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/load_compiler_config.m`
- Test: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestContractHardening.m`

### 7.1 Write all mutation tests before implementation

- [ ] **Step 1: Add a complete-fixture helper**

Add these private static helpers to `TestContractHardening`:

```matlab
methods (Static, Access = private)
    function fixture = createFixture(baseDir)
        fixture.dir = tempname;
        mkdir(fixture.dir);
        fixture.cleanup = onCleanup(@() rmdir(fixture.dir, 's'));
        copyfile(fullfile(baseDir, 'configs', 'descriptor_definition.json'), ...
            fullfile(fixture.dir, 'descriptor_definition.json'));
        copyfile(fullfile(baseDir, 'configs', 'parameter_domain_manifest.json'), ...
            fullfile(fixture.dir, 'parameter_domain_manifest.json'));
        configPath = fullfile(baseDir, 'configs', 'compiler_config.example.json');
        fixture.data = jsondecode(fileread(configPath));
        fixture.configPath = fullfile(fixture.dir, 'compiler_config.json');
    end

    function writeJson(path, value)
        fileId = fopen(path, 'w');
        assert(fileId ~= -1, 'Cannot open temporary JSON file: %s', path);
        cleanup = onCleanup(@() fclose(fileId));
        fprintf(fileId, '%s', jsonencode(value));
    end

    function verifyInvalid(testCase, fixture, expectedMessage)
        TestContractHardening.writeJson(fixture.configPath, fixture.data);
        caughtException = [];
        try
            load_compiler_config(fixture.configPath);
        catch caught
            caughtException = caught;
        end
        if isempty(caughtException)
            testCase.verifyTrue(false, sprintf( ...
                'Expected InvalidConfig containing "%s".', expectedMessage));
            return;
        end
        testCase.verifyEqual(caughtException.identifier, testCase.ErrorId);
        testCase.verifyTrue(contains(caughtException.message, expectedMessage));
    end
end
```

- [ ] **Step 2: Add exact method-semantics mutation tests**

Add one test method for every row:

| Test name | Mutation | Required message fragment |
|---|---|---|
| `testM1ActiveSetRejected` | M1 active only `c0,c1` | `M1.active_variables` |
| `testM1NonzeroWRejected` | M1 fixed `w=7` | `M1.fixed_variables.w` |
| `testM1ProjectionRejected` | give M1 a nonempty projection | `M1.projection` |
| `testM1BoundsSetRejected` | remove M1 bound `c2` | `M1.bounds` |
| `testM2ActiveSetRejected` | M2 active only `w` | `M2.active_variables` |
| `testM2MissingProjectionRejected` | remove M2 projection | `M2.projection` |
| `testM2ProjectionTypeRejected` | type=`bogus` | `M2.projection.type` |
| `testM2ProjectionVariablesRejected` | variables=`w` | `M2.projection.variables` |
| `testM2ProjectedNameRejected` | name=`c0` | `M2.projection.projected_name` |
| `testM2ProjectionFormulaRejected` | formula=`c0` | `M2.projection.formula` |
| `testM2FixedVariablesRejected` | add fixed `w=0` | `M2.fixed_variables` |
| `testM2BoundsSetRejected` | remove `c_projected` | `M2.bounds` |
| `testM3ActiveSetRejected` | M3 active only `c0` | `M3.active_variables` |
| `testM3FixedVariablesRejected` | add fixed `w=0` | `M3.fixed_variables` |
| `testM3ProjectionRejected` | give M3 a nonempty projection | `M3.projection` |
| `testM3BoundsSetRejected` | remove M3 bound `w` | `M3.bounds` |

Example implementation pattern:

```matlab
function testM1NonzeroWRejected(testCase)
    fixture = TestContractHardening.createFixture(testCase.BaseDir);
    fixture.data.method_bounds.M1.fixed_variables.w = 7;
    TestContractHardening.verifyInvalid(testCase, fixture, ...
        'M1.fixed_variables.w');
end
```

Repeat the full three-line fixture/mutation/assertion body for each row; do not combine unrelated mutations into a single test.

- [ ] **Step 3: Add bounds/provenance mutation tests**

Required tests:

```matlab
function testM2ZeroToTwoPointFiveWRejected(testCase)
    fixture = TestContractHardening.createFixture(testCase.BaseDir);
    fixture.data.method_bounds.M2.bounds.w.lower = 0;
    fixture.data.method_bounds.M2.bounds.w.upper = 2.5;
    TestContractHardening.verifyInvalid(testCase, fixture, ...
        'M2.bounds.w');
end

function testClass3ProvenanceRejected(testCase)
    fixture = TestContractHardening.createFixture(testCase.BaseDir);
    fixture.data.method_bounds.M3.bounds_manifest_method = 'class3';
    TestContractHardening.verifyInvalid(testCase, fixture, ...
        'M3.bounds_manifest_method');
end

function testSingleResolutionLevelRejected(testCase)
    fixture = TestContractHardening.createFixture(testCase.BaseDir);
    fixture.data.method_bounds.M3.levels = 128;
    TestContractHardening.verifyInvalid(testCase, fixture, 'M3.levels');
end
```

- [ ] **Step 4: Add hash mutation tests**

Copy the descriptor/manifest into a complete fixture, mutate each copied file without updating the declared hash, and require rejection:

```matlab
function testDescriptorSemanticMutationRejectedByHash(testCase)
    fixture = TestContractHardening.createFixture(testCase.BaseDir);
    path = fullfile(fixture.dir, 'descriptor_definition.json');
    definition = jsondecode(fileread(path));
    if iscell(definition.descriptors)
        definition.descriptors{5}.algorithm_params.slice_count = 25;
    else
        definition.descriptors(5).algorithm_params.slice_count = 25;
    end
    TestContractHardening.writeJson(path, definition);
    TestContractHardening.verifyInvalid(testCase, fixture, ...
        'descriptor_definition_sha256');
end

function testParameterManifestMutationRejectedByHash(testCase)
    fixture = TestContractHardening.createFixture(testCase.BaseDir);
    path = fullfile(fixture.dir, 'parameter_domain_manifest.json');
    manifest = jsondecode(fileread(path));
    manifest.methods.M2.compiler_bounds.w.lower = 0;
    TestContractHardening.writeJson(path, manifest);
    TestContractHardening.verifyInvalid(testCase, fixture, ...
        'parameter_domain_manifest_sha256');
end
```

- [ ] **Step 5: Run the red suite**

Run `TestContractHardening.m`. The new mutation tests must fail because v4 still accepts the mutations. Capture the failing test names in the Agent report.

### 7.2 Implement exact validation

- [ ] **Step 6: Validate the public argument before `exist`**

At the top of `load_compiler_config`:

```matlab
if nargin ~= 1
    throw(MException(ERROR_ID, ...
        'load_compiler_config requires exactly one config_path argument'));
end
if ~(ischar(config_path) && isrow(config_path)) && ...
        ~(isstring(config_path) && isscalar(config_path))
    throw(MException(ERROR_ID, ...
        'config_path must be a character row vector or string scalar'));
end
config_path = char(config_path);
```

- [ ] **Step 7: Extend the required top-level fields**

Require:

```matlab
{'schema_version', 'reference_length_mm', 'resolution', ...
 'descriptor_names', 'descriptor_definition_path', ...
 'descriptor_definition_sha256', ...
 'parameter_domain_manifest_path', ...
 'parameter_domain_manifest_sha256', ...
 'solid_convention', 'method_bounds', 'mesh_qc', 'geometry_parameters'}
```

- [ ] **Step 8: Validate resolution without silent saturation**

After the existing positive-integer checks:

```matlab
if data.resolution > double(intmax('uint32'))
    throw(MException(ERROR_ID, ...
        'Resolution exceeds uint32 capacity: %.0f', data.resolution));
end
```

- [ ] **Step 9: Resolve, read, hash, and parse both contract files**

For each file:

1. Resolve relative to the main config directory.
2. Reject absolute paths and any path component equal to `..`.
3. Compute the exact byte hash with `sha256_file`.
4. Compare actual hash to the hash declared in the main config.
5. Validate the declared hash is exactly 64 hexadecimal characters.
6. Read with `fileread` inside `try/catch` and wrap read/parse errors with `MATLABGyroid:InvalidConfig`.

The descriptor mismatch message must contain `descriptor_definition_sha256`; the manifest mismatch message must contain `parameter_domain_manifest_sha256`.

- [ ] **Step 10: Validate geometry parameters exactly**

Require these fields:

```matlab
{'coordinate_units', 'output_units', 'Lx_over_l', 'Ly_over_l', ...
 'Lz0_over_l', 'domain_over_l', 'w_units', 'cell_size_profile', ...
 'physical_conversion', 'validation_status'}
```

Enforce:

```text
coordinate_units = normalized_by_reference_length
output_units = mm
Lx_over_l = 1
Ly_over_l = 1
Lz0_over_l = 1.5
domain_over_l.x = [0,1]
domain_over_l.y = [0,1]
domain_over_l.z = [0,2]
w_units = normalized_denominator_parameter
cell_size_profile = gamma(z)=1.5+z/w
validation_status = candidate_pending_gate0
```

Each domain vector must be numeric, finite, have exactly two elements, and be strictly increasing before checking the canonical values.

- [ ] **Step 11: Require `projection` and `bounds_manifest_method` for every method**

Update `method_fields` to include both fields. This prevents the v4 missing-projection false positive at the validator itself.

- [ ] **Step 12: Add exact method validation after generic shape checks**

Use a dedicated local helper such as:

```matlab
function validate_exact_method_contract(mb, manifest, requiredLevels, ERROR_ID)
    assert_cellstr_exact(mb.M1.active_variables, {'c0','c1','c2'}, ...
        'M1.active_variables', ERROR_ID);
    assert_field_set(mb.M1.fixed_variables, {'w'}, ...
        'M1.fixed_variables', ERROR_ID);
    if mb.M1.fixed_variables.w ~= 0
        throw(MException(ERROR_ID, 'M1.fixed_variables.w must equal 0'));
    end
    assert_empty_projection(mb.M1.projection, 'M1.projection', ERROR_ID);
    assert_field_set(mb.M1.bounds, {'c0','c1','c2'}, 'M1.bounds', ERROR_ID);

    assert_cellstr_exact(mb.M2.active_variables, {'c_projected','w'}, ...
        'M2.active_variables', ERROR_ID);
    assert_field_set(mb.M2.fixed_variables, {}, 'M2.fixed_variables', ERROR_ID);
    validate_m2_projection(mb.M2.projection, ERROR_ID);
    assert_field_set(mb.M2.bounds, {'c_projected','w'}, 'M2.bounds', ERROR_ID);

    assert_cellstr_exact(mb.M3.active_variables, {'c0','c1','c2','w'}, ...
        'M3.active_variables', ERROR_ID);
    assert_field_set(mb.M3.fixed_variables, {}, 'M3.fixed_variables', ERROR_ID);
    assert_empty_projection(mb.M3.projection, 'M3.projection', ERROR_ID);
    assert_field_set(mb.M3.bounds, {'c0','c1','c2','w'}, ...
        'M3.bounds', ERROR_ID);

    names = {'M1','M2','M3'};
    for i = 1:numel(names)
        name = names{i};
        if ~strcmp(char(string(mb.(name).bounds_manifest_method)), name)
            throw(MException(ERROR_ID, ...
                '%s.bounds_manifest_method must equal %s', name, name));
        end
        levels = double(mb.(name).levels(:)');
        if ~all(ismember(requiredLevels, levels))
            throw(MException(ERROR_ID, ...
                '%s.levels must contain [96, 128, 160]', name));
        end
        validate_bounds_match_manifest(mb.(name).bounds, ...
            manifest.methods.(name).compiler_bounds, name, ERROR_ID);
    end
end
```

Implement the named helpers; do not leave generic names unresolved. They must:

- compare cell-string sequences exactly and reject duplicates;
- compare struct field names as sets so JSON object ordering is irrelevant;
- require empty projections for M1/M3;
- require the exact M2 type, variables, projected name, and formula from Task 4;
- compare `lower`, `upper`, `lower_inclusive`, and `upper_inclusive` to the manifest.

- [ ] **Step 13: Return the validated provenance and hashes**

The returned config must contain:

```matlab
config.parameter_domain_manifest_path
config.parameter_domain_manifest_sha256
config.parameter_domain
config.descriptor_definition_path
config.descriptor_definition_sha256
config.geometry_parameters
```

- [ ] **Step 14: Run the focused green suite**

Every mutation test must now pass because the mutation is rejected for its intended reason.

- [ ] **Step 15: Commit the contract implementation**

```powershell
git add `
  paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/compiler_config.example.json `
  paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/descriptor_definition.json `
  paper_A_reliable_inverse_design/geometry_compiler_matlab/configs/parameter_domain_manifest.json `
  paper_A_reliable_inverse_design/geometry_compiler_matlab/core/compiler_contract.m `
  paper_A_reliable_inverse_design/geometry_compiler_matlab/core/sha256_file.m `
  paper_A_reliable_inverse_design/geometry_compiler_matlab/core/load_compiler_config.m `
  paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestContractHardening.m
git commit -m "fix(geometry): enforce Small compiler scientific contract"
```

---

## Task 8: Eliminate existing false-positive fixtures and close error handling

**Files:**

- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestBootstrap.m`
- Modify: `paper_A_reliable_inverse_design/geometry_compiler_matlab/core/load_compiler_config.m`

- [ ] **Step 1: Replace `testMissingProjectionInM2Rejected`**

It must create a complete fixture containing descriptor and manifest files, remove only M2 projection, and assert the message contains `M2.projection`. Do not merely check the shared error ID.

- [ ] **Step 2: Audit every temp-file test**

For each test that expects validation after path resolution:

1. Use a temporary directory, not a lone temporary JSON filename.
2. Copy both referenced JSON contract files.
3. Write the main config into that same directory.
4. Assert both identifier and a targeted message fragment.

Tests that deliberately fail before dependency resolution, such as malformed top-level JSON, may remain single-file fixtures.

- [ ] **Step 3: Wrap descriptor and manifest reads**

No `fileread` for either contract file may remain outside a `try/catch` that converts expected I/O failures to `MATLABGyroid:InvalidConfig` and preserves the cause with `addCause`.

- [ ] **Step 4: Add boundary tests for public input**

Required cases:

| Input | Expected message |
|---|---|
| no arguments | `exactly one config_path` |
| numeric path `1` | `config_path` |
| string array with two elements | `config_path` |
| missing descriptor file | `Descriptor definition not found` |
| missing manifest file | `Parameter-domain manifest not found` |
| resolution `2^32` | `uint32 capacity` |

- [ ] **Step 5: Tighten mesh-QC value ranges**

Require:

```text
0 < min_edge_length_ratio <= 1
0 < max_angle_deviations <= 180
surface_tolerance_mm > 0 and finite
```

Add one rejection test for ratio `1.1` and one for angle `181`.

- [ ] **Step 6: Run the complete suite**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:\small++\paper_A_reliable_inverse_design\geometry_compiler_matlab'); run_tests"
```

Expected: all tests pass. The total must be greater than 37 and must include every named v5 mutation test.

- [ ] **Step 7: Commit test and error-boundary repairs**

```powershell
git add `
  paper_A_reliable_inverse_design/geometry_compiler_matlab/core/load_compiler_config.m `
  paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestBootstrap.m `
  paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/TestContractHardening.m
git commit -m "test(geometry): reject bootstrap contract mutations"
```

---

## Task 9: Run explicit black-box acceptance probes

**Files:** No committed files. Temporary scripts must be outside Git or removed before completion.

- [ ] **Step 1: Re-run each former escape condition against a complete fixture**

The following mutations must all be rejected:

```text
M1 active_variables missing c2
M1 fixed w=7
M2 projection missing
M2 projection type=bogus
M2 projection variables=[w]
M3 active_variables=[c0]
M3 levels=[128]
M2 w bounds=[0,2.5]
M3 bounds_manifest_method=class3
descriptor areaMean slice_count=25
descriptor areaMean connectivity=4
parameter manifest M2 w lower=0
```

For each case, print:

```text
REJECTED <case-name> MATLABGyroid:InvalidConfig <targeted-message>
```

Any line beginning with `ACCEPTED` is a release blocker.

- [ ] **Step 2: Verify the valid example loads**

Print and check:

```text
VALID_CONFIG_LOADED=1
M1_W_FIXED=0
M2_W_DOMAIN=(2,8)
M3_SHEET=class12
PROFILE=gamma(z)=1.5+z/w
DOMAIN_Z_OVER_L=[0,2]
```

- [ ] **Step 3: Remove the temporary probe script**

Confirm it does not appear in `git status --short`.

---

## Task 10: Static analysis, clean-scope verification, and final report

**Files:** Only fixes required by the following checks may be modified.

- [ ] **Step 1: Run Code Analyzer on every MATLAB file in scope**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "b='F:\small++\paper_A_reliable_inverse_design\geometry_compiler_matlab'; files=[dir(fullfile(b,'core','*.m'));dir(fullfile(b,'tests','*.m'));dir(fullfile(b,'*.m'))]; for i=1:numel(files), p=fullfile(files(i).folder,files(i).name); m=checkcode(p,'-id'); fprintf('%s %d\n',p,numel(m)); for j=1:numel(m), fprintf('L%d %s %s\n',m(j).line,m(j).id,m(j).message); end; end"
```

Expected: no errors. Remove the known unused `dummy_img`/`distance_map` assignments or annotate them intentionally so `TestBootstrap` no longer has the two NASGU warnings.

- [ ] **Step 2: Run the suite from outside the project directory**

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd(tempdir); addpath('F:\small++\paper_A_reliable_inverse_design\geometry_compiler_matlab'); run_tests"
```

Expected: identical pass result, proving path independence.

- [ ] **Step 3: Verify JSON and hashes one final time**

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath `
  'F:\small++\paper_A_reliable_inverse_design\geometry_compiler_matlab\configs\parameter_domain_manifest.json',`
  'F:\small++\paper_A_reliable_inverse_design\geometry_compiler_matlab\configs\descriptor_definition.json'
```

Both outputs must match the main config exactly.

- [ ] **Step 4: Verify Git scope**

```powershell
git diff --check 087f818a19dd1779521185305964fe175f5e6993 HEAD
git diff --name-status 087f818a19dd1779521185305964fe175f5e6993 HEAD
git status --short --untracked-files=no
```

Expected:

- `git diff --check` produces no output.
- Changed files are limited to Section 2.
- Tracked worktree status is empty.

- [ ] **Step 5: Produce the completion report**

The Agent's final report must contain all of the following, as text rather than screenshots:

1. Branch name and every commit SHA.
2. Exact changed-file list.
3. MATLAB release and toolbox availability.
4. Complete test count, passed count, and failed count.
5. Names of all v5 mutation tests.
6. Black-box output showing every invalid configuration was rejected.
7. The three immutable source hashes.
8. The two newly generated contract-file hashes.
9. Archived row counts and observed extrema.
10. Confirmation that the implemented formula is `gamma(z)=1.5+z/w`, not a multiplier.
11. Code Analyzer results.
12. `git diff --check` result and tracked-worktree status.
13. Residual scientific status: descriptor definitions and physical scaling remain `candidate_pending_gate0` until Gate 0 comparison is complete.

Do not claim M01 complete merely because the test count increased. M01 v5 is reviewable only when every item above has direct command output.

---

## Reviewer acceptance checklist

The reviewing Agent will independently repeat these checks:

- [ ] HEAD descends from `087f818` and only approved files changed.
- [ ] SI S8-S9 denominator formula is corrected in spec and config.
- [ ] M2/M3 `w` domain is `(2,8)`, with observed extrema recorded separately.
- [ ] M3 source sheet is `class12`.
- [ ] Source workbook/PDF hashes and row counts match Section 1.
- [ ] Method active/fixed/projection/bounds sets are exact and mutation-resistant.
- [ ] M2 projection is deterministic and explicitly defined.
- [ ] M1/M3 reject nonempty projections.
- [ ] Each convergence schedule contains 96, 128, and 160.
- [ ] Finite normalized domain and one-time mm conversion are explicit.
- [ ] Descriptor and parameter manifest hashes are checked at runtime.
- [ ] Descriptor semantic mutations are rejected.
- [ ] Pore boundary policy and anisotropic area element are explicit.
- [ ] Missing-projection test fails for the projection, not a missing dependency.
- [ ] All expected validation failures use the common error ID plus targeted messages.
- [ ] Complete suite passes in MATLAB R2023b from project and external directories.
- [ ] Code Analyzer has no errors and no unexplained warnings.
- [ ] No source workbook, PDF, `.qoder`, preview, or temporary script is committed.

## Explicitly deferred beyond M01

The Agent must not attempt these items in v5:

- Implement the complete implicit-field generator.
- Generate production STL files.
- Run Gate 0 descriptor comparison.
- Select production resolution from convergence results.
- Freeze final physical scale after Gate 0.
- Run Abaqus or generate the 150-300 Paper A samples.
- Modify Graph Transformer, Diffusion, or PyG code.

Those are later tasks. M01 v5 is solely the trustworthy, versioned compiler contract and bootstrap validation layer.
