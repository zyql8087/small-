"""Generate a Chinese PDF report for the SWOMPS curve-dataset work."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import fitz
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CURVE_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "pdf"
TMP_DIR = PROJECT_ROOT / "tmp" / "pdfs"
PDF_PATH = OUTPUT_DIR / "swomps_curve_dataset_stage_report.pdf"

FONT_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")
FONT_NAME = "SimHei"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def fmt_seconds(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} s"
    return f"{seconds / 60:.1f} min"


def register_fonts() -> None:
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"Chinese font not found: {FONT_PATH}")
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName=FONT_NAME,
            fontSize=24,
            leading=32,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=11,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName=FONT_NAME,
            fontSize=16,
            leading=22,
            textColor=colors.HexColor("#0F766E"),
            spaceBefore=6,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName=FONT_NAME,
            fontSize=12,
            leading=18,
            textColor=colors.HexColor("#374151"),
            spaceBefore=4,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=10.5,
            leading=16,
            textColor=colors.HexColor("#111827"),
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=4,
        ),
    }


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def make_table(data: list[list[str]], widths: list[float] | None = None) -> Table:
    table = Table(data, colWidths=widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 12),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0F2F1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def add_footer(canvas, doc) -> None:  # noqa: ANN001
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    footer = f"SWOMPS 力-位移曲线数据集阶段汇报 | Page {doc.page}"
    canvas.drawCentredString(A4[0] / 2, 12 * mm, footer)
    canvas.restoreState()


def build_story() -> list:
    styles = make_styles()
    audit = load_json(CURVE_ROOT / "smoke_results" / "mixed_batch_audit.json")
    metrics = load_json(CURVE_ROOT / "smoke_results" / "curve_smoke_metrics.json")
    metadata = load_json(CURVE_ROOT / "data" / "metadata.json")

    miura_err = audit["rel_stiff_error_by_source"]["miura"]
    tmp_err = audit["rel_stiff_error_by_source"]["tmp"]
    miura_cv = audit["secant_stiff_cv_by_source"]["miura"]
    tmp_cv = audit["secant_stiff_cv_by_source"]["tmp"]
    timing = audit["timing_by_source_from_file_write_intervals"]

    story: list = []
    story.append(p("SWOMPS 力-位移曲线新数据集阶段汇报", styles["title"]))
    story.append(
        p(
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 工作目录：F:/small++/origami_experiments/curve_dataset",
            styles["subtitle"],
        )
    )
    story.append(p("1. 工作目标", styles["h1"]))
    story.append(
        p(
            "本阶段目标是在原始折纸数据集生成逻辑基础上，借鉴 GraphMetaMat 的“完整物理响应离散化存储”思路，构造新的机器学习数据集："
            "输入为原始 8 个结构与材料参数，输出为多工况力-位移响应曲线。",
            styles["body"],
        )
    )
    story.append(
        make_table(
            [
                ["项目", "当前设定"],
                ["输入 X", "pattern, m, n, tcrease, tpanel, W, creaseE, panelE"],
                ["输出 Y", "6 个工况的力-位移曲线"],
                ["工况", "bending/axial × deployment 0.3, 0.6, 0.9"],
                ["曲线离散点", "每条曲线 30 个加载步"],
                ["单样本目标形状", "displacement: [6, 30], curve_raw: [6, 30, 2]"],
                ["仿真工具", "MATLAB R2020b + SWOMPS/OrigamiSimulator"],
            ],
            [38 * mm, 122 * mm],
        )
    )

    story.append(Spacer(1, 8))
    story.append(p("2. 当前有效数据", styles["h1"]))
    story.append(
        make_table(
            [
                ["类别", "数量", "范围或说明"],
                ["Miura", str(audit["source_counts"]["miura"]), "miura_00001 至 miura_00026"],
                ["TMP", str(audit["source_counts"]["tmp"]), "tmp_00001 至 tmp_00003"],
                ["合计 CSV", str(audit["csv_files"]), "每个 CSV 为 6 × 30 = 180 行"],
                ["打包训练集", str(metadata["train_samples"]), "data/origami_curve_train.npz"],
                ["打包测试集", str(metadata["test_samples"]), "data/origami_curve_test.npz"],
            ],
            [42 * mm, 28 * mm, 92 * mm],
        )
    )
    story.append(
        p(
            "最新打包数据集包含 29 个完整样本，训练/测试切分为 23/6。该数据量只适合验证数据链路和模型接口，不适合作为正式性能结论。",
            styles["body"],
        )
    )

    story.append(PageBreak())
    story.append(p("3. 仿真质量自审结果", styles["h1"]))
    story.append(
        p(
            "已对当前 29 个样本进行结构、收敛、数值合法性和与原始刚度标签一致性检查。没有发现结构性错误。",
            styles["body"],
        )
    )
    story.append(
        make_table(
            [
                ["检查项", "结果"],
                ["行数与工况", "每个样本 180 行，curve_id = 0..5"],
                ["加载步", "每条曲线 step = 1..30"],
                ["收敛", "converged 全部为 True"],
                ["数值合法性", "无 NaN/Inf，位移为正"],
                ["单调性", "力单调递增，位移单调递增"],
                ["失败日志", "无失败样本，stderr 为空"],
            ],
            [50 * mm, 112 * mm],
        )
    )
    story.append(Spacer(1, 8))
    story.append(p("与原始刚度标签的一致性", styles["h2"]))
    story.append(
        make_table(
            [
                ["来源", "曲线数", "平均相对误差", "95 分位误差", "最大误差", "Secant CV 平均值"],
                ["Miura", str(miura_err["count"]), percent(miura_err["mean"]), percent(miura_err["p95"]), percent(miura_err["max"]), percent(miura_cv["mean"])],
                ["TMP", str(tmp_err["count"]), percent(tmp_err["mean"]), percent(tmp_err["p95"]), percent(tmp_err["max"]), percent(tmp_cv["mean"])],
            ],
            [24 * mm, 22 * mm, 32 * mm, 32 * mm, 28 * mm, 32 * mm],
        )
    )
    story.append(
        p(
            "说明：误差并不表示仿真错误。原始数据的刚度来自 3 步加载末端等效刚度；当前数据保存 30 步完整曲线。若响应存在轻微非线性，二者不会完全相同。",
            styles["small"],
        )
    )

    story.append(PageBreak())
    story.append(p("4. 模型读取与训练 Smoke Test", styles["h1"]))
    story.append(
        p(
            "为了验证新数据能进入模型端，已训练两个最小 MLP：forward 模型学习 8 参数到 180 维曲线，inverse 模型学习 180 维曲线到 8 参数。"
            "该实验只验证读取、shape、反向传播和优化链路。",
            styles["body"],
        )
    )
    story.append(
        make_table(
            [
                ["项目", "数值"],
                ["PyTorch 版本", metrics["torch_version"]],
                ["训练/测试样本", f"{metrics['train_samples']} / {metrics['test_samples']}"],
                ["输入维度", str(metrics["x_dim"])],
                ["曲线目标维度", str(metrics["curve_dim"])],
                ["curve_raw 训练形状", str(metrics["curve_raw_shape_train"])],
                ["curve_raw 测试形状", str(metrics["curve_raw_shape_test"])],
            ],
            [50 * mm, 112 * mm],
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        make_table(
            [
                ["模型", "初始训练 MSE", "最终训练 MSE", "训练降幅", "最终测试 MSE"],
                [
                    "Forward: X 到曲线",
                    f"{metrics['forward_x_to_curve']['initial_train_mse']:.4f}",
                    f"{metrics['forward_x_to_curve']['final_train_mse']:.6f}",
                    percent(metrics["forward_x_to_curve"]["train_mse_reduction_ratio"]),
                    f"{metrics['forward_x_to_curve']['final_test_mse']:.4f}",
                ],
                [
                    "Inverse: 曲线到 X",
                    f"{metrics['inverse_curve_to_x']['initial_train_mse']:.4f}",
                    f"{metrics['inverse_curve_to_x']['final_train_mse']:.5f}",
                    percent(metrics["inverse_curve_to_x"]["train_mse_reduction_ratio"]),
                    f"{metrics['inverse_curve_to_x']['final_test_mse']:.4f}",
                ],
            ],
            [42 * mm, 30 * mm, 30 * mm, 28 * mm, 30 * mm],
        )
    )
    story.append(
        p(
            "结论：数据读取、标准化、张量形状、反向传播和优化链路均已跑通。测试误差不作为模型泛化能力结论，因为当前样本量过小。",
            styles["body"],
        )
    )

    story.append(PageBreak())
    story.append(p("5. 发现的问题与工程判断", styles["h1"]))
    story.append(
        make_table(
            [
                ["问题", "观察", "影响"],
                ["GPU 加速不可用", "SWOMPS/MATLAB 求解主要依赖 CPU", "不能像 PyTorch 训练一样直接用 GPU 提速"],
                ["多 MATLAB 并行不合适", "两个实例并行时 Miura 明显变慢", "资源争用导致总吞吐下降"],
                ["TMP 明显更慢", f"TMP 平均输出间隔约 {fmt_seconds(timing['tmp']['mean_output_interval_sec'])}", "全量顺序跑耗时较高"],
                ["全量 4000 不宜直接启动", "已主动停止 200/50 长任务", "需要分段、审计、再扩展"],
            ],
            [38 * mm, 64 * mm, 58 * mm],
        )
    )
    story.append(Spacer(1, 8))
    story.append(p("当前判断", styles["h2"]))
    story.append(
        p(
            "仿真结果本身没有发现结构性问题；真正的瓶颈是计算耗时。大批量数据可以继续做，但应该采用单 MATLAB 实例、分阶段运行，并在每个阶段结束后自动审计和打包。",
            styles["body"],
        )
    )

    story.append(PageBreak())
    story.append(p("6. 下一步建议", styles["h1"]))
    story.append(
        make_table(
            [
                ["阶段", "建议动作", "目的"],
                ["短期", "继续 Miura: StartIndex 27 起，先跑到 100", "扩大 Miura 样本并观察耗时稳定性"],
                ["短期", "继续 TMP: StartIndex 2004 起，先跑到 2010", "验证 TMP 后续样本稳定性"],
                ["每阶段结束", "运行审计与 build_curve_dataset_npz.py --allow-partial", "避免错误数据进入训练集"],
                ["模型侧", "将正式 forward/inverse 模型适配 180 维曲线目标", "从 smoke test 转向正式实验"],
                ["论文侧", "报告 SWOMPS 数据集与少量高保真验证的关系", "说明仿真可信度与工程意义"],
            ],
            [28 * mm, 82 * mm, 52 * mm],
        )
    )
    story.append(Spacer(1, 8))
    story.append(p("关键文件", styles["h2"]))
    story.append(
        make_table(
            [
                ["文件", "作用"],
                ["CURRENT_STATUS.md", "当前工作区状态说明"],
                ["raw_curves/*.csv", "逐样本力-位移曲线"],
                ["data/origami_curve_train.npz", "模型训练数据"],
                ["smoke_results/mixed_batch_audit.json", "最新仿真审计结果"],
                ["smoke_results/curve_smoke_metrics.json", "模型读取/训练 smoke test 结果"],
            ],
            [62 * mm, 100 * mm],
        )
    )
    story.append(
        p(
            "推荐汇报结论：数据集构造路线已经跑通；当前瓶颈不是模型接口，而是 SWOMPS 批量仿真吞吐。后续应优先优化分段运行与自动审计流程，再扩大样本规模。",
            styles["body"],
        )
    )
    return story


def build_pdf() -> None:
    register_fonts()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="SWOMPS 力-位移曲线新数据集阶段汇报",
        author="Codex",
    )
    doc.build(build_story(), onFirstPage=add_footer, onLaterPages=add_footer)


def render_previews() -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(PDF_PATH))
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
        pix.save(str(TMP_DIR / f"swomps_curve_dataset_stage_report_page_{i}.png"))


def validate_pdf() -> None:
    reader = PdfReader(str(PDF_PATH))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    required = [
        "SWOMPS 力-位移曲线新数据集阶段汇报",
        "当前有效数据",
        "仿真质量自审结果",
        "模型读取与训练 Smoke Test",
        "下一步建议",
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise RuntimeError(f"PDF text validation failed, missing: {missing}")
    print(f"PDF written: {PDF_PATH}")
    print(f"Pages: {len(reader.pages)}")
    print(f"Preview images: {TMP_DIR}")


def main() -> None:
    build_pdf()
    render_previews()
    validate_pdf()


if __name__ == "__main__":
    main()
