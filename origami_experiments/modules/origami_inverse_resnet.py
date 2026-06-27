"""ResNet1D Inverse model adapted for Origami Sheet data (6 stiffness values -> 8 parameters)."""

import torch
import torch.nn as nn


class ResNet1DBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, dropout_rate=0.1):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm1d(out_channels)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout_rate)
        self.shortcut = nn.Identity()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv1d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm1d(out_channels),
            )

    def forward(self, x):
        residual = self.shortcut(x)
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.dropout(x)
        x = self.conv2(x)
        x = self.bn2(x)
        x = x + residual
        return self.act(x)


class OrigamiResNet1DInverse(nn.Module):
    """ResNet1D Inverse: 6 stiffness values -> 8 origami parameters."""

    def __init__(self, dropout_rate=0.1, num_outputs=8):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv1d(1, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm1d(64),
            nn.GELU(),
        )
        self.layer1 = ResNet1DBlock(64, 64, stride=1, dropout_rate=dropout_rate)
        self.layer2 = ResNet1DBlock(64, 128, stride=2, dropout_rate=dropout_rate)
        self.layer3 = ResNet1DBlock(128, 256, stride=2, dropout_rate=dropout_rate)
        self.layer4 = ResNet1DBlock(256, 256, stride=1, dropout_rate=dropout_rate)
        self.pool = nn.AdaptiveAvgPool1d(1)

        self.head = nn.Sequential(
            nn.Linear(256, 512),
            nn.LayerNorm(512),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(512, 256),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(256, num_outputs),
        )

    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(1)
        x = self.stem(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.pool(x).squeeze(-1)
        return self.head(x)
