"""Compiler-informed homogeneous PyG graph construction."""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

import numpy as np
import torch
from torch_geometric.data import Data

from .contracts import (
    DESCRIPTOR_COUNT,
    DESCRIPTOR_NAMES,
    EDGE_ATTR_DIM,
    METHOD_IDS,
    NODE_COUNT,
    PARAMETER_COUNT,
    PARAMETER_NAMES,
    PROFILE_IDS,
    STRAIN_COORDINATES,
    method_active_mask,
    method_id,
    project_parameters,
    profile_id,
    validate_curve,
    validate_descriptors,
)

NODE_INDEX = {"method": 0}
NODE_INDEX.update({name: index + 1 for index, name in enumerate(PARAMETER_NAMES)})
NODE_INDEX.update({name: index + 1 + PARAMETER_COUNT for index, name in enumerate(DESCRIPTOR_NAMES)})
NODE_INDEX["readout"] = NODE_COUNT - 1

EDGE_TYPE_AXIAL = 0
EDGE_TYPE_COMPILER = 1
EDGE_TYPE_METHOD = 2
EDGE_TYPE_READOUT = 3


def _standardize(value: float, mean: float, std: float) -> float:
    if not np.isfinite(mean) or not np.isfinite(std) or std <= 0.0:
        raise ValueError("node standardization requires finite means and positive standard deviations")
    return float((value - mean) / std)


def _standardization_arrays(standardization: Optional[Mapping[str, Sequence[float]]]):
    if standardization is None:
        return (
            np.zeros(PARAMETER_COUNT, dtype=np.float64),
            np.ones(PARAMETER_COUNT, dtype=np.float64),
            np.zeros(DESCRIPTOR_COUNT, dtype=np.float64),
            np.ones(DESCRIPTOR_COUNT, dtype=np.float64),
        )
    keys = {"parameter_mean", "parameter_std", "descriptor_mean", "descriptor_std"}
    if set(standardization) != keys:
        raise ValueError(f"standardization keys must be {sorted(keys)}")
    arrays = tuple(np.asarray(standardization[key], dtype=np.float64) for key in sorted(keys))
    parameter_mean = arrays[2]
    parameter_std = arrays[3]
    descriptor_mean = arrays[0]
    descriptor_std = arrays[1]
    if parameter_mean.shape != (PARAMETER_COUNT,) or parameter_std.shape != (PARAMETER_COUNT,):
        raise ValueError("parameter standardization arrays must have length four")
    if descriptor_mean.shape != (DESCRIPTOR_COUNT,) or descriptor_std.shape != (DESCRIPTOR_COUNT,):
        raise ValueError("descriptor standardization arrays must have length five")
    return parameter_mean, parameter_std, descriptor_mean, descriptor_std


def _relation_features(value: float, valid: float, confidence: float) -> list[float]:
    if not np.isfinite(value):
        value = 0.0
        valid = 0.0
    valid = float(valid)
    confidence = float(confidence) if np.isfinite(confidence) else 0.0
    confidence = float(np.clip(confidence, 0.0, 1.0))
    magnitude = abs(float(value)) if valid else 0.0
    return [
        float(value) if valid else 0.0,
        magnitude,
        float(np.sign(value)) if valid else 0.0,
        float(np.log1p(magnitude)),
        valid,
        confidence,
        0.0,
        0.0,
    ]


def _append_edge(edges: list[list[int]], edge_types: list[int], attrs: list[list[float]], source: int, target: int, edge_type: int, attr: list[float]) -> None:
    if len(attr) != EDGE_ATTR_DIM:
        raise ValueError(f"edge attributes must have length {EDGE_ATTR_DIM}")
    edges.append([source, target])
    edge_types.append(edge_type)
    attrs.append(attr)


def build_graph(
    *,
    method: str,
    parameters: Sequence[float],
    descriptors: Sequence[float],
    sensitivities: Sequence[Sequence[float]],
    descriptor_profile: str,
    y_curve: Optional[Sequence[float]] = None,
    descriptor_validity: Optional[Sequence[bool]] = None,
    sensitivity_validity: Optional[Sequence[Sequence[bool]]] = None,
    sensitivity_confidence: Optional[Sequence[Sequence[float]]] = None,
    standardization: Optional[Mapping[str, Sequence[float]]] = None,
    base_structure_id: int = 0,
) -> Data:
    """Build one fixed-semantics 11-node graph from compiler outputs.

    The compiler edge family is deliberately sparse and sample-specific. It is
    not a wrapper around the original nine scalar columns.
    """

    method_id(method)
    profile_id(descriptor_profile)
    projected = project_parameters(method, parameters)
    descriptor_values = validate_descriptors(descriptors)
    sensitivity_values = np.asarray(sensitivities, dtype=np.float64)
    if sensitivity_values.shape != (PARAMETER_COUNT, DESCRIPTOR_COUNT):
        raise ValueError("sensitivities must have shape (4, 5)")
    finite_sensitivity = np.isfinite(sensitivity_values)
    sensitivity_values = np.where(finite_sensitivity, sensitivity_values, 0.0)
    if sensitivity_validity is None:
        sensitivity_mask = finite_sensitivity
    else:
        sensitivity_mask = np.asarray(sensitivity_validity, dtype=bool)
        if sensitivity_mask.shape != (PARAMETER_COUNT, DESCRIPTOR_COUNT):
            raise ValueError("sensitivity_validity must have shape (4, 5)")
        sensitivity_mask &= finite_sensitivity
    if sensitivity_confidence is None:
        confidence = np.ones((PARAMETER_COUNT, DESCRIPTOR_COUNT), dtype=np.float64)
    else:
        confidence = np.asarray(sensitivity_confidence, dtype=np.float64)
        if confidence.shape != (PARAMETER_COUNT, DESCRIPTOR_COUNT):
            raise ValueError("sensitivity_confidence must have shape (4, 5)")
    if descriptor_validity is None:
        descriptor_mask = np.ones(DESCRIPTOR_COUNT, dtype=bool)
    else:
        descriptor_mask = np.asarray(descriptor_validity, dtype=bool)
        if descriptor_mask.shape != (DESCRIPTOR_COUNT,):
            raise ValueError("descriptor_validity must have length five")
    parameter_mean, parameter_std, descriptor_mean, descriptor_std = _standardization_arrays(standardization)
    active = method_active_mask(method)

    node_features = np.zeros((NODE_COUNT, 7), dtype=np.float32)
    node_features[0] = [METHOD_IDS[method] / max(len(METHOD_IDS) - 1, 1), 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    axial_coordinates = (0.0, 0.5, 1.0, 0.0)
    for index in range(PARAMETER_COUNT):
        node_features[index + 1] = [
            _standardize(projected[index], parameter_mean[index], parameter_std[index]),
            1.0,
            axial_coordinates[index],
            1.0,
            0.0,
            float(active[index]),
            0.0,
        ]
    for index in range(DESCRIPTOR_COUNT):
        node_features[index + 1 + PARAMETER_COUNT] = [
            _standardize(descriptor_values[index], descriptor_mean[index], descriptor_std[index]),
            float(descriptor_mask[index]),
            0.0,
            0.0,
            1.0,
            1.0,
            0.0,
        ]
    node_features[-1] = [0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0]

    edges: list[list[int]] = []
    edge_types: list[int] = []
    attrs: list[list[float]] = []
    for left, right in ((1, 2), (2, 3)):
        delta = float(projected[right - 1] - projected[left - 1])
        for source, target in ((left, right), (right, left)):
            attr = _relation_features(delta if source == left else -delta, 1.0, 1.0)
            attr[6] = 0.5
            attr[7] = delta if source == left else -delta
            _append_edge(edges, edge_types, attrs, source, target, EDGE_TYPE_AXIAL, attr)

    for parameter_index in range(PARAMETER_COUNT):
        if not active[parameter_index]:
            continue
        for descriptor_index in range(DESCRIPTOR_COUNT):
            value = sensitivity_values[parameter_index, descriptor_index]
            valid = float(sensitivity_mask[parameter_index, descriptor_index])
            attr = _relation_features(value, valid, confidence[parameter_index, descriptor_index])
            _append_edge(
                edges,
                edge_types,
                attrs,
                parameter_index + 1,
                descriptor_index + 1 + PARAMETER_COUNT,
                EDGE_TYPE_COMPILER,
                attr,
            )

    equality_enforced = {
        "M1": (False, False, False, True),
        "M2": (False, True, True, False),
        "M3": (False, False, False, False),
    }[method]
    for parameter_index in range(PARAMETER_COUNT):
        valid = float(active[parameter_index])
        attr = _relation_features(valid, 1.0, 1.0)
        attr[6] = valid
        attr[7] = float(equality_enforced[parameter_index])
        _append_edge(edges, edge_types, attrs, 0, parameter_index + 1, EDGE_TYPE_METHOD, attr)

    for source in range(NODE_COUNT - 1):
        _append_edge(edges, edge_types, attrs, source, NODE_COUNT - 1, EDGE_TYPE_READOUT, _relation_features(1.0, 1.0, 1.0))

    if y_curve is None:
        curve_tensor = torch.empty((1, 0), dtype=torch.float32)
    else:
        curve_tensor = torch.tensor(validate_curve(y_curve), dtype=torch.float32).reshape(1, -1)

    data = Data(
        x=torch.tensor(node_features, dtype=torch.float32),
        node_type=torch.arange(NODE_COUNT, dtype=torch.long),
        edge_index=torch.tensor(edges, dtype=torch.long).t().contiguous(),
        edge_type=torch.tensor(edge_types, dtype=torch.long),
        edge_attr=torch.tensor(attrs, dtype=torch.float32),
        method_id=torch.tensor([METHOD_IDS[method]], dtype=torch.long),
        descriptor_profile_id=torch.tensor([PROFILE_IDS[descriptor_profile]], dtype=torch.long),
        parameters=torch.tensor(projected, dtype=torch.float32),
        parameter_active_mask=torch.tensor(active, dtype=torch.bool),
        descriptors=torch.tensor(descriptor_values, dtype=torch.float32),
        descriptor_validity=torch.tensor(descriptor_mask, dtype=torch.bool),
        sensitivities=torch.tensor(sensitivity_values, dtype=torch.float32),
        sensitivity_validity=torch.tensor(sensitivity_mask, dtype=torch.bool),
        sensitivity_confidence=torch.tensor(confidence, dtype=torch.float32),
        y_curve=curve_tensor,
        base_structure_id=torch.tensor([int(base_structure_id)], dtype=torch.long),
        strain_coordinates=torch.tensor(STRAIN_COORDINATES, dtype=torch.float32),
    )
    data.num_nodes = NODE_COUNT
    return data

