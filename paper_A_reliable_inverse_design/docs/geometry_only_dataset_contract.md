# Geometry-only auxiliary dataset contract

This package defines a reproducible auxiliary geometry dataset for Paper A. It
is not a high-fidelity mechanical dataset and it contains no stress-strain
labels, Abaqus outputs, volume meshes, solver submissions, or print evidence.

## Compiler boundary

`GeometryOnlyGenerator` accepts a callback implementing the validated M03/M04
contract. The callback must return one explicitly named descriptor profile,
projected `[c0,c1,c2,w]` parameters, finite `physical_m04` descriptors,
feasibility flags, compiler/version hashes, and `solver_ready=false`.

`SyntheticM04Compiler` is only a deterministic smoke fixture. Its records carry
`compiler_mode: synthetic_smoke` and must not be used as mechanics evidence.
Production geometry generation must inject a MATLAB M03/M04 callback; this
Python package never starts Abaqus.

## Profile separation

`physical_m04` and `legacy_small` are different dataset profiles. A manifest,
shard set, or loader result containing both profiles is rejected. The legacy
profile remains compatibility data for Small alignment; it is not relabelled
as the physical profile.

## Storage and recovery

Each dataset directory contains a canonical `manifest.json` and compressed
`shard-XXXX.npz` files. NPZ shards store canonical JSON records rather than
pickled Python objects. The manifest records the seed, config hash, compiler
version/mode, descriptor-definition hash, record hashes, shard hashes, and its
own SHA-256. Loading rechecks all of these before returning records.

The committed repository contains only the generator and tests. Formal
10k/50k/100k datasets, checkpoints, STL files, and caches remain external to
Git until the storage budget and acceptance gates are approved.

