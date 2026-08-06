"""Stable data contracts shared by graph, generator, and model code."""

from __future__ import annotations

from typing import Iterable, Mapping

import numpy as np

METHODS = ("M1", "M2", "M3")
PARAMETER_NAMES = ("c0", "c1", "c2", "w")
DESCRIPTOR_NAMES = (
    "relativeVolume",
    "relativeArea",
    "thickness",
    "poreDiameter",
    "areaMean",
)
PROFILES = ("legacy_small", "physical_m04")
CURVE_POINTS = 20
STRAIN_COORDINATES = np.linspace(0.0125, 0.25, CURVE_POINTS, dtype=np.float64)
PARAMETER_COUNT = len(PARAMETER_NAMES)
DESCRIPTOR_COUNT = len(DESCRIPTOR_NAMES)
NODE_COUNT = 1 + PARAMETER_COUNT + DESCRIPTOR_COUNT + 1
EDGE_ATTR_DIM = 8

METHOD_IDS = {name: index for index, name in enumerate(METHODS)}
PROFILE_IDS = {name: index for index, name in enumerate(PROFILES)}

# The padded graph always has four variable nodes. The mask identifies variables
# that are independently controlled for a given Small generation method.
METHOD_ACTIVE_MASKS = {
    "M1": np.array([True, True, True, False]),
    "M2": np.array([True, False, False, True]),
    "M3": np.array([True, True, True, True]),
}


def _as_vector(values: Iterable[float], expected_size: int, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (expected_size,):
        raise ValueError(f"{name} must have shape ({expected_size},), got {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def method_id(method: str) -> int:
    try:
        return METHOD_IDS[method]
    except KeyError as exc:
        raise ValueError(f"unknown method {method!r}; expected one of {METHODS}") from exc


def profile_id(profile: str) -> int:
    try:
        return PROFILE_IDS[profile]
    except KeyError as exc:
        raise ValueError(f"unknown descriptor profile {profile!r}; expected one of {PROFILES}") from exc


def method_active_mask(method: str) -> np.ndarray:
    method_id(method)
    return METHOD_ACTIVE_MASKS[method].copy()


def project_parameters(method: str, parameters: Iterable[float]) -> np.ndarray:
    """Project a raw padded vector onto the method's approved parameter subspace."""

    method_id(method)
    projected = _as_vector(parameters, PARAMETER_COUNT, "parameters").copy()
    if method == "M1":
        projected[3] = 0.0
    elif method == "M2":
        projected[:3] = np.mean(projected[:3])
    return projected


def validate_parameters(method: str, parameters: Iterable[float], *, tolerance: float = 1e-8) -> None:
    """Fail closed when a padded parameter vector violates the compiler domain."""

    projected = _as_vector(parameters, PARAMETER_COUNT, "parameters")
    method_id(method)
    if method == "M1" and abs(projected[3]) > tolerance:
        raise ValueError("M1 requires w=0")
    if method == "M2" and not np.allclose(projected[:3], projected[0], atol=tolerance, rtol=0.0):
        raise ValueError("M2 requires c0=c1=c2")
    if not np.all((0.03 <= projected[:3]) & (projected[:3] <= 0.20)):
        raise ValueError("c0, c1, and c2 must lie in [0.03, 0.20]")
    if method in ("M2", "M3") and not (2.0 < projected[3] < 8.0):
        raise ValueError("w must lie in the open interval (2, 8)")


def validate_descriptors(values: Iterable[float]) -> np.ndarray:
    return _as_vector(values, DESCRIPTOR_COUNT, "descriptors")


def validate_curve(curve: Iterable[float]) -> np.ndarray:
    array = _as_vector(curve, CURVE_POINTS, "curve")
    if np.any(array < 0.0):
        raise ValueError("the Small compression stress curve contract is non-negative")
    return array


def decompose_curve(curve: Iterable[float], *, epsilon: float = 1e-8) -> tuple[float, np.ndarray]:
    """Return positive amplitude and a non-negative shape with exact reconstruction."""

    values = validate_curve(curve)
    amplitude = float(np.sqrt(np.mean(values * values) + epsilon))
    shape = values / amplitude
    return amplitude, shape


def reconstruct_curve(amplitude: float, shape: Iterable[float]) -> np.ndarray:
    shape_array = _as_vector(shape, CURVE_POINTS, "shape")
    if not np.isfinite(amplitude) or amplitude < 0.0:
        raise ValueError("amplitude must be finite and non-negative")
    return float(amplitude) * shape_array


def compiler_profile_envelope(profile: str, values: Mapping[str, float], *, definition_sha256: str) -> dict:
    """Build the M04 shared profile envelope without flattening profile semantics."""

    profile_id(profile)
    if set(values) != set(DESCRIPTOR_NAMES):
        raise ValueError("descriptor envelope keys must match the frozen descriptor order")
    ordered = {name: float(values[name]) for name in DESCRIPTOR_NAMES}
    validate_descriptors(ordered.values())
    return {
        "profile": profile,
        "definition_sha256": str(definition_sha256),
        "sampling": {},
        "units": {},
        "values": ordered,
        "diagnostics": {},
    }

