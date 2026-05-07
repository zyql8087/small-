import torch
import torch.nn as nn


class TPMSForwardTransformer(nn.Module):
    def __init__(
            self,
            num_parameters=9,  # TPMS 的输入参数数量 (Vx, Vy, Vz, w, 及 5 个几何参数)
            hidden_dim=128,  # Transformer 隐藏层维度
            num_heads=4,  # 多头注意力头数
            num_layers=3,  # Transformer 编码器层数
            out_dim=21,  # 输出维度 (应力-应变曲线上的 21 个离散点)
            dropout=0.1
    ):
        super(TPMSForwardTransformer, self).__init__()
        self.num_parameters = num_parameters
        self.hidden_dim = hidden_dim

        # 1. 特征嵌入层 (Parameter Tokenization)
        # 将每个一维的标量参数映射为 hidden_dim 维的特征向量
        self.param_embedding = nn.Linear(1, hidden_dim)

        # 2. 参数类型编码 (Parameter-Type Encoding)
        # 这是一个可学习的嵌入矩阵，用于区分 9 个不同的物理参数
        self.type_encoding = nn.Parameter(torch.randn(1, num_parameters, hidden_dim))

        # 3. 引入一个全局信息的虚拟 Token (类似于 Vision Transformer 的 [CLS] token)
        # 用于汇聚 9 个参数的全局信息以进行最终的曲线预测
        self.cls_token = nn.Parameter(torch.randn(1, 1, hidden_dim))

        # 4. Transformer Encoder 核心模块
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            activation='gelu',
            batch_first=True  # 确保输入格式为 [Batch, Seq_len, Dim]
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # 5. 预测头 (Prediction Head)
        # 基于 [CLS] token 的特征输出应力-应变曲线
        self.mlp_head = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, out_dim)
        )

    def forward(self, x):
        """
        前向传播函数
        x: TPMS 的结构参数输入矩阵，形状应为 [batch_size, 9]
        """
        batch_size = x.size(0)

        # 调整 x 的形状为 [batch_size, 9, 1] 以便进行 Token 化映射
        x = x.unsqueeze(-1)

        # 1. Token 嵌入 -> 形状变为 [batch_size, 9, hidden_dim]
        tokens = self.param_embedding(x)

        # 2. 加上参数类型编码，赋予物理意义
        tokens = tokens + self.type_encoding

        # 3. 拼接 [CLS] token -> 序列长度变为 10
        # cls_tokens 形状: [batch_size, 1, hidden_dim]
        cls_tokens = self.cls_token.expand(batch_size, -1, -1)
        x_seq = torch.cat((cls_tokens, tokens), dim=1)  # 形状: [batch_size, 10, hidden_dim]

        # 4. 通过 Transformer 编码器提取全局耦合特征
        out_seq = self.transformer(x_seq)

        # 5. 提取经过注意力计算后的 [CLS] token 特征 (位于序列的第一位)
        cls_out = out_seq[:, 0, :]  # 形状: [batch_size, hidden_dim]

        # 6. 预测力学曲线
        pred_curve = self.mlp_head(cls_out)  # 形状: [batch_size, 21]

        return pred_curve