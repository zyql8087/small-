from pathlib import Path
from datetime import date
from PIL import Image, ImageDraw, ImageFont

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "reports"
ASSET_DIR = OUT_DIR / "_docx_assets"
OUT_PATH = OUT_DIR / "Paper_A_final_framework_mechanism_resolved_attainability.docx"
PIPELINE_PATH = ASSET_DIR / "paper_a_pipeline.png"


# compact_reference_guide preset, resolved to exact values.
PAGE_W = Inches(8.5)
PAGE_H = Inches(11)
MARGIN = Inches(1.0)
HEADER_DIST = Inches(0.492)
FOOTER_DIST = Inches(0.492)
CONTENT_DXA = 9360
TABLE_INDENT_DXA = 120
CELL_MARGINS = {"top": 80, "bottom": 80, "start": 120, "end": 120}

NAVY = RGBColor(31, 77, 120)
BLUE = RGBColor(46, 116, 181)
INK = RGBColor(25, 42, 61)
MUTED = RGBColor(90, 100, 112)
LIGHT_BLUE = "E8EEF5"
LIGHT_GRAY = "F2F4F7"
CALLOUT = "F4F6F9"
WHITE = RGBColor(255, 255, 255)
BLACK = RGBColor(0, 0, 0)
RED = RGBColor(155, 28, 28)
GOLD = RGBColor(122, 90, 0)


def set_run_font(run, name="Microsoft YaHei", size=11, color=BLACK,
                 bold=False, italic=False):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.bold = bold
    run.italic = italic


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, **kwargs):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for side in ("top", "start", "bottom", "end"):
        if side in kwargs:
            node = tc_mar.find(qn(f"w:{side}"))
            if node is None:
                node = OxmlElement(f"w:{side}")
                tc_mar.append(node)
            node.set(qn("w:w"), str(kwargs[side]))
            node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_table_geometry(table, widths_dxa, indent_dxa=TABLE_INDENT_DXA):
    assert sum(widths_dxa) == CONTENT_DXA
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr

    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(CONTENT_DXA))
    tbl_w.set(qn("w:type"), "dxa")

    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(indent_dxa))
    tbl_ind.set(qn("w:type"), "dxa")

    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)

    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(widths_dxa[idx]))
            tc_w.set(qn("w:type"), "dxa")
            set_cell_margins(cell, **CELL_MARGINS)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def set_table_borders(table, color="C7CDD4", size="4"):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = borders.find(qn(f"w:{edge}"))
        if tag is None:
            tag = OxmlElement(f"w:{edge}")
            borders.append(tag)
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), size)
        tag.set(qn("w:space"), "0")
        tag.set(qn("w:color"), color)


def set_paragraph_border_bottom(paragraph, color="D7DBE2", size="6"):
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr")
        p_pr.append(p_bdr)
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), size)
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)


def set_keep_with_next(paragraph, keep=True):
    paragraph.paragraph_format.keep_with_next = keep


def add_field(paragraph, instruction):
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    for node in (fld_begin, instr, fld_sep, text, fld_end):
        run._r.append(node)
    set_run_font(run, size=9, color=MUTED)


def set_update_fields(doc):
    settings = doc.settings._element
    update = settings.find(qn("w:updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    update.set(qn("w:val"), "true")


def add_custom_numbering(doc):
    numbering = doc.part.numbering_part.element

    def add_abstract(abs_id, num_fmt, lvl_text, left=540, hanging=270):
        abstract = OxmlElement("w:abstractNum")
        abstract.set(qn("w:abstractNumId"), str(abs_id))
        multi = OxmlElement("w:multiLevelType")
        multi.set(qn("w:val"), "singleLevel")
        abstract.append(multi)
        lvl = OxmlElement("w:lvl")
        lvl.set(qn("w:ilvl"), "0")
        start = OxmlElement("w:start")
        start.set(qn("w:val"), "1")
        fmt = OxmlElement("w:numFmt")
        fmt.set(qn("w:val"), num_fmt)
        txt = OxmlElement("w:lvlText")
        txt.set(qn("w:val"), lvl_text)
        jc = OxmlElement("w:lvlJc")
        jc.set(qn("w:val"), "left")
        p_pr = OxmlElement("w:pPr")
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "num")
        tab.set(qn("w:pos"), str(left))
        tabs.append(tab)
        ind = OxmlElement("w:ind")
        ind.set(qn("w:left"), str(left))
        ind.set(qn("w:hanging"), str(hanging))
        spacing = OxmlElement("w:spacing")
        spacing.set(qn("w:after"), "80")
        spacing.set(qn("w:line"), "300")
        spacing.set(qn("w:lineRule"), "auto")
        p_pr.extend([tabs, ind, spacing])
        lvl.extend([start, fmt, txt, jc, p_pr])
        if num_fmt == "bullet":
            r_pr = OxmlElement("w:rPr")
            r_fonts = OxmlElement("w:rFonts")
            r_fonts.set(qn("w:ascii"), "Segoe UI Symbol")
            r_fonts.set(qn("w:hAnsi"), "Segoe UI Symbol")
            r_pr.append(r_fonts)
            lvl.append(r_pr)
        abstract.append(lvl)
        numbering.append(abstract)

    def add_num(num_id, abs_id):
        num = OxmlElement("w:num")
        num.set(qn("w:numId"), str(num_id))
        abs_ref = OxmlElement("w:abstractNumId")
        abs_ref.set(qn("w:val"), str(abs_id))
        num.append(abs_ref)
        numbering.append(num)

    add_abstract(50, "bullet", "•")
    add_num(50, 50)
    add_abstract(51, "decimal", "%1.")
    add_num(51, 51)
    return 50, 51


def set_numbering(paragraph, num_id):
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = p_pr.find(qn("w:numPr"))
    if num_pr is None:
        num_pr = OxmlElement("w:numPr")
        p_pr.append(num_pr)
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    num_id_el = OxmlElement("w:numId")
    num_id_el.set(qn("w:val"), str(num_id))
    num_pr.extend([ilvl, num_id_el])


def add_bullet(doc, text, bullet_id, bold_prefix=None):
    p = doc.add_paragraph()
    set_numbering(p, bullet_id)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.25
    if bold_prefix and text.startswith(bold_prefix):
        r1 = p.add_run(bold_prefix)
        set_run_font(r1, bold=True)
        r2 = p.add_run(text[len(bold_prefix):])
        set_run_font(r2)
    else:
        r = p.add_run(text)
        set_run_font(r)
    return p


def add_body(doc, text, bold_prefix=None, italic=False, color=BLACK, after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.25
    if bold_prefix and text.startswith(bold_prefix):
        r1 = p.add_run(bold_prefix)
        set_run_font(r1, color=color, bold=True, italic=italic)
        r2 = p.add_run(text[len(bold_prefix):])
        set_run_font(r2, color=color, italic=italic)
    else:
        r = p.add_run(text)
        set_run_font(r, color=color, italic=italic)
    return p


def add_label_line(doc, label, text, color=BLACK):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.12)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.20
    r1 = p.add_run(label + "：")
    set_run_font(r1, size=10.5, color=NAVY, bold=True)
    r2 = p.add_run(text)
    set_run_font(r2, size=10.5, color=color)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.add_run(text)
    set_keep_with_next(p)
    return p


def add_callout(doc, label, text, fill=CALLOUT, accent=NAVY):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.12)
    p.paragraph_format.right_indent = Inches(0.08)
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(7)
    p.paragraph_format.line_spacing = 1.20
    p_pr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    p_pr.append(shd)
    p_bdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "18")
    left.set(qn("w:space"), "6")
    left.set(qn("w:color"), str(accent))
    p_bdr.append(left)
    p_pr.append(p_bdr)
    r1 = p.add_run(label + "　")
    set_run_font(r1, size=11, color=accent, bold=True)
    r2 = p.add_run(text)
    set_run_font(r2, size=11, color=INK, bold=False)
    return p


def add_simple_table(doc, headers, rows, widths_dxa, header_fill=LIGHT_BLUE,
                     font_size=9.2, first_col_bold=False):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for idx, text in enumerate(headers):
        cell = hdr.cells[idx]
        set_cell_shading(cell, header_fill)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.10
        r = p.add_run(str(text))
        set_run_font(r, size=9.2, color=INK, bold=True)
    for row_data in rows:
        row = table.add_row()
        for idx, value in enumerate(row_data):
            cell = row.cells[idx]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if idx == 0 and len(headers) <= 3 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.12
            r = p.add_run(str(value))
            set_run_font(r, size=font_size, color=BLACK,
                         bold=(first_col_bold and idx == 0))
    set_table_geometry(table, widths_dxa)
    set_table_borders(table)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def add_step(doc, number, title, problem, method, output, gate=None):
    p = doc.add_paragraph(style="Heading 2")
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r1 = p.add_run(f"步骤 {number}｜")
    set_run_font(r1, size=12, color=BLUE, bold=True)
    r2 = p.add_run(title)
    set_run_font(r2, size=12, color=INK, bold=True)
    add_label_line(doc, "要解决的问题", problem)
    add_label_line(doc, "采用的方法", method)
    add_label_line(doc, "主要产出", output)
    if gate:
        add_label_line(doc, "通过标准", gate, color=INK)


def make_pipeline_image(path):
    width, height = 1800, 520
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font_path = Path(r"C:\Windows\Fonts\msyh.ttc")
    bold_path = Path(r"C:\Windows\Fonts\msyhbd.ttc")
    title_font = ImageFont.truetype(str(bold_path if bold_path.exists() else font_path), 42)
    box_font = ImageFont.truetype(str(font_path), 29)
    small_font = ImageFont.truetype(str(font_path), 23)
    draw.text((60, 32), "Paper A：从目标曲线到可交付设计的证据链", font=title_font, fill=(31, 77, 120))
    labels = [
        ("限定研究域", "几何 / 材料 / 载荷"),
        ("Diffusion 提议", "生成多样候选"),
        ("几何编译", "合法性 + 轴向图"),
        ("前向验证", "曲线 + 局部机制"),
        ("证据门控", "接受 / 延后 / 未找到"),
        ("高保真裁决", "Abaqus + 压缩视频"),
    ]
    x0, y0, bw, bh, gap = 55, 170, 250, 190, 44
    colors = [(232, 238, 245), (242, 244, 247), (232, 238, 245),
              (232, 238, 245), (244, 246, 249), (232, 238, 245)]
    for i, ((head, sub), fill) in enumerate(zip(labels, colors)):
        x = x0 + i * (bw + gap)
        draw.rounded_rectangle((x, y0, x + bw, y0 + bh), radius=18,
                               fill=fill, outline=(92, 115, 136), width=3)
        hb = draw.textbbox((0, 0), head, font=box_font)
        draw.text((x + (bw - (hb[2] - hb[0])) / 2, y0 + 42), head,
                  font=box_font, fill=(25, 42, 61))
        sb = draw.textbbox((0, 0), sub, font=small_font)
        draw.text((x + (bw - (sb[2] - sb[0])) / 2, y0 + 112), sub,
                  font=small_font, fill=(90, 100, 112))
        if i < len(labels) - 1:
            ax1 = x + bw + 8
            ax2 = x + bw + gap - 8
            ay = y0 + bh // 2
            draw.line((ax1, ay, ax2, ay), fill=(46, 116, 181), width=6)
            draw.polygon([(ax2, ay), (ax2 - 18, ay - 12), (ax2 - 18, ay + 12)],
                         fill=(46, 116, 181))
    draw.text((60, 420), "核心原则：生成模型只负责“提议”；最终结论由明确阈值、留出测试和物理证据共同决定。",
              font=small_font, fill=(122, 90, 0))
    img.save(path, dpi=(180, 180))


def configure_styles(doc):
    styles = doc.styles

    normal = styles["Normal"]
    normal.font.name = "Microsoft YaHei"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Microsoft YaHei")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Microsoft YaHei")
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    normal.font.size = Pt(11)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25

    specs = {
        "Title": (24, INK, 0, 6),
        "Subtitle": (13, MUTED, 0, 18),
        "Heading 1": (16, BLUE, 18, 10),
        "Heading 2": (13, BLUE, 14, 7),
        "Heading 3": (12, NAVY, 10, 5),
    }
    for name, (size, color, before, after) in specs.items():
        style = styles[name]
        style.font.name = "Microsoft YaHei"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Microsoft YaHei")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Microsoft YaHei")
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        style.font.size = Pt(size)
        style.font.color.rgb = color
        style.font.bold = name != "Subtitle"
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True


def configure_document(doc):
    section = doc.sections[0]
    section.page_width = PAGE_W
    section.page_height = PAGE_H
    section.top_margin = MARGIN
    section.bottom_margin = MARGIN
    section.left_margin = MARGIN
    section.right_margin = MARGIN
    section.header_distance = HEADER_DIST
    section.footer_distance = FOOTER_DIST

    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run("PAPER A 研究总纲  |  机制分辨经验可实现域")
    set_run_font(r, size=8.5, color=MUTED, bold=True)

    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run("第 ")
    set_run_font(r, size=9, color=MUTED)
    add_field(p, "PAGE")
    r = p.add_run(" 页")
    set_run_font(r, size=9, color=MUTED)


def build_doc():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    make_pipeline_image(PIPELINE_PATH)

    doc = Document()
    configure_styles(doc)
    configure_document(doc)
    set_update_fields(doc)
    bullet_id, number_id = add_custom_numbering(doc)

    # Opening block: memo_masthead pattern without decorative border.
    p = doc.add_paragraph(style="Title")
    p.paragraph_format.space_before = Pt(22)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run("论文 A 最终研究框架与执行总纲")
    set_run_font(r, size=24, color=INK, bold=True)

    p = doc.add_paragraph(style="Subtitle")
    p.paragraph_format.space_after = Pt(16)
    r = p.add_run("机制分辨的经验可实现域驱动的渐变 TPMS 逆向设计")
    set_run_font(r, size=13, color=MUTED, bold=False)

    metadata = [
        ("定位", "3–4 个月可完成的 Paper A 主线"),
        ("核心资源", "Small 历史数据 + 240 次 Abaqus 分析 + 36 件打印压缩试样"),
        ("算法资产", "轴向 Graph Transformer 前向验证器 + 条件 Diffusion 候选生成器"),
        ("文档状态", "最终框架摘要；实施参数仍需由先导实验冻结"),
        ("更新日期", date.today().isoformat()),
    ]
    for label, value in metadata:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        r1 = p.add_run(f"{label}：")
        set_run_font(r1, size=10.5, color=INK, bold=True)
        r2 = p.add_run(value)
        set_run_font(r2, size=10.5, color=INK)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    add_callout(
        doc,
        "一句话目标",
        "在预先限定的渐变 TPMS 设计域中，判断一条目标曲线是否有足够证据可实现、能够通过什么局部塌缩路径实现，并生成和筛选机制更稳定的候选。",
    )
    add_callout(
        doc,
        "最重要的改变",
        "论文不再以“Graph Transformer + Diffusion 的组合”作为主创新，而以“只看全局曲线会丢失局部机制，生成模型还可能对证据不足的目标强行给答案”这一客观问题为起点。",
        fill="FFF8E8",
        accent=GOLD,
    )

    add_heading(doc, "一、论文到底要解决什么问题", 1)
    add_body(doc, "传统逆向设计通常只问：哪组参数能匹配目标应力–应变曲线？Paper A 进一步回答三个更接近真实交付的问题：")
    add_bullet(doc, "同一条全局曲线附近，是否存在局部塌缩顺序明显不同的结构？", bullet_id)
    add_bullet(doc, "目标曲线在当前几何、材料、载荷和制造约束内，是否有足够证据支持交付？", bullet_id)
    add_bullet(doc, "若有多个候选，哪个候选对所研究的厚度、材料和加载扰动更不敏感？", bullet_id)
    add_body(doc, "因此，研究对象不是普适的“所有 TPMS 可实现域”，而是一个有明确边界的经验集合：在冻结的渐变 TPMS 几何族、参数范围、材料模型、加载窗口、容差和有限搜索预算内，已经找到并验证的可实现响应区域。")

    add_heading(doc, "二、核心概念：用白话先讲清楚", 1)
    concept_rows = [
        ("等响应机制分歧", "两种结构的全局曲线很接近，但首个塌缩区、塌缩顺序或局部化位置不同。未经稳定性分析，不称为“分岔”。"),
        ("经验可实现域", "在声明的设计域和预算内，已经找到满足曲线与机制要求的设计所覆盖的目标区域。不是数学上的完整边界。"),
        ("顺序分离分数", "比较相邻局部塌缩事件在应变轴上隔得多远，并用预先定义的扰动波动归一化。分数越大，预期顺序越不容易翻转。"),
        ("证据门控", "模型不必对每个目标都强行给设计；可以接受、延后到 Abaqus 裁决，或报告“在声明域和预算内未找到可行设计”。"),
    ]
    add_simple_table(doc, ["概念", "本科生式解释"], concept_rows,
                     [2450, 6910], font_size=9.5, first_col_bold=True)

    add_heading(doc, "三、三条可证伪假设", 1)
    add_label_line(doc, "H1 等响应机制分歧", "存在曲线误差低于预注册阈值、但局部塌缩顺序或局部化模式可重复区分的设计对。")
    add_label_line(doc, "H2 顺序稳定性", "面向本工作流的扰动归一化顺序分离分数，与扰动后的顺序翻转风险相关，并优于只看密度、梯度、最小壁厚或名义曲线误差。")
    add_label_line(doc, "H3 前向验证有效", "在相同候选数和 Abaqus 预算下，“Diffusion 提议 + 前向验证 + 证据门控”比 Diffusion-only 获得更高的曲线与机制联合 success@K。")
    add_callout(doc, "否证原则", "如果 H1 在先导样本中不成立，就转为“经验可实现包络 + OOD 拒答”；如果 Graph Transformer 或 Diffusion 不优于简单基线，就降级为工具，不让论文主线依赖某个网络名称。", fill="FDECEC", accent=RED)

    add_heading(doc, "四、总体技术路线", 1)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(5)
    picture_run = p.add_run()
    shape = picture_run.add_picture(str(PIPELINE_PATH), width=Inches(6.45))
    doc_pr = shape._inline.docPr
    doc_pr.set("title", "Paper A 技术路线")
    doc_pr.set("descr", "从研究域限定、Diffusion 候选生成、几何编译、前向机制验证、证据门控到 Abaqus 与压缩实验裁决的六阶段流程。")
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(8)
    r = cap.add_run("图 1｜Paper A 的完整证据链。算法模块是解决问题的工具，Abaqus 与实验承担最终裁决。")
    set_run_font(r, size=9, color=MUTED, italic=True)

    add_heading(doc, "五、逐步实施：每一步用什么方法", 1)

    add_step(doc, 0, "冻结研究边界与预注册规则",
             "若设计域、容差和标签规则不断变化，最终结果无法被独立判断。",
             "冻结 TPMS 几何族和参数范围、材料模型、加载轴、0–25% 应变窗口、网格与接触方案、曲线误差、机制差异、扰动场景、Abaqus 总预算和密封测试规则。",
             "一页“研究域清单”与一份可版本追踪的配置文件。",
             "在查看先导结果前完成；后续任何修改必须记录原因。")

    add_step(doc, 1, "清理并正确使用 Small 历史数据",
             "Small 数据中精度扩增行并不等于独立 FE 结构，行级随机拆分可能让训练和测试包含同一母结构。",
             "用基础结构 ID、参数哈希或几何近邻进行分组拆分；同一母结构及其扩增版本只能位于同一 split。Small 数据只用于全局曲线预训练、Diffusion 预训练和公开基线对齐。",
             "无泄漏的训练/验证/测试清单；历史数据与新机制数据的用途边界。",
             "传统随机拆分仅作为与原文对齐的补充，不承担主要科学结论。")

    add_step(doc, 2, "建立确定性几何编译器",
             "离散参数只有先转成真实空间场，GNN 才有物理意义，几何合法性也才能自动检查。",
             "把设计参数编译为隐式曲面、STL/体素、局部厚度和胞元尺度场；沿实际加载轴划分 8–12 个轴向区域，生成节点特征、相邻边和可制造性标志。",
             "可重复生成几何的编译器、版本哈希、轴向图 PyG 数据和失败原因。",
             "历史锚点几何与描述量复现误差应低于预设阈值，几何生成成功率建议不低于 95%。")

    add_step(doc, 3, "校准 Abaqus 与局部机制标签",
             "若网格、加载速率或接触设置改变了塌缩顺序，后续机器学习只是在学习数值噪声。",
             "选 6 个代表结构，每个运行基准网格、加密网格和更慢加载/替代接触，共 18 次分析；检查曲线、局部起始应变和能量平衡。",
             "冻结的 FE 协议与自动后处理程序。",
             "曲线及局部事件对数值设置稳定；动能/内能、人工能和求解失败率满足预注册标准。")

    add_step(doc, 4, "先导发现“等响应机制分歧”",
             "这是整篇论文最关键、也最可能失败的基础假设，必须先用小预算验证。",
             "运行 36 个发现性 FE；结合 DOE、现有 Diffusion 与近邻搜索，寻找曲线距离小但塌缩顺序、局部化中心或剪切模式差异大的候选对。阈值由步骤 3 的数值噪声决定。",
             "至少 3 组探索性设计对，以及每组的全局曲线和局部场证据。",
             "若 24–36 次 FE 后仍无稳定设计对，停止强推机制主线并执行降级路线。")

    add_step(doc, 5, "把局部塌缩过程变成可学习标签",
             "全局曲线看不到“哪里先塌、怎样传播”，需要把 Abaqus 场压缩成稳定的低维标签。",
             "在每个轴向区域计算局部缩短历史；用“超过弹性基线 + 持续若干增量”的规则提取塌缩起始应变 τ；再得到顺序、局部化中心、前沿、剪切带角度和接触起始。人工抽查后冻结规则。",
             "curve、local history、τ、order、localization、contact、quality flag 等统一字段。",
             "自动标签与人工复核具有高一致性；单侧视频能够映射其中至少两项可观察指标。")

    add_step(doc, 6, "建立原创机制数据集",
             "只有 Small 历史曲线不能支持局部机制、OOD 和扰动稳定性的结论。",
             "在固定 240 次 Abaqus 分析预算内，分批生成发现、边界、设计对确认、密封 OOD 和扰动数据；保存成功样本，也保存几何/网格/求解失败样本。",
             "约 140–150 个名义设计及其复算/扰动记录组成的机制数据集；总计 240 次分析，而非 240 个独立结构。",
             "母设计及其扰动不得跨 split；48 次密封测试在模型、阈值和候选预算冻结前不可查看。")

    add_step(doc, 7, "训练前向 Graph Transformer 验证器",
             "需要快速预测候选的全局曲线、局部塌缩路径和不确定性，才能判断生成结果是否值得送入 Abaqus。",
             "把轴向区域作为节点，相邻区域作为边；节点含局部厚度、胞元尺度、相对密度代理、曲率/面积代理、梯度和边界位置。多任务输出曲线、局部历史、τ、顺序、有效性和不确定性。使用深度集合并在独立校准集上校准。",
             "机制感知的前向验证器与校准后的预测区间。",
             "必须与 MLP、1D CNN、普通 Transformer、MPNN 和打乱边图比较；若图模型无稳定增益，改用更简单模型。")

    add_step(doc, 8, "用 Diffusion 生成多解候选",
             "目标曲线到结构参数是一对多关系，需要一次生成多个不同候选，而不是只返回单一最优点。",
             "沿用现有条件 Diffusion/DiT，以目标曲线和可选机制条件为输入；每个目标固定生成 K 个候选（主实验建议 K=64），先投影到合法参数域，再经过几何编译。",
             "每个目标的多样候选池，而不是未经验证的最终答案。",
             "与 CMA-ES、多起点代理优化或其他低维优化在相同时间/候选预算下比较；若无优势，Diffusion 降为候选生成基线。")

    add_step(doc, 9, "候选排序与证据门控",
             "生成模型会对低支持目标也给出看似合理的参数，因此必须允许系统拒答。",
             "先做几何硬筛选，再按曲线误差、机制命中、顺序分离分数、扰动敏感性和预测不确定性排序。输出 accept、defer，或“在声明域和预算内未找到可行设计”。defer 的候选进入有限 Abaqus 裁决。",
             "可追溯的候选清单、评分分解和决策理由。",
             "禁止把“生成器没采到候选”直接写成“物理不可实现”。")

    add_step(doc, 10, "可选的边界自适应采样",
             "随机采样容易把预算花在已经学会的区域，而关键证据集中在机制变化边界和高不确定区域。",
             "按机制熵、顺序事件接近程度、模型分歧和几何多样性组合选择 30 个边界样本；批内用 k-center 或最远点保持多样性。",
             "更密集的机制边界数据和 FE 学习曲线。",
             "主动采样不是主创新；只有在同预算、同初始集的 LHS 对照中有效时才形成独立结论。")

    add_step(doc, 11, "密封 OOD 与公平算法比较",
             "随机测试集容易高估泛化能力，且后验挑目标会造成选择偏差。",
             "预先冻结 48 次独立前瞻 FE，用相同训练数据、相同 K、相同推理和 Abaqus 预算比较：Small/MLP、Diffusion-only、Diffusion + curve-only verifier、完整机制验证闭环。",
             "联合 success@1/5/10、错误接受率、风险–覆盖曲线和每个成功目标所需 FE 次数。",
             "测试目标不能参与主动学习、阈值选择或候选规则调节；报告效应量和置信区间。")

    add_step(doc, 12, "36 件打印压缩与侧面视频验证",
             "FE 中的机制差异必须在实物中至少保留可观察意义，否则不能声称工程有效。",
             "选择 6 个密封目标；每个目标选 1 个 curve-only 候选与 1 个 mechanism-aware 候选；每个设计打印 3 个重复件，共 36 件。跨至少 3 个打印批次阻断和随机化，记录质量、尺寸、加载顺序和固定侧视视频。",
             "实验曲线、表面投影塌缩顺序、局部化位置及重复件离散性。",
             "统计单位主要是 6 个目标和 12 个设计，不是 36 个完全独立样本；只支持选定设计对的概念验证，不证明普适制造可靠性。")

    add_heading(doc, "六、240 次 Abaqus 分析如何分配", 1)
    budget_rows = [
        ("F0 数值与标签校准", "18", "6 个锚点 × 3 种数值设置；不计入独立测试证据"),
        ("F1 机制发现", "36", "寻找等响应机制分歧，完成 Gate 1"),
        ("F2 边界自适应采样", "30", "补充模式转换边界与高不确定区域"),
        ("F3 设计对独立确认", "24", "确认至少 6 个目标配对及复算稳定性"),
        ("F4 密封 OOD 测试", "48", "模型与规则冻结后一次性打开"),
        ("F5 扰动分析", "84", "12 个代表设计 × 7 个预注册场景"),
        ("合计", "240", "约 140–150 个名义设计 + 配对复算/扰动；须保存重复关系"),
    ]
    add_simple_table(doc, ["批次", "分析数", "用途"], budget_rows,
                     [2600, 1100, 5660], font_size=9.1, first_col_bold=True)
    add_body(doc, "说明：扰动若未由 CT 或实测缺陷分布标定，应称为“所研究扰动场景”，不能直接等同于真实制造缺陷概率分布。", color=GOLD)

    add_heading(doc, "七、算法框架：哪些部分保留，哪些部分必须改", 1)
    algo_rows = [
        ("几何编译器", "保留并强化", "把参数转为空间场、轴向图和合法性标志；它是物理坐标系。"),
        ("Graph Transformer", "需要适配", "输入不再是把少量标量硬凑成图，而是真实轴向区域图；输出增加局部机制、有效性和不确定性。"),
        ("Conditional Diffusion / DiT", "主体可复用", "继续负责多解候选生成；不负责证明候选正确。需增加机制条件接口和固定 K 的公平比较。"),
        ("前向–逆向闭环", "必须重构", "由 verifier 进行曲线/机制/风险排序，并允许 defer。前向模块的价值由密封 FE 验证，而不是网络名称。"),
        ("主动学习", "轻量可选", "只用于有限预算下补边界；若无同预算对照，不作为主要创新。"),
        ("DiffuMeta 自由代数语法", "Paper A 暂缓", "会扩大几何域、网格和制造验证范围，优先留给长期主论文/Paper B。"),
    ]
    add_simple_table(doc, ["模块", "处理方式", "本项目中的真实作用"], algo_rows,
                     [2100, 1550, 5710], font_size=9.2, first_col_bold=True)

    add_heading(doc, "八、评价指标与必要对照", 1)
    add_heading(doc, "8.1 主要指标", 2)
    metric_rows = [
        ("前向曲线", "NRMSE、峰值/平台/致密化误差、吸能误差"),
        ("局部机制", "塌缩起始应变 MAE、顺序 exact match、Kendall 距离、局部化中心误差"),
        ("不确定性与拒答", "Brier/ECE、风险–覆盖曲线、AURC、错误接受率"),
        ("逆向设计", "Abaqus 验证后的联合 success@1/5/10、有效候选率、多样性、单位成功 FE 成本"),
        ("物理实验", "曲线 NRMSE、投影顺序一致率、局部化位置误差、重复件 CV、目标级配对效应"),
    ]
    add_simple_table(doc, ["任务", "指标"], metric_rows, [2300, 7060], font_size=9.4, first_col_bold=True)

    add_heading(doc, "8.2 必须做的基线和消融", 2)
    for item in [
        "前向表示：Small 六通道 MLP / 普通 MLP / 1D CNN / 参数 Transformer / MPNN / 轴向 Graph Transformer。",
        "图结构：真实轴向边 / 完全连接图 / 打乱边 / 无图模型。",
        "任务头：curve-only / curve + local history / curve + mechanism + uncertainty。",
        "逆向闭环：Diffusion-only / + 几何筛选 / + curve verifier / + mechanism verifier / + evidence gate。",
        "生成器：Diffusion 与 CMA-ES、多起点代理优化等在同候选数和时间预算下比较。",
        "数据采样：自适应边界采样与同预算 LHS/随机采样比较。",
        "顺序分数：扰动归一化分数与原始最小事件间隔、密度、梯度、最小壁厚等简单基线比较。",
    ]:
        add_bullet(doc, item, bullet_id)

    add_heading(doc, "九、16 周执行计划与阶段门", 1)
    timeline_rows = [
        ("第 1–2 周", "冻结研究域；完成几何编译与 18 次 FE 校准", "G0：数值链和标签稳定"),
        ("第 3–4 周", "36 次先导发现；提取局部机制", "G1：至少 3 组探索性设计对"),
        ("第 5–8 周", "原创数据、轴向图模型、边界采样并行", "G2：至少 6 个可复算目标配对；否则转向"),
        ("第 9–11 周", "逆向闭环、48 次密封 OOD、核心消融", "G3：完整闭环在联合 success@K 或拒答风险上有价值"),
        ("第 10–13 周", "样件打印、36 件压缩与侧面视频", "G4：选定设计对的实验机制趋势可重复"),
        ("第 14–16 周", "统计、补算、主图、写作与内部审稿", "冻结结论边界并投稿"),
    ]
    add_simple_table(doc, ["时间", "主要工作", "阶段门"], timeline_rows,
                     [1550, 4610, 3200], font_size=9.2, first_col_bold=True)

    add_heading(doc, "十、最终创新点：按重要性排序", 1)
    innovation_rows = [
        ("1. 问题创新", "把“匹配曲线”升级为“判断目标是否有证据可实现，以及通过什么局部机制实现”。"),
        ("2. 科学发现", "系统检验渐变 TPMS 中的等响应机制分歧，以及局部塌缩事件分离与扰动后顺序翻转的关系。"),
        ("3. 概念框架", "在预注册研究域内估计并标注机制分辨的经验可实现区域，区分名义、机制约束和扰动场景下的可实现性。"),
        ("4. 原创数据", "建立同时含全局曲线、局部历史、塌缩起始/顺序、失败样本和扰动配对的新 Abaqus 数据集。"),
        ("5. 问题定制方法", "轴向图多任务验证器 + Diffusion 多解提议 + 几何硬约束 + 证据门控。"),
        ("6. 证据创新", "结构分组、密封前瞻 FE、固定预算和 36 件配对压缩视频构成完整验证链。"),
    ]
    add_simple_table(doc, ["层级", "贡献"], innovation_rows, [2100, 7260], font_size=9.35, first_col_bold=True)

    add_heading(doc, "十一、可以说什么，不能说什么", 1)
    claim_rows = [
        ("建立所研究设计域内的经验可实现区域", "建立所有 TPMS 的普适可实现域"),
        ("发现/表征等响应机制分歧（需通过 Gate）", "证明存在隐藏稳定性分岔"),
        ("顺序分离分数是本工作流中的候选指标", "提出普适的新物理定律或可靠性证书"),
        ("在密封 FE 与选定实验对上改善联合成功率", "实现任意 OOD 泛化或工业可靠设计"),
        ("在声明域和预算内未找到可行设计", "证明目标物理上绝对不可达"),
        ("单侧视频验证表面投影顺序与局部化", "单侧视频获得内部三维全场应力/应变"),
        ("36 件试样支持 6 个目标配对的概念验证", "n=36 足以证明普适低失效概率"),
    ]
    add_simple_table(doc, ["建议表述", "禁止或谨慎表述"], claim_rows,
                     [4680, 4680], font_size=9.15)

    add_heading(doc, "十二、主要风险与降级路线", 1)
    risk_rows = [
        ("找不到稳定的等响应机制分歧", "转为经验可实现包络 + OOD 拒答；已有 FE 和验证器仍可复用。"),
        ("Graph Transformer 不优于简单模型", "采用 1D CNN/Transformer/MLP，把图模型从创新点中删除。"),
        ("顺序分离分数解释力弱", "保留为描述量，进一步比较能量、接触起始或耗散间隔，不宣称统一规律。"),
        ("Diffusion 不优于低维优化", "将其降为候选生成基线，论文主线保留问题、数据和证据门控。"),
        ("Abaqus 局部标签不稳定", "缩小应变窗口、简化接触/材料模型，先保证可重复的轴向顺序标签。"),
        ("实验与 FE 偏差大", "限制结论到配对趋势和投影机制；增加尺寸/质量标定，不宣称制造鲁棒性。"),
        ("时间不足", "优先完成 G0–G3 和 24 件核心试样；取消鞋底演示、自由语法和次级实验。"),
    ]
    add_simple_table(doc, ["风险", "降级路线"], risk_rows, [3500, 5860], font_size=9.25, first_col_bold=True)

    add_heading(doc, "十三、项目完成时应交付什么", 1)
    deliverables = [
        "可版本追踪的渐变 TPMS 几何编译器、Abaqus 自动建模/提交/后处理脚本。",
        "按母结构分组的 Small 数据拆分与泄漏审计记录。",
        "约 140–150 个名义设计及其配对复算/扰动组成的 240 次 Abaqus 分析数据。",
        "局部机制标签规则、人工复核记录和数据字典。",
        "MLP/1D CNN/Transformer/MPNN/Graph Transformer 前向基线与公平消融。",
        "Diffusion 候选生成、几何筛选、前向排序、证据门控和 Abaqus 裁决闭环。",
        "48 次密封前瞻 FE 结果与 risk–coverage / success@K 报告。",
        "36 件压缩试样、固定侧面视频、目标级配对统计和失败案例。",
        "可复现实验配置、随机种子、模型检查点、主图和补充材料。",
    ]
    for item in deliverables:
        add_bullet(doc, item, bullet_id)

    add_heading(doc, "十四、给导师汇报时的 60 秒版本", 1)
    add_callout(
        doc,
        "汇报口径",
        "Paper A 不再研究“换一个更强网络能否把误差再降一点”，而研究一个真实设计缺口：同一条目标曲线可能由不同局部塌缩路径实现，而现有生成模型既看不到这种差异，也不会判断证据是否足够。我们先用 36 个先导 Abaqus 样本验证这一现象，再用约 240 次分析建立带局部机制标签的新数据集；Small++ 中的 Diffusion 负责提出多解候选，轴向 Graph Transformer 负责预测曲线、塌缩顺序和不确定性，证据门控决定接受、延后或报告有限预算内未找到。最后用 48 次密封 FE 和 36 件重复压缩视频做前瞻验证。路线的最大风险可在第 4 周前判断，即使核心机制假设不成立，已有数据和代码也能转为可实现包络与 OOD 拒答论文。",
        fill="E8EEF5",
        accent=NAVY,
    )

    add_heading(doc, "十五、建议保留的关键参考文献", 1)
    refs = [
        "Zong et al. Machine-Learning-Powered Rapid, Accurate, and Multi-Target Mechanical Metamaterials Inverse Design. Small (2025). DOI: 10.1002/smll.202500634.",
        "Bastek and Kochmann. Inverse design of nonlinear mechanical metamaterials via video denoising diffusion models. Nature Machine Intelligence (2023). DOI: 10.1038/s42256-023-00762-x.",
        "Maurizi et al. Designing metamaterials with programmable nonlinear responses and geometric constraints in graph space. Nature Machine Intelligence (2025). DOI: 10.1038/s42256-025-01067-x.",
        "Ha et al. Rapid inverse design of metamaterials based on prescribed mechanical behavior through machine learning. Nature Communications (2023). DOI: 10.1038/s41467-023-40854-1.",
        "Chai et al. Tailoring stress–strain curves of flexible snapping mechanical metamaterials. Advanced Materials (2024). DOI: 10.1002/adma.202404369.",
        "Bastek et al. DiffuMeta: algebraic implicit geometry generation with diffusion transformers. Nature Machine Intelligence (2026). DOI: 10.1038/s42256-026-01218-8.",
        "Zhang et al. Compression and deformation localization of nonlinear periodically graded porous structures. Materials & Design (2022). DOI: 10.1016/j.matdes.2022.111257.",
        "Geifman and El-Yaniv. SelectiveNet: A Deep Neural Network with an Integrated Reject Option. ICML (2019).",
    ]
    for ref in refs:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.18)
        p.paragraph_format.hanging_indent = Inches(0.18)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        r = p.add_run(ref)
        set_run_font(r, size=9.2, color=INK)

    add_heading(doc, "结论", 1)
    add_body(doc, "Paper A 的最稳妥定位是：以“机制分辨的经验可实现域”为主线，以原创 Abaqus 机制数据为核心资产，以 Graph Transformer + Diffusion 为解决多解生成和候选验证的工具，再用密封 FE 与小规模重复压缩完成证据闭环。它比单纯的架构升级更问题驱动，也比完整工业可靠性研究更适合 3–4 个月的资源边界。", bold_prefix="Paper A 的最稳妥定位是：")

    # Prevent table rows from being artificially pinned and set document core properties.
    doc.core_properties.title = "论文 A 最终研究框架与执行总纲"
    doc.core_properties.subject = "机制分辨经验可实现域驱动的渐变 TPMS 逆向设计"
    doc.core_properties.author = "Small++ Project"
    doc.core_properties.keywords = "TPMS, inverse design, Graph Transformer, diffusion, attainability"
    doc.core_properties.comments = "Generated as a concise project execution brief."

    doc.save(OUT_PATH)
    print(OUT_PATH)


if __name__ == "__main__":
    build_doc()
