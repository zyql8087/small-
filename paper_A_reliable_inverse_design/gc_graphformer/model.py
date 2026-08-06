"""GC-GraphFormer and the parameter-matched fully-connected graph ablation."""

from __future__ import annotations

from typing import Optional

import torch
from torch import Tensor, nn
from torch_geometric.nn import TransformerConv
from torch_geometric.utils import to_dense_batch

from .contracts import EDGE_ATTR_DIM, CURVE_POINTS, NODE_COUNT, STRAIN_COORDINATES
from .graph_builder import EDGE_TYPE_AXIAL, NODE_INDEX


class EdgeAwareBlock(nn.Module):
    def __init__(self, hidden_dim: int, heads: int, edge_dim: int, dropout: float) -> None:
        super().__init__()
        if hidden_dim % heads != 0:
            raise ValueError("hidden_dim must be divisible by heads")
        self.conv = TransformerConv(
            hidden_dim,
            hidden_dim // heads,
            heads=heads,
            concat=True,
            beta=True,
            dropout=dropout,
            edge_dim=edge_dim,
        )
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)
        self.feed_forward = nn.Sequential(
            nn.Linear(hidden_dim, 4 * hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(4 * hidden_dim, hidden_dim),
            nn.Dropout(dropout),
        )

    def forward(self, x: Tensor, edge_index: Tensor, edge_attr: Tensor) -> Tensor:
        x = self.norm1(x + self.conv(x, edge_index, edge_attr))
        return self.norm2(x + self.feed_forward(x))


class GCGraphFormer(nn.Module):
    """Graph Transformer using compiler, axial, method, and readout relations."""

    edge_policy = "compiler_relations"

    def __init__(
        self,
        *,
        node_feature_dim: int = 7,
        edge_dim: int = EDGE_ATTR_DIM,
        hidden_dim: int = 128,
        heads: int = 4,
        num_layers: int = 3,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if hidden_dim % heads != 0:
            raise ValueError("hidden_dim must be divisible by heads")
        if num_layers <= 0:
            raise ValueError("num_layers must be positive")
        self.hidden_dim = hidden_dim
        self.edge_dim = edge_dim
        self.node_encoder = nn.Linear(node_feature_dim, hidden_dim)
        self.node_type_embedding = nn.Embedding(NODE_COUNT, hidden_dim)
        self.edge_type_embedding = nn.Embedding(4, edge_dim)
        self.encoder = nn.ModuleList(
            [EdgeAwareBlock(hidden_dim, heads, edge_dim, dropout) for _ in range(num_layers)]
        )
        self.strain_query = nn.Sequential(
            nn.Linear(1, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.cross_attention = nn.MultiheadAttention(hidden_dim, heads, dropout=dropout, batch_first=True)
        self.amplitude_head = nn.Sequential(nn.LayerNorm(hidden_dim), nn.Linear(hidden_dim, 1))
        self.shape_head = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
        )

    def _encode(
        self,
        batch,
        edge_index: Tensor,
        edge_attr: Tensor,
        edge_type: Optional[Tensor],
    ) -> tuple[Tensor, Tensor, Tensor, Tensor]:
        graph_batch = getattr(batch, "batch", None)
        if graph_batch is None:
            graph_batch = torch.zeros(batch.x.size(0), dtype=torch.long, device=batch.x.device)
        node_type = batch.node_type.to(dtype=torch.long)
        x = self.node_encoder(batch.x) + self.node_type_embedding(node_type)
        if edge_type is None:
            edge_type = torch.zeros(edge_index.size(1), dtype=torch.long, device=edge_index.device)
        edge_features = edge_attr + self.edge_type_embedding(edge_type)
        for layer in self.encoder:
            x = layer(x, edge_index, edge_features)
        dense, mask = to_dense_batch(x, graph_batch)
        readout_mask = node_type == NODE_INDEX["readout"]
        global_state = x[readout_mask]
        if global_state.size(0) != dense.size(0):
            raise ValueError("each graph must contain exactly one global readout node")
        return x, dense, mask, global_state

    def _decode(self, batch, dense: Tensor, mask: Tensor, global_state: Tensor) -> dict[str, Tensor]:
        if hasattr(batch, "strain_coordinates"):
            strain = batch.strain_coordinates.reshape(-1, CURVE_POINTS).to(dtype=dense.dtype, device=dense.device)
        else:
            strain = torch.as_tensor(STRAIN_COORDINATES, dtype=dense.dtype, device=dense.device).expand(dense.size(0), -1)
        queries = self.strain_query(strain.unsqueeze(-1))
        attended, _ = self.cross_attention(queries, dense, dense, key_padding_mask=~mask)
        amplitude = torch.nn.functional.softplus(self.amplitude_head(global_state).squeeze(-1)) + 1e-6
        shape = torch.nn.functional.softplus(self.shape_head(attended).squeeze(-1))
        shape = shape / torch.sqrt(torch.mean(shape * shape, dim=1, keepdim=True) + 1e-8)
        curve = amplitude.unsqueeze(-1) * shape
        return {
            "curve": curve,
            "amplitude": amplitude,
            "shape": shape,
            "latent": global_state,
        }

    def _forward_with_edges(self, batch, edge_index: Tensor, edge_attr: Tensor, edge_type: Optional[Tensor]) -> dict[str, Tensor]:
        _, dense, mask, global_state = self._encode(batch, edge_index, edge_attr, edge_type)
        return self._decode(batch, dense, mask, global_state)

    def forward(self, batch, *, return_aux: bool = False) -> Tensor | dict[str, Tensor]:
        output = self._forward_with_edges(batch, batch.edge_index, batch.edge_attr, getattr(batch, "edge_type", None))
        return output if return_aux else output["curve"]


class FullyConnectedPyGGraphTransformer(GCGraphFormer):
    """Parameter-matched all-pairs PyG ablation, not a physical topology model."""

    edge_policy = "fully_connected_all_ones"

    @staticmethod
    def _dense_edges(batch) -> tuple[Tensor, Tensor, Tensor]:
        graph_batch = getattr(batch, "batch", None)
        if graph_batch is None:
            graph_batch = torch.zeros(batch.x.size(0), dtype=torch.long, device=batch.x.device)
        counts = torch.bincount(graph_batch)
        if counts.numel() == 0 or not torch.all(counts == NODE_COUNT):
            raise ValueError("fully-connected ablation requires fixed 11-node graphs")
        local = torch.arange(NODE_COUNT, device=batch.x.device)
        source = local.repeat_interleave(NODE_COUNT)
        target = local.repeat(NODE_COUNT)
        offsets = torch.arange(counts.numel(), device=batch.x.device) * NODE_COUNT
        edge_index = torch.cat(
            [torch.stack((source + offset, target + offset), dim=0) for offset in offsets], dim=1
        )
        edge_attr = torch.ones((edge_index.size(1), EDGE_ATTR_DIM), dtype=batch.x.dtype, device=batch.x.device)
        edge_type = torch.zeros(edge_index.size(1), dtype=torch.long, device=batch.x.device)
        return edge_index, edge_attr, edge_type

    def forward(self, batch, *, return_aux: bool = False) -> Tensor | dict[str, Tensor]:
        edge_index, edge_attr, edge_type = self._dense_edges(batch)
        output = self._forward_with_edges(batch, edge_index, edge_attr, edge_type)
        return output if return_aux else output["curve"]

