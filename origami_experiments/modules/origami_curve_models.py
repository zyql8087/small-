"""Curve-aware Origami models for nonlinear force-displacement datasets.

The legacy models in this project map 8 design parameters to six stiffness
scalars. These models keep the same design-parameter interface, but target the
new Miura nonlinear dataset where each sample stores 6 loading conditions x T
force-displacement points.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import DenseGATConv


PARAMETER_NAMES = ("pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE")
NODE_INDEX = {name: idx for idx, name in enumerate(PARAMETER_NAMES)}


def build_parameter_adjacency(
    graph_type: str = "physical",
    device: torch.device | None = None,
    num_nodes: int | None = None,
) -> torch.Tensor:
    """Build a graph over base parameters and optional derived feature nodes."""
    base_nodes = len(PARAMETER_NAMES)
    total_nodes = base_nodes if num_nodes is None else num_nodes
    if total_nodes < base_nodes:
        raise ValueError(f"num_nodes must be at least {base_nodes}, got {total_nodes}")
    adj = torch.eye(total_nodes, dtype=torch.float32, device=device)

    def connect(*names: str) -> None:
        ids = [NODE_INDEX[name] for name in names]
        for i in ids:
            for j in ids:
                adj[i, j] = 1.0

    def edge(a: str, b: str) -> None:
        i, j = NODE_INDEX[a], NODE_INDEX[b]
        adj[i, j] = 1.0
        adj[j, i] = 1.0

    if graph_type == "full":
        adj[:] = 1.0
    elif graph_type == "physical":
        connect("pattern", "m", "n")
        connect("tcrease", "tpanel", "W")
        connect("creaseE", "panelE")
        edge("pattern", "tcrease")
        edge("pattern", "tpanel")
        edge("pattern", "W")
        edge("m", "W")
        edge("n", "W")
        edge("tcrease", "creaseE")
        edge("tpanel", "panelE")
        edge("W", "tpanel")
        edge("W", "panelE")
        edge("tcrease", "tpanel")
    elif graph_type == "physical_sparse":
        connect("pattern", "m", "n")
        edge("m", "W")
        edge("n", "W")
        edge("tcrease", "creaseE")
        edge("tpanel", "panelE")
        edge("pattern", "tcrease")
        edge("pattern", "tpanel")
    else:
        raise ValueError(f"Unknown graph_type: {graph_type}")

    if total_nodes > base_nodes and graph_type != "full":
        base_continuous = [NODE_INDEX[name] for name in ("tcrease", "tpanel", "W", "creaseE", "panelE")]
        extra_nodes = range(base_nodes, total_nodes)
        for extra in extra_nodes:
            for base in base_continuous:
                adj[extra, base] = 1.0
                adj[base, extra] = 1.0
            for other in extra_nodes:
                adj[extra, other] = 1.0
    return adj


class ResidualMLPBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim * 2, dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.net(x)


class TemporalRefinementBlock(nn.Module):
    """Residual temporal convolution block over each loading curve."""

    def __init__(self, hidden_dim: int, kernel_size: int = 5, dropout: float = 0.1) -> None:
        super().__init__()
        if kernel_size % 2 == 0:
            raise ValueError("temporal kernel_size must be odd to preserve sequence length")
        self.norm = nn.LayerNorm(hidden_dim)
        self.temporal = nn.Sequential(
            nn.Conv1d(
                hidden_dim,
                hidden_dim,
                kernel_size=kernel_size,
                padding=kernel_size // 2,
                groups=hidden_dim,
            ),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        y = self.norm(x).transpose(1, 2)
        y = self.temporal(y).transpose(1, 2)
        return residual + y


class SinusoidalTimeEmbedding(nn.Module):
    def __init__(self, dim: int) -> None:
        super().__init__()
        self.dim = dim

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        half = self.dim // 2
        freqs = torch.exp(
            -torch.arange(half, device=t.device, dtype=torch.float32)
            * torch.log(torch.tensor(10000.0, device=t.device))
            / max(half - 1, 1)
        )
        args = t.float().unsqueeze(1) * freqs.unsqueeze(0)
        emb = torch.cat([torch.sin(args), torch.cos(args)], dim=1)
        if self.dim % 2 == 1:
            emb = F.pad(emb, (0, 1))
        return emb


class OrigamiCurveGNNTransformerForward(nn.Module):
    """Forward model: design parameters -> 6 x T x C response curves.

    The design side is a GAT over parameter nodes followed by a Transformer
    encoder. The response side uses condition/step query tokens and a
    Transformer decoder so the model predicts a dense force-displacement
    response rather than six scalar stiffness labels.
    """

    def __init__(
        self,
        cat_cardinalities: tuple[int, int, int] = (2, 3, 3),
        cont_dim: int = 5,
        hidden_dim: int = 192,
        gnn_heads: int = 4,
        num_heads: int = 4,
        encoder_layers: int = 2,
        decoder_layers: int = 3,
        num_curve_points: int = 80,
        num_conditions: int = 6,
        curve_channels: int = 2,
        physics_channels: int = 0,
        temporal_refiner_layers: int = 2,
        temporal_kernel_size: int = 5,
        monotonic_displacement: bool = True,
        dropout: float = 0.1,
        graph_type: str = "physical",
    ) -> None:
        super().__init__()
        if hidden_dim % num_heads != 0:
            raise ValueError("hidden_dim must be divisible by num_heads")
        self.num_cat = len(cat_cardinalities)
        self.cont_dim = cont_dim
        self.num_nodes = self.num_cat + cont_dim
        self.num_curve_points = num_curve_points
        self.num_conditions = num_conditions
        self.curve_channels = curve_channels
        self.physics_channels = physics_channels
        self.temporal_refiner_layers = temporal_refiner_layers
        self.monotonic_displacement = monotonic_displacement
        self.graph_type = graph_type

        self.cat_embeddings = nn.ModuleList([nn.Embedding(card, hidden_dim) for card in cat_cardinalities])
        self.cat_value_encoders = nn.ModuleList([nn.Linear(1, hidden_dim) for _ in cat_cardinalities])
        self.cont_encoders = nn.ModuleList([nn.Linear(1, hidden_dim) for _ in range(cont_dim)])
        self.node_type = nn.Parameter(torch.empty(self.num_nodes, hidden_dim))
        nn.init.xavier_uniform_(self.node_type)

        self.gat1 = DenseGATConv(hidden_dim, hidden_dim, heads=gnn_heads, concat=False)
        self.gat2 = DenseGATConv(hidden_dim, hidden_dim, heads=gnn_heads, concat=False)
        self.gnn_norm = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.design_encoder = nn.TransformerEncoder(encoder_layer, num_layers=encoder_layers)

        self.curve_embedding = nn.Embedding(num_conditions, hidden_dim)
        self.load_case_embedding = nn.Embedding(2, hidden_dim)
        self.deployment_embedding = nn.Embedding(3, hidden_dim)
        self.step_embedding = nn.Embedding(num_curve_points, hidden_dim)
        self.step_value_encoder = nn.Linear(1, hidden_dim)
        self.force_value_encoder = nn.Linear(1, hidden_dim)

        decoder_layer = nn.TransformerDecoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.curve_decoder = nn.TransformerDecoder(decoder_layer, num_layers=decoder_layers)
        self.temporal_refiner = nn.ModuleList(
            [
                TemporalRefinementBlock(
                    hidden_dim=hidden_dim,
                    kernel_size=temporal_kernel_size,
                    dropout=dropout,
                )
                for _ in range(temporal_refiner_layers)
            ]
        )
        self.response_head = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, curve_channels),
        )
        self.physics_head = None
        if physics_channels > 0:
            self.physics_head = nn.Sequential(
                nn.LayerNorm(hidden_dim),
                nn.Linear(hidden_dim, hidden_dim),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, physics_channels),
            )

        if num_conditions != 6:
            raise ValueError("The current Miura curve protocol expects exactly 6 loading conditions")
        load_case_ids = torch.tensor([0, 0, 0, 1, 1, 1], dtype=torch.long)
        deployment_ids = torch.tensor([0, 1, 2, 0, 1, 2], dtype=torch.long)
        self.register_buffer("condition_load_case_ids", load_case_ids, persistent=False)
        self.register_buffer("condition_deployment_ids", deployment_ids, persistent=False)
        cat_denominators = torch.tensor([max(card - 1, 1) for card in cat_cardinalities], dtype=torch.float32)
        self.register_buffer("cat_value_denominators", cat_denominators, persistent=False)

    def _nodes_from_hard(self, cat_ids: torch.Tensor, cont_scaled: torch.Tensor) -> torch.Tensor:
        cat_nodes = []
        for i, (emb, value_encoder) in enumerate(zip(self.cat_embeddings, self.cat_value_encoders)):
            value = cat_ids[:, i : i + 1].float() / self.cat_value_denominators[i].to(cat_ids.device)
            cat_nodes.append(emb(cat_ids[:, i]) + value_encoder(value))
        cont_nodes = [enc(cont_scaled[:, i : i + 1]) for i, enc in enumerate(self.cont_encoders)]
        return torch.stack(cat_nodes + cont_nodes, dim=1) + self.node_type.unsqueeze(0)

    def _nodes_from_soft(self, cat_probs: list[torch.Tensor], cont_scaled: torch.Tensor) -> torch.Tensor:
        if len(cat_probs) != len(self.cat_embeddings):
            raise ValueError(f"Expected {len(self.cat_embeddings)} categorical probability tensors")
        cat_nodes = []
        for i, (probs, emb, value_encoder) in enumerate(
            zip(cat_probs, self.cat_embeddings, self.cat_value_encoders)
        ):
            values = torch.arange(emb.num_embeddings, device=probs.device, dtype=probs.dtype).view(-1, 1)
            expected_value = probs @ values / self.cat_value_denominators[i].to(probs.device)
            cat_nodes.append(probs @ emb.weight + value_encoder(expected_value))
        cont_nodes = [enc(cont_scaled[:, i : i + 1]) for i, enc in enumerate(self.cont_encoders)]
        return torch.stack(cat_nodes + cont_nodes, dim=1) + self.node_type.unsqueeze(0)

    def _encode_design(self, nodes: torch.Tensor, adj: torch.Tensor | None) -> torch.Tensor:
        batch_size = nodes.size(0)
        if adj is None:
            adj = build_parameter_adjacency(self.graph_type, device=nodes.device, num_nodes=self.num_nodes)
        else:
            adj = adj.to(device=nodes.device, dtype=nodes.dtype)
        if adj.dim() == 2:
            adj = adj.unsqueeze(0).expand(batch_size, -1, -1)
        x = F.gelu(self.gat1(nodes, adj))
        x = self.dropout(x)
        x = self.gnn_norm(self.gat2(x, adj) + nodes)
        return self.design_encoder(F.gelu(x))

    def _curve_queries(
        self,
        batch_size: int,
        device: torch.device,
        force_condition: torch.Tensor | None = None,
    ) -> torch.Tensor:
        condition_ids = torch.arange(self.num_conditions, device=device).repeat_interleave(self.num_curve_points)
        step_ids = torch.arange(self.num_curve_points, device=device).repeat(self.num_conditions)
        load_case_ids = self.condition_load_case_ids.to(device).repeat_interleave(self.num_curve_points)
        deployment_ids = self.condition_deployment_ids.to(device).repeat_interleave(self.num_curve_points)
        step_values = step_ids.float().view(-1, 1) / max(self.num_curve_points - 1, 1)

        query = (
            self.curve_embedding(condition_ids)
            + self.load_case_embedding(load_case_ids)
            + self.deployment_embedding(deployment_ids)
            + self.step_embedding(step_ids)
            + self.step_value_encoder(step_values)
        )
        query = query.unsqueeze(0).expand(batch_size, -1, -1)
        if force_condition is None:
            return query

        if force_condition.dim() == 3:
            force_condition = force_condition.unsqueeze(-1)
        expected_shape = (batch_size, self.num_conditions, self.num_curve_points, 1)
        if tuple(force_condition.shape) != expected_shape:
            raise ValueError(f"force_condition must have shape {expected_shape}, got {tuple(force_condition.shape)}")
        force_values = force_condition.to(device=device, dtype=query.dtype).reshape(batch_size, -1, 1)
        return query + self.force_value_encoder(force_values)

    def _decode_from_nodes(
        self,
        nodes: torch.Tensor,
        adj: torch.Tensor | None,
        force_condition: torch.Tensor | None = None,
    ) -> torch.Tensor:
        memory = self._encode_design(nodes, adj)
        query = self._curve_queries(nodes.size(0), nodes.device, force_condition=force_condition)
        decoded = self.curve_decoder(query, memory)
        if not self.temporal_refiner:
            return decoded
        batch_size, _, hidden_dim = decoded.shape
        decoded = decoded.view(batch_size, self.num_conditions, self.num_curve_points, hidden_dim)
        decoded = decoded.reshape(batch_size * self.num_conditions, self.num_curve_points, hidden_dim)
        for block in self.temporal_refiner:
            decoded = block(decoded)
        return decoded.view(batch_size, self.num_conditions * self.num_curve_points, hidden_dim)

    def _parameterize_curve_response(self, raw_curve: torch.Tensor) -> torch.Tensor:
        if raw_curve.size(2) <= 1:
            return raw_curve
        channels = []
        for channel_idx in range(raw_curve.size(-1)):
            channel = raw_curve[..., channel_idx : channel_idx + 1]
            if channel_idx == 0 and not self.monotonic_displacement:
                channels.append(channel)
                continue
            initial = channel[:, :, :1, :]
            positive_increments = F.softplus(channel[:, :, 1:, :]) / float(channel.size(2) - 1)
            cumulative = initial + torch.cumsum(positive_increments, dim=2)
            channels.append(torch.cat([initial, cumulative], dim=2))
        return torch.cat(channels, dim=-1)

    def _predict_from_nodes(
        self,
        nodes: torch.Tensor,
        adj: torch.Tensor | None,
        force_condition: torch.Tensor | None = None,
    ) -> torch.Tensor:
        decoded = self._decode_from_nodes(nodes, adj, force_condition=force_condition)
        raw_curve = self.response_head(decoded).view(
            nodes.size(0), self.num_conditions, self.num_curve_points, self.curve_channels
        )
        return self._parameterize_curve_response(raw_curve)

    def _predict_with_aux_from_nodes(
        self,
        nodes: torch.Tensor,
        adj: torch.Tensor | None,
        force_condition: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        decoded = self._decode_from_nodes(nodes, adj, force_condition=force_condition)
        raw_curve = self.response_head(decoded).view(
            nodes.size(0), self.num_conditions, self.num_curve_points, self.curve_channels
        )
        curve = self._parameterize_curve_response(raw_curve)
        outputs = {"curve": curve}
        if self.physics_head is not None:
            outputs["physics"] = self.physics_head(decoded).view(
                nodes.size(0), self.num_conditions, self.num_curve_points, self.physics_channels
            )
        return outputs

    def forward(
        self,
        cat_ids: torch.Tensor,
        cont_scaled: torch.Tensor,
        adj: torch.Tensor | None = None,
        force_condition: torch.Tensor | None = None,
    ) -> torch.Tensor:
        return self._predict_from_nodes(self._nodes_from_hard(cat_ids, cont_scaled), adj, force_condition=force_condition)

    def forward_from_probs(
        self,
        cat_probs: list[torch.Tensor],
        cont_scaled: torch.Tensor,
        adj: torch.Tensor | None = None,
        force_condition: torch.Tensor | None = None,
    ) -> torch.Tensor:
        return self._predict_from_nodes(self._nodes_from_soft(cat_probs, cont_scaled), adj, force_condition=force_condition)

    def forward_with_aux(
        self,
        cat_ids: torch.Tensor,
        cont_scaled: torch.Tensor,
        adj: torch.Tensor | None = None,
        force_condition: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        return self._predict_with_aux_from_nodes(
            self._nodes_from_hard(cat_ids, cont_scaled),
            adj,
            force_condition=force_condition,
        )

    def forward_with_aux_from_probs(
        self,
        cat_probs: list[torch.Tensor],
        cont_scaled: torch.Tensor,
        adj: torch.Tensor | None = None,
        force_condition: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        return self._predict_with_aux_from_nodes(
            self._nodes_from_soft(cat_probs, cont_scaled),
            adj,
            force_condition=force_condition,
        )

    def forward_flat(
        self,
        cat_ids: torch.Tensor,
        cont_scaled: torch.Tensor,
        adj: torch.Tensor | None = None,
        force_condition: torch.Tensor | None = None,
    ) -> torch.Tensor:
        return self.forward(cat_ids, cont_scaled, adj, force_condition=force_condition).reshape(cat_ids.size(0), -1)


class CurveConditionEncoder(nn.Module):
    """Encode 6 force-displacement curves into one conditioning vector."""

    def __init__(
        self,
        curve_channels: int = 2,
        physics_channels: int = 0,
        hidden_dim: int = 192,
        cond_dim: int = 192,
        num_curve_points: int = 80,
        num_conditions: int = 6,
        num_heads: int = 4,
        encoder_layers: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if hidden_dim % num_heads != 0:
            raise ValueError("hidden_dim must be divisible by num_heads")
        self.curve_channels = curve_channels
        self.physics_channels = physics_channels
        self.num_curve_points = num_curve_points
        self.num_conditions = num_conditions
        in_channels = curve_channels + physics_channels

        self.point_encoder = nn.Sequential(
            nn.Conv1d(in_channels, hidden_dim // 2, kernel_size=5, padding=2),
            nn.GELU(),
            nn.Conv1d(hidden_dim // 2, hidden_dim, kernel_size=5, padding=2),
            nn.GELU(),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=3, stride=2, padding=1),
            nn.GELU(),
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
        )
        self.curve_embedding = nn.Embedding(num_conditions, hidden_dim)
        self.load_case_embedding = nn.Embedding(2, hidden_dim)
        self.deployment_embedding = nn.Embedding(3, hidden_dim)
        self.cls_token = nn.Parameter(torch.empty(1, 1, hidden_dim))
        nn.init.xavier_uniform_(self.cls_token)

        layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.condition_encoder = nn.TransformerEncoder(layer, num_layers=encoder_layers)
        self.proj = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, cond_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            ResidualMLPBlock(cond_dim, dropout),
        )

        if num_conditions != 6:
            raise ValueError("The current Miura curve protocol expects exactly 6 loading conditions")
        self.register_buffer("condition_load_case_ids", torch.tensor([0, 0, 0, 1, 1, 1]), persistent=False)
        self.register_buffer("condition_deployment_ids", torch.tensor([0, 1, 2, 0, 1, 2]), persistent=False)

    def forward(self, curve: torch.Tensor, physics: torch.Tensor | None = None) -> torch.Tensor:
        if curve.dim() != 4:
            raise ValueError("curve must have shape [batch, conditions, points, channels]")
        batch_size, conditions, points, channels = curve.shape
        if conditions != self.num_conditions or points != self.num_curve_points or channels != self.curve_channels:
            raise ValueError(
                "curve shape mismatch: expected "
                f"[B, {self.num_conditions}, {self.num_curve_points}, {self.curve_channels}], got {list(curve.shape)}"
            )
        if self.physics_channels:
            if physics is None:
                physics = torch.zeros(
                    batch_size,
                    conditions,
                    points,
                    self.physics_channels,
                    dtype=curve.dtype,
                    device=curve.device,
                )
            curve = torch.cat([curve, physics.to(dtype=curve.dtype, device=curve.device)], dim=-1)

        x = curve.reshape(batch_size * conditions, points, -1).transpose(1, 2)
        tokens = self.point_encoder(x).view(batch_size, conditions, -1)

        condition_ids = torch.arange(conditions, device=curve.device)
        tokens = (
            tokens
            + self.curve_embedding(condition_ids).unsqueeze(0)
            + self.load_case_embedding(self.condition_load_case_ids.to(curve.device)).unsqueeze(0)
            + self.deployment_embedding(self.condition_deployment_ids.to(curve.device)).unsqueeze(0)
        )
        cls = self.cls_token.expand(batch_size, -1, -1)
        encoded = self.condition_encoder(torch.cat([cls, tokens], dim=1))
        return self.proj(encoded[:, 0])


class OrigamiCurveConditionalDiffusion(nn.Module):
    """Curve-conditioned denoiser for inverse design.

    Input x_t is the noised 8-parameter target. The condition is the complete
    nonlinear response tensor [B, 6, T, 2] and optional physical history tensor.
    """

    def __init__(
        self,
        target_dim: int = 8,
        curve_channels: int = 2,
        physics_channels: int = 0,
        time_dim: int = 64,
        cond_dim: int = 192,
        hidden_dim: int = 512,
        num_curve_points: int = 80,
        num_conditions: int = 6,
        num_heads: int = 4,
        encoder_layers: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.target_dim = target_dim
        self.time_emb = nn.Sequential(
            SinusoidalTimeEmbedding(time_dim),
            nn.Linear(time_dim, time_dim),
            nn.GELU(),
        )
        self.condition_encoder = CurveConditionEncoder(
            curve_channels=curve_channels,
            physics_channels=physics_channels,
            hidden_dim=cond_dim,
            cond_dim=cond_dim,
            num_curve_points=num_curve_points,
            num_conditions=num_conditions,
            num_heads=num_heads,
            encoder_layers=encoder_layers,
            dropout=dropout,
        )
        self.net = nn.Sequential(
            nn.Linear(target_dim + time_dim + cond_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            ResidualMLPBlock(hidden_dim, dropout),
            ResidualMLPBlock(hidden_dim, dropout),
            nn.Linear(hidden_dim, target_dim),
        )

    def forward(
        self,
        x_t: torch.Tensor,
        t: torch.Tensor,
        curve: torch.Tensor,
        physics: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if x_t.size(1) != self.target_dim:
            raise ValueError(f"x_t must have target_dim={self.target_dim}, got {x_t.size(1)}")
        time_feat = self.time_emb(t)
        cond_feat = self.condition_encoder(curve, physics=physics)
        return self.net(torch.cat([x_t, time_feat, cond_feat], dim=1))
