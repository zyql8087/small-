"""Historical forward baselines retained for parameter-matched comparisons."""

from __future__ import annotations

import torch
from torch import Tensor, nn
from torch_geometric.nn import GATConv, global_mean_pool


class ResMLPBaseline(nn.Module):
    """Small-style nine-column residual MLP baseline."""

    def __init__(self, *, input_dim: int = 9, hidden_dim: int = 128) -> None:
        super().__init__()
        self.input = nn.Linear(input_dim, hidden_dim)
        self.block = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.output = nn.Sequential(nn.LayerNorm(hidden_dim), nn.Linear(hidden_dim, 20))

    def forward(self, design: Tensor) -> Tensor:
        hidden = self.input(design)
        hidden = hidden + self.block(hidden)
        return self.output(hidden)


class ParameterTokenTransformerBaseline(nn.Module):
    """Existing parameter-token Transformer semantics without graph edges."""

    def __init__(self, *, input_dim: int = 9, hidden_dim: int = 128, heads: int = 4, num_layers: int = 3) -> None:
        super().__init__()
        if hidden_dim % heads != 0:
            raise ValueError("hidden_dim must be divisible by heads")
        self.value_projection = nn.Linear(1, hidden_dim)
        self.type_embedding = nn.Embedding(input_dim, hidden_dim)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, hidden_dim))
        layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=heads,
            dim_feedforward=4 * hidden_dim,
            dropout=0.1,
            activation="gelu",
            batch_first=True,
            norm_first=False,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=num_layers)
        self.output = nn.Linear(hidden_dim, 20)

    def forward(self, design: Tensor) -> Tensor:
        if design.ndim != 2:
            raise ValueError("parameter-token input must have shape [batch, 9]")
        batch_size, token_count = design.shape
        token_values = self.value_projection(design.unsqueeze(-1))
        token_types = self.type_embedding(torch.arange(token_count, device=design.device)).unsqueeze(0)
        tokens = token_values + token_types
        cls = self.cls_token.expand(batch_size, -1, -1)
        encoded = self.encoder(torch.cat((cls, tokens), dim=1))
        return self.output(encoded[:, 0])


class DenseAllOnesGATBaseline(nn.Module):
    """Dense all-ones parameter graph retained as a non-topological baseline."""

    graph_semantics = "dense_all_ones_baseline"

    def __init__(self, *, input_dim: int = 9, hidden_dim: int = 128, heads: int = 4) -> None:
        super().__init__()
        if hidden_dim % heads != 0:
            raise ValueError("hidden_dim must be divisible by heads")
        self.input_projection = nn.Linear(1, hidden_dim)
        self.gat = GATConv(
            hidden_dim,
            hidden_dim // heads,
            heads=heads,
            concat=True,
            add_self_loops=False,
            edge_dim=1,
        )
        self.output = nn.Linear(hidden_dim, 20)
        self.input_dim = input_dim

    def _dense_edges(self, batch_size: int, device: torch.device) -> tuple[Tensor, Tensor, Tensor]:
        local = torch.arange(self.input_dim, device=device)
        source = local.repeat_interleave(self.input_dim)
        target = local.repeat(self.input_dim)
        offsets = torch.arange(batch_size, device=device) * self.input_dim
        edge_index = torch.cat(
            [torch.stack((source + offset, target + offset), dim=0) for offset in offsets], dim=1
        )
        edge_attr = torch.ones((edge_index.size(1), 1), device=device)
        graph_batch = torch.arange(batch_size, device=device).repeat_interleave(self.input_dim)
        return edge_index, edge_attr, graph_batch

    def forward(self, design: Tensor) -> Tensor:
        if design.ndim != 2 or design.size(1) != self.input_dim:
            raise ValueError(f"dense GAT input must have shape [batch, {self.input_dim}]")
        batch_size = design.size(0)
        edge_index, edge_attr, graph_batch = self._dense_edges(batch_size, design.device)
        node_features = self.input_projection(design.reshape(-1, 1))
        node_features = self.gat(node_features, edge_index, edge_attr)
        pooled = global_mean_pool(node_features, graph_batch)
        return self.output(pooled)
