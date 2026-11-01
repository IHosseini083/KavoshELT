from __future__ import annotations

import html
import os
import re
from typing import Any, Dict, List, Tuple

import arabic_reshaper
from bidi.algorithm import get_display

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph as DocxParagraph
from docx.text.run import Run as DocxRun

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

FONTS_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")
VAZIR_REG = os.path.join(FONTS_DIR, "Vazirmatn-Regular.ttf")
VAZIR_BOLD = os.path.join(FONTS_DIR, "Vazirmatn-Bold.ttf")

_FONTS_REGISTERED = False


def ensure_fonts_registered() -> Tuple[str, str]:
    global _FONTS_REGISTERED
    if (
        not _FONTS_REGISTERED
        and os.path.exists(VAZIR_REG)
        and os.path.exists(VAZIR_BOLD)
    ):
        pdfmetrics.registerFont(TTFont("Vazirmatn", VAZIR_REG))
        pdfmetrics.registerFont(TTFont("Vazirmatn-Bold", VAZIR_BOLD))
        _FONTS_REGISTERED = True
    if _FONTS_REGISTERED:
        return "Vazirmatn", "Vazirmatn-Bold"
    return "Helvetica", "Helvetica-Bold"


def has_persian(text_str: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]", text_str))


def shape_persian(text_str: str) -> str:
    if not text_str or not has_persian(text_str):
        return text_str
    reshaped = arabic_reshaper.reshape(text_str)
    return str(get_display(reshaped))


def _set_paragraph_rtl(paragraph: DocxParagraph, is_rtl: bool = True) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    bidi = p_pr.find(qn("w:bidi"))
    if is_rtl:
        if bidi is None:
            bidi = OxmlElement("w:bidi")
            p_pr.append(bidi)
        bidi.set(qn("w:val"), "1")
    else:
        if bidi is not None:
            p_pr.remove(bidi)


def _set_run_rtl_and_font(run: DocxRun, font_name: str, is_rtl: bool = True) -> None:
    run.font.name = font_name
    r_pr = run._r.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.append(r_fonts)
    r_fonts.set(qn("w:ascii"), font_name)
    r_fonts.set(qn("w:hAnsi"), font_name)
    r_fonts.set(qn("w:cs"), font_name)

    rtl_el = r_pr.find(qn("w:rtl"))
    if is_rtl:
        if rtl_el is None:
            rtl_el = OxmlElement("w:rtl")
            r_pr.append(rtl_el)
        rtl_el.set(qn("w:val"), "1")
    else:
        if rtl_el is not None:
            r_pr.remove(rtl_el)


def _set_table_rtl(table: DocxTable) -> None:
    tbl_pr = table._tbl.tblPr
    if tbl_pr is not None:
        bidi_vis = tbl_pr.find(qn("w:bidiVisual"))
        if bidi_vis is None:
            bidi_vis = OxmlElement("w:bidiVisual")
            tbl_pr.append(bidi_vis)


def parse_exam_markdown(md_path: str) -> Dict[str, Any]:
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    title_match = re.search(r"#\s+(.+)", content)
    title = title_match.group(1).strip() if title_match else "English Examination"

    subtitle_match = re.search(r"##\s+(.+)", content)
    subtitle = subtitle_match.group(1).strip() if subtitle_match else ""

    grade_label = "پایه دهم (Vision 1)"
    if "نهم" in title or "Grade 9" in content:
        grade_label = "پایه نهم (Prospect 3)"
    elif "هفتم" in title or "Grade 7" in content:
        grade_label = "پایه هفتم (Prospect 1)"
    elif "هشتم" in title or "Grade 8" in content:
        grade_label = "پایه هشتم (Prospect 2)"
    elif "یازدهم" in title or "Grade 11" in content:
        grade_label = "پایه یازدهم (Vision 2)"
    elif "دوازدهم" in title or "Grade 12" in content:
        grade_label = "پایه دوازدهم (Vision 3)"

    term_label = (
        "نوبت دوم (خردادماه)"
        if ("نوبت دوم" in title or "Term 2" in content)
        else "نوبت اول (دی‌ماه)"
    )

    student_section = content
    script_section = ""
    key_section = ""

    for sec1, sec2, sec3 in [
        ("## بخش اول", "## بخش دوم", "## بخش سوم"),
        ("## بخش ۱", "## بخش ۲", "## بخش ۳"),
    ]:
        if sec1 in content:
            rest = content.split(sec1, 1)[1]
            if sec2 in rest:
                student_section, rest2 = rest.split(sec2, 1)
                if sec3 in rest2:
                    script_section, key_section = rest2.split(sec3, 1)
                else:
                    script_section = rest2
            else:
                student_section = rest
            break

    def parse_lines(raw_block: str) -> List[Tuple[str, str]]:
        items: List[Tuple[str, str]] = []
        for line in raw_block.strip().split("\n"):
            line_s = line.strip()
            if (
                not line_s
                or line_s.startswith("---")
                or line_s.startswith("**نام")
                or line_s.startswith("**کلاس")
                or line_s.startswith("**مدت")
                or line_s.startswith("**نمره")
            ):
                continue
            if line_s.startswith("### ") or line_s.startswith("#### "):
                items.append(("heading", line_s.lstrip("#").replace("**", "").strip()))
            elif line_s.startswith(">"):
                items.append(
                    ("instruction", line_s.lstrip("> *").replace("**", "").strip())
                )
            elif re.match(r"^(\*\*)?\d+\.", line_s):
                items.append(("question", line_s.replace("**", "")))
            elif re.match(r"^[a-d]\)", line_s) or re.match(r"^-\s*[a-d]\)", line_s):
                items.append(("option", line_s.lstrip("- ").strip()))
            elif line_s.startswith("* ") or line_s.startswith("- "):
                items.append(("bullet", line_s[2:].replace("**", "").strip()))
            elif not line_s.startswith("```"):
                items.append(("text", line_s.replace("**", "")))
        return items

    return {
        "title": title,
        "subtitle": subtitle,
        "grade_label": grade_label,
        "term_label": term_label,
        "items": parse_lines(student_section),
        "script_items": parse_lines(script_section),
        "key_items": parse_lines(key_section),
    }


def generate_exam_docx(
    md_path: str,
    out_docx: str,
    school_name: str = "دبیرستان نمونه دولتی",
) -> None:
    exam_data = parse_exam_markdown(md_path)
    doc = docx.Document()

    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.55)
        section.right_margin = Inches(0.55)

    top_p = doc.add_paragraph()
    top_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_paragraph_rtl(top_p, True)
    top_run = top_p.add_run("به نام خدا")
    top_run.bold = True
    top_run.font.size = Pt(11)
    _set_run_rtl_and_font(top_run, "Vazirmatn", True)
    top_p.paragraph_format.space_after = Pt(4)

    table = doc.add_table(rows=3, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    _set_table_rtl(table)

    headers = [
        (
            "نام و نام خانوادگی: .............................",
            "درس: زبان انگلیسی (شنیداری)",
            "تاریخ امتحان: ۱۴۰۵/..../....",
            "نمره با عدد: ............ از ۱۰",
        ),
        (
            "نام پدر: ...........................................",
            f"پایه تحصیلی: {exam_data['grade_label']}",
            "مدت امتحان: ۲۰ دقیقه",
            "نمره با حروف: ........................",
        ),
        (
            "کلاس / شماره داوطلب: ....................",
            f"آموزشگاه: {school_name}",
            f"نوبت: {exam_data['term_label']}",
            "نام و امضای مصحح: ...............",
        ),
    ]

    for r_idx, row in enumerate(headers):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            _set_paragraph_rtl(p, True)
            run = p.add_run(val)
            run.font.size = Pt(9)
            run.bold = True
            _set_run_rtl_and_font(run, "Vazirmatn", True)

    doc.add_paragraph()

    for item_type, val in exam_data["items"]:
        is_fa = has_persian(val)
        if item_type == "heading":
            h = doc.add_paragraph()
            h.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_fa else WD_ALIGN_PARAGRAPH.LEFT
            _set_paragraph_rtl(h, is_fa)
            run = h.add_run(val)
            run.bold = True
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
            _set_run_rtl_and_font(run, "Vazirmatn" if is_fa else "Calibri", is_fa)
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(3)
        elif item_type == "instruction":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_fa else WD_ALIGN_PARAGRAPH.LEFT
            _set_paragraph_rtl(p, is_fa)
            run = p.add_run(val)
            run.italic = not is_fa
            run.bold = is_fa
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
            _set_run_rtl_and_font(run, "Vazirmatn" if is_fa else "Calibri", is_fa)
            p.paragraph_format.space_after = Pt(4)
        elif item_type == "question":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _set_paragraph_rtl(p, False)
            run = p.add_run(val)
            run.font.size = Pt(10.5)
            run.bold = True
            _set_run_rtl_and_font(run, "Calibri", False)
            p.paragraph_format.left_indent = Inches(0.1)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(2)
        elif item_type == "option":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _set_paragraph_rtl(p, False)
            run = p.add_run("    ( )  " + val)
            run.font.size = Pt(10)
            _set_run_rtl_and_font(run, "Calibri", False)
            p.paragraph_format.left_indent = Inches(0.3)
            p.paragraph_format.space_after = Pt(1)
        else:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_fa else WD_ALIGN_PARAGRAPH.LEFT
            _set_paragraph_rtl(p, is_fa)
            run = p.add_run(val)
            run.font.size = Pt(9.5)
            _set_run_rtl_and_font(run, "Vazirmatn" if is_fa else "Calibri", is_fa)
            p.paragraph_format.space_after = Pt(2)

    footer_p = doc.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_paragraph_rtl(footer_p, True)
    footer_p.paragraph_format.space_before = Pt(12)
    f_run = footer_p.add_run("جمع بارم: ۱۰ نمره  |  موفق و پیروز باشید — Good Luck!")
    f_run.bold = True
    f_run.font.size = Pt(9.5)
    _set_run_rtl_and_font(f_run, "Vazirmatn", True)

    doc.save(out_docx)
    print(f"[OK] Word document generated: {out_docx}")


def generate_exam_pdf(
    md_path: str,
    out_pdf: str,
    school_name: str = "دبیرستان نمونه دولتی",
) -> None:
    font_reg, font_bold = ensure_fonts_registered()
    exam_data = parse_exam_markdown(md_path)

    doc = SimpleDocTemplate(
        out_pdf,
        pagesize=A4,
        rightMargin=32,
        leftMargin=32,
        topMargin=28,
        bottomMargin=28,
    )

    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(
        "BaseNormal",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=9.5,
        leading=13,
    )

    fa_header_style = ParagraphStyle(
        "FaHeader",
        parent=normal_style,
        fontName=font_bold,
        fontSize=8.5,
        leading=13,
        alignment=2,
        textColor=colors.HexColor("#1A202C"),
    )

    god_style = ParagraphStyle(
        "InTheNameOfGod",
        parent=normal_style,
        fontName=font_bold,
        fontSize=11,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=6,
    )

    heading_ltr = ParagraphStyle(
        "PartHeadingLTR",
        parent=normal_style,
        fontName=font_bold,
        fontSize=10.5,
        leading=14,
        alignment=0,
        textColor=colors.HexColor("#1A365D"),
        backColor=colors.HexColor("#EBF8FF"),
        borderPadding=4,
        spaceBefore=8,
        spaceAfter=4,
    )

    instruction_rtl = ParagraphStyle(
        "InstructionRTL",
        parent=normal_style,
        fontName=font_reg,
        fontSize=9,
        leading=13,
        alignment=2,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=5,
    )

    instruction_ltr = ParagraphStyle(
        "InstructionLTR",
        parent=normal_style,
        fontName=font_reg,
        fontSize=9,
        leading=12,
        alignment=0,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=4,
    )

    q_style = ParagraphStyle(
        "QuestionLTR",
        parent=normal_style,
        fontName=font_bold,
        fontSize=9.5,
        leading=13,
        leftIndent=6,
        spaceBefore=3,
        spaceAfter=2,
    )

    opt_style = ParagraphStyle(
        "OptionLTR",
        parent=normal_style,
        fontName=font_reg,
        fontSize=9,
        leading=12,
        leftIndent=20,
        spaceAfter=1,
    )

    footer_style = ParagraphStyle(
        "FooterStyle",
        parent=normal_style,
        fontName=font_bold,
        fontSize=9.5,
        leading=13,
        alignment=1,
        textColor=colors.HexColor("#1A365D"),
        spaceBefore=12,
    )

    story: List[Any] = []
    story.append(Paragraph(shape_persian("به نام خدا"), god_style))

    header_rows = [
        [
            Paragraph(shape_persian("نمره با عدد: .......... از ۱۰"), fa_header_style),
            Paragraph(shape_persian("مدت آزمون: ۲۰ دقیقه"), fa_header_style),
            Paragraph(
                shape_persian("نام درس: زبان انگلیسی (شنیداری)"), fa_header_style
            ),
            Paragraph(
                shape_persian("نام و نام خانوادگی: ................................."),
                fa_header_style,
            ),
        ],
        [
            Paragraph(
                shape_persian("نمره با حروف: ........................"), fa_header_style
            ),
            Paragraph(
                shape_persian(f"نوبت: {exam_data['term_label']}"), fa_header_style
            ),
            Paragraph(
                shape_persian(f"پایه: {exam_data['grade_label']}"), fa_header_style
            ),
            Paragraph(
                shape_persian("کلاس / شعبه: ......................................"),
                fa_header_style,
            ),
        ],
        [
            Paragraph(
                shape_persian("امضای مصحح: ........................."), fa_header_style
            ),
            Paragraph(shape_persian("تاریخ: ۱۴۰۵/..../...."), fa_header_style),
            Paragraph(shape_persian(f"آموزشگاه: {school_name}"), fa_header_style),
            Paragraph(
                shape_persian("شماره داوطلب: ....................................."),
                fa_header_style,
            ),
        ],
    ]

    col_w = (A4[0] - 64) / 4.0
    header_table = Table(header_rows, colWidths=[col_w] * 4)
    header_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor("#1A365D")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 8))

    for item_type, val in exam_data["items"]:
        clean_val = val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        is_fa = has_persian(clean_val)
        rendered_text = shape_persian(clean_val) if is_fa else clean_val

        if item_type == "heading":
            story.append(Paragraph(rendered_text, heading_ltr))
        elif item_type == "instruction":
            story.append(
                Paragraph(rendered_text, instruction_rtl if is_fa else instruction_ltr)
            )
        elif item_type == "question":
            story.append(Paragraph(rendered_text, q_style))
        elif item_type == "option":
            story.append(Paragraph(f"( )  {rendered_text}", opt_style))
        else:
            story.append(
                Paragraph(rendered_text, instruction_rtl if is_fa else normal_style)
            )

    story.append(Spacer(1, 8))
    story.append(
        HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E0"))
    )
    story.append(
        Paragraph(
            shape_persian("جمع بارم: ۱۰ نمره  |  موفق و پیروز باشید") + " — Good Luck!",
            footer_style,
        )
    )

    doc.build(story)
    print(f"[OK] PDF generated: {out_pdf}")


def generate_answer_key_pdf(
    md_path: str,
    out_pdf: str,
    school_name: str = "دبیرستان نمونه دولتی",
) -> None:
    font_reg, font_bold = ensure_fonts_registered()
    exam_data = parse_exam_markdown(md_path)

    doc = SimpleDocTemplate(
        out_pdf,
        pagesize=A4,
        rightMargin=32,
        leftMargin=32,
        topMargin=28,
        bottomMargin=28,
    )

    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(
        "KeyNormal",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=9,
        leading=13,
    )
    title_style = ParagraphStyle(
        "KeyTitle",
        parent=normal_style,
        fontName=font_bold,
        fontSize=12,
        leading=16,
        alignment=1,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=8,
    )
    sec_style = ParagraphStyle(
        "KeySection",
        parent=normal_style,
        fontName=font_bold,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2B6CB0"),
        backColor=colors.HexColor("#EDF2F7"),
        borderPadding=4,
        spaceBefore=8,
        spaceAfter=4,
    )
    rtl_style = ParagraphStyle(
        "KeyRTL",
        parent=normal_style,
        fontName=font_reg,
        fontSize=9,
        leading=13,
        alignment=2,
    )

    story: List[Any] = []
    story.append(
        Paragraph(
            shape_persian(
                f"پاسخنامه تشریحی و راهنمای معلم — {exam_data['grade_label']} ({exam_data['term_label']})"
            ),
            title_style,
        )
    )
    story.append(
        HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#1A365D"))
    )
    story.append(Spacer(1, 6))

    if exam_data["key_items"]:
        story.append(Paragraph("Answer Key & Scoring Rubric", sec_style))
        for _, val in exam_data["key_items"]:
            clean_val = (
                val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )
            is_fa = has_persian(clean_val)
            txt = shape_persian(clean_val) if is_fa else clean_val
            story.append(Paragraph(txt, rtl_style if is_fa else normal_style))

    if exam_data["script_items"]:
        story.append(Spacer(1, 8))
        story.append(
            Paragraph(
                "Audio Transcripts (Teacher Read-Aloud / TTS Reference)", sec_style
            )
        )
        for _, val in exam_data["script_items"]:
            clean_val = (
                val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )
            is_fa = has_persian(clean_val)
            txt = shape_persian(clean_val) if is_fa else clean_val
            story.append(Paragraph(txt, rtl_style if is_fa else normal_style))

    doc.build(story)
    print(f"[OK] Answer Key PDF generated: {out_pdf}")


def generate_exam_html(
    md_path: str,
    out_html: str,
    school_name: str = "دبیرستان نمونه دولتی",
) -> None:
    exam_data = parse_exam_markdown(md_path)

    body_parts: List[str] = []
    for item_type, val in exam_data["items"]:
        esc = html.escape(val)
        is_fa = has_persian(val)
        dir_attr = "rtl" if is_fa else "ltr"
        if item_type == "heading":
            body_parts.append(f'<h3 class="part-heading" dir="{dir_attr}">{esc}</h3>')
        elif item_type == "instruction":
            body_parts.append(f'<p class="instruction" dir="{dir_attr}">{esc}</p>')
        elif item_type == "question":
            body_parts.append(f'<p class="question" dir="ltr">{esc}</p>')
        elif item_type == "option":
            body_parts.append(f'<p class="option" dir="ltr">( ) {esc}</p>')
        else:
            body_parts.append(f'<p class="text-line" dir="{dir_attr}">{esc}</p>')

    html_doc = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<title>{html.escape(exam_data["title"])}</title>
<style>
@page {{ size: A4; margin: 12mm; }}
body {{ font-family: 'Vazirmatn', 'Tahoma', 'Calibri', sans-serif; color: #1a202c; margin: 0; padding: 16px; font-size: 13px; }}
.god-header {{ text-align: center; font-weight: bold; font-size: 15px; color: #1a365d; margin-bottom: 8px; }}
.header-table {{ width: 100%; border-collapse: collapse; margin-bottom: 14px; background: #f7fafc; border: 2px solid #1a365d; }}
.header-table td {{ border: 1px solid #cbd5e0; padding: 6px 8px; font-weight: bold; font-size: 12px; text-align: right; }}
.part-heading {{ background: #ebf8ff; color: #1a365d; padding: 6px 10px; border-left: 4px solid #2b6cb0; margin-top: 14px; margin-bottom: 6px; font-size: 14px; }}
.instruction {{ color: #2d3748; font-weight: bold; margin: 4px 0 8px 0; font-size: 12.5px; }}
.question {{ font-family: 'Calibri', 'Arial', sans-serif; font-weight: bold; margin: 6px 0 3px 8px; font-size: 13.5px; }}
.option {{ font-family: 'Calibri', 'Arial', sans-serif; margin: 2px 0 2px 28px; font-size: 13px; }}
.footer {{ text-align: center; font-weight: bold; color: #1a365d; border-top: 1px solid #cbd5e0; margin-top: 18px; padding-top: 8px; }}
</style>
</head>
<body>
<div class="god-header">به نام خدا</div>
<table class="header-table" dir="rtl">
  <tr>
    <td>نام و نام خانوادگی: .................................</td>
    <td>نام درس: زبان انگلیسی (شنیداری)</td>
    <td>مدت آزمون: ۲۰ دقیقه</td>
    <td>نمره با عدد: .......... از ۱۰</td>
  </tr>
  <tr>
    <td>کلاس / شعبه: ......................................</td>
    <td>پایه: {html.escape(exam_data["grade_label"])}</td>
    <td>نوبت: {html.escape(exam_data["term_label"])}</td>
    <td>نمره با حروف: ........................</td>
  </tr>
  <tr>
    <td>شماره داوطلب: .....................................</td>
    <td>آموزشگاه: {html.escape(school_name)}</td>
    <td>تاریخ: ۱۴۰۵/..../....</td>
    <td>امضای مصحح: .........................</td>
  </tr>
</table>
{"".join(body_parts)}
<div class="footer">جمع بارم: ۱۰ نمره | موفق و پیروز باشید — Good Luck!</div>
</body>
</html>
"""
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"[OK] Printable HTML generated: {out_html}")
