# SWOMPS <-> Abaqus validation plan

Selected **10 samples x 4 conditions = 40 curves** to reproduce in
high-fidelity FEA and overlay against the SWOMPS bar-and-hinge probe curves.

## Why these samples
  sample_id            select_reason              label
miura_00026          shape=snap_back          snap_back
miura_00020            shape=plateau            plateau
miura_00032 shape=monotone_softening monotone_softening
miura_00019 shape=monotone_hardening monotone_hardening
miura_00044   extreme:softest crease monotone_softening
miura_00029   extreme:stiffest panel            plateau
miura_00023   extreme:thinnest panel          snap_back
miura_00011 extreme:narrowest crease          snap_back
miura_00002     extreme:most cells m          snap_back
miura_00006     extreme:most cells n monotone_softening

## Abaqus setup (match SWOMPS as closely as possible)
- Geometry: same Miura sheet, L=0.2 m, gamma=70 deg, (m,n) per row, held at `deployment` then loaded.
  Export the SAME deployed mesh SWOMPS uses if possible (node coords), else rebuild from (a,b,gamma,Ext).
- Material: **linear-elastic isotropic**, E = `panelE` (panels) / `creaseE` (creases), nu = 0.3.
  (Shell/solid panels + reduced-stiffness crease zones, or a validated bar-and-hinge-equivalent shell model.)
- BC: clamp the min-x edge (all 6 DOF); drive the max-x edge with **displacement control** along the load axis
  (bending: -z, axial: +x). Use a static, geometrically-nonlinear step (NLGEOM=ON; Riks/arc-length if snap-back).
- Output: reaction force at the loaded edge vs its displacement -> force-displacement curve.

## What to compare (acceptance)
For each curve, overlay SWOMPS vs Abaqus and report:
- NRMSE of force vs displacement (target: SWOMPS within ~15-25% of FEA in the regime of interest);
- **qualitative agreement of features**: does Abaqus ALSO show the snap-through / plateau / peak that SWOMPS predicts? (most important — if the snap is a bar-and-hinge artifact, this is where it shows.)
- limit-point load and displacement (for snap cases).

> Decision: if SWOMPS reproduces the FEA *shape features* (even with magnitude offset), the fast SWOMPS
> dataset is defensible (cite the offset, validate final designs in FEA). If the snap features are artifacts,
> fall back to FEA-only data on a smaller design space, or pivot structure family.
