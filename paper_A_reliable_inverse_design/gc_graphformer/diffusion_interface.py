"""Method-conditioned padded-vector boundary for the existing diffusion model."""

from __future__ import annotations

from collections.abc import Sequence

import torch
from torch import Tensor
from torch.nn import functional as F

from .contracts import CURVE_POINTS, METHODS, METHOD_ACTIVE_MASKS, PARAMETER_COUNT, method_id


class MethodConditionedDiffusionInterface:
    """Define, project, and validate diffusion IO without changing the sampler."""

    scope = "method_conditioned_interface_only"

    def __init__(self, *, response_descriptor_dim: int | None = None, width_epsilon: float = 1e-6) -> None:
        if response_descriptor_dim is not None and response_descriptor_dim <= 0:
            raise ValueError("response_descriptor_dim must be positive when supplied")
        if width_epsilon <= 0.0 or width_epsilon >= 1.0:
            raise ValueError("width_epsilon must be in (0, 1)")
        self.response_descriptor_dim = response_descriptor_dim
        self.width_epsilon = float(width_epsilon)

    @staticmethod
    def _method_list(methods: str | Sequence[str], batch_size: int) -> list[str]:
        if isinstance(methods, str):
            values = [methods] * batch_size
        else:
            values = list(methods)
            if len(values) == 1 and batch_size != 1:
                values = values * batch_size
            if len(values) != batch_size:
                raise ValueError("method condition count must match batch size")
        for value in values:
            method_id(value)
        return values

    def build_condition(
        self,
        methods: str | Sequence[str],
        *,
        target_curve: Tensor,
        response_descriptors: Tensor,
    ) -> dict[str, Tensor]:
        target = torch.as_tensor(target_curve)
        if target.ndim == 1:
            target = target.unsqueeze(0)
        if target.ndim != 2 or target.size(1) != CURVE_POINTS or not torch.isfinite(target).all():
            raise ValueError("target_curve must be finite with shape [batch, 20]")
        descriptors = torch.as_tensor(response_descriptors, dtype=target.dtype, device=target.device)
        if descriptors.ndim == 1:
            descriptors = descriptors.unsqueeze(0)
        if descriptors.ndim != 2 or descriptors.size(0) not in (1, target.size(0)):
            raise ValueError("response_descriptors must have shape [batch, descriptor_count]")
        if descriptors.size(0) == 1 and target.size(0) != 1:
            descriptors = descriptors.expand(target.size(0), -1)
        if self.response_descriptor_dim is not None and descriptors.size(1) != self.response_descriptor_dim:
            raise ValueError("response descriptor dimension does not match the interface contract")
        if not torch.isfinite(descriptors).all():
            raise ValueError("response_descriptors must be finite")
        method_values = self._method_list(methods, target.size(0))
        method_token = F.one_hot(
            torch.tensor([METHODS.index(value) for value in method_values], device=target.device),
            num_classes=len(METHODS),
        ).to(dtype=target.dtype)
        variable_mask = torch.tensor(
            [METHOD_ACTIVE_MASKS[value].tolist() for value in method_values],
            dtype=torch.bool,
            device=target.device,
        )
        return {
            "target_curve": target,
            "response_descriptors": descriptors,
            "method_token": method_token,
            "variable_validity_mask": variable_mask,
        }

    def project_training_output(self, raw_output: Tensor, methods: str | Sequence[str]) -> Tensor:
        return self._project(raw_output, methods)

    def decode_output(self, raw_output: Tensor, methods: str | Sequence[str]) -> Tensor:
        return self._project(raw_output, methods)

    def _project(self, raw_output: Tensor, methods: str | Sequence[str]) -> Tensor:
        raw = torch.as_tensor(raw_output)
        if raw.ndim == 1:
            raw = raw.unsqueeze(0)
        if raw.ndim != 2 or raw.size(1) != PARAMETER_COUNT:
            raise ValueError("diffusion output must have shape [batch, 4]")
        method_values = self._method_list(methods, raw.size(0))
        bounded_c = torch.clamp(raw[:, :3], min=0.03, max=0.20)
        width = torch.clamp(raw[:, 3], min=2.0 + self.width_epsilon, max=8.0 - self.width_epsilon)
        rows = []
        for row, method in enumerate(method_values):
            if method == "M1":
                rows.append(torch.cat((bounded_c[row], raw[row, 3:4] * 0.0), dim=0))
            elif method == "M2":
                mean_c = torch.clamp(torch.mean(raw[row, :3]), min=0.03, max=0.20)
                rows.append(torch.cat((mean_c.expand(3), width[row].reshape(1)), dim=0))
            else:
                rows.append(torch.cat((bounded_c[row], width[row].reshape(1)), dim=0))
        return torch.stack(rows, dim=0)

    def validate_padded_parameters(self, parameters: Tensor, methods: str | Sequence[str], *, tolerance: float = 1e-6) -> Tensor:
        values = torch.as_tensor(parameters)
        if values.ndim == 1:
            values = values.unsqueeze(0)
        if values.ndim != 2 or values.size(1) != PARAMETER_COUNT:
            raise ValueError("parameters must have shape [batch, 4]")
        method_values = self._method_list(methods, values.size(0))
        valid = torch.isfinite(values).all(dim=1)
        valid &= (values[:, :3] >= 0.03 - tolerance).all(dim=1)
        valid &= (values[:, :3] <= 0.20 + tolerance).all(dim=1)
        for row, method in enumerate(method_values):
            if method == "M1":
                valid[row] &= torch.abs(values[row, 3]) <= tolerance
            else:
                valid[row] &= values[row, 3] > 2.0
                valid[row] &= values[row, 3] < 8.0
            if method == "M2":
                valid[row] &= torch.max(torch.abs(values[row, :3] - values[row, 0])) <= tolerance
        return valid
