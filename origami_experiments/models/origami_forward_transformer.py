"""Transformer Forward model adapted for Origami Sheet data (8 params -> 6 stiffness targets)."""

import torch
import torch.nn as nn


class OrigamiForwardTransformer(nn.Module):
    """Forward Transformer: 8 origami params -> 6 stiffness values.
    Treats each parameter as a token with learnable type encoding,
    uses [CLS] token aggregation + Transformer encoder + MLP head."""

    def __init__(
        self,
        num_parameters=8,
        hidden_dim=256,
        num_heads=8,
        num_layers=4,
        out_dim=6,
        dropout=0.1,
    ):
        super().__init__()
        self.num_parameters = num_parameters
        self.hidden_dim = hidden_dim

        self.param_embedding = nn.Linear(1, hidden_dim)
        self.type_encoding = nn.Parameter(torch.randn(1, num_parameters, hidden_dim))
        self.cls_token = nn.Parameter(torch.randn(1, 1, hidden_dim))

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.mlp_head = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, out_dim),
        )

    def forward(self, x):
        batch_size = x.size(0)
        x = x.unsqueeze(-1)
        tokens = self.param_embedding(x)
        tokens = tokens + self.type_encoding
        cls_tokens = self.cls_token.expand(batch_size, -1, -1)
        x_seq = torch.cat((cls_tokens, tokens), dim=1)
        out_seq = self.transformer(x_seq)
        cls_out = out_seq[:, 0, :]
        return self.mlp_head(cls_out)
