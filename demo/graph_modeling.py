import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# 1. 加载数据 (合并所有类别以获得全局视角)
files = [
    'origin_code/train.xlsx - class1.csv',
    'origin_code/train.xlsx - class2.csv',
    'origin_code/train.xlsx - class12.csv'
]
dfs = [pd.read_csv(f) for f in files]
df_all = pd.concat(dfs, axis=0)

# 定义9个输入参数
input_cols = ['V1a', 'V1b', 'V1c', 'w', 'relativeVolume', 'relativeArea', 'thickness', 'poreDiameter', 'areaMean']
data_matrix = df_all[input_cols]

# 2. 计算相关性矩阵
corr_matrix = data_matrix.corr().abs()

# 3. 使用 NetworkX 构建图
G = nx.Graph()
G.add_nodes_from(input_cols)

# 阈值设定：仅连接相关性 > 0.3 的参数，或者构建全连接图带权重
threshold = 0.3
for i in range(len(input_cols)):
    for j in range(i + 1, len(input_cols)):
        weight = corr_matrix.iloc[i, j]
        if weight > threshold:
            G.add_edge(input_cols[i], input_cols[j], weight=weight)

# 4. 可视化图结构 (可选，用于验证)
plt.figure(figsize=(10, 8))
pos = nx.spring_layout(G, seed=42)
nx.draw_networkx_nodes(G, pos, node_size=2000, node_color='lightblue')
nx.draw_networkx_edges(G, pos, width=[G[u][v]['weight']*2 for u,v in G.edges()])
nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
plt.title("Parameter Interaction Graph (Correlation based)")
plt.show()

print("Graph Edges defined by correlation:")
print(G.edges(data=True))