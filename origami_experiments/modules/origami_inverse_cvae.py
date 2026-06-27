"""CVAE Inverse model adapted for Origami Sheet data (6 stiffness values -> 8 parameters)."""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ResBlock1D(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.ln1 = nn.GroupNorm(4, out_channels)
        self.act = nn.GELU()
        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.ln2 = nn.GroupNorm(4, out_channels)
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv1d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.GroupNorm(4, out_channels),
            )

    def forward(self, x):
        out = self.act(self.ln1(self.conv1(x)))
        out = self.ln2(self.conv2(out))
        out += self.shortcut(x)
        return self.act(out)


class CurveEncoder(nn.Module):
    def __init__(self, feature_dim=128):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=3, padding=1),
            nn.GroupNorm(4, 32),
            nn.GELU(),
        )
        self.layer1 = ResBlock1D(32, 64, stride=2)
        self.layer2 = ResBlock1D(64, 128, stride=2)
        self.layer3 = ResBlock1D(128, feature_dim, stride=2)
        self.pool = nn.AdaptiveAvgPool1d(1)

    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(1)
        x = self.stem(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.pool(x).squeeze(-1)
        return x


class OrigamiCVAE(nn.Module):
    """CVAE Inverse: 6 stiffness values (condition) -> 8 origami parameters (target)."""

    def __init__(self, param_dim=8, curve_points=6, latent_dim=4, hidden_dim=512):
        super().__init__()
        self.latent_dim = latent_dim
        self.condition_encoder = CurveEncoder(feature_dim=128)

        self.encoder_fc = nn.Sequential(
            nn.Linear(param_dim + 128, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, latent_dim * 2),
        )

        self.decoder_fc = nn.Sequential(
            nn.Linear(latent_dim + 128, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, param_dim),
        )

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, params, curves, condition_dropout_prob=0.0):
        cond_feat = self.condition_encoder(curves)
        encoder_input = torch.cat([params, cond_feat], dim=1)
        h = self.encoder_fc(encoder_input)
        mu, logvar = torch.chunk(h, 2, dim=1)
        z = self.reparameterize(mu, logvar)

        if self.training and condition_dropout_prob > 0:
            mask = torch.bernoulli(torch.full_like(cond_feat, 1 - condition_dropout_prob))
            cond_feat_input = cond_feat * mask
        else:
            cond_feat_input = cond_feat

        decoder_input = torch.cat([z, cond_feat_input], dim=1)
        recon_params = self.decoder_fc(decoder_input)
        return recon_params, mu, logvar

    @torch.no_grad()
    def inference(self, curves, z=None):
        batch_size = curves.size(0)
        cond_feat = self.condition_encoder(curves)
        if z is None:
            z = torch.randn(batch_size, self.latent_dim).to(curves.device)
        decoder_input = torch.cat([z, cond_feat], dim=1)
        return self.decoder_fc(decoder_input)
