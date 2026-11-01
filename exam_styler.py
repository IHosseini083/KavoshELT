import os
import re
from typing import Dict, Any, List, Optional, Tuple

import arabic_reshaper
from bidi.algorithm import get_display

# --- ReportLab Imports ---
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

# --- Docx Imports ---
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

FONTS_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")
VAZIR_REG = os.path.join(FONTS_DIR, "Vazirmatn-Regular.ttf")
VAZIR_BOLD = os.path.join(FONTS_DIR, "Vazirmatn-Bold.ttf")

_FONTS_REGISTERED = False


def ensure_fonts_registered() -> Tuple[str, str]:
    global _FONTS_REGISTERED
    if not _FONTS_REGISTERED and os.path.exists(VAZIR_REG) and os.path.exists(VAZIR_BOLD):
        pdfmetrics.registerFont(TTFont("Vazirmatn", VAZIR_REG))
        pdfmetrics.registerFont(TTFont("Vazirmatn-Bold", VAZIR_BOLD))
        _FONTS_REGISTERED = True
    if _FONTS_REGISTERED:
        return "Vazirmatn", "Vazirmatn-Bold"
    return "Helvetica", "Helvetica-Bold"


def has_persian(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]", text))


def shape_persian(text: str) -> str:
    if not text or not has_persian(text):
        return text
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def parse_exam_markdown(md_path: str) -> Dict[str, Any]:
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    title_match = re.search(r"#\s+(.+)", content)
    title = title_match.group(1).strip() if title_match else "English Examination"

    subtitle_match = re.search(r"##\s+(.+)", content)
    subtitle = subtitle_match.group(1).strip() if subtitle_match else ""

    # Detect grade and term from title or content
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

    term_label = "نوبت دوم (خردادماه)" if ("نوبت دوم" in title or "Term 2" in content) else "نوبت اول (دی‌ماه)"

    # Split sections
    student_section = content
    script_section = ""
    key_section = ""

    if "## بخش اول" in content:
        rest = content.split("## بخش اول", 1)[1]
        if "## بخش دوم" in rest:
            student_section, rest2 = rest.split("## بخش دوم", 1)
            if "## بخش سوم" in rest2:
                script_section, key_section = rest2.split("## بخش سوم", 1)
            else:
                script_section = rest2
        else:
            student_section = rest
    elif "## بخش ۱" in content:
        rest = content.split("## بخش ۱", 1)[1]
        if "## بخش ۲" in rest:
            student_section, rest2 = rest.split("## بخش ۲", 1)
            if "## بخش ۳" in rest2:
                script_section, key_section = rest2.split("## بخش ۳", 1)
            else:
                script_section = rest2
        else:
            student_section = rest

    def parse_lines(raw_block: str) -> List[Tuple[str, str]]:
        items: List[Tuple[str, str]] = []
        for line in raw_block.strip().split("\n"):
            line_s = line.strip()
            if not line_s or line_s.startswith("---") or line_s.startswith("**نام") or line_s.startswith("**کلاس") or line_s.startswith("**مدت") or line_s.startswith("**نمره"):
                continue
            if line_s.startswith("### ") or line_s.startswith("#### "):
                items.append(("heading", line_s.lstrip("#").replace("**", "").strip()))
            elif line_s.startswith(">"):
                items.append(("instruction", line_s.lstrip("> *").replace("**", "").strip()))
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

    # Top "In the Name of God"
    top_p = doc.add_paragraph()
    top_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    top_run = top_p.add_run("به نام خدا")
    top_run.bold = True
    top_run.font.size = Pt(11)
    top_run.font.name = "Vazirmatn"
    top_p.paragraph_format.space_after = Pt(4)

    # 1. Official Exam Header Table
    table = doc.add_table(rows=3, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    headers = [
        (
            "نمره با حروف: ........................",
            "تاریخ امتحان: ۱۴۰۵/..../....",
            "درس: زبان انگلیسی (شنیداری)",
            "نام و نام خانوادگی: .............................",
        ),
        (
            "نمره با عدد: ............ از ۱۰",
            "مدت امتحان: ۲۰ دقیقه",
            f"پایه تحصیلی: {exam_data['grade_label']}",
            "نام پدر: ...........................................",
        ),
        (
            "نام و امضای مصحح: ...............",
            f"نوبت: {exam_data['term_label']}",
            f"آموزشگاه: {school_name}",
            "کلاس / شماره داوطلب: ....................",
        ),
    ]

    for r_idx, row in enumerate(headers):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.text = val
            p = cell.paragraphs[0]
            p.runs[0].font.size = Pt(9)
            p.runs[0].font.bold = True
            p.runs[0].font.name = "Vazirmatn"
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph()

    # 2. Questions Body
    for item_type, val in exam_data["items"]:
        is_fa = has_persian(val)
        if item_type == "heading":
            h = doc.add_paragraph()
            h.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_fa else WD_ALIGN_PARAGRAPH.LEFT
            run = h.add_run(val)
            run.bold = True
            run.font.size = Pt(11)
            run.font.name = "Vazirmatn" if is_fa else "Calibri"
            run.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(3)
        elif item_type == "instruction":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_fa else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(val)
            run.italic = not is_fa
            run.bold = is_fa
            run.font.size = Pt(9.5)
            run.font.name = "Vazirmatn" if is_fa else "Calibri"
            run.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
            p.paragraph_format.space_after = Pt(4)
        elif item_type == "question":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(val)
            run.font.size = Pt(10.5)
            run.font.name = "Calibri"
            run.bold = True
            p.paragraph_format.left_indent = Inches(0.1)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(2)
        elif item_type == "option":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run("    ◯  " + val)
            run.font.size = Pt(10)
            run.font.name = "Calibri"
            p.paragraph_format.left_indent = Inches(0.3)
            p.paragraph_format.space_after = Pt(1)
        else:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_fa else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(val)
            run.font.size = Pt(9.5)
            run.font.name = "Vazirmatn" if is_fa else "Calibri"
            p.paragraph_format.space_after = Pt(2)

    # Footer
    footer_p = doc.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_p.paragraph_format.space_before = Pt(12)
    f_run = footer_p.add_run("جمع بارم: ۱۰ نمره  |  موفق و پیروز باشید — Good Luck!")
    f_run.bold = True
    f_run.font.size = Pt(9.5)
    f_run.font.name = "Vazirmatn"

    doc.save(out_docx)
    print(f"✓ Word document successfully generated: {out_docx}")


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
        alignment=2,  # Right align for Persian
        textColor=colors.HexColor("#1A202C"),
    )

    god_style = ParagraphStyle(
        "InTheNameOfGod",
        parent=normal_style,
        fontName=font_bold,
        fontSize=11,
        leading=14,
        alignment=1,  # Center
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
        alignment=2,  # Right
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

    story = []

    # Top "به نام خدا"
    story.append(Paragraph(shape_persian("به نام خدا"), god_style))

    # 1. Official Bilingual/Persian Header Box
    header_rows = [
        [
            Paragraph(shape_persian("نمره با عدد: .......... از ۱۰"), fa_header_style),
            Paragraph(shape_persian("مدت آزمون: ۲۰ دقیقه"), fa_header_style),
            Paragraph(shape_persian("نام درس: زبان انگلیسی (شنیداری)"), fa_header_style),
            Paragraph(shape_persian("نام و نام خانوادگی: ................................."), fa_header_style),
        ],
        [
            Paragraph(shape_persian("نمره با حروف: ........................"), fa_header_style),
            Paragraph(shape_persian(f"نوبت: {exam_data['term_label']}"), fa_header_style),
            Paragraph(shape_persian(f"پایه: {exam_data['grade_label']}"), fa_header_style),
            Paragraph(shape_persian("کلاس / شعبه: ......................................"), fa_header_style),
        ],
        [
            Paragraph(shape_persian("امضای مصحح: ........................."), fa_header_style),
            Paragraph(shape_persian("تاریخ: ۱۴۰۵/..../...."), fa_header_style),
            Paragraph(shape_persian(f"آموزشگاه: {school_name}"), fa_header_style),
            Paragraph(shape_persian("شماره داوطلب: ....................................."), fa_header_style),
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

    # 2. Questions Story
    for item_type, val in exam_data["items"]:
        clean_val = val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        is_fa = has_persian(clean_val)
        rendered_text = shape_persian(clean_val) if is_fa else clean_val

        if item_type == "heading":
            story.append(Paragraph(rendered_text, heading_ltr))
        elif item_type == "instruction":
            story.append(Paragraph(rendered_text, instruction_rtl if is_fa else instruction_ltr))
        elif item_type == "question":
            story.append(Paragraph(rendered_text, q_style))
        elif item_type == "option":
            story.append(Paragraph(f"O  {rendered_text}", opt_style))
        else:
            story.append(Paragraph(rendered_text, instruction_rtl if is_fa else normal_style))

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E0")))
    story.append(
        Paragraph(
            shape_persian("جمع بارم: ۱۰ نمره  |  موفق و پیروز باشید") + " — Good Luck!",
            footer_style,
        )
    )

    doc.build(story)
    print(f"✓ PDF successfully generated: {out_pdf}")


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

    story = []
    story.append(
        Paragraph(
            shape_persian(f"پاسخنامه تشریحی و راهنمای معلم — {exam_data['grade_label']} ({exam_data['term_label']})"),
            title_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#1A365D")))
    story.append(Spacer(1, 6))

    if exam_data["key_items"]:
        story.append(Paragraph("Answer Key & Scoring Rubric", sec_style))
        for item_type, val in exam_data["key_items"]:
            clean_val = val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            is_fa = has_persian(clean_val)
            txt = shape_persian(clean_val) if is_fa else clean_val
            story.append(Paragraph(txt, rtl_style if is_fa else normal_style))

    if exam_data["script_items"]:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Audio Transcripts (Teacher Read-Aloud / TTS Reference)", sec_style))
        for item_type, val in exam_data["script_items"]:
            clean_val = val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            is_fa = has_persian(clean_val)
            txt = shape_persian(clean_val) if is_fa else clean_val
            story.append(Paragraph(txt, rtl_style if is_fa else normal_style))

    doc.build(story)
    print(f"✓ Answer Key PDF successfully generated: {out_pdf}")
