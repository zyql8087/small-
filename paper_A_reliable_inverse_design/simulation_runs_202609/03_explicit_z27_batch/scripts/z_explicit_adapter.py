# -*- coding: utf-8 -*-
"""M08 z-explicit INP adapter.

Transforms the implicit x-drive Standard solver INP (gen_build_model.py
output + M05_ZDRIVE/M05_ZFIX part-set patch, drive u1=-10.0 UNPATCHED)
into the explicit z-compression INP, per plan
docs/superpowers/plans/2026-09-25-m08-explicit-z27.md section 0-C.

Construction (structural assertion, plan section 3.1):
  - The file is split at the separator line immediately preceding the
    unique "** STEP: Step-1" comment. The PREFIX (nodes, elements,
    part/assembly node sets, section, MATERIALS) is copied BYTE-FOR-BYTE;
    a sha256 of the prefix is asserted equal between input and output.
  - The TAIL (step / boundary conditions / output requests / *End Step) is
    fully REGENERATED from the constants below; no other line is ever
    emitted. Allowed changed card classes: step block, amplitude, BC block,
    output requests (plan 0-C). Material/geometry/set cards cannot be
    altered by construction.
  - Assembly set existence asserted before writing.

Author-anchored values (frozen): drive U3 = -10.0, six-face BC structure
(drive -10 / opposite 0 / four side faces normal-0), 20 output intervals,
material block untouched.

Explicit-port values (plan 0-C): *Dynamic, Explicit T=0.1 s;
*Fixed Mass Scaling type=ELEMENT BY ELEMENT dt=1e-06 (per-element scaling
touches only elements below the dt target, per plan "缩放仅作用于小元素";
TYPE=BELOW MIN (only elements below dt target are scaled, per plan); DT+TYPE must appear together per Abaqus keyword rules - both found by datacheck);
amplitude SMOOTH STEP 0->1 over 0.1 s. inc parameter is NOT allowed on
*Step for Explicit (datacheck finding) - omitted. History output uses
time interval=0.005 s = T/20 because Explicit forbids number interval on
*Output, history (datacheck finding); equivalent 20-interval semantics.
double precision & resources are solver-command options, not INP cards.

Usage: python z_explicit_adapter.py <implicit_inp> <explicit_inp>
"""
import hashlib
import re
import sys

STEP_CARD = b"*Step, name=Step-1, nlgeom=YES"
PROCEDURE = [b"*Dynamic, Explicit", b", 0.1",
             b"*Fixed Mass Scaling, type=BELOW MIN, dt=1e-06"]
AMPLITUDE = [b"*Amplitude, name=A_SMOOTH_DRIVE, definition=SMOOTH STEP",
             b"0., 0., 0.1, 1."]
BC_BLOCK = [
    b"** Name: BC-z-drive Type: Displacement/Rotation",
    b"*Boundary, amplitude=A_SMOOTH_DRIVE",
    b"A_ZPOS, 3, 3, -10.0",
    b"** Name: BC-z-fix Type: Displacement/Rotation",
    b"*Boundary",
    b"A_ZNEG, 3, 3",
    b"** Name: BC-x-neg-side Type: Displacement/Rotation",
    b"*Boundary",
    b"A_FIX, 1, 1",
    b"** Name: BC-x-pos-side Type: Displacement/Rotation",
    b"*Boundary",
    b"A_DRIVE, 1, 1",
    b"** Name: BC-y-neg Type: Displacement/Rotation",
    b"*Boundary",
    b"A_YNEG, 2, 2",
    b"** Name: BC-y-pos Type: Displacement/Rotation",
    b"*Boundary",
    b"A_YPOS, 2, 2",
]
OUTPUT_BLOCK = [
    b"**",
    b"** FIELD OUTPUT: F-Output-1",
    b"**",
    b"*Output, field, number interval=20",
    b"*Node Output",
    b"U",
    b"*Element Output, directions=YES",
    b"S, SENER",
    b"**",
    b"** HISTORY OUTPUT: H-Output-1",
    b"**",
    b"*Output, history, time interval=0.005",
    b"*Energy Output",
    b"ALLIE, ALLKE, ALLAE, ALLPD, ETOTAL",
    b"**",
    b"** HISTORY OUTPUT: H-Drive",
    b"**",
    b"*Node Output, nset=A_ZPOS",
    b"RF3, U3",
    b"*End Step",
]

REQUIRED_NSETS = (b"A_DRIVE", b"A_FIX", b"A_YNEG", b"A_YPOS",
                  b"A_ZNEG", b"A_ZPOS", b"M05_ZDRIVE", b"M05_ZFIX")


def split_prefix(inp_bytes):
    """Return (prefix_bytes, sep_line_with_eol) where prefix ends just
    before the separator line that precedes the unique ** STEP: Step-1."""
    lines = inp_bytes.splitlines(keepends=True)
    step_idx = [i for i, ln in enumerate(lines)
                if ln.strip() == b"** STEP: Step-1"]
    assert len(step_idx) == 1, f"expected 1 '** STEP: Step-1', got {step_idx}"
    si = step_idx[0]
    # walk back over the '**' comment line to the '----' separator
    assert lines[si - 1].strip() == b"**", lines[si - 1]
    sep = si - 2
    assert lines[sep].startswith(b"** ---"), lines[sep]
    return b"".join(lines[:sep]), lines[sep], lines[sep:], si


def main():
    src, dst = sys.argv[1], sys.argv[2]
    raw = open(src, "rb").read()
    lines = raw.splitlines(keepends=True)
    step_idx = [i for i, ln in enumerate(lines)
                if ln.strip() == b"** STEP: Step-1"]
    assert len(step_idx) == 1, step_idx
    si = step_idx[0]
    assert lines[si - 1].strip() == b"**"
    sep = si - 2
    assert lines[sep].startswith(b"** ---")
    prefix = b"".join(lines[:sep])
    sep_line = lines[sep]

    # --- set existence (assembly + part nsets) ---
    for name in REQUIRED_NSETS:
        pat = re.compile(rb"^\*Nset, nset=" + re.escape(name) + rb"\b", re.M)
        assert pat.search(raw), f"required nset {name!r} not found in {src}"

    # --- sanity on the implicit tail we are replacing ---
    tail = b"".join(lines[sep:])
    assert tail.count(b"*Boundary") == 6, tail.count(b"*Boundary")
    assert b"*Static" in tail and b"*Dynamic" not in tail
    # CAE may trim -10.0 -> -10. on the data line; accept both spellings
    assert re.search(rb"A_DRIVE, 1, 1, -10\.0?", tail), \
        "implicit drive -10.0 expected (must NOT be the M06 -9.6 patch)"

    # --- material byte identity is implied by prefix copy; assert marker ---
    assert b"*Hyperelastic, n=2, test data input, poisson=0.47" in prefix
    assert b"*Density" in prefix and b"*Plastic" in prefix

    eol = b"\r\n" if b"\r\n" in raw else b"\n"

    out_lines = [prefix + sep_line]
    out_lines += [ln + eol for ln in
                  [b"**", b"** STEP: Step-1 (M08 explicit z, plan 0-C)", b"**"]]
    out_lines.append(STEP_CARD + eol)
    out_lines += [ln + eol for ln in PROCEDURE]
    out_lines += [b"**" + eol, b"** AMPLITUDE" + eol, b"**" + eol]
    out_lines += [ln + eol for ln in AMPLITUDE]
    out_lines += [b"**" + eol, b"** BOUNDARY CONDITIONS" + eol, b"**" + eol]
    out_lines += [ln + eol for ln in BC_BLOCK]
    out_lines += [b"**" + eol, b"** OUTPUT REQUESTS" + eol, b"**" + eol]
    out_lines += [ln + eol for ln in OUTPUT_BLOCK]
    out_bytes = b"".join(out_lines)

    # --- post-assertions on the output ---
    assert out_bytes.count(b"*Boundary") == 6
    assert out_bytes.count(b"*Dynamic, Explicit") == 1
    assert b"*Static" not in out_bytes
    assert b"*Restart" not in out_bytes
    assert out_bytes.count(b"*Amplitude") == 1
    assert b"ALLSE" not in out_bytes
    assert out_bytes.count(b"number interval=20") == 1
    assert out_bytes.count(b"time interval=0.005") == 1
    assert b"type=BELOW MIN, dt=1e-06" in out_bytes

    # --- prefix byte identity ---
    out_lines2 = out_bytes.splitlines(keepends=True)
    step_idx2 = [i for i, ln in enumerate(out_lines2)
                 if ln.strip() == b"** STEP: Step-1 (M08 explicit z, plan 0-C)"]
    assert len(step_idx2) == 1
    si2 = step_idx2[0]
    sep2 = si2 - 2
    assert out_lines2[sep2].startswith(b"** ---")
    assert out_lines2[sep2 + 1].strip() == b"**"
    out_prefix = b"".join(out_lines2[:sep2])
    h_in = hashlib.sha256(prefix).hexdigest()
    h_out = hashlib.sha256(out_prefix).hexdigest()
    assert h_in == h_out, "PREFIX NOT BYTE-IDENTICAL - aborting"

    with open(dst, "wb") as f:
        f.write(out_bytes)
    print(f"ADAPT_OK {dst}")
    print(f"  prefix_bytes={len(prefix)} sha256={h_in[:16]} (material+mesh+sets byte-identical)")
    print(f"  tail regenerated: {len(lines) - sep} -> {len(out_lines2) - sep2} lines")
    print(f"  total {len(raw)} -> {len(out_bytes)} bytes")


if __name__ == "__main__":
    main()
