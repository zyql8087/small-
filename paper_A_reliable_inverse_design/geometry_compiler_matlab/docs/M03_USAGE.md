# M03 continuous-CSG geometry compiler

M03 converts one validated graded-Gyroid request into a continuous hard-box
CSG surface, applies fail-closed topology and self-intersection gates, and
publishes a verified binary STL plus JSON provenance. It does not calculate
the five geometry descriptors or run Abaqus.

## Production request

The following resolution-96 M1 parameters are an archived Small record from
`test-4canshu.xlsx`, sheet `class1`, row 1198. They are also the deterministic
production integration fixture.

```json
{
  "schema_version": "1.0",
  "request_id": "m03-m1-example-001",
  "method": "M1",
  "c0": 0.0700794,
  "c1": 0.1246504,
  "c2": 0.0693255,
  "w": 0,
  "resolution": 96,
  "output_dir": "outputs"
}
```

`output_dir` is resolved beneath the directory containing the request JSON.
It cannot escape that directory. Existing response, manifest, or STL paths
are never overwritten.

From PowerShell, replace the two example JSON paths with absolute paths:

```powershell
$compilerDir = (Resolve-Path 'paper_A_reliable_inverse_design\geometry_compiler_matlab').Path.Replace('\','/')
$requestPath = 'C:/absolute/job/request.json'
$responsePath = 'C:/absolute/job/response.json'
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "addpath('$compilerDir'); response=run_geometry_compiler('$requestPath','$responsePath'); disp(response);"
```

The equivalent MATLAB call is:

```matlab
addpath('C:/absolute/path/to/geometry_compiler_matlab');
response = run_geometry_compiler( ...
    'C:/absolute/job/request.json', ...
    'C:/absolute/job/response.json');
```

## Outputs and identity

A successful request writes:

- the caller-selected `response.json`;
- `outputs/geometry_<geometry_identity_sha256>.stl`;
- `outputs/geometry_<geometry_identity_sha256>.manifest.json`.

The geometry identity includes the compiler version, effective parameters,
physical domain, resolution, CSG/isosurface constants, and immutable config
hashes. It excludes `request_id`, `output_dir`, timestamps, and machine-local
temporary paths. Two isolated executions of the same semantic geometry must
therefore have identical geometry identities and byte-identical STL SHA-256
values, even when their request IDs differ.

The manifest records the half-step grid, physical spacing, 26-connected
sampled-solid component count, surface topology metrics, float32-degenerate
facet count, self-intersection result, STL byte length, triangle count, and
artifact SHA-256. Binary STL vertices are float32; a face that collapses only
after float32 conversion fails before publication as `DEGENERATE_MESH`.

## Fail-closed behavior

Malformed or out-of-domain requests, method-constraint violations, empty or
full solids, open/non-manifold/disconnected/degenerate meshes, inconsistent
orientation, duplicate faces, self-intersections, serialization failures, and
artifact-verification failures produce `valid=false` with a stable
`failure_code`. Known codes include:

```text
INVALID_REQUEST
METHOD_CONSTRAINT
OUT_OF_BOUNDS
EMPTY_SOLID
FULL_SOLID
NONFINITE_FIELD
EMPTY_MESH
DISCONNECTED_SOLID
DEGENERATE_MESH
OPEN_MESH
NONMANIFOLD_MESH
INCONSISTENT_ORIENTATION
DUPLICATE_FACE
SELF_INTERSECTION
SELF_INTERSECTION_CHECK_UNAVAILABLE
STL_SERIALIZATION_ERROR
STL_VERIFICATION_ERROR
OUTPUT_CONFLICT
INTERNAL_ERROR
```

The failure response contains no stack trace. Request-owned STL and manifest
files created during a failed run are removed; unrelated files and output
directories are not recursively cleaned.

## Convergence evidence boundary

`compare_mesh_convergence` reports deterministic bidirectional maximum/RMS
sampled-vertex distance proxies, relative surface-area and volume changes,
and face-component stability. It does not embed a universal publication
tolerance.

The unit suite uses internal levels 12 and 16 only as inexpensive M1/M2/M3
smoke tests. These are not publication convergence evidence. Production
resolution studies must use the configured levels:

- M1: 96, 128, 160;
- M2: 96, 128, 160;
- M3: 96, 128, 160, 192.

Run the complete suite with:

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:/absolute/path/to/geometry_compiler_matlab'); run_tests;"
```

M03 valid=true confirms request, continuous geometry, surface topology,
self-intersection, STL serialization, and artifact integrity only. It does
not confirm descriptor calibration, Abaqus Gate 0, printability, or
experimental performance.
