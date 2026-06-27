"""Task-adapted Origami models for discrete design variables and log stiffness targets."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import DenseGATConv


class ResidualMLPBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
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


class OrigamiForwardResMLP(nn.Module):
    """Forward baseline: categorical embeddings + continuous MLP -> 6 log-stiffness targets."""

    def __init__(
        self,
        cat_cardinalities: tuple[int, int, int] = (2, 3, 3),
        cont_dim: int = 5,
        emb_dim: int = 16,
        hidden_dim: int = 256,
        num_blocks: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.embeddings = nn.ModuleList([nn.Embedding(card, emb_dim) for card in cat_cardinalities])
        self.cont_encoder = nn.Sequential(
            nn.Linear(cont_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        fusion_dim = hidden_dim + emb_dim * len(cat_cardinalities)
        self.fusion = nn.Sequential(
            nn.Linear(fusion_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            *[ResidualMLPBlock(hidden_dim, dropout) for _ in range(num_blocks)],
        )
        self.bending_head = nn.Linear(hidden_dim, 3)
        self.axial_head = nn.Linear(hidden_dim, 3)

    def _embed_hard(self, cat_ids: torch.Tensor) -> torch.Tensor:
        return torch.cat([emb(cat_ids[:, i]) for i, emb in enumerate(self.embeddings)], dim=1)

    def _embed_soft(self, cat_probs: list[torch.Tensor]) -> torch.Tensor:
        return torch.cat([probs @ emb.weight for probs, emb in zip(cat_probs, self.embeddings)], dim=1)

    def _predict_from_emb(self, cat_emb: torch.Tensor, cont_scaled: torch.Tensor) -> torch.Tensor:
        cont_feat = self.cont_encoder(cont_scaled)
        x = torch.cat([cat_emb, cont_feat], dim=1)
        x = self.fusion(x)
        return torch.cat([self.bending_head(x), self.axial_head(x)], dim=1)

    def forward(self, cat_ids: torch.Tensor, cont_scaled: torch.Tensor) -> torch.Tensor:
        return self._predict_from_emb(self._embed_hard(cat_ids), cont_scaled)

    def forward_from_probs(self, cat_probs: list[torch.Tensor], cont_scaled: torch.Tensor) -> torch.Tensor:
        return self._predict_from_emb(self._embed_soft(cat_probs), cont_scaled)


class OrigamiForwardGATTaskfit(nn.Module):
    """Forward GAT with categorical embeddings as graph nodes and continuous scalar nodes."""

    def __init__(
        self,
        cat_cardinalities: tuple[int, int, int] = (2, 3, 3),
        cont_dim: int = 5,
        hidden_dim: int = 256,
        heads: int = 8,
        mlp_dim: int = 256,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.num_cat = len(cat_cardinalities)
        self.cont_dim = cont_dim
        self.num_nodes = self.num_cat + cont_dim
        self.cat_embeddings = nn.ModuleList([nn.Embedding(card, hidden_dim) for card in cat_cardinalities])
        self.cont_encoders = nn.ModuleList([nn.Linear(1, hidden_dim) for _ in range(cont_dim)])
        self.node_type = nn.Parameter(torch.empty(self.num_nodes, hidden_dim))
        nn.init.xavier_uniform_(self.node_type)

        self.gat1 = DenseGATConv(hidden_dim, hidden_dim, heads=heads, concat=False)
        self.gat2 = DenseGATConv(hidden_dim, hidden_dim, heads=heads, concat=False)
        self.norm = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(dropout)
        self.mlp = nn.Sequential(
            nn.Linear(self.num_nodes * hidden_dim, mlp_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            ResidualMLPBlock(mlp_dim, dropout),
            ResidualMLPBlock(mlp_dim, dropout),
        )
        self.bending_head = nn.Linear(mlp_dim, 3)
        self.axial_head = nn.Linear(mlp_dim, 3)

    def _nodes_from_hard(self, cat_ids: torch.Tensor, cont_scaled: torch.Tensor) -> torch.Tensor:
        cat_nodes = [emb(cat_ids[:, i]) for i, emb in enumerate(self.cat_embeddings)]
        cont_nodes = [enc(cont_scaled[:, i : i + 1]) for i, enc in enumerate(self.cont_encoders)]
        nodes = torch.stack(cat_nodes + cont_nodes, dim=1)
        return nodes + self.node_type.unsqueeze(0)

    def _nodes_from_soft(self, cat_probs: list[torch.Tensor], cont_scaled: torch.Tensor) -> torch.Tensor:
        cat_nodes = [probs @ emb.weight for probs, emb in zip(cat_probs, self.cat_embeddings)]
        cont_nodes = [enc(cont_scaled[:, i : i + 1]) for i, enc in enumerate(self.cont_encoders)]
        nodes = torch.stack(cat_nodes + cont_nodes, dim=1)
        return nodes + self.node_type.unsqueeze(0)

    def _predict_from_nodes(self, nodes: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        batch_size = nodes.size(0)
        if adj.dim() == 2:
            adj = adj.unsqueeze(0).expand(batch_size, -1, -1)
        x = F.gelu(self.gat1(nodes, adj))
        x = self.dropout(x)
        x = self.norm(self.gat2(x, adj) + nodes)
        x = F.gelu(x).reshape(batch_size, -1)
        x = self.mlp(x)
        return torch.cat([self.bending_head(x), self.axial_head(x)], dim=1)

    def forward(self, cat_ids: torch.Tensor, cont_scaled: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        return self._predict_from_nodes(self._nodes_from_hard(cat_ids, cont_scaled), adj)

    def forward_from_probs(
        self, cat_probs: list[torch.Tensor], cont_scaled: torch.Tensor, adj: torch.Tensor
    ) -> torch.Tensor:
        return self._predict_from_nodes(self._nodes_from_soft(cat_probs, cont_scaled), adj)


class OrigamiForwardTransformerTaskfit(nn.Module):
    """Forward Transformer with categorical/continuous tokens -> 6 log-stiffness targets."""

    def __init__(
        self,
        cat_cardinalities: tuple[int, int, int] = (2, 3, 3),
        cont_dim: int = 5,
        hidden_dim: int = 192,
        num_heads: int = 4,
        num_layers: int = 3,
        dropout: float = 0.12,
    ):
        super().__init__()
        self.num_cat = len(cat_cardinalities)
        self.cont_dim = cont_dim
        self.num_tokens = self.num_cat + cont_dim
        self.cat_embeddings = nn.ModuleList([nn.Embedding(card, hidden_dim) for card in cat_cardinalities])
        self.cont_encoders = nn.ModuleList([nn.Linear(1, hidden_dim) for _ in range(cont_dim)])
        self.type_encoding = nn.Parameter(torch.empty(1, self.num_tokens, hidden_dim))
        self.cls_token = nn.Parameter(torch.empty(1, 1, hidden_dim))
        nn.init.xavier_uniform_(self.type_encoding)
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
        self.transformer = nn.TransformerEncoder(layer, num_layers=num_layers)
        self.head = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.bending_head = nn.Linear(hidden_dim, 3)
        self.axial_head = nn.Linear(hidden_dim, 3)

    def _tokens_from_hard(self, cat_ids: torch.Tensor, cont_scaled: torch.Tensor) -> torch.Tensor:
        cat_tokens = [emb(cat_ids[:, i]) for i, emb in enumerate(self.cat_embeddings)]
        cont_tokens = [enc(cont_scaled[:, i : i + 1]) for i, enc in enumerate(self.cont_encoders)]
        return torch.stack(cat_tokens + cont_tokens, dim=1) + self.type_encoding

    def _tokens_from_soft(self, cat_probs: list[torch.Tensor], cont_scaled: torch.Tensor) -> torch.Tensor:
        cat_tokens = [probs @ emb.weight for probs, emb in zip(cat_probs, self.cat_embeddings)]
        cont_tokens = [enc(cont_scaled[:, i : i + 1]) for i, enc in enumerate(self.cont_encoders)]
        return torch.stack(cat_tokens + cont_tokens, dim=1) + self.type_encoding

    def _predict_from_tokens(self, tokens: torch.Tensor) -> torch.Tensor:
        cls = self.cls_token.expand(tokens.size(0), -1, -1)
        seq = torch.cat([cls, tokens], dim=1)
        feat = self.transformer(seq)[:, 0]
        feat = self.head(feat)
        return torch.cat([self.bending_head(feat), self.axial_head(feat)], dim=1)

    def forward(self, cat_ids: torch.Tensor, cont_scaled: torch.Tensor) -> torch.Tensor:
        return self._predict_from_tokens(self._tokens_from_hard(cat_ids, cont_scaled))

    def forward_from_probs(self, cat_probs: list[torch.Tensor], cont_scaled: torch.Tensor) -> torch.Tensor:
        return self._predict_from_tokens(self._tokens_from_soft(cat_probs, cont_scaled))


class OrigamiInverseResMLP(nn.Module):
    """Inverse baseline: 6 log-stiffness targets -> categorical logits + continuous parameters."""

    def __init__(
        self,
        curve_dim: int = 6,
        cont_dim: int = 5,
        hidden_dim: int = 256,
        num_blocks: int = 4,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(curve_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            *[ResidualMLPBlock(hidden_dim, dropout) for _ in range(num_blocks)],
        )
        self.pattern_head = nn.Linear(hidden_dim, 2)
        self.m_head = nn.Linear(hidden_dim, 3)
        self.n_head = nn.Linear(hidden_dim, 3)
        self.cont_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, cont_dim),
        )

    def forward(self, curve_scaled: torch.Tensor) -> dict[str, torch.Tensor]:
        x = self.encoder(curve_scaled)
        return {
            "pattern": self.pattern_head(x),
            "m": self.m_head(x),
            "n": self.n_head(x),
            "cont": self.cont_head(x),
        }


class OrigamiInverseDiscreteClassifier(nn.Module):
    """Predict only discrete origami variables from the 6 log-stiffness targets."""

    def __init__(
        self,
        curve_dim: int = 6,
        hidden_dim: int = 256,
        num_blocks: int = 3,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(curve_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            *[ResidualMLPBlock(hidden_dim, dropout) for _ in range(num_blocks)],
        )
        self.pattern_head = nn.Linear(hidden_dim, 2)
        self.m_head = nn.Linear(hidden_dim, 3)
        self.n_head = nn.Linear(hidden_dim, 3)

    def forward(self, curve_scaled: torch.Tensor) -> dict[str, torch.Tensor]:
        x = self.encoder(curve_scaled)
        return {
            "pattern": self.pattern_head(x),
            "m": self.m_head(x),
            "n": self.n_head(x),
        }


class OrigamiInverseCVAEHeaded(nn.Module):
    """CVAE inverse model with discrete heads and continuous regression head."""

    def __init__(
        self,
        curve_dim: int = 6,
        cont_dim: int = 5,
        latent_dim: int = 8,
        hidden_dim: int = 512,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.latent_dim = latent_dim
        self.condition_encoder = nn.Sequential(
            nn.Linear(curve_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            ResidualMLPBlock(hidden_dim, dropout),
        )
        self.target_encoder = nn.Sequential(
            nn.Linear(3 + cont_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.posterior = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, latent_dim * 2),
        )
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim + latent_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            ResidualMLPBlock(hidden_dim, dropout),
        )
        self.pattern_head = nn.Linear(hidden_dim, 2)
        self.m_head = nn.Linear(hidden_dim, 3)
        self.n_head = nn.Linear(hidden_dim, 3)
        self.cont_head = nn.Linear(hidden_dim, cont_dim)

    @staticmethod
    def reparameterize(mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        return mu + torch.randn_like(mu) * torch.exp(0.5 * logvar)

    def _decode(self, cond_feat: torch.Tensor, z: torch.Tensor) -> dict[str, torch.Tensor]:
        x = self.decoder(torch.cat([cond_feat, z], dim=1))
        return {
            "pattern": self.pattern_head(x),
            "m": self.m_head(x),
            "n": self.n_head(x),
            "cont": self.cont_head(x),
        }

    def forward(
        self, curve_scaled: torch.Tensor, cat_ids: torch.Tensor, cont_scaled: torch.Tensor
    ) -> tuple[dict[str, torch.Tensor], torch.Tensor, torch.Tensor]:
        cond_feat = self.condition_encoder(curve_scaled)
        target = torch.cat([cat_ids.float(), cont_scaled], dim=1)
        target_feat = self.target_encoder(target)
        mu, logvar = torch.chunk(self.posterior(torch.cat([cond_feat, target_feat], dim=1)), 2, dim=1)
        return self._decode(cond_feat, self.reparameterize(mu, logvar)), mu, logvar

    @torch.no_grad()
    def inference(self, curve_scaled: torch.Tensor, z: torch.Tensor | None = None) -> dict[str, torch.Tensor]:
        cond_feat = self.condition_encoder(curve_scaled)
        if z is None:
            z = torch.randn(curve_scaled.size(0), self.latent_dim, device=curve_scaled.device)
        return self._decode(cond_feat, z)


class SinusoidalTimeEmbedding(nn.Module):
    def __init__(self, dim: int):
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


class OrigamiInverseDiffusionTaskfit(nn.Module):
    """Conditional denoiser for mixed or continuous-only inverse design vectors."""

    def __init__(
        self,
        target_dim: int = 8,
        curve_dim: int = 6,
        cond_extra_dim: int = 0,
        time_dim: int = 64,
        cond_dim: int = 128,
        hidden_dim: int = 512,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.cond_extra_dim = cond_extra_dim
        self.time_emb = nn.Sequential(
            SinusoidalTimeEmbedding(time_dim),
            nn.Linear(time_dim, time_dim),
            nn.GELU(),
        )
        self.cond_encoder = nn.Sequential(
            nn.Linear(curve_dim + cond_extra_dim, cond_dim),
            nn.LayerNorm(cond_dim),
            nn.GELU(),
            ResidualMLPBlock(cond_dim, dropout),
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
        curve_scaled: torch.Tensor,
        cond_extra: torch.Tensor | None = None,
    ) -> torch.Tensor:
        time_feat = self.time_emb(t)
        if self.cond_extra_dim:
            if cond_extra is None:
                cond_extra = torch.zeros(
                    curve_scaled.size(0),
                    self.cond_extra_dim,
                    dtype=curve_scaled.dtype,
                    device=curve_scaled.device,
                )
            cond_input = torch.cat([curve_scaled, cond_extra], dim=1)
        else:
            cond_input = curve_scaled
        cond_feat = self.cond_encoder(cond_input)
        return self.net(torch.cat([x_t, time_feat, cond_feat], dim=1))
