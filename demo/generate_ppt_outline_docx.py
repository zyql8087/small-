import os
import zipfile
from typing import Optional
from xml.sax.saxutils import escape


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "TPMS_项目汇报_PPT逐页文案版.docx")


SECTIONS = [
    {
        "title": "封面页：项目名称与阶段定位",
        "bullets": [
            "项目主题：TPMS 力学超材料前向预测与后向逆向设计。",
            "阶段定位：完成主线架构重构、模型重训、闭环筛选、集成学习与 baseline 对比。",
            "本阶段目标：从“能跑通”推进到“可验证、可对比、可汇报”。",
            "汇报重点：模型结构调整原因、实验结果提升、与论文 baseline 的定量关系。",
        ],
        "figure": "配图建议：项目整体流程图，展示“参数 -> 前向模型 -> 曲线”和“目标曲线 -> 后向模型 -> 候选参数 -> 前向筛选”的双向闭环。",
    },
    {
        "title": "第1页：研究背景与问题定义",
        "bullets": [
            "研究任务包括两个方向：前向预测和后向逆向设计。",
            "前向任务：输入 9 个结构参数，预测 20 个应力点组成的力学曲线。",
            "后向任务：输入目标力学曲线，反推出满足目标响应的结构参数。",
            "难点在于：后向映射本质是一对多，单一确定性模型难以覆盖合理解空间。",
        ],
        "figure": "配图建议：用一张示意图说明前向是一对一映射、后向是一对多映射。",
    },
    {
        "title": "第2页：原始方案问题与改造动机",
        "bullets": [
            "原有 6 通道/6 pipeline 方案更接近物理外推式思路，但对生成模型并不必要。",
            "CVAE 和 Diffusion 本身已经通过随机采样建模概率分布，不需要为多样性单独复制 6 套模型。",
            "继续保留 6 通道会显著增加训练成本和推理成本，尤其对 Diffusion 更不划算。",
            "因此主线调整为：单通道生成 + 多候选采样 + 前向筛选。",
        ],
        "figure": "配图建议：展示“旧方案：6 通道并行生成”与“新方案：单模型采样 N 次再筛选”的对比框图。",
    },
    {
        "title": "第3页：整体技术路线重构",
        "bullets": [
            "前向模块保留两条路线：GAT 和 GNNTransformer。",
            "后向模块采用两条生成路线：CVAE 和 Diffusion。",
            "后向模型先生成多组候选参数，再交给前向模型预测曲线，按误差排序取 Top-k。",
            "这样将“生成能力”和“验证能力”解耦，形成可解释的闭环设计流程。",
        ],
        "figure": "配图建议：闭环流程图，突出“后向生成 -> 前向评估 -> Top-k 输出”。",
    },
    {
        "title": "第4页：代码与实验工作流整理",
        "bullets": [
            "完成单通道主线重构，统一了前向和后向训练脚本。",
            "测试脚本新增可视化、集成推理和 Top-k 排序支持。",
            "结果文件统一输出，便于后续做横向对比与论文对齐。",
            "同时保留旧逻辑和历史结果，保证可回溯性。",
        ],
        "figure": "配图建议：脚本关系图，列出训练脚本、测试脚本、对比脚本和结果目录之间的关系。",
    },
    {
        "title": "第5页：前向模型设计与改进",
        "bullets": [
            "GAT 作为当前图建模前向基线，负责结构参数到曲线的预测。",
            "GNNTransformer 作为增强方案，引入全局建模能力，并进一步做 3-5 模型集成。",
            "集成学习目标是减少单模型随机波动，提高整体泛化稳定性。",
            "测试脚本支持单模型与集成模型统一评估。",
        ],
        "figure": "配图建议：前向模型结构简图，左右对比 GAT 与 Transformer。",
    },
    {
        "title": "第6页：前向实验结果",
        "bullets": [
            "前向测试结果显示，Transformer 集成整体优于单 GAT。",
            "GAT 指标：MSE 11.48，MAE 1.06，R2 0.9759，NRMSE 2.32%。",
            "Transformer_ens_5 指标：MSE 7.26，MAE 0.80，R2 0.9846，NRMSE 1.84%。",
            "相对 GAT，Transformer 集成实现 MSE 下降 36.8%，MAE 下降 25.1%，NRMSE 下降 20.5%。",
        ],
        "figure": "配图建议：使用 [forward_test_comparison_stratified.png](F:\\TPMS\\forward_test_results\\forward_test_comparison_stratified.png) 和 [metrics_comparison_visualization.png](F:\\TPMS\\comparison_results\\metrics_comparison_visualization.png)。",
    },
    {
        "title": "第7页：为什么改前向测试可视化方式",
        "bullets": [
            "初始测试图采用随机抽样，容易出现“局部样本观感”与“整体指标结论”不一致的问题。",
            "后来改成按 class 分层展示，并固定抽取 best、worst、median 与随机样本。",
            "这样既能展示模型总体趋势，也能保留典型优劣案例。",
            "新的可视化方式更适合直接放入 PPT 做结果说明。",
        ],
        "figure": "配图建议：直接放分层测试图，并标注 class1/class2/class12 的代表样本。",
    },
    {
        "title": "第8页：后向模型设计与改进",
        "bullets": [
            "CVAE 作为后向生成模型基线，负责从目标曲线采样参数候选。",
            "Diffusion 作为增强型生成方案，通过逐步去噪生成参数，理论上更适合复杂分布。",
            "两者都改为单 pipeline 主线，不再保留 6 通道冗余结构。",
            "测试环节统一加入可视化与 Top-k 候选保存，便于定量对比和样本分析。",
        ],
        "figure": "配图建议：CVAE 与 Diffusion 的生成流程对比图。",
    },
    {
        "title": "第9页：多候选采样 + 前向 Top-k 筛选",
        "bullets": [
            "后向模型不是直接输出唯一解，而是对同一目标曲线生成多组候选参数。",
            "再利用训练好的前向模型预测每组候选对应的曲线，与目标曲线计算误差。",
            "按误差从小到大排序，输出 Top-k 候选作为最终设计结果。",
            "这一策略本质上把生成模型的一对多优势真正利用起来，提高了后向设计质量。",
        ],
        "figure": "配图建议：展示“1 个目标曲线 -> N 个候选参数 -> 前向验证 -> Top-k 输出”的流程图。",
    },
    {
        "title": "第10页：后向实验结果",
        "bullets": [
            "在当前闭环测试中，Diffusion 明显优于 CVAE。",
            "CVAE 的 curve NRMSE 约为 3.67%，Diffusion 的 curve NRMSE 约为 1.09%。",
            "Diffusion 在参数误差和曲线误差上均有明显优势，说明其生成质量和筛选后结果更稳定。",
            "这表明“生成式模型 + 前向筛选”的路线是有效的，其中 Diffusion 是当前最优后向方案。",
        ],
        "figure": "配图建议：使用 [inverse_test_comparison.png](F:\\TPMS\\inverse_test_results\\inverse_test_comparison.png) 和 [metrics_comparison_visualization.png](F:\\TPMS\\comparison_results\\metrics_comparison_visualization.png)。",
    },
    {
        "title": "第11页：与论文 baseline 的对齐思路",
        "bullets": [
            "为了避免只做内部模型对比，额外引入了论文 baseline 作为外部参照。",
            "从补充材料 Table S1 和 Table S2 中提取前向/后向 baseline 的最优分数与网络结构信息。",
            "先做表格分数级别对齐，再进一步复现实验流程，保证对比更有说服力。",
            "这一部分的目的不是简单追求数值高低，而是说明当前方案相对论文方法的改进幅度和适用边界。",
        ],
        "figure": "配图建议：使用 [paper_baseline_comparison.png](F:\\TPMS\\comparison_results\\paper_baseline_comparison.png)。",
    },
    {
        "title": "第12页：后向 baseline 严格复现结果",
        "bullets": [
            "按照论文补充材料的后向网络配置，复现了 5-fold + RMSE/NRMSE 评价流程。",
            "复现 baseline 的 5-fold OOF NRMSE 约为 1.918%，test NRMSE 约为 2.511%。",
            "同口径 test 指标下，CVAE Top1 的 NRMSE 为 3.425%，Diffusion Top1 的 NRMSE 为 2.033%。",
            "结论是：Diffusion 相对复现 baseline 进一步提升约 19.1%，而 CVAE 仍落后于 baseline。",
        ],
        "figure": "配图建议：使用 [inverse_strict_comparable_plot.png](F:\\TPMS\\comparison_results\\inverse_paper_baseline_reproduce\\inverse_strict_comparable_plot.png)。",
    },
    {
        "title": "第13页：阶段性结论",
        "bullets": [
            "前向最优方案：GNNTransformer + 3-5 模型集成。",
            "后向最优方案：Diffusion + 多候选采样 + 前向 Top-k 筛选。",
            "单通道主线相比旧的 6 通道方案更简洁、更经济，也更符合生成模型的建模逻辑。",
            "整个项目已经形成从模型训练、测试、可视化、baseline 对比到复现实验的完整闭环。",
        ],
        "figure": "配图建议：结论页可放一张总览表，汇总当前最优前向与后向方案及关键指标。",
    },
    {
        "title": "第14页：当前产出与下一步计划",
        "bullets": [
            "当前产出包括：训练脚本、测试脚本、可视化脚本、论文 baseline 对比脚本和 5-fold 复现实验脚本。",
            "结果产出包括：前向分层测试图、综合指标图、论文 baseline 对比图、后向严格可比图。",
            "下一步建议：做多随机种子统计、继续做 3 模型与 5 模型集成消融，并优化 Diffusion 的采样效率。",
            "如果后续用于论文或答辩，可将本阶段重点浓缩为“结构重构、闭环筛选、严格 baseline 对比”三条主线。",
        ],
        "figure": "配图建议：用一页“成果总览”，列出关键图表、关键脚本和下一步计划。",
    },
]


def make_paragraph(text: str, bold: bool = False, size_half_points: Optional[int] = None) -> str:
    text_xml = escape(text)
    run_props = []
    if bold:
        run_props.append("<w:b/>")
    if size_half_points is not None:
        run_props.append(f'<w:sz w:val="{size_half_points}"/>')
        run_props.append(f'<w:szCs w:val="{size_half_points}"/>')
    run_props_xml = f"<w:rPr>{''.join(run_props)}</w:rPr>" if run_props else ""
    return f"<w:p><w:r>{run_props_xml}<w:t xml:space=\"preserve\">{text_xml}</w:t></w:r></w:p>"


def build_document_xml() -> str:
    body = []
    body.append(make_paragraph("TPMS 项目汇报：PPT逐页文案版", bold=True, size_half_points=32))
    body.append(make_paragraph("用途：用于向老师汇报阶段进度，可直接作为 PPT 内容大纲扩展。", size_half_points=22))
    body.append(make_paragraph("说明：每页包含标题、3-5 条要点和配图建议，强调逻辑清晰、结构紧凑、突出工作重点。", size_half_points=22))
    body.append(make_paragraph(""))

    for idx, section in enumerate(SECTIONS, start=1):
        body.append(make_paragraph(f"{idx}. {section['title']}", bold=True, size_half_points=28))
        for bullet in section["bullets"]:
            body.append(make_paragraph(f"• {bullet}", size_half_points=22))
        body.append(make_paragraph(section["figure"], size_half_points=21))
        body.append(make_paragraph(""))

    sect_pr = (
        "<w:sectPr>"
        "<w:pgSz w:w=\"11906\" w:h=\"16838\"/>"
        "<w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" "
        "w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/>"
        "</w:sectPr>"
    )
    body_xml = "".join(body) + sect_pr
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:wpc=\"http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas\" "
        "xmlns:mc=\"http://schemas.openxmlformats.org/markup-compatibility/2006\" "
        "xmlns:o=\"urn:schemas-microsoft-com:office:office\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:m=\"http://schemas.openxmlformats.org/officeDocument/2006/math\" "
        "xmlns:v=\"urn:schemas-microsoft-com:vml\" "
        "xmlns:wp14=\"http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing\" "
        "xmlns:wp=\"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing\" "
        "xmlns:w10=\"urn:schemas-microsoft-com:office:word\" "
        "xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\" "
        "xmlns:w14=\"http://schemas.microsoft.com/office/word/2010/wordml\" "
        "xmlns:wpg=\"http://schemas.microsoft.com/office/word/2010/wordprocessingGroup\" "
        "xmlns:wpi=\"http://schemas.microsoft.com/office/word/2010/wordprocessingInk\" "
        "xmlns:wne=\"http://schemas.microsoft.com/office/word/2006/wordml\" "
        "xmlns:wps=\"http://schemas.microsoft.com/office/word/2010/wordprocessingShape\" "
        "mc:Ignorable=\"w14 wp14\">"
        f"<w:body>{body_xml}</w:body>"
        "</w:document>"
    )


def write_docx(output_path: str) -> None:
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""
    package_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""
    core_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>TPMS 项目汇报：PPT逐页文案版</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">2026-03-25T00:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2026-03-25T00:00:00Z</dcterms:modified>
</cp:coreProperties>"""
    app_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Microsoft Office Word</Application>
</Properties>"""

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", package_rels)
        zf.writestr("docProps/core.xml", core_xml)
        zf.writestr("docProps/app.xml", app_xml)
        zf.writestr("word/document.xml", build_document_xml())


if __name__ == "__main__":
    write_docx(OUTPUT_PATH)
    print(f"[Saved] {OUTPUT_PATH}")
