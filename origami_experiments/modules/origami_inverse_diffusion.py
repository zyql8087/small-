"""Diffusion inverse model adapted for Origami Sheet data (6 stiffness values -> 8 parameters)."""

import math
import torch
import torch.nn as nn


class ResidualConvBlock1D(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.norm1 = nn.GroupNorm(4, out_channels)
        self.act = nn.GELU()
        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.norm2 = nn.GroupNorm(4, out_channels)
        self.shortcut = nn.Identity()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv1d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.GroupNorm(4, out_channels),
            )

    def forward(self, x):
        out = self.act(self.norm1(self.conv1(x)))
        out = self.norm2(self.conv2(out))
        return self.act(out + self.shortcut(x))


class SinusoidalPositionEmbeddings(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, time):
        device = time.device
        half_dim = self.dim // 2
        embeddings = math.log(10000) / (half_dim - 1)
        embeddings = torch.exp(torch.arange(half_dim, device=device) * -embeddings)
        embeddings = time[:, None] * embeddings[None, :]
        return torch.cat((embeddings.sin(), embeddings.cos()), dim=-1)


class OrigamiConditionalDenoisingMLP(nn.Module):
    """Diffusion Inverse: 6 stiffness curve + timestep -> denoise 8 origami parameters."""

    def __init__(
        self,
        param_dim=8,
        curve_dim=6,
        time_emb_dim=64,
        cond_emb_dim=128,
        hidden_dim=512,
    ):
        super().__init__()
        self.time_mlp = nn.Sequential(
            SinusoidalPositionEmbeddings(time_emb_dim),
            nn.Linear(time_emb_dim, time_emb_dim * 2),
            nn.GELU(),
            nn.Linear(time_emb_dim * 2, time_emb_dim),
        )

        self.cond_encoder = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=3, padding=1, bias=False),
            nn.GroupNorm(4, 32),
            nn.GELU(),
            ResidualConvBlock1D(32, 64, stride=2),
            ResidualConvBlock1D(64, 128, stride=2),
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(128, cond_emb_dim),
            nn.GELU(),
            nn.Linear(cond_emb_dim, cond_emb_dim),
        )

        input_dim = param_dim + time_emb_dim + cond_emb_dim
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, param_dim),
        )

    def forward(self, x_t, time, condition_curve):
        t_emb = self.time_mlp(time)
        c_emb = self.cond_encoder(condition_curve.unsqueeze(1))
        x_input = torch.cat([x_t, t_emb, c_emb], dim=-1)
        return self.net(x_input)
