import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import DenseGATConv
import math

# 配置检测
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"[GNN_Module] Running on device: {device}")
if torch.cuda.is_available():
    torch.backends.cudnn.benchmark = True
    torch.backends.cuda.matmul.allow_tf32 = True

# 基础组件
class ResidualBlock(nn.Module):
    def __init__(self, units, dropout_rate=0.1):
        super(ResidualBlock, self).__init__()
        self.dense1 = nn.Linear(units, units)
        self.dense2 = nn.Linear(units, units)
        self.act = nn.GELU()
        self.ln = nn.LayerNorm(units)
        self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x):
        shortcut = x
        x = self.ln(x)
        x = self.act(self.dense1(x))
        x = self.dropout(x)
        x = self.dense2(x)
        x = x + shortcut
        return x


class ParameterGraphEncoder(nn.Module):
    def __init__(self, num_nodes, input_dim=1, hidden_dim=64):
        super(ParameterGraphEncoder, self).__init__()
        self.num_nodes = num_nodes
        self.node_encoders = nn.ModuleList([
            nn.Linear(input_dim, hidden_dim) for _ in range(num_nodes)
        ])
        self.node_type_emb = nn.Parameter(torch.Tensor(num_nodes, hidden_dim))
        nn.init.xavier_uniform_(self.node_type_emb)

    def forward(self, x):
        node_features = []
        for i in range(self.num_nodes):
            val = x[:, i].unsqueeze(1)
            emb = self.node_encoders[i](val)
            emb = emb + self.node_type_emb[i].unsqueeze(0)
            node_features.append(emb)
        return torch.stack(node_features, dim=1)


# 前向模型
class GNNForwardNetwork(nn.Module):
    def __init__(self, units_layer1=1024, units_layer2=1600, units_layer3=1600, units_layer4=512,
                 gnn_hidden_dim=256, gnn_heads=8, dropout_rate=0.1):
        super(GNNForwardNetwork, self).__init__()
        self.num_nodes = 9
        self.encoder = ParameterGraphEncoder(num_nodes=self.num_nodes, input_dim=1, hidden_dim=gnn_hidden_dim)
        self.gnn1 = DenseGATConv(gnn_hidden_dim, gnn_hidden_dim, heads=gnn_heads, concat=False)
        self.gnn2 = DenseGATConv(gnn_hidden_dim, gnn_hidden_dim, heads=gnn_heads, concat=False)
        self.ln_gnn = nn.LayerNorm(gnn_hidden_dim)
        self.flatten_dim = self.num_nodes * gnn_hidden_dim
        self.proj = nn.Linear(self.flatten_dim, units_layer1)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout_rate)

        self.res_block1 = ResidualBlock(units_layer1, dropout_rate)
        self.dense2 = nn.Linear(units_layer1, units_layer2)
        self.res_block2 = ResidualBlock(units_layer2, dropout_rate)
        self.dense3 = nn.Linear(units_layer2, units_layer3)
        self.res_block3 = ResidualBlock(units_layer3, dropout_rate)
        self.dense4 = nn.Linear(units_layer3, units_layer4)
        self.output_layer = nn.Linear(units_layer4, 20)

    def forward(self, x, adj):
        batch_size = x.size(0)
        x_encoded = self.encoder(x)
        if adj.dim() == 2: adj = adj.unsqueeze(0).repeat(batch_size, 1, 1)
        x_graph = self.gnn1(x_encoded, adj)
        x_graph = F.relu(x_graph)
        x_graph = self.dropout(x_graph)
        x_graph = self.gnn2(x_graph, adj)
        x_graph = self.ln_gnn(x_graph)
        x_combined = x_graph + x_encoded
        x_combined = F.relu(x_combined)
        x_flat = x_combined.view(batch_size, -1)
        x = self.proj(x_flat)
        x = self.act(x)
        x = self.dropout(x)
        x = self.res_block1(x)
        x = self.act(self.dense2(x))
        x = self.dropout(x)
        x = self.res_block2(x)
        x = self.act(self.dense3(x))
        x = self.dropout(x)
        x = self.res_block3(x)
        x = self.act(self.dense4(x))
        out = self.output_layer(x)
        return out


class ResNet1DBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, dropout_rate=0.1):
        super(ResNet1DBlock, self).__init__()
        self.conv1 = nn.Conv1d(
            in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False
        )
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.conv2 = nn.Conv1d(
            out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False
        )
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
        x = self.act(x)
        return x


class ResNet1DInverse(nn.Module):
    """
    Inverse model:
    input  - stress curve tensor of shape [batch, 20]
    output - TPMS parameters tensor of shape [batch, 9]
    """

    def __init__(self, dropout_rate=0.1):
        super(ResNet1DInverse, self).__init__()
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
            nn.Linear(256, 9),
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


# # ----------------------------------------------------------------
# # 反向模型 (Inverse Model)
# # ----------------------------------------------------------------



# class SEBlock(nn.Module):
#     def __init__(self, channel, reduction=16):
#         super(SEBlock, self).__init__()
#         self.avg_pool = nn.AdaptiveAvgPool1d(1)
#         self.fc = nn.Sequential(
#             nn.Linear(channel, channel // reduction, bias=False),
#             nn.ReLU(inplace=True),
#             nn.Linear(channel // reduction, channel, bias=False),
#             nn.Sigmoid()
#         )
#
#     def forward(self, x):
#         b, c, _ = x.size()
#         y = self.avg_pool(x).view(b, c)
#         y = self.fc(y).view(b, c, 1)
#         return x * y.expand_as(x)
#
#
# class CNNInverseNetwork(nn.Module):
#     def __init__(self,
#                  units_layer1=1024,
#                  units_layer2=2048,
#                  units_layer3=2048,
#                  units_layer4=512,
#                  dropout_rate=0.2):  # Dropout 提升至 0.2
#         super(CNNInverseNetwork, self).__init__()
#
#         # 1D CNN 特征提取器
#         # 输入: (Batch, 1, 20)
#         self.features = nn.Sequential(
#             # L1: 1 -> 64
#             nn.Conv1d(1, 64, kernel_size=3, padding=1),
#             nn.BatchNorm1d(64),
#             nn.GELU(),
#
#             # L2: 64 -> 128
#             nn.Conv1d(64, 128, kernel_size=3, padding=1),
#             nn.BatchNorm1d(128),
#             nn.GELU(),
#             SEBlock(128),
#
#             # L3: 128 -> 256
#             nn.Conv1d(128, 256, kernel_size=3, padding=1),
#             nn.BatchNorm1d(256),
#             nn.GELU(),
#             # 【核心修改】移除 AdaptiveAvgPool1d(1)
#             # 我们要保留 (256, 20) 的完整张量，不丢失任何位置信息
#         )
#
#         # 投影层：输入维度 = 256 * 20 = 5120
#         self.flatten_dim = 256 * 20
#         self.proj = nn.Linear(self.flatten_dim, units_layer1)
#         self.act = nn.GELU()
#         self.dropout = nn.Dropout(dropout_rate)
#
#         # ResMLP 解码器
#         self.res_block1 = ResidualBlock(units_layer1, dropout_rate)
#         self.dense2 = nn.Linear(units_layer1, units_layer2)
#         self.res_block2 = ResidualBlock(units_layer2, dropout_rate)
#         self.dense3 = nn.Linear(units_layer2, units_layer3)
#         self.res_block3 = ResidualBlock(units_layer3, dropout_rate)
#         self.dense4 = nn.Linear(units_layer3, units_layer4)
#
#         self.output_layer = nn.Linear(units_layer4, 9)
#
#     def forward(self, x):
#         # x: (Batch, 20) -> (Batch, 1, 20)
#         x = x.unsqueeze(1)
#
#         # CNN
#         x = self.features(x)  # (Batch, 256, 20)
#
#         # Flatten: 展开为 (Batch, 5120)
#         # 这里保留了所有时序点的特征
#         x = x.view(x.size(0), -1)
#
#         # MLP
#         x = self.proj(x)
#         x = self.act(x)
#         x = self.dropout(x)
#
#         x = self.res_block1(x)
#         x = self.act(self.dense2(x))
#         x = self.dropout(x)
#         x = self.res_block2(x)
#         x = self.act(self.dense3(x))
#         x = self.dropout(x)
#         x = self.res_block3(x)
#
#         x = self.act(self.dense4(x))
#         out = self.output_layer(x)
#
#         return out
