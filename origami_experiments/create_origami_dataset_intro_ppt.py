from __future__ import annotations

import html
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"F:\small++\origami_experiments")
OUT_DIR = ROOT / "reports"
PPTX_PATH = OUT_DIR / "origami_dataset_intro_slide.pptx"
PNG_PATH = OUT_DIR / "origami_dataset_intro_slide_preview.png"

SLIDE_W = 13.333333
SLIDE_H = 7.5
EMU_PER_INCH = 914400

PX_W = 1600
PX_H = 900
PX_PER_INCH = 120

COLORS = {
    "navy": "0B3D78",
    "blue": "165BAA",
    "light_blue": "DCEBFA",
    "mid_blue": "7EAFDF",
    "red": "D71920",
    "gray": "F2F5F9",
    "dark": "111827",
    "text": "263238",
    "muted": "5B6B7A",
    "white": "FFFFFF",
    "green": "248A5B",
    "orange": "E68A00",
}


def emu(v: float) -> int:
    return int(round(v * EMU_PER_INCH))


def px(v: float) -> int:
    return int(round(v * PX_PER_INCH))


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def shape_xml(
    sid: int,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str = "FFFFFF",
    line: str | None = "0B3D78",
    radius: bool = False,
    text: str | None = None,
    font_size: int = 16,
    bold: bool = False,
    color: str = "111827",
    align: str = "ctr",
    margin: int = 65000,
) -> str:
    geom = "roundRect" if radius else "rect"
    line_xml = '<a:ln><a:noFill/></a:ln>' if line is None else f'<a:ln w="19050"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>'
    text_xml = ""
    if text is not None:
        paras = []
        for part in text.split("\n"):
            paras.append(
                f'<a:p><a:pPr algn="{align}"/><a:r><a:rPr lang="zh-CN" sz="{font_size * 100}" b="{1 if bold else 0}">'
                f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="Microsoft YaHei"/>'
                f'<a:ea typeface="Microsoft YaHei"/></a:rPr><a:t>{esc(part)}</a:t></a:r></a:p>'
            )
        text_xml = (
            f'<p:txBody><a:bodyPr lIns="{margin}" tIns="{margin}" rIns="{margin}" bIns="{margin}" anchor="mid"/>'
            f"<a:lstStyle/>{''.join(paras)}</p:txBody>"
        )
    return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{sid}" name="{esc(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
    <a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>
    {line_xml}
  </p:spPr>
  {text_xml}
</p:sp>"""


def text_xml(
    sid: int,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    font_size: int,
    color: str = "111827",
    bold: bool = False,
    align: str = "l",
) -> str:
    return shape_xml(sid, name, x, y, w, h, fill="FFFFFF", line=None, text=text, font_size=font_size, bold=bold, color=color, align=align, margin=0)


def line_xml(sid: int, x1: float, y1: float, x2: float, y2: float, color: str = "165BAA", weight: int = 3, arrow: bool = True) -> str:
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    flip_h = ' flipH="1"' if x2 < x1 else ""
    flip_v = ' flipV="1"' if y2 < y1 else ""
    arrow_xml = '<a:tailEnd type="triangle"/>' if arrow else ""
    return f"""
<p:cxnSp>
  <p:nvCxnSpPr><p:cNvPr id="{sid}" name="arrow {sid}"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>
  <p:spPr>
    <a:xfrm{flip_h}{flip_v}><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(max(w, 0.01))}" cy="{emu(max(h, 0.01))}"/></a:xfrm>
    <a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom>
    <a:ln w="{weight * 12700}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>{arrow_xml}</a:ln>
  </p:spPr>
</p:cxnSp>"""


def build_slide_xml() -> str:
    shapes: list[str] = []
    sid = 2

    # Header band
    shapes.append(shape_xml(sid, "top navy wedge", 0.0, 0.0, 1.15, 0.62, COLORS["navy"], None)); sid += 1
    shapes.append(shape_xml(sid, "top white band", 1.15, 0.0, 8.45, 0.62, COLORS["white"], None)); sid += 1
    shapes.append(shape_xml(sid, "top navy right", 9.6, 0.0, 3.73, 0.62, COLORS["navy"], None)); sid += 1
    shapes.append(text_xml(sid, "team", 1.22, 0.08, 6.0, 0.42, "仿生结构与机械智能研究团队", 21, COLORS["navy"], True)); sid += 1
    shapes.append(text_xml(sid, "institute", 10.0, 0.08, 2.75, 0.42, "先进仿生与智能机械创新研究院\n智能机器人与仿生工程研究中心", 8, COLORS["white"], True, "r")); sid += 1
    shapes.append(shape_xml(sid, "logo circle", 12.55, 0.08, 0.42, 0.42, COLORS["navy"], COLORS["white"], True, "研", 16, True, COLORS["white"])); sid += 1

    # Title
    shapes.append(shape_xml(sid, "red square", 0.18, 0.82, 0.22, 0.22, COLORS["white"], COLORS["red"])); sid += 1
    shapes.append(text_xml(sid, "title", 0.48, 0.72, 12.0, 0.46, "训练数据集介绍——Origami Sheet MaterialProperty 刚度数据集", 23, COLORS["dark"], True)); sid += 1

    # Top panels
    shapes.append(shape_xml(sid, "left panel", 0.35, 1.28, 5.95, 2.0, COLORS["white"], COLORS["blue"], True)); sid += 1
    shapes.append(shape_xml(sid, "left panel title", 0.48, 1.39, 5.69, 0.34, COLORS["light_blue"], None, True, "数据来源：Miura 与 TMP 两类折纸结构", 14, True, COLORS["dark"])); sid += 1
    shapes.append(text_xml(sid, "left desc", 0.55, 1.78, 5.45, 0.35, "原始仿真数据来自 GenerateOrigamiDataSet / Data_Origami_Sheet_MaterialProperty", 9, COLORS["dark"], True)); sid += 1

    top_cards = [
        ("Miura\n2000 条", "折纸模式 1"),
        ("TMP\n2000 条", "折纸模式 2"),
        ("共 4000\n条样本", "合并数据集"),
        ("3200 / 800", "train / test"),
    ]
    for i, (big, small) in enumerate(top_cards):
        x = 0.6 + i * 1.36
        shapes.append(shape_xml(sid, f"source card {i}", x, 2.18, 1.15, 0.82, COLORS["gray"], COLORS["mid_blue"], True)); sid += 1
        shapes.append(text_xml(sid, f"source card big {i}", x + 0.08, 2.28, 0.99, 0.28, big, 13, COLORS["blue"], True, "ctr")); sid += 1
        shapes.append(text_xml(sid, f"source card small {i}", x + 0.06, 2.72, 1.03, 0.18, small, 7, COLORS["muted"], False, "ctr")); sid += 1

    shapes.append(shape_xml(sid, "right panel", 6.55, 1.28, 6.4, 2.0, COLORS["white"], COLORS["blue"], True)); sid += 1
    shapes.append(shape_xml(sid, "right panel title", 6.68, 1.39, 6.14, 0.34, COLORS["light_blue"], None, True, "学习任务：8 个设计/材料参数 → 6 个刚度目标", 14, True, COLORS["dark"])); sid += 1
    task_cards = [
        ("pattern / m / n", "离散变量\nembedding"),
        ("tcrease / tpanel / W", "几何变量\nlog10 + 标准化"),
        ("creaseE / panelE", "材料变量\nlog10 + 标准化"),
        ("bend / axial × 3", "6 个刚度\nlog10(stiffness)"),
    ]
    for i, (big, small) in enumerate(task_cards):
        x = 6.85 + i * 1.42
        shapes.append(shape_xml(sid, f"task card {i}", x, 1.92, 1.22, 1.04, COLORS["gray"], COLORS["mid_blue"], True)); sid += 1
        shapes.append(text_xml(sid, f"task big {i}", x + 0.05, 2.04, 1.12, 0.22, big, 8, COLORS["blue"], True, "ctr")); sid += 1
        shapes.append(text_xml(sid, f"task small {i}", x + 0.08, 2.35, 1.06, 0.42, small, 7, COLORS["dark"], False, "ctr")); sid += 1

    # Main route panel
    shapes.append(shape_xml(sid, "route panel", 0.2, 3.42, 12.95, 2.55, COLORS["white"], COLORS["blue"], True)); sid += 1
    shapes.append(shape_xml(sid, "route title", 0.35, 3.53, 11.2, 0.34, COLORS["light_blue"], None, False, "技术路线：数据整理与模型训练链路", 15, True, COLORS["dark"])); sid += 1

    steps = [
        ("原始仿真", "MiuraSheetMat.txt\nTMPSheetMat.txt"),
        ("数据清洗", "合并 4000 条\n固定随机切分"),
        ("特征编码", "离散 id + embedding\n连续量 log 标准化"),
        ("正向训练", "8 参数 → 6 刚度\nResMLP/GAT/Transformer"),
        ("逆向训练", "6 刚度 → 8 参数\nResMLP/CVAE/Diffusion"),
        ("测试评估", "held-out test\nR² / MAE / NRMSE"),
    ]
    x0 = 0.55
    for i, (label, body) in enumerate(steps):
        x = x0 + i * 1.92
        shapes.append(shape_xml(sid, f"step circle {i}", x + 0.42, 4.1, 0.58, 0.58, COLORS["light_blue"], COLORS["blue"], True, str(i + 1), 17, True, COLORS["blue"])); sid += 1
        shapes.append(text_xml(sid, f"step label {i}", x, 4.77, 1.42, 0.24, label, 12, COLORS["dark"], True, "ctr")); sid += 1
        shapes.append(text_xml(sid, f"step body {i}", x - 0.1, 5.08, 1.62, 0.5, body, 8, COLORS["muted"], False, "ctr")); sid += 1
        if i < len(steps) - 1:
            shapes.append(line_xml(sid, x + 1.35, 4.4, x + 1.78, 4.4, COLORS["blue"], 2, True)); sid += 1

    # Right expected applications
    shapes.append(shape_xml(sid, "right app rail", 11.7, 3.88, 1.2, 1.85, COLORS["gray"], COLORS["mid_blue"], True)); sid += 1
    shapes.append(text_xml(sid, "right app vertical", 11.86, 4.04, 0.28, 1.3, "预\n期\n应\n用", 16, COLORS["blue"], True, "ctr")); sid += 1
    shapes.append(text_xml(sid, "right app text", 12.15, 4.08, 0.55, 1.2, "折纸刚度\n快速预测\n与逆向设计", 7, COLORS["dark"], True, "ctr")); sid += 1

    # Bottom strip
    bottom_y = 6.18
    items = [
        ("数据规模", "4000 = Miura 2000 + TMP 2000"),
        ("任务目标", "正向预测刚度；逆向生成设计参数"),
        ("关键澄清", "本页数据不是 Bump/TPMS Excel 数据集"),
    ]
    for i, (head, body) in enumerate(items):
        x = 0.55 + i * 4.05
        shapes.append(shape_xml(sid, f"bottom item {i}", x, bottom_y, 3.55, 0.62, COLORS["white"], COLORS["mid_blue"], True)); sid += 1
        shapes.append(text_xml(sid, f"bottom head {i}", x + 0.18, bottom_y + 0.12, 0.8, 0.18, head, 11, COLORS["blue"], True)); sid += 1
        shapes.append(text_xml(sid, f"bottom body {i}", x + 1.0, bottom_y + 0.1, 2.35, 0.24, body, 8, COLORS["dark"], True)); sid += 1

    shapes.append(text_xml(sid, "footer", 0.75, 7.02, 12.0, 0.28, "用于 ResMLP / GAT / Transformer / CVAE / Diffusion 的重训、调参与最终测试", 15, COLORS["red"], True, "ctr")); sid += 1

    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {''.join(shapes)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""


def package_pptx() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""
    presentation = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>
  <p:sldSz cx="{emu(SLIDE_W)}" cy="{emu(SLIDE_H)}" type="wide"/>
  <p:notesSz cx="{emu(10)}" cy="{emu(7.5)}"/>
</p:presentation>"""
    pres_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
</Relationships>"""
    theme = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Origami Dataset Theme">
  <a:themeElements>
    <a:clrScheme name="Office"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1><a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F497D"/></a:dk2><a:lt2><a:srgbClr val="EEECE1"/></a:lt2><a:accent1><a:srgbClr val="165BAA"/></a:accent1><a:accent2><a:srgbClr val="D71920"/></a:accent2><a:accent3><a:srgbClr val="248A5B"/></a:accent3><a:accent4><a:srgbClr val="E68A00"/></a:accent4><a:accent5><a:srgbClr val="7EAFDF"/></a:accent5><a:accent6><a:srgbClr val="5B6B7A"/></a:accent6><a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme>
    <a:fontScheme name="Office"><a:majorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:majorFont><a:minorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:minorFont></a:fontScheme>
    <a:fmtScheme name="Office"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
  </a:themeElements>
</a:theme>"""
    core = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>Origami Dataset Introduction</dc:title><dc:creator>Codex</dc:creator></cp:coreProperties>"""
    app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Codex</Application><PresentationFormat>Widescreen</PresentationFormat><Slides>1</Slides></Properties>"""

    with zipfile.ZipFile(PPTX_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("ppt/presentation.xml", presentation)
        z.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        z.writestr("ppt/slides/slide1.xml", build_slide_xml())
        z.writestr("ppt/slides/_rels/slide1.xml.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>""")
        z.writestr("ppt/theme/theme1.xml", theme)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)


def font(size: int, bold: bool = False):
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def draw_center(draw, box, text, fnt, fill, spacing=3):
    x, y, w, h = box
    lines = text.split("\n")
    heights = [draw.textbbox((0, 0), line, font=fnt)[3] for line in lines]
    total = sum(heights) + spacing * (len(lines) - 1)
    yy = y + (h - total) / 2
    for line, lh in zip(lines, heights):
        bbox = draw.textbbox((0, 0), line, font=fnt)
        draw.text((x + (w - (bbox[2] - bbox[0])) / 2, yy), line, font=fnt, fill=fill)
        yy += lh + spacing


def preview_png() -> None:
    img = Image.new("RGB", (PX_W, PX_H), "white")
    d = ImageDraw.Draw(img)
    def xy(x, y, w, h):
        return [px(x), px(y), px(x + w), px(y + h)]
    def rect(x, y, w, h, fill, outline=None, width=2, radius=8):
        d.rounded_rectangle(xy(x, y, w, h), radius=radius, fill="#" + fill, outline=("#" + outline) if outline else None, width=width)
    def txt(x, y, w, h, s, size, fill, bold=False, anchor="center"):
        f = font(size, bold)
        box = (px(x), px(y), px(w), px(h))
        if anchor == "center":
            draw_center(d, box, s, f, "#" + fill)
        else:
            d.multiline_text((box[0], box[1]), s, font=f, fill="#" + fill, spacing=4)

    d.rectangle(xy(0, 0, 1.15, 0.62), fill="#" + COLORS["navy"])
    d.rectangle(xy(1.15, 0, 8.45, 0.62), fill="white")
    d.rectangle(xy(9.6, 0, 3.73, 0.62), fill="#" + COLORS["navy"])
    txt(1.22, 0.08, 6.0, 0.42, "仿生结构与机械智能研究团队", 28, COLORS["navy"], True, "left")
    txt(10.0, 0.08, 2.75, 0.42, "先进仿生与智能机械创新研究院\n智能机器人与仿生工程研究中心", 11, COLORS["white"], True)
    rect(12.55, 0.08, 0.42, 0.42, COLORS["navy"], COLORS["white"], 2, 999)
    txt(12.55, 0.08, 0.42, 0.42, "研", 20, COLORS["white"], True)
    d.rectangle(xy(0.18, 0.82, 0.22, 0.22), outline="#" + COLORS["red"], width=5)
    txt(0.48, 0.72, 12.0, 0.46, "训练数据集介绍——Origami Sheet MaterialProperty 刚度数据集", 31, COLORS["dark"], True, "left")

    rect(0.35, 1.28, 5.95, 2.0, COLORS["white"], COLORS["blue"], 3, 12)
    rect(0.48, 1.39, 5.69, 0.34, COLORS["light_blue"], None, 1, 8)
    txt(0.48, 1.39, 5.69, 0.34, "数据来源：Miura 与 TMP 两类折纸结构", 18, COLORS["dark"], True)
    txt(0.55, 1.78, 5.45, 0.35, "原始仿真数据来自 GenerateOrigamiDataSet / Data_Origami_Sheet_MaterialProperty", 12, COLORS["dark"], True)
    for i, (big, small) in enumerate([("Miura\n2000 条", "折纸模式 1"), ("TMP\n2000 条", "折纸模式 2"), ("共 4000\n条样本", "合并数据集"), ("3200 / 800", "train / test")]):
        x = 0.6 + i * 1.36
        rect(x, 2.18, 1.15, 0.82, COLORS["gray"], COLORS["mid_blue"], 2, 10)
        txt(x + 0.08, 2.28, 0.99, 0.28, big, 17, COLORS["blue"], True)
        txt(x + 0.06, 2.72, 1.03, 0.18, small, 9, COLORS["muted"])

    rect(6.55, 1.28, 6.4, 2.0, COLORS["white"], COLORS["blue"], 3, 12)
    rect(6.68, 1.39, 6.14, 0.34, COLORS["light_blue"], None, 1, 8)
    txt(6.68, 1.39, 6.14, 0.34, "学习任务：8 个设计/材料参数 → 6 个刚度目标", 18, COLORS["dark"], True)
    for i, (big, small) in enumerate([("pattern / m / n", "离散变量\nembedding"), ("tcrease / tpanel / W", "几何变量\nlog10 + 标准化"), ("creaseE / panelE", "材料变量\nlog10 + 标准化"), ("bend / axial × 3", "6 个刚度\nlog10(stiffness)")]):
        x = 6.85 + i * 1.42
        rect(x, 1.92, 1.22, 1.04, COLORS["gray"], COLORS["mid_blue"], 2, 10)
        txt(x + 0.05, 2.04, 1.12, 0.22, big, 10, COLORS["blue"], True)
        txt(x + 0.08, 2.35, 1.06, 0.42, small, 9, COLORS["dark"])

    rect(0.2, 3.42, 12.95, 2.55, COLORS["white"], COLORS["blue"], 3, 12)
    rect(0.35, 3.53, 11.2, 0.34, COLORS["light_blue"], None, 1, 0)
    txt(0.35, 3.53, 11.2, 0.34, "技术路线：数据整理与模型训练链路", 19, COLORS["dark"], True)
    steps = [("原始仿真", "MiuraSheetMat.txt\nTMPSheetMat.txt"), ("数据清洗", "合并 4000 条\n固定随机切分"), ("特征编码", "离散 id + embedding\n连续量 log 标准化"), ("正向训练", "8 参数 → 6 刚度\nResMLP/GAT/Transformer"), ("逆向训练", "6 刚度 → 8 参数\nResMLP/CVAE/Diffusion"), ("测试评估", "held-out test\nR² / MAE / NRMSE")]
    for i, (label, body) in enumerate(steps):
        x = 0.55 + i * 1.92
        rect(x + 0.42, 4.1, 0.58, 0.58, COLORS["light_blue"], COLORS["blue"], 2, 999)
        txt(x + 0.42, 4.1, 0.58, 0.58, str(i + 1), 22, COLORS["blue"], True)
        txt(x, 4.77, 1.42, 0.24, label, 16, COLORS["dark"], True)
        txt(x - 0.1, 5.08, 1.62, 0.5, body, 10, COLORS["muted"])
        if i < len(steps) - 1:
            d.line([px(x + 1.35), px(4.4), px(x + 1.78), px(4.4)], fill="#" + COLORS["blue"], width=4)
            d.polygon([(px(x+1.78), px(4.4)), (px(x+1.68), px(4.35)), (px(x+1.68), px(4.45))], fill="#" + COLORS["blue"])
    rect(11.7, 3.88, 1.2, 1.85, COLORS["gray"], COLORS["mid_blue"], 2, 10)
    txt(11.86, 4.04, 0.28, 1.3, "预\n期\n应\n用", 20, COLORS["blue"], True)
    txt(12.15, 4.08, 0.55, 1.2, "折纸刚度\n快速预测\n与逆向设计", 9, COLORS["dark"], True)

    for i, (head, body) in enumerate([("数据规模", "4000 = Miura 2000 + TMP 2000"), ("任务目标", "正向预测刚度；逆向生成设计参数"), ("关键澄清", "本页数据不是 Bump/TPMS Excel 数据集")]):
        x = 0.55 + i * 4.05
        rect(x, 6.18, 3.55, 0.62, COLORS["white"], COLORS["mid_blue"], 2, 8)
        txt(x + 0.18, 6.3, 0.8, 0.18, head, 14, COLORS["blue"], True, "left")
        txt(x + 1.0, 6.28, 2.35, 0.24, body, 11, COLORS["dark"], True, "left")
    txt(0.75, 7.02, 12.0, 0.28, "用于 ResMLP / GAT / Transformer / CVAE / Diffusion 的重训、调参与最终测试", 20, COLORS["red"], True)
    img.save(PNG_PATH)


if __name__ == "__main__":
    package_pptx()
    preview_png()
    print(PPTX_PATH)
    print(PNG_PATH)
