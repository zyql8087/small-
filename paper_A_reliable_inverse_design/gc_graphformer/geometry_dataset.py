"""Deterministic, provenance-rich geometry-only dataset generation and shards."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePath
from typing import Iterable

import numpy as np

from .compiler import GeometryCompiler, finite_difference_sensitivities, validate_compile_result
from .contracts import METHODS, PARAMETER_COUNT, method_active_mask, profile_id, project_parameters


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _record_payload(record: dict) -> dict:
    return {key: value for key, value in record.items() if key != "record_sha256"}


def _record_hash(record: dict) -> str:
    return sha256_text(canonical_json(_record_payload(record)))


def _sample_parameters(rng: np.random.Generator, method: str) -> np.ndarray:
    values = np.empty(PARAMETER_COUNT, dtype=np.float64)
    values[:3] = rng.uniform(0.03, 0.20, size=3)
    values[3] = 0.0 if method == "M1" else rng.uniform(2.0 + 1e-5, 8.0 - 1e-5)
    return project_parameters(method, values)


class GeometryOnlyGenerator:
    """Generate compiler-derived records without mechanical labels or Abaqus."""

    def __init__(self, compiler: GeometryCompiler, *, seed: int, profile: str = "physical_m04") -> None:
        profile_id(profile)
        if getattr(compiler, "profile", None) != profile:
            raise ValueError("generator profile must match the injected compiler profile")
        self.compiler = compiler
        self.seed = int(seed)
        self.profile = profile

    def generate(self, count: int) -> list[dict]:
        if count < 0:
            raise ValueError("count must be non-negative")
        rng = np.random.Generator(np.random.PCG64(self.seed))
        records: list[dict] = []
        for index in range(int(count)):
            method = METHODS[int(rng.integers(0, len(METHODS)))]
            parameters = _sample_parameters(rng, method)
            result = validate_compile_result(
                self.compiler.compile(method, parameters, sample_index=index),
                expected_profile=self.profile,
            )
            sensitivity, valid, confidence = finite_difference_sensitivities(
                self.compiler,
                method,
                result.parameters,
                sample_index=index,
            )
            record = {
                "record_index": index,
                "record_type": "geometry_only",
                "dataset_role": "original_auxiliary_geometry_dataset",
                "mechanical_labels": False,
                "abaqus_executed": False,
                "solver_ready": False,
                "descriptor_profile": self.profile,
                "method": result.method,
                "parameters": [float(value) for value in result.parameters],
                "descriptors": [float(value) for value in result.descriptors],
                "sensitivities": sensitivity.tolist(),
                "sensitivity_validity": valid.tolist(),
                "sensitivity_confidence": confidence.tolist(),
                "feasibility": result.feasibility,
                "compiler_version": result.compiler_version,
                "compiler_mode": result.compiler_mode,
                "descriptor_definition_sha256": result.descriptor_definition_sha256,
                "geometry_identity": result.geometry_identity,
                "artifact_hashes": result.artifact_hashes,
            }
            record["record_sha256"] = _record_hash(record)
            records.append(record)
        return records


def _validate_records(records: list[dict], profile: str) -> tuple[list[dict], dict[str, str]]:
    profile_id(profile)
    if not records:
        raise ValueError("a geometry-only shard manifest requires at least one record")
    normalized: list[dict] = []
    for expected_index, record in enumerate(records):
        if record.get("record_index") != expected_index:
            raise ValueError("records must be ordered and indexed from zero")
        if record.get("descriptor_profile") != profile:
            raise ValueError("legacy_small and physical_m04 records cannot share a dataset")
        if record.get("dataset_role") != "original_auxiliary_geometry_dataset":
            raise ValueError("geometry-only records must carry the auxiliary-dataset role")
        if record.get("mechanical_labels") is not False or record.get("abaqus_executed") is not False:
            raise ValueError("geometry-only records cannot carry mechanics or Abaqus claims")
        if record.get("solver_ready") is not False:
            raise ValueError("geometry-only records must remain solver_ready=false")
        expected_hash = _record_hash(record)
        if record.get("record_sha256") != expected_hash:
            raise ValueError(f"record {expected_index} hash mismatch")
        normalized.append(json.loads(canonical_json(record)))
    compiler_keys = ("compiler_version", "compiler_mode", "descriptor_definition_sha256")
    compiler_info = {key: str(normalized[0][key]) for key in compiler_keys}
    if any({key: str(record[key]) for key in compiler_keys} != compiler_info for record in normalized):
        raise ValueError("all records in one shard set must share compiler provenance")
    return normalized, compiler_info


def _write_atomic_bytes(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise FileExistsError(f"temporary output already exists: {temporary}")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def write_dataset(
    output_dir: str | Path,
    records: Iterable[dict],
    *,
    seed: int,
    profile: str,
    shard_size: int = 1024,
) -> dict:
    """Write immutable compressed JSON-in-NPZ shards and a hash-verified manifest."""

    if shard_size <= 0:
        raise ValueError("shard_size must be positive")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"refusing to overwrite existing dataset manifest: {manifest_path}")
    normalized, compiler_info = _validate_records(list(records), profile)
    shard_entries = []
    for shard_index, start in enumerate(range(0, len(normalized), int(shard_size))):
        shard_records = normalized[start : start + int(shard_size)]
        shard_name = f"shard-{shard_index:04d}.npz"
        shard_path = output / shard_name
        if shard_path.exists():
            raise FileExistsError(f"refusing to overwrite existing shard: {shard_path}")
        temporary = output / f".{shard_name}.tmp.npz"
        np.savez_compressed(temporary, records=np.asarray([canonical_json(record) for record in shard_records], dtype=np.str_))
        os.replace(temporary, shard_path)
        shard_entries.append(
            {
                "path": shard_name,
                "sha256": hashlib.sha256(shard_path.read_bytes()).hexdigest(),
                "record_count": len(shard_records),
                "first_record_index": start,
            }
        )
    config = {
        "seed": int(seed),
        "profile": profile,
        "shard_size": int(shard_size),
        "methods": list(METHODS),
        "finite_difference": {"scheme": "central_with_one_sided_fallback", "steps": [1e-3, 1e-3, 1e-3, 1e-2]},
    }
    manifest = {
        "schema_version": "geometry-only-1.0",
        "dataset_role": "original_auxiliary_geometry_dataset",
        "mechanical_labels": False,
        "abaqus_executed": False,
        "solver_ready": False,
        "compiler_mode": compiler_info["compiler_mode"],
        "profile": profile,
        "seed": int(seed),
        "config": config,
        "config_sha256": sha256_text(canonical_json(config)),
        "compiler": compiler_info,
        "record_count": len(normalized),
        "record_hashes": [record["record_sha256"] for record in normalized],
        "shards": shard_entries,
    }
    manifest["manifest_sha256"] = sha256_text(canonical_json(manifest))
    _write_atomic_bytes(manifest_path, (canonical_json(manifest) + "\n").encode("utf-8"))
    return manifest


def _safe_relative_path(value: str) -> Path:
    candidate = PurePath(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("manifest shard paths must be relative and cannot escape the dataset directory")
    return Path(candidate)


def load_dataset(output_dir: str | Path) -> list[dict]:
    """Verify and recover a shard set, refusing profile mixing and tampering."""

    output = Path(output_dir)
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_hash = manifest.get("manifest_sha256")
    unsigned_manifest = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if manifest_hash != sha256_text(canonical_json(unsigned_manifest)):
        raise ValueError("manifest hash mismatch")
    profile = manifest.get("profile")
    profile_id(profile)
    if manifest.get("dataset_role") != "original_auxiliary_geometry_dataset":
        raise ValueError("unexpected dataset role")
    if manifest.get("mechanical_labels") is not False or manifest.get("abaqus_executed") is not False:
        raise ValueError("dataset manifest contains forbidden mechanics/Abaqus claims")
    records: list[dict] = []
    for shard in manifest.get("shards", []):
        relative = _safe_relative_path(str(shard["path"]))
        shard_path = output / relative
        if not shard_path.is_file():
            raise FileNotFoundError(shard_path)
        digest = hashlib.sha256(shard_path.read_bytes()).hexdigest()
        if digest != shard["sha256"]:
            raise ValueError(f"shard hash mismatch: {relative}")
        with np.load(shard_path, allow_pickle=False) as payload:
            if "records" not in payload:
                raise ValueError(f"missing records array in {relative}")
            shard_records = [json.loads(value) for value in payload["records"].tolist()]
        if len(shard_records) != shard["record_count"]:
            raise ValueError(f"shard record count mismatch: {relative}")
        records.extend(shard_records)
    if len(records) != manifest.get("record_count"):
        raise ValueError("dataset record count mismatch")
    normalized, compiler_info = _validate_records(records, profile)
    if [record["record_sha256"] for record in normalized] != manifest["record_hashes"]:
        raise ValueError("manifest record hash list mismatch")
    if compiler_info != {key: str(value) for key, value in manifest["compiler"].items()}:
        raise ValueError("manifest compiler provenance mismatch")
    return normalized

