# Abaqus 仿真文件

## 当前方向（2026-10-08 整理）

**此后实验唯一基线为 M09：Explicit 显式求解、z 向渐变、z 向加载、25% 压缩；仿真已全量交师弟。M08 及以前只作历史记录。**

参数与遗留事项以 [当前仿真记录](../../simulation_runs_202609/CURRENT_SIMULATION_SETTINGS.md) 为入口。
`current_config.json` 已登记 M09 参数：PDE 网格（归一化 HMax=0.05、HGrad=1.2）、计划 C3D10 二阶单元、x/y 周期边界、默认无质量缩放、T=0.1s、SMOOTH STEP、double=both、作者原 TPU 材料。
单元和周期边界等实现仍须验证；截至本次整理未找到 M09 验收回传。该文件为声明式参数登记，尚无可直接消费它的已验收 M09 建模器；不运行本目录的旧生成器来代替 M09。

## 历史入口（2026-09-24 脚本优先，x 向 Standard）

`script_first_config_20260924.json` 保存旧参数，`build_current_model.py` 仅读取该归档，不用于当前 M09。以下命令仅用于历史复现，不作为后续实验入口：

历史生成器依赖本地作者仓库（路径及 SHA-256 见归档配置）与 `audits/m05_small_mechanism_pilot_20260919/scripts/gen_build_model.py`；本 PR 不打包这些旧依赖，不将该工具声明为独立可运行的 M09 管线。

```text
python build_current_model.py <已验收mesh.inp绝对路径> <全新输出目录> <唯一job_name>
```

生成 CAE 建模脚本及配置/来源快照，不自动建模、datacheck 或提交求解。历史基线为 x 向、Standard、25%（-10mm）、原材料、六面位移约束、场/历史各20区间；具体见 `docs/handoffs/2026-09-24-script-first-alignment.md`。旧 M06 工具为 24% 历史批次。

## 以下是早期目录占位说明（不代表当前整个工作区状态）

早期目录创建时未收录 Abaqus 工件。如今本地 `audits/` 已有 INP/ODB 等结果，不能沿用该占位说明断言整个工作区无仿真文件；ODB 交接清单见当前仿真记录。

上级目录中的 `abaqus_scratch` 不在本工作区写入范围内，未移动或修改。
