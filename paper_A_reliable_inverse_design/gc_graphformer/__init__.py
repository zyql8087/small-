"""Paper A geometry-compiler-informed graph learning components."""

from .compiler import GeometryCompileResult, SyntheticM04Compiler, finite_difference_sensitivities
from .contracts import (
    CURVE_POINTS,
    DESCRIPTOR_NAMES,
    METHODS,
    PARAMETER_NAMES,
    PROFILES,
    decompose_curve,
    project_parameters,
    reconstruct_curve,
)
from .diffusion_interface import MethodConditionedDiffusionInterface
from .geometry_dataset import GeometryOnlyGenerator, load_dataset, write_dataset
from .graph_builder import build_graph
from .model import FullyConnectedPyGGraphTransformer, GCGraphFormer

__all__ = [
    "CURVE_POINTS",
    "DESCRIPTOR_NAMES",
    "METHODS",
    "PARAMETER_NAMES",
    "PROFILES",
    "GeometryCompileResult",
    "SyntheticM04Compiler",
    "finite_difference_sensitivities",
    "decompose_curve",
    "project_parameters",
    "reconstruct_curve",
    "MethodConditionedDiffusionInterface",
    "GeometryOnlyGenerator",
    "load_dataset",
    "write_dataset",
    "build_graph",
    "GCGraphFormer",
    "FullyConnectedPyGGraphTransformer",
]
