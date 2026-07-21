"""GNN Forward model adapted for Origami Sheet data (8 parameters -> 6 stiffness targets)."""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import DenseGATConv


class ResidualBlock(nn.Module):
    def __init__(self, units, dropout_rate=0.1):
        super().__init__()
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
        return x + shortcut


class ParameterGraphEncoder(nn.Module):
    def __init__(self, num_nodes, input_dim=1, hidden_dim=64):
        super().__init__()
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


class OrigamiGNNForward(nn.Module):
    """Forward GNN: 8 origami params -> 6 stiffness values."""

    def __init__(
        self,
        num_inputs=8,
        num_outputs=6,
        gnn_hidden_dim=256,
        gnn_heads=8,
        units_layer1=512,
        units_layer2=256,
        units_layer3=128,
        units_layer4=64,
        dropout_rate=0.1,
    ):
        super().__init__()
        self.num_nodes = num_inputs
        self.encoder = ParameterGraphEncoder(
            num_nodes=num_inputs, input_dim=1, hidden_dim=gnn_hidden_dim
        )
        self.gnn1 = DenseGATConv(gnn_hidden_dim, gnn_hidden_dim, heads=gnn_heads, concat=False)
        self.gnn2 = DenseGATConv(gnn_hidden_dim, gnn_hidden_dim, heads=gnn_heads, concat=False)
        self.ln_gnn = nn.LayerNorm(gnn_hidden_dim)
        self.flatten_dim = num_inputs * gnn_hidden_dim
        self.proj = nn.Linear(self.flatten_dim, units_layer1)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout_rate)
        self.res_block1 = ResidualBlock(units_layer1, dropout_rate)
        self.dense2 = nn.Linear(units_layer1, units_layer2)
        self.res_block2 = ResidualBlock(units_layer2, dropout_rate)
        self.dense3 = nn.Linear(units_layer2, units_layer3)
        self.res_block3 = ResidualBlock(units_layer3, dropout_rate)
        self.dense4 = nn.Linear(units_layer3, units_layer4)
        self.output_layer = nn.Linear(units_layer4, num_outputs)

    def forward(self, x, adj):
        batch_size = x.size(0)
        x_encoded = self.encoder(x)
        if adj.dim() == 2:
            adj = adj.unsqueeze(0).repeat(batch_size, 1, 1)
        x_graph = self.gnn1(x_encoded, adj)
        x_graph = F.gelu(x_graph)
        x_graph = self.dropout(x_graph)
        x_graph = self.gnn2(x_graph, adj)
        x_graph = self.ln_gnn(x_graph)
        x_combined = x_graph + x_encoded
        x_combined = F.gelu(x_combined)
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
        return self.output_layer(x)
