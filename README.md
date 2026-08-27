# Small++: Mechanism-Resolved Inverse Design of Graded TPMS

> Small++ develops evidence-gated inverse design for graded triply periodic minimal surface structures, connecting target stress–strain responses to realizable geometries and distinguishable local collapse mechanisms.

Small++ 面向渐变三周期极小曲面（TPMS）的可信逆向设计。当前主线不是单纯比较神经网络误差，而是在预先声明的几何、材料、制造和加载域内研究：目标响应是否有证据支持、哪些不同局部塌缩路径可以实现近似响应，以及何时应接受候选、延迟裁决或拒绝过度自信的输出。

## 核心研究问题

- 目标应力–应变曲线在声明的渐变 TPMS 设计域与有限搜索预算内是否存在已验证候选？
- 曲线相近的候选是否可能具有可区分的首塌区域、塌缩顺序或局部化路径？
- 哪些候选靠近模式转换边界，并对厚度、材料、摩擦或加载偏心等扰动更敏感？
- 几何硬约束、前向验证和不确定性门控能否提高 Diffusion 候选的联合成功率？

## 技术路线

1. 确定性渐变 Gyroid/TPMS 几何编译与制造约束检查；
2. Abaqus 曲线、局部场、接触与塌缩事件数据；
3. Graph Transformer/基线模型联合预测全局曲线和局部机制；
4. Conditional Diffusion 提议多个满足方法约束的候选；
5. 几何筛选、前向复核、不确定性排序和 `accept` / `defer` / `no feasible design found within the declared domain and budget` 门控；
6. 密封数值裁决与小规模重复打印压缩实验。

## 当前已实现

- **M01–M03**：编译器契约、渐变 Gyroid 场、有限连续 CSG、表面网格验证和二进制 STL；
- **M04**：Legacy/Physical 双描述符接口、Gate-0 冻结与溯源约束；
- **Paper A 模型层**：曲线/参数契约、编译器感知图、前向基线、GC-GraphFormer 和方法约束 Diffusion 接口；
- **验证接口**：MATLAB 与 Python 单元测试覆盖上述核心模块。

真实 discovery、30-case confirmation、正式 Abaqus 主数据、3D 打印与压缩实验尚未完成，因此当前仓库不声称已完成论文级物理验证。

## 仓库结构

- [`paper_A_reliable_inverse_design/geometry_compiler_matlab/`](paper_A_reliable_inverse_design/geometry_compiler_matlab/)：M01–M04 几何与描述符编译器；
- [`paper_A_reliable_inverse_design/gc_graphformer/`](paper_A_reliable_inverse_design/gc_graphformer/)：图构建、基线、GC-GraphFormer 和 Diffusion 约束接口；
- [`paper_A_reliable_inverse_design/tests/`](paper_A_reliable_inverse_design/tests/)：Python 合约与模型测试；
- [`paper_A_reliable_inverse_design/docs/`](paper_A_reliable_inverse_design/docs/)：研究计划、规格、实施记录与报告；
- [`.qoder/skills/executing-research-experiments/`](.qoder/skills/executing-research-experiments/)：实验交付与证据审计工作流。

## 快速验证

在仓库根目录运行：

```powershell
python -m pytest paper_A_reliable_inverse_design/tests -q
matlab -batch "cd('paper_A_reliable_inverse_design/geometry_compiler_matlab'); run_tests"
```

完整研究入口见 [`CURRENT_PAPER_A_PLAN.md`](paper_A_reliable_inverse_design/docs/CURRENT_PAPER_A_PLAN.md)；M03 用法见 [`M03_USAGE.md`](paper_A_reliable_inverse_design/geometry_compiler_matlab/docs/M03_USAGE.md)；M04 与仿真实验接手信息见 [`SIMULATION_EXPERIMENT_MEMORY.md`](paper_A_reliable_inverse_design/geometry_compiler_matlab/docs/SIMULATION_EXPERIMENT_MEMORY.md)。

## 数据与证据约定

- 不提交模型权重、打包数据集、原始 Abaqus 输出、日志、缓存和其他可再生产物；
- `.qoder/repowiki/` 为自动生成资料，不作为权威研究记录；
- “可实现”仅指预注册设计域、容差和有限预算下的经验可实现性；
- `no feasible design found within the declared domain and budget` 不等于证明物理上绝对不可实现；
- Graph Transformer 与 Diffusion 是解决研究问题的工具，不作为脱离证据链的创新声明。

## 路线图

1. 完成 Small 历史几何与 FE 复现 Gate 0；
2. 冻结局部事件、扰动场景和数据契约；
3. 生成名义与局部场 Abaqus 数据，开展机制发现；
4. 训练并比较前向验证器，完成多候选逆向门控；
5. 执行密封目标和配对扰动裁决；
6. 锁定打印设计并开展重复压缩与侧面视频验证。

## 关键文档

- [机制分辨经验可实现域正式设计](paper_A_reliable_inverse_design/docs/superpowers/specs/2026-07-31-paper-a-mechanism-resolved-attainability-design.md)
- [导师汇报讨论报告](paper_A_reliable_inverse_design/docs/reports/2026-07-31-advisor-discussion-report.md)
- [项目记录与理解指南](paper_A_reliable_inverse_design/docs/PROJECT_RECORD_AND_LEARNING_GUIDE.md)
- [GC-GraphFormer 第一里程碑](paper_A_reliable_inverse_design/docs/superpowers/reports/2026-08-06-paper-a-gc-graphformer-milestone.md)
