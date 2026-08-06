"""Read-only compiler callback boundary used by geometry-only generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .contracts import (
    DESCRIPTOR_COUNT,
    METHOD_IDS,
    PARAMETER_COUNT,
    PROFILES,
    method_active_mask,
    project_parameters,
    profile_id,
    validate_descriptors,
    validate_parameters,
)


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GeometryCompileResult:
    method: str
    parameters: np.ndarray
    descriptor_profile: str
    descriptors: np.ndarray
    feasibility: dict[str, bool]
    compiler_version: str
    descriptor_definition_sha256: str
    geometry_identity: str
    artifact_hashes: dict[str, str]
    compiler_mode: str
    solver_ready: bool = False
    abaqus_executed: bool = False


class GeometryCompiler(Protocol):
    profile: str
    compiler_version: str
    compiler_mode: str

    def compile(self, method: str, parameters: np.ndarray | list[float], *, sample_index: int = 0) -> GeometryCompileResult:
        ...


def validate_compile_result(result: GeometryCompileResult, *, expected_profile: str) -> GeometryCompileResult:
    """Validate a callback result before it can become a dataset record."""

    profile_id(expected_profile)
    if result.descriptor_profile != expected_profile:
        raise ValueError(
            f"compiler returned profile {result.descriptor_profile!r}, expected {expected_profile!r}"
        )
    if result.method not in METHOD_IDS:
        raise ValueError(f"unknown compiler method {result.method!r}")
    parameters = np.asarray(result.parameters, dtype=np.float64)
    if parameters.shape != (PARAMETER_COUNT,) or not np.isfinite(parameters).all():
        raise ValueError("compiler parameters must be a finite padded vector of length four")
    expected_parameters = project_parameters(result.method, parameters)
    validate_parameters(result.method, expected_parameters)
    if not np.allclose(parameters, expected_parameters, atol=1e-8, rtol=0.0):
        raise ValueError("compiler parameters are not in the method-projected padded form")
    descriptors = validate_descriptors(result.descriptors)
    if not isinstance(result.feasibility, dict) or not result.feasibility:
        raise ValueError("compiler must provide non-empty feasibility flags")
    if not result.compiler_version or not result.compiler_mode:
        raise ValueError("compiler provenance must include version and mode")
    if len(result.descriptor_definition_sha256) != 64:
        raise ValueError("descriptor definition provenance must be a SHA-256 digest")
    if len(result.geometry_identity) != 64:
        raise ValueError("geometry identity must be a SHA-256 digest")
    if any(len(value) != 64 for value in result.artifact_hashes.values()):
        raise ValueError("compiler artifact hashes must be SHA-256 digests")
    if result.solver_ready or result.abaqus_executed:
        raise ValueError("geometry-only generation rejects solver-ready or executed compiler results")
    return GeometryCompileResult(
        method=result.method,
        parameters=expected_parameters.copy(),
        descriptor_profile=result.descriptor_profile,
        descriptors=descriptors.copy(),
        feasibility={str(key): bool(value) for key, value in result.feasibility.items()},
        compiler_version=str(result.compiler_version),
        descriptor_definition_sha256=str(result.descriptor_definition_sha256),
        geometry_identity=str(result.geometry_identity),
        artifact_hashes={str(key): str(value) for key, value in result.artifact_hashes.items()},
        compiler_mode=str(result.compiler_mode),
        solver_ready=False,
        abaqus_executed=False,
    )


class SyntheticM04Compiler:
    """Deterministic analytic smoke compiler, never a mechanics-data substitute.

    Production generation receives a callback to the validated MATLAB M03/M04
    compiler. This class exists only to exercise the data and model contracts
    without MATLAB or Abaqus and is labelled in every returned record.
    """

    compiler_version = "synthetic-m04-smoke-0.1.0"
    compiler_mode = "synthetic_smoke"

    def __init__(self, *, profile: str = "physical_m04", reference_length_mm: float = 1.0) -> None:
        profile_id(profile)
        if not np.isfinite(reference_length_mm) or reference_length_mm <= 0.0:
            raise ValueError("reference_length_mm must be finite and positive")
        self.profile = profile
        self.reference_length_mm = float(reference_length_mm)
        self.descriptor_definition_sha256 = hashlib.sha256(
            f"m04-dual-profile-v2:{profile}".encode("utf-8")
        ).hexdigest()

    def compile(self, method: str, parameters: np.ndarray | list[float], *, sample_index: int = 0) -> GeometryCompileResult:
        projected = project_parameters(method, parameters)
        validate_parameters(method, projected)
        c0, c1, c2, width = projected
        c_mean = float(np.mean(projected[:3]))
        width_term = float(np.tanh(width - 5.0)) if method in ("M2", "M3") else 0.0
        gradient_term = abs(float(c2 - c0))
        relative_volume = float(np.clip(0.35 + 1.25 * (c_mean - 0.03) + 0.025 * width_term, 0.05, 0.95))
        if self.profile == "physical_m04":
            relative_area = float(0.8 + 0.5 * gradient_term + 0.04 * (width_term + 1.0))
        else:
            relative_area = float(0.25 + 0.3 * gradient_term + 0.02 * (width_term + 1.0))
        thickness = self.reference_length_mm * (0.08 + 0.42 * relative_volume)
        pore_diameter = self.reference_length_mm * (0.08 + 0.34 * (1.0 - relative_volume))
        area_mean = self.reference_length_mm**2 * (0.16 + 0.68 * relative_volume)
        descriptors = np.array(
            [relative_volume, relative_area, thickness, pore_diameter, area_mean],
            dtype=np.float64,
        )
        identity_payload = {
            "compiler_version": self.compiler_version,
            "descriptor_definition_sha256": self.descriptor_definition_sha256,
            "method": method,
            "parameters": [float(value) for value in projected],
            "profile": self.profile,
            "reference_length_mm": self.reference_length_mm,
            "sample_index": int(sample_index),
        }
        geometry_identity = _sha256_json(identity_payload)
        return GeometryCompileResult(
            method=method,
            parameters=projected,
            descriptor_profile=self.profile,
            descriptors=descriptors,
            feasibility={"closed_surface": True, "connected": True, "meshing": True},
            compiler_version=self.compiler_version,
            descriptor_definition_sha256=self.descriptor_definition_sha256,
            geometry_identity=geometry_identity,
            artifact_hashes={"geometry_identity": geometry_identity},
            compiler_mode=self.compiler_mode,
        )


def finite_difference_sensitivities(
    compiler: GeometryCompiler,
    method: str,
    parameters: np.ndarray | list[float],
    *,
    sample_index: int = 0,
    steps: np.ndarray | list[float] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Recompute compiler descriptors and finite-difference relation edges.

    Exactly one valid side yields a one-sided derivative with confidence 0.5;
    two invalid sides retain an unavailable edge instead of fabricating zero.
    """

    base_parameters = project_parameters(method, parameters)
    base = validate_compile_result(
        compiler.compile(method, base_parameters, sample_index=sample_index),
        expected_profile=compiler.profile,
    )
    if steps is None:
        step_values = np.array([1e-3, 1e-3, 1e-3, 1e-2], dtype=np.float64)
    else:
        step_values = np.asarray(steps, dtype=np.float64)
    if step_values.shape != (PARAMETER_COUNT,) or not np.isfinite(step_values).all() or np.any(step_values <= 0.0):
        raise ValueError("finite-difference steps must be positive and have length four")
    sensitivity = np.zeros((PARAMETER_COUNT, DESCRIPTOR_COUNT), dtype=np.float64)
    valid = np.zeros((PARAMETER_COUNT, DESCRIPTOR_COUNT), dtype=bool)
    confidence = np.zeros((PARAMETER_COUNT, DESCRIPTOR_COUNT), dtype=np.float64)
    active = method_active_mask(method)
    for parameter_index in range(PARAMETER_COUNT):
        if not active[parameter_index]:
            continue
        step = step_values[parameter_index]
        plus = None
        minus = None
        try:
            plus_parameters = base_parameters.copy()
            plus_parameters[parameter_index] += step
            plus = validate_compile_result(
                compiler.compile(method, project_parameters(method, plus_parameters), sample_index=sample_index),
                expected_profile=compiler.profile,
            )
        except (ValueError, RuntimeError):
            plus = None
        try:
            minus_parameters = base_parameters.copy()
            minus_parameters[parameter_index] -= step
            minus = validate_compile_result(
                compiler.compile(method, project_parameters(method, minus_parameters), sample_index=sample_index),
                expected_profile=compiler.profile,
            )
        except (ValueError, RuntimeError):
            minus = None
        if plus is not None and minus is not None:
            sensitivity[parameter_index] = (plus.descriptors - minus.descriptors) / (2.0 * step)
            valid[parameter_index] = True
            confidence[parameter_index] = 1.0
        elif plus is not None:
            sensitivity[parameter_index] = (plus.descriptors - base.descriptors) / step
            valid[parameter_index] = True
            confidence[parameter_index] = 0.5
        elif minus is not None:
            sensitivity[parameter_index] = (base.descriptors - minus.descriptors) / step
            valid[parameter_index] = True
            confidence[parameter_index] = 0.5
    return sensitivity, valid, confidence

