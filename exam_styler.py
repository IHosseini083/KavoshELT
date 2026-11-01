import os
import re
from typing import Dict, Any, List, Optional

# --- ReportLab Imports ---
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

# --- Docx Imports ---
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

def parse_exam_markdown(md_path: str) -> Dict[str, Any]:
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract title
    title_match = re.search(r"#\s+(.+)", content)
    title = title_match.group(1).strip() if title_match else "English Examination"

    subtitle_match = re.search(r"##\s+(.+)", content)
    subtitle = subtitle_match.group(1).strip() if subtitle_match else ""

    # Extract student sheet section
    student_section = ""
    if "## بخش اول" in content:
        parts = content.split("## بخش اول")
        rest = parts[1]
        if "## بخش دوم" in rest:
            student_section = rest.split("## بخش دوم")[0]
        else:
            student_section = rest
    else:
        student_section = content

    # Clean student section
    lines = student_section.strip().split("\n")
    cleaned_lines = []
    for line in lines:
        line_s = line.strip()
        if line_s.startswith("### **Part") or line_s.startswith("### Part") or line_s.startswith("#### Task"):
            cleaned_lines.append(("heading", line_s.replace("#", "").strip("* ")))
        elif line_s.startswith(">"):
            cleaned_lines.append(("instruction", line_s.lstrip("> *").strip()))
        elif re.match(r"^\d+\.", line_s):
            cleaned_lines.append(("question", line_s))
        elif re.match(r"^[a-d]\)", line_s):
            cleaned_lines.append(("option", line_s))
        elif line_s.startswith("-") or line_s.startswith("*"):
            cleaned_lines.append(("bullet", line_s.lstrip("-* ")))
        elif line_s and not line_s.startswith("---") and not line_s.startswith("**نام"):
            cleaned_lines.append(("text", line_s))

    return {
        "title": title,
        "subtitle": subtitle,
        "items": cleaned_lines
    }

def generate_exam_docx(md_path: str, out_docx: str, school_name: str = "دبیرستان نمونه") -> None:
    exam_data = parse_exam_markdown(md_path)
    doc = docx.Document()

    # Page Margins (0.6 inch)
    for section in doc.sections:
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.6)
        section.right_margin = Inches(0.6)

    # 1. Header Table (Standard Ministry of Education Layout)
    table = doc.add_table(rows=3, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Styling cells
    headers = [
        ("اداره کل آموزش و پرورش", "نام و نام خانوادگی: .............................", "نام آزمون: زبان انگلیسی", "مدت آزمون: ۲۰ دقیقه"),
        (f"نام واحد آموزشی: {school_name}", "پایه و رشته: پایه دهم", "نوبت آزمون: نوبت اول / دی‌ماه", "تاریخ آزمون: ۱۴۰۵/۱۰/..."),
        ("طراح سوال: دبیر محترم", "شماره داوطلب: .............................", "تعداد صفحه: ۲", "نمره نهایی: ......... از ۱۰")
    ]

    for r_idx, row in enumerate(headers):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.text = val
            p = cell.paragraphs[0]
            p.runs[0].font.size = Pt(8.5)
            p.runs[0].font.name = "Arial"
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph() # Spacer

    # 2. Exam Content
    for item_type, val in exam_data["items"]:
        if item_type == "heading":
            h = doc.add_paragraph()
            run = h.add_run(val)
            run.bold = True
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(2)
        elif item_type == "instruction":
            p = doc.add_paragraph()
            run = p.add_run(val)
            run.italic = True
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0x4a, 0x55, 0x68)
            p.paragraph_format.space_after = Pt(4)
        elif item_type == "question":
            p = doc.add_paragraph()
            run = p.add_run(val)
            run.font.size = Pt(10)
            run.bold = True
            p.paragraph_format.left_indent = Inches(0.15)
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(2)
        elif item_type == "option":
            p = doc.add_paragraph()
            run = p.add_run("   " + val)
            run.font.size = Pt(9.5)
            p.paragraph_format.left_indent = Inches(0.35)
            p.paragraph_format.space_after = Pt(1)
        else:
            p = doc.add_paragraph()
            run = p.add_run(val)
            run.font.size = Pt(9.5)
            p.paragraph_format.space_after = Pt(2)

    doc.save(out_docx)
    print(f"✓ Word document successfully generated: {out_docx}")

def generate_exam_pdf(md_path: str, out_pdf: str, school_name: str = "Islamic Republic of Iran - Ministry of Education") -> None:
    exam_data = parse_exam_markdown(md_path)

    doc = SimpleDocTemplate(
        out_pdf,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    
    title_style = ParagraphStyle(
        "ExamTitle",
        parent=normal_style,
        fontSize=12,
        leading=14,
        alignment=1, # Center
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1A365D")
    )

    heading_style = ParagraphStyle(
        "PartHeading",
        parent=normal_style,
        fontSize=10,
        leading=12,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=6,
        spaceAfter=3
    )

    instruction_style = ParagraphStyle(
        "Instruction",
        parent=normal_style,
        fontSize=8.5,
        leading=11,
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=4
    )

    q_style = ParagraphStyle(
        "Question",
        parent=normal_style,
        fontSize=9.5,
        leading=12,
        fontName="Helvetica-Bold",
        leftIndent=10,
        spaceBefore=3,
        spaceAfter=2
    )

    opt_style = ParagraphStyle(
        "Option",
        parent=normal_style,
        fontSize=9,
        leading=11,
        fontName="Helvetica",
        leftIndent=22,
        spaceAfter=1
    )

    story = []

    # 1. Header Box
    header_data = [
        [
            Paragraph("<b>Ministry of Education</b><br/>High School Exam", normal_style),
            Paragraph(f"<b>Exam:</b> English Language<br/><b>Grade:</b> Grade 10", normal_style),
            Paragraph("<b>Time:</b> 20 Minutes<br/><b>Total Points:</b> 10.0", normal_style),
            Paragraph("<b>Date:</b> Term Examination<br/><b>Score:</b> ..... / 10", normal_style)
        ],
        [
            Paragraph("<b>Student Name:</b> ........................................", normal_style),
            Paragraph("<b>Class:</b> ....................", normal_style),
            Paragraph("<b>Date:</b> ....................", normal_style),
            Paragraph("<b>Signature:</b> ....................", normal_style)
        ]
    ]

    header_table = Table(header_data, colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch, 1.8 * inch])
    header_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.2, colors.HexColor("#2B6CB0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # 2. Questions Story
    for item_type, val in exam_data["items"]:
        clean_text = val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if item_type == "heading":
            story.append(Paragraph(clean_text, heading_style))
        elif item_type == "instruction":
            story.append(Paragraph(clean_text, instruction_style))
        elif item_type == "question":
            story.append(Paragraph(clean_text, q_style))
        elif item_type == "option":
            story.append(Paragraph(clean_text, opt_style))
        else:
            story.append(Paragraph(clean_text, normal_style))

    doc.build(story)
    print(f"✓ PDF successfully generated: {out_pdf}")
