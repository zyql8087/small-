# MATLAB Graded-Gyroid Geometry Compiler Design Specification

## 1. Decision and scope

Implement a self-contained MATLAB R2023 geometry compiler for the three graded Gyroid methods used by the Small dataset. The compiler receives only the method label and independent controls `c0,c1,c2,w`, then deterministically produces a finite, manufacturable sheet-TPMS specimen, five recomputed geometry descriptors, a watertight STL, and a versioned manifest.

The compiler is the Gate 0 prerequisite for Paper A. It is not an Abaqus solver, a diffusion model, or a replacement for the archived Small data extractor. Abaqus pre-processing may consume the generated STL and manifest only after Gate 0 passes.

## 2. Canonical inputs and outputs

### 2.1 Inputs

| Field | Meaning |
|---|---|
| `method` | `M1`, `M2`, or `M3` |
| `c0,c1,c2` | Axial grading controls at `z=0,l,2l` |
| `w` | z-direction cell-size grading control |
| `resolution` | Voxel samples per reference unit length |
| `output_dir` | Per-request artifact directory |

Method constraints are frozen as follows.

- `M1`: `c0,c1,c2` are active and `w=0`.
- `M2`: `c0=c1=c2` after projection; `w` is active.
- `M3`: all four continuous controls are active.

The parameter domain is loaded from a versioned JSON configuration derived from archived valid records. The MATLAB code does not carry unversioned hard-coded sampling bounds.

### 2.2 Outputs

Every request produces a JSON response compatible with the Paper A `GeometryCompiler` contract, a local artifact manifest, and—when valid—a watertight STL.

```json
{
  "schema_version": "1.0",
  "request_id": "uuid",
  "compiler_version": "matlab-gyroid-0.1.0",
  "valid": true,
  "descriptors": {
    "relativeVolume": 0.0,
    "relativeArea": 0.0,
    "thickness": 0.0,
    "poreDiameter": 0.0,
    "areaMean": 0.0
  },
  "stl_path": "absolute-or-request-relative-path",
  "geometry_sha256": "hex digest",
  "failure_code": null,
  "diagnostics": {}
}
```

The descriptor order used by Python is permanently
`[relativeVolume, relativeArea, thickness, poreDiameter, areaMean]`.

## 3. Mathematical reconstruction

### 3.1 Base implicit Gyroid

The implementation follows Supporting Information Equations S6–S9. In physical coordinates, the base implicit field is

\[
G(x,y,z)=\sin\!\left(\frac{2\pi x}{L_x}\right)\cos\!\left(\frac{2\pi y}{L_y}\right)
+\sin\!\left(\frac{2\pi y}{L_y}\right)\cos\!\left(\frac{2\pi z}{L_z(z)}\right)
+\sin\!\left(\frac{2\pi z}{L_z(z)}\right)\cos\!\left(\frac{2\pi x}{L_x}\right).
\]

The finite specimen domain and the reference length `l` are configuration fields. The initial canonical domain is `x∈[0,Lx]`, `y∈[0,Ly]`, `z∈[0,2l]`; it becomes frozen only after historic descriptor validation. Unit conversion is applied once, at the compiler boundary.

### 3.2 Method 1: axial threshold profile

For `M1`, the threshold profile is piecewise linear and must satisfy the three knot values exactly:

\[
t(z)=
\begin{cases}
c_0+\frac{c_1-c_0}{l}z, & 0\le z\le l,\\
c_1+\frac{c_2-c_1}{l}(z-l), & l<z\le 2l.
\end{cases}
\]

Unit tests must prove `t(0)=c0`, `t(l)=c1`, and `t(2l)=c2`, including floating-point boundary handling.

### 3.3 Method 2: axial cell-size profile

For `M2`, `t(z)` is uniform after the method projection and the z-direction cell-size profile follows S8. The compiler implements the published affine form

\[
L_z(z)=L_{z,0}+w\frac{z}{l},
\]

where the dimensionless base convention reported in the supplement is `Lz,0=1.5`. The archived data and Gate 0 benchmark determine the physical scale and allowed `w` interval. The code stores these values in configuration and records them in every manifest.

### 3.4 Method 3: combined profile

For `M3`, apply both the Method 1 threshold profile and Method 2 cell-size profile to the same field.

### 3.5 Solid convention

Equation S6 specifies a surface. A finite printable specimen requires a solid convention. The default candidate is a sheet-TPMS band:

\[
\Omega_{solid}=\{(x,y,z): |G(x,y,z)|\le t(z)\}.
\]

The compiler keeps the alternative signed-level-set convention as an explicit experimental configuration, never as an implicit branch. A single convention is selected by the preregistered Gate 0 descriptor benchmark and then frozen with a configuration hash. Validated results may not mix conventions.

## 4. MATLAB project architecture

All new MATLAB source resides under `paper_A_reliable_inverse_design/geometry_compiler_matlab/`.

```text
geometry_compiler_matlab/
  run_geometry_compiler.m
  core/
    parse_and_validate_request.m
    project_method_constraints.m
    build_graded_gyroid_field.m
    build_solid_volume.m
    mesh_and_cap_volume.m
    export_watertight_stl.m
    hash_geometry_request.m
  metrics/
    compute_five_descriptors.m
    check_resolution_convergence.m
  validation/
    build_gate0_manifest.m
    run_gate0.m
    render_qc_preview.m
  tests/
  configs/
    compiler_config.example.json
    descriptor_definition.json
    gate0_cases.example.csv
```

`run_geometry_compiler(requestPath,responsePath)` is the only production entry point. It is callable without GUI through:

```powershell
F:\MATLAB\R2023a\bin\matlab.exe -batch "run_geometry_compiler('<request.json>','<response.json>')"
```

The dispatch Agent must replace the executable path only through a local launch configuration. Source code and committed example configurations must not contain user-specific paths.

## 5. Meshing and descriptor computation

### 5.1 Finite volume and mesh

The compiler samples the implicit field on a configuration-controlled Cartesian grid. It builds a binary solid volume, pads the exterior as void, extracts the finite specimen boundary with `isosurface`, and writes an STL through a MATLAB-supported triangulation/STL path.

Before STL export, the compiler checks nonempty solid and void, finite coordinates, connected-component count, degenerate triangles, zero-area triangles, boundary-edge count, and minimum-feature guards. A mesh with open boundary edges, self-intersection diagnostics, or failed topology checks returns `valid=false` and preserves diagnostics; it is never silently repaired into a different design.

Resolution convergence uses at least 96, 128, and 160 samples per reference unit length for representative cases. The selected production resolution is frozen only when all five descriptors meet predeclared relative-change tolerances between the two finest levels.

### 5.2 Five derived descriptors

The compiler calculates the following quantities from the generated geometry, never from inverse-model outputs.

| Descriptor | Candidate operational definition |
|---|---|
| `relativeVolume` | solid occupancy volume divided by configured specimen bounding-box volume |
| `relativeArea` | triangulated solid surface area divided by configured reference volume |
| `thickness` | local material thickness based on Euclidean distance transform and material medial locations; report selected summary statistic and units |
| `poreDiameter` | diameter of the largest admissible inscribed sphere in connected void, with connected-component rule recorded |
| `areaMean` | mean open-void cross-sectional area over predeclared axial slices and connectivity rule |

`descriptor_definition.json` fixes resolution, units, summary statistics, slice locations, connectivity, and normalization. The Agent must not tune an individual descriptor after inspecting a test result. If the archived Small metric definition differs, the result is labeled a candidate descriptor implementation until a revised definition passes a new preregistered Gate 0 manifest.

## 6. Error handling and provenance

Every request writes `request.json`, `response.json`, `manifest.json`, a configuration copy, and diagnostics. The manifest records method-projected variables, domain, resolution, solid convention, code version, MATLAB version, available toolboxes, descriptor-definition hash, geometry SHA-256, mesh QC and timestamps.

Failure codes include:

- `INVALID_REQUEST`
- `METHOD_CONSTRAINT`
- `OUT_OF_BOUNDS`
- `EMPTY_SOLID`
- `FULL_SOLID`
- `DISCONNECTED_SOLID`
- `OPEN_MESH`
- `DEGENERATE_MESH`
- `MIN_FEATURE_VIOLATION`
- `DESCRIPTOR_NONFINITE`
- `RESOLUTION_NOT_CONVERGED`
- `MATLAB_RUNTIME_ERROR`

MATLAB Image Processing Toolbox availability is checked at startup. Its absence produces an explicit dependency failure; the Agent must not substitute an unvalidated descriptor approximation without changing the versioned descriptor definition.

## 7. Gate 0 validation protocol

### 7.1 Preregistered cases

Before generation, create a locked manifest of 30 historical cases: 10 valid examples from each method. The manifest stores source-row identifier, class, independent variables, archived five descriptors, source workbook hash, expected units, compiler configuration hash and a case selection seed. The cases must not be selected after seeing compiler results.

### 7.2 Pass criteria

For each descriptor and pooled across descriptors, compare MATLAB-computed values with archived values using relative error. Gate 0 passes only if:

- all three methods generate deterministically;
- all valid case artifacts pass mesh QC;
- median relative descriptor error is at most 2%;
- 95th-percentile relative descriptor error is at most 5%;
- all invalid inputs yield explicit structural failure records;
- the selected solid convention, domain and descriptor-definition hash are frozen.

If any condition fails, the deliverable is a diagnostic report stratified by method, descriptor and resolution. No 225-case Abaqus queue, OOD manifest freeze, or claim of Small reproduction may begin.

## 8. Tests and executable evidence

The MATLAB tests must cover:

1. method projection and profile knot conditions;
2. field determinism and request hash determinism;
3. valid M1/M2/M3 synthetic geometries;
4. invalid parameter, empty/full solid and malformed request paths;
5. STL boundary-edge and degenerate-triangle checks;
6. all descriptor outputs finite and invariant to repeated execution;
7. resolution-convergence control flow;
8. JSON response compatibility with `framework/gc_graphformer/compiler_protocol.schema.json`;
9. headless `matlab -batch` execution under MATLAB R2023;
10. Gate 0 manifest immutability and result provenance.

The dispatch Agent returns the commands, MATLAB release/toolbox inventory, test results, three representative previews, three representative STL artifacts, a Gate 0 manifest, and a concise QA report. Large production voxel volumes and uncurated batch STL collections remain out of Git.

## 9. Explicit non-goals

- Do not run or submit the 225 formal Abaqus analyses.
- Do not change the Paper A GC-GraphFormer, diffusion, or legacy baseline code.
- Do not manufacture historical descriptor values by fitting them directly.
- Do not claim Abaqus compatibility merely because an STL exists; actual Abaqus import/mesh validation is a later gated task.
- Do not call the result a full reproduction until Gate 0 passes.

## 10. Approval record

The user approved the implicit-field, sheet-TPMS, descriptor-recomputation route on 2026-07-28. This specification is the source for the subsequent MATLAB dispatch task and review checklist.
