# M03 Continuous-CSG Finite-Boundary Meshing Design

**Status:** Approved design, implementation not yet started

**Date:** 2026-08-04

**Project:** Paper A / MATLAB graded-Gyroid geometry compiler

**Scope:** M03 finite-boundary construction, surface extraction, strict mesh QC, watertight binary STL, request/response/manifest integration, and the M01/M02 integration work required by that pipeline

## 1. Decision summary

M03 shall use a continuous implicit constructive-solid-geometry (CSG) definition as the authoritative geometry source. The final specimen is the exact set intersection of the graded sheet-Gyroid solid and a hard rectangular box. The finite faces are therefore part of the declared geometry, not holes patched after meshing.

The previously considered padded binary-volume route is retained only as a diagnostic oracle for connectivity, volume-fraction trends, and implementation cross-checks. It shall not define the production STL.

The following decisions are fixed for M03:

- continuous implicit field as the source of truth;
- hard-box clipping with no fillet, shell, taper, smoothing, or automatic repair;
- strict fail-closed validation;
- no substitution of a rejected candidate with a nearby valid design;
- a public JSON compiler entry point and auditable response/manifest artifacts;
- explicit separation between M03 geometry validity and later Abaqus, descriptor, printability, or experiment validity.

## 2. Scientific intent

The compiler must establish a reproducible mapping

```text
(method, c0, c1, c2, w, configuration, resolution)
    -> continuous finite implicit solid
    -> audited triangle mesh
    -> byte-identical binary STL artifact
```

This mapping supports a stronger paper claim than a voxel-to-STL utility because the designed object exists independently of the output mesh. Resolution controls the numerical approximation of one declared continuous object rather than changing the object definition itself.

M03 does not claim that a geometry is mechanically correct, printable, or experimentally validated. It only establishes that the request, continuous solid, extracted mesh, and serialized STL satisfy the M03 geometry contract.

## 3. Authoritative geometry contract

### 3.1 Graded sheet-Gyroid solid

Let `g(X,Y,Z)` be the existing graded Gyroid field evaluated in physical coordinates and let `t(Z)` be the continuous threshold profile produced by the M1/M2/M3 method rules. The sheet field is

```text
f_sheet(X,Y,Z) = abs(g(X,Y,Z)) - t(Z)
```

The unbounded graded sheet solid is the sublevel set `f_sheet <= 0`.

The implementation shall preserve the current M02 formulas and their regression results. M03 may refactor the evaluator so that it accepts arbitrary coordinate arrays, but the existing M02 public behavior on the original grid must remain unchanged.

### 3.2 Hard-box finite boundary

Let the physical specimen bounds be obtained from `geometry_parameters.domain_over_l` multiplied exactly once by `reference_length_mm`. For bounds `[Xmin,Xmax]`, `[Ymin,Ymax]`, and `[Zmin,Zmax]`, define

```text
f_box(X,Y,Z) = max(Xmin-X, X-Xmax,
                       Ymin-Y, Y-Ymax,
                       Zmin-Z, Z-Zmax)
```

`f_box` is negative in the box interior, zero on the box, and positive outside. It is converted to a dimensionless quantity using the configured reference length:

```text
b_box = f_box / reference_length_mm
```

### 3.3 Finite CSG intersection

The unique M03 field is

```text
F(X,Y,Z) = max(f_sheet(X,Y,Z), beta_box * b_box(X,Y,Z))
```

where `beta_box` is a positive, immutable compiler constant recorded in the manifest. The initial contract uses `beta_box = 1.0`.

For every positive `beta_box`, the exact sublevel set is

```text
F <= 0  <=>  f_sheet <= 0 AND f_box <= 0
```

so `beta_box` does not alter the continuous solid. It only fixes the relative numerical scaling used by interpolation near the CSG seam.

The hard `max` operation is intentional. M03 shall not use a smooth maximum, rounded box, transition shell, morphological closing, Laplacian smoothing, or mesh hole filling.

### 3.4 Exterior sampling margin

M03 shall use a cell-centred grid that is staggered relative to the hard-box faces. With physical spacing `h = reference_length_mm / resolution`, an axis with bounds `[Amin,Amax]` is sampled at

```text
Amin-h/2, Amin+h/2, ..., Amax-h/2, Amax+h/2
```

The existing integer-span contract guarantees an integral number of interior cells. No sampling node lies exactly on a box face. This avoids a complete plane of zero-valued CSG samples and brackets every finite face symmetrically, so linear zero-crossing interpolation locates the hard boundary at its declared physical coordinate.

The scalar field is therefore sampled over one half-spacing of exterior margin beyond every box face. This exterior region is evaluated as a continuous scalar field and must satisfy `F > 0` on every outermost sampled plane.

The exterior samples are required so that `isosurface(F, 0)` observes both sides of every finite face. They are not a padded binary occupancy field and do not redefine the solid.

For profile functions whose method domain is limited to the specimen height, the profile input outside the box shall be clamped to the nearest valid endpoint solely to keep the scalar evaluation finite. Because `f_box > 0` outside the box, those extrapolated sheet values cannot become part of the solid. This convention must be tested and recorded.

## 4. Public compiler interface

### 4.1 Entry point

The public API shall be

```matlab
response = run_geometry_compiler(request_path, response_path)
```

The function shall always attempt to write a response JSON to the caller-provided `response_path`, including when the request is invalid. Invalid requests shall not create an STL.

### 4.2 Request schema

The request shall contain exactly the following allowed fields:

```json
{
  "schema_version": "1.0",
  "request_id": "stable-nonempty-text-id",
  "method": "M1",
  "c0": 0.10,
  "c1": 0.10,
  "c2": 0.10,
  "w": 0.0,
  "resolution": 128,
  "output_dir": "absolute-or-explicit-project-relative-path"
}
```

Validation requirements:

- reject missing, additional, incorrectly typed, non-scalar, non-finite, or logically invalid fields;
- require `schema_version == "1.0"`;
- require `method` to be exactly `M1`, `M2`, or `M3`;
- require `resolution` to be one of the configured levels for the selected method;
- interpret `resolution` as the number of physical grid cells per configured reference length, consistent with the existing M02 spacing contract;
- validate dimensions, units, parameter bounds, method-specific active variables, and projection rules through the M01 contract;
- keep both requested and effective/projected parameter values in the response and manifest;
- reject output conflicts rather than silently overwriting a different artifact.

The lower-level M02 field kernel may continue to accept small arbitrary resolutions for unit testing. The public M03 parser is the boundary that enforces production resolution levels.

### 4.3 Response schema

The response shall include at least:

```text
schema_version
request_id
compiler_version
validation_stage = "M03_GEOMETRY_MESH"
valid
failure_code
failure_message
requested_parameters
effective_parameters
geometry_definition = "continuous_sheet_gyroid_intersect_hard_box"
mesh_qc
artifacts
diagnostics
```

`valid=true` means only that the M03 request, continuous geometry, surface mesh, serialization, and artifact integrity checks passed. It must not imply descriptor completion, Abaqus Gate 0, printability, manufacturing, or experimental validation.

Fields reserved for later mechanical or geometric descriptors shall be omitted or explicitly marked `not_computed`; they shall never be populated with placeholders that look like measurements.

## 5. Pipeline architecture

The implementation shall provide or complete these responsibilities:

```text
run_geometry_compiler.m
  parse_and_validate_request.m
  project_method_constraints.m              [existing M01/M02]
  evaluate_continuous_graded_gyroid.m        [new continuous kernel]
  build_finite_csg_field.m                   [new]
  extract_isosurface_mesh.m                  [new]
  validate_surface_mesh.m                    [new]
  detect_mesh_self_intersections.m           [new]
  export_binary_stl.m                        [new]
  verify_binary_stl.m                        [new]
  hash_geometry_request.m                    [new]
  build_geometry_manifest.m                  [new]
```

The exact file boundaries may be adjusted during implementation if MATLAB limitations make a different grouping clearer, but the responsibilities and contracts shall not be weakened.

## 6. Surface extraction

The mesh shall be extracted from the continuous CSG samples using the zero level:

```matlab
[faces, vertices] = isosurface(X, Y, Z, F, 0);
```

The implementation shall:

- keep all vertex coordinates in millimetres;
- reject empty face or vertex arrays;
- never infer physical scale from array indices;
- construct a shared-index surface mesh before serialization;
- preserve the geometry returned by the zero-set extraction;
- permit one global face reversal when needed to establish outward orientation, recording `global_orientation_flip=true`; this changes serialization orientation, not geometry;
- reject locally inconsistent orientation instead of repairing individual faces.

No component deletion, vertex welding, hole filling, decimation, smoothing, remeshing, or local face editing is permitted in M03 production output.

## 7. Strict mesh and topology gate

The in-memory shared-index mesh shall pass every enabled check before STL export.

### 7.1 Basic integrity

- all vertex coordinates are real and finite;
- all faces are triangles with valid integer indices;
- every face has three distinct indices;
- triangle areas exceed a documented numerical tolerance tied to grid spacing;
- edge lengths exceed the configured mesh-quality tolerance;
- duplicate faces are absent.

The minimum triangle edge is a mesh-quality metric only. It shall not be reported as minimum wall thickness or minimum printable feature.

### 7.2 Closed two-manifold topology

- every undirected edge occurs exactly twice;
- boundary-edge count is zero;
- non-manifold-edge count is zero;
- the two uses of each shared edge have opposite directions;
- face-connected component count satisfies the configured solid-component requirement;
- the sampled sublevel-set solid satisfies the corresponding connectivity requirement.

M03 initially requires one connected solid component. Void component count shall be reported but shall not be forced to one because a sheet TPMS may intentionally partition the void.

### 7.3 Self-intersection

Self-intersection checking is mandatory when the configuration requires it. The implementation shall use a deterministic broad phase based on triangle axis-aligned bounding boxes or spatial bins, followed by a tested triangle-triangle narrow-phase predicate. Adjacent faces sharing an edge or vertex shall be excluded only from the invalid non-adjacent-intersection test; their shared-edge topology is checked separately.

If the runtime cannot execute the configured self-intersection check, the compiler shall fail closed with `SELF_INTERSECTION_CHECK_UNAVAILABLE`. It shall not mark the mesh valid with an `unknown` status.

### 7.4 Failure codes

At minimum, M03 shall distinguish:

```text
INVALID_REQUEST
METHOD_CONSTRAINT
OUT_OF_BOUNDS
OUTPUT_CONFLICT
NONFINITE_FIELD
EMPTY_SOLID
FULL_SOLID
DISCONNECTED_SOLID
EMPTY_MESH
DEGENERATE_MESH
OPEN_MESH
NONMANIFOLD_MESH
INCONSISTENT_ORIENTATION
SELF_INTERSECTION
SELF_INTERSECTION_CHECK_UNAVAILABLE
STL_SERIALIZATION_ERROR
STL_VERIFICATION_ERROR
INTERNAL_ERROR
```

## 8. Binary STL serialization and artifact integrity

Only a mesh that passes the in-memory gate may be serialized.

The exporter shall:

- write binary STL in millimetres;
- write to a request-scoped temporary artifact first;
- reopen and verify the binary header, declared triangle count, exact byte length, finite coordinates, and triangle count agreement;
- atomically publish the verified artifact to its final name;
- compute SHA-256 from the final bytes;
- never publish a temporary or failed STL under the final artifact name.

Because STL stores triangles independently, topological water-tightness is established on the shared-index in-memory mesh. The round-trip verifier establishes that serialization preserved the same triangle soup; it shall not weld serialized vertices and then claim that welding repaired topology.

## 9. Determinism and manifest

The manifest shall include:

- raw request-file SHA-256;
- canonical request-semantic hash using a fixed field order and normalized numeric representation while excluding `request_id` and `output_dir`;
- canonical geometry-identity hash over the effective parameters, physical domain, resolution, continuous-CSG constants, compiler version, and immutable configuration hashes;
- compiler version and geometry-definition identifier;
- hashes of compiler configuration, parameter-domain manifest, and descriptor definition;
- requested and effective parameters;
- physical dimensions and units;
- resolution, physical grid spacing, exterior margin, isosurface level, and `beta_box`;
- all mesh-QC metrics and pass/fail results;
- global orientation decision;
- STL path, byte length, triangle count, and SHA-256;
- explicit validation stage and deferred validation stages.

`request_id`, `output_dir`, and timestamps are execution/provenance data. They shall not participate in the geometry-identity hash or alter STL bytes.

Identical geometry identities must produce identical effective parameters, mesh topology, STL bytes, and artifact hashes on the supported MATLAB runtime.

## 10. Resolution-convergence evidence

M03 distinguishes routine generation from publication evidence.

### 10.1 Every generated candidate

Every candidate receives full mesh/topology/STL QC at its requested, method-allowed resolution.

### 10.2 Abaqus, printing, and paper-validation candidates

Candidates selected for Abaqus, printing, or reported validation must be evaluated at consecutive allowed resolutions:

- M1/M2: 96, 128, and 160 as applicable;
- M3: 96, 128, 160, and 192 as applicable.

The convergence record shall include:

- topology and component-count stability;
- solid volume and volume-fraction change;
- surface-area change;
- triangle-count and grid-spacing metadata;
- a deterministic bidirectional surface-distance proxy;
- all mesh-QC results at each level.

Numerical convergence thresholds shall be configuration fields justified by a later calibration study. M03 shall implement the metrics and evidence format without inventing universal scientific tolerances in code.

## 11. Relationship to the padded-volume route

The existing binary `solid_volume` is retained for:

- early empty/full screening;
- 26-connectivity diagnostics;
- volume-fraction cross-checks;
- regression tests against the existing M02 kernel;
- diagnosis of continuous-field or CSG implementation errors.

It shall not be used to generate the production STL, and no binary-route mesh shall automatically replace a failed continuous-CSG mesh.

## 12. Deferred work

The following are explicitly outside M03:

- final five-descriptor computation and calibration;
- exact minimum wall-thickness and pore-size characterization;
- printability certification;
- Abaqus model generation and Gate 0;
- constitutive-law calibration;
- 3D printing and compression experiments;
- any claim that M03-valid geometries are mechanically valid.

These stages may consume M03 artifacts only when their own gates are implemented and passed.

## 13. Test and acceptance plan

M03 is accepted only when all existing M01/M02 tests and the new tests pass from both the project directory and an unrelated temporary working directory.

Required new coverage includes:

1. **CSG truth table:** sampled points satisfy `F<=0` exactly when both component fields are non-positive.
2. **Hard-box closure:** an analytic box-only fixture extracts a closed two-manifold mesh.
3. **Exterior margin:** all outermost sampled planes are positive and the zero surface is contained inside the sampled domain.
4. **M1/M2/M3 smoke cases:** at least one archived-valid parameter set per method produces deterministic continuous fields and audited meshes.
5. **Invalid solids:** empty, full, non-finite, and disconnected fixtures return the correct failure code.
6. **Invalid meshes:** open, non-manifold, degenerate, duplicate-face, locally inconsistent, and self-intersecting fixtures are rejected.
7. **STL round trip:** binary length, face count, coordinates, and SHA-256 are verified.
8. **Determinism:** two isolated executions of the same semantic request produce identical effective parameters and STL bytes.
9. **Output conflict:** a different request cannot overwrite an existing artifact with the same target identity.
10. **Backward compatibility:** existing M01/M02 tests remain green, including current threshold, projection, gamma, field-value, volume-fraction, finite-provenance, and temporary-directory checks.
11. **Code quality:** MATLAB Code Analyzer reports no new actionable issues in changed production and test files.

## 14. Acceptance boundary

M03 is complete when the repository contains a documented, deterministic, fail-closed continuous-CSG compiler path that can accept a valid M1/M2/M3 JSON request and produce a verified watertight binary STL plus response and manifest, while rejecting every known invalid request, solid, mesh, or serialization fixture without automatic geometry modification.

Passing M03 authorizes progression to descriptor computation and Abaqus preprocessing. It does not authorize any scientific performance claim by itself.
