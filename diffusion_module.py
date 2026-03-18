import torch
import torch.nn as nn
import math


class SinusoidalPositionEmbeddings(nn.Module):
    """时间步的正弦位置编码"""

    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, time):
        device = time.device
        half_dim = self.dim // 2
        embeddings = math.log(10000) / (half_dim - 1)
        embeddings = torch.exp(torch.arange(half_dim, device=device) * -embeddings)
        embeddings = time[:, None] * embeddings[None, :]
        embeddings = torch.cat((embeddings.sin(), embeddings.cos()), dim=-1)
        return embeddings


class ConditionalDenoisingMLP(nn.Module):
    def __init__(
            self,
            param_dim=9,  # 预测的 TPMS 参数维度
            curve_dim=21,  # 目标 S-S 曲线维度
            time_emb_dim=64,  # 时间步嵌入维度
            cond_emb_dim=128,  # 条件(曲线)嵌入维度
            hidden_dim=256  # MLP 隐藏层维度
    ):
        super().__init__()

        # 1. 时间嵌入层
        self.time_mlp = nn.Sequential(
            SinusoidalPositionEmbeddings(time_emb_dim),
            nn.Linear(time_emb_dim, time_emb_dim * 2),
            nn.GELU(),
            nn.Linear(time_emb_dim * 2, time_emb_dim)
        )

        # 2. 条件(曲线)编码器
        self.cond_encoder = nn.Sequential(
            nn.Linear(curve_dim, cond_emb_dim),
            nn.GELU(),
            nn.Linear(cond_emb_dim, cond_emb_dim)
        )

        # 3. 核心去噪 MLP (输入为: 噪声参数 + 时间特征 + 条件特征)
        # 采用最稳健的拼接(Concatenation)方式融合特征
        input_dim = param_dim + time_emb_dim + cond_emb_dim

        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, param_dim)  # 输出预测的噪声，维度与 param_dim 相同
        )

    def forward(self, x_t, time, condition_curve):
        """
        x_t: 加噪后的 9 维结构参数 [Batch, 9]
        time: 时间步 [Batch]
        condition_curve: 目标 S-S 曲线 [Batch, 21]
        """
        # 获取时间嵌入和条件嵌入
        t_emb = self.time_mlp(time)  # [Batch, time_emb_dim]
        c_emb = self.cond_encoder(condition_curve)  # [Batch, cond_emb_dim]

        # 拼接所有特征
        x_input = torch.cat([x_t, t_emb, c_emb], dim=-1)

        # 预测并输出噪声
        predicted_noise = self.net(x_input)

        return predicted_noise