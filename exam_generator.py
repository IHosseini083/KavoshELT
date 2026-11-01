import os
import sqlite3
from typing import Dict, Any, List, Tuple
from exam_styler import generate_exam_pdf, generate_exam_docx, generate_answer_key_pdf
from validator import validate_exam_text


GRADE_EXAM_TEMPLATES: Dict[Tuple[int, int], Dict[str, Any]] = {
    (7, 1): {
        "book": "Prospect 1",
        "lessons_label": "Lessons 1 to 4 (My Name, My Classmates, My Age, My Family)",
        "max_lesson": 4,
        "part_a": {
            "context_fa": "دانش‌آموز عزیز، به مکالمه بین «علی» و «معلم» گوش دهید و مشخص کنید جملات زیر درست (True) هستند یا نادرست (False). (هر سوال ۰.۵ نمره)",
            "questions": [
                ("1. The student's first name is Ali.", "True"),
                ("2. Ali's last name is Rezaei.", "False"),
                ("3. Ali is twelve years old.", "True"),
                ("4. Ali's father is a dentist.", "False"),
                ("5. Ali's mother is a kind teacher.", "True"),
            ],
            "dialogue": [
                ("Speaker 1 - Fola", "Warm, encouraging, and slow", "Hello! Welcome to our class. <short pause> What is your first name and last name?"),
                ("Speaker 2 - Rami", "Polite, clear, and slow", "Hello teacher! <short pause> My first name is Ali, <short pause> and my last name is Moradi."),
                ("Speaker 1 - Fola", "Friendly and slow", "Nice to meet you, Ali. <short pause> How old are you?"),
                ("Speaker 2 - Rami", "Clear and slow", "I am twelve years old. <short pause> My birthday is in Mehr."),
                ("Speaker 1 - Fola", "Interested and slow", "What is your father's job, Ali?"),
                ("Speaker 2 - Rami", "Proud and slow", "My father is an engineer, <short pause> and my mother is a kind teacher."),
            ],
        },
        "part_b": {
            "context_fa": "به مکالمه بین «مینا» و «سارا» درباره همکلاسی‌ها و خانواده گوش دهید و بهترین گزینه را انتخاب کنید. (هر سوال ۰.۵ نمره)",
            "questions": [
                ("6. Who is that girl in the classroom?", ["a) Mina's sister", "b) Mina's new classmate", "c) The school nurse"], "b) Mina's new classmate"),
                ("7. How old is Mina's brother, Nima?", ["a) Ten years old", "b) Twelve years old", "c) Fourteen years old"], "a) Ten years old"),
                ("8. What is Mina's uncle's job?", ["a) He is a pilot", "b) He is a doctor", "c) He is a dentist"], "a) He is a pilot"),
                ("9. When is Sara's birthday?", ["a) In Mehr", "b) In Bahman", "c) In Tir"], "b) In Bahman"),
                ("10. How many sisters does Sara have?", ["a) One sister", "b) Two sisters", "c) Three sisters"], "b) Two sisters"),
            ],
            "dialogue": [
                ("Speaker 1 - Fola", "Friendly, curious, and slow", "Hi Mina! Who is that girl over there? <short pause> Is she your sister?"),
                ("Speaker 2 - Rami", "Clear and slow", "Hi Sara! No, she is my new classmate, Zahra. <short pause> My little brother Nima is at home. He is ten years old."),
                ("Speaker 1 - Fola", "Interested and slow", "Oh, nice! And what is your uncle's job?"),
                ("Speaker 2 - Rami", "Clear and slow", "My uncle is a pilot. <short pause> By the way, Sara, when is your birthday?"),
                ("Speaker 1 - Fola", "Cheerful and slow", "My birthday is in Bahman. <short pause> I celebrate it with my two sisters."),
            ],
        },
        "part_c": {
            "context_fa": "به مکالمه گوش دهید و جاهای خالی را با یک کلمه مناسب از فایل صوتی کامل کنید. (هر سوال ۱ نمره)",
            "questions": [
                ("11. Good ..........................., teacher! How are you today?", "morning"),
                ("12. This boy is my best ........................... at school.", "friend"),
                ("13. What is your phone ...........................?", "number"),
                ("14. My ........................... is sixty-five years old.", "grandfather"),
                ("15. Her aunt is a ........................... at the hospital.", "doctor"),
            ],
            "dialogue": [
                ("Speaker 1 - Fola", "Clear and slow", "Good morning, teacher! How are you today?"),
                ("Speaker 2 - Rami", "Warm and slow", "Good morning! I am fine, thank you. <short pause> Who is this boy with you?"),
                ("Speaker 1 - Fola", "Polite and slow", "This boy is my best friend at school. <short pause> Can I write our phone number here?"),
                ("Speaker 2 - Rami", "Helpful and slow", "Yes, please write your phone number. <short pause> Tell me about your family."),
                ("Speaker 1 - Fola", "Clear and slow", "My grandfather is sixty-five years old, <short pause> and my aunt is a doctor at the hospital."),
            ],
        },
    },
    (10, 1): {
        "book": "Vision 1",
        "lessons_label": "Lessons 1 & 2 (Saving Nature & Wonders of Creation)",
        "max_lesson": 2,
        " existing_md": "/home/ubuntu/آزمون_شنیداری_زبان_انگلیسی_پایه_دهم_نوبت_اول.md",
    },
    (10, 2): {
        "book": "Vision 1",
        "lessons_label": "Lessons 1 to 4 (Full Vision 1 — Focus on Lessons 3 & 4)",
        "max_lesson": 4,
        "existing_md": "/home/ubuntu/آزمون_شنیداری_زبان_انگلیسی_پایه_دهم_نوبت_دوم.md",
    },
}


def build_markdown_from_template(grade: int, term: int, tpl: Dict[str, Any]) -> str:
    term_fa = "نوبت اول (دی‌ماه)" if term == 1 else "نوبت دوم (خردادماه)"
    grade_fa = {7: "هفتم", 8: "هشتم", 9: "نهم", 10: "دهم", 11: "یازدهم", 12: "دوازدهم"}.get(grade, str(grade))

    lines = [
        f"# بسته کامل آزمون شنیداری (Listening) زبان انگلیسی پایه {grade_fa} - {term_fa} (۱۰ نمره / ۱۵ سوال)",
        "",
        f"**مشخصات و استانداردهای طراحی آزمون ({tpl['book']}):**",
        f"* **محدوده:** {tpl['lessons_label']}",
        "* **بارم‌بندی کل:** **۱۰ نمره** (مجموعاً ۱۵ سوال در ۳ بخش ۵ سوالی)",
        "* **مدل صوتی:** `Gemini 3.8 Flash TTS` (گویندگان: `Fola` و `Rami`)",
        "",
        "---",
        "",
        "## بخش اول: برگه سوالات دانش‌آموز (Student's Question Sheet)",
        "",
        "### **Part A: True / False (Questions 1 - 5) — [2.5 Points]**",
        f"> **{tpl['part_a']['context_fa']}**",
        "",
    ]

    for q_text, _ in tpl["part_a"]["questions"]:
        lines.append(f"{q_text} ( **True** / **False** )")
    lines.append("\n---\n")

    lines.append("### **Part B: Multiple Choice (Questions 6 - 10) — [2.5 Points]**")
    lines.append(f"> **{tpl['part_b']['context_fa']}**\n")
    for q_text, opts, _ in tpl["part_b"]["questions"]:
        lines.append(f"**{q_text}**")
        for opt in opts:
            lines.append(opt)
        lines.append("")
    lines.append("---\n")

    lines.append("### **Part C: Fill in the Blanks (Questions 11 - 15) — [5 Points]**")
    lines.append(f"> **{tpl['part_c']['context_fa']}**\n")
    for q_text, _ in tpl["part_c"]["questions"]:
        lines.append(q_text)

    lines.extend(["", "---", "---", "", "## بخش دوم: اسکریپت‌های صوتی (Google AI Studio TTS Blocks)", ""])

    for idx, (part_key, part_title) in enumerate([("part_a", "Part A"), ("part_b", "Part B"), ("part_c", "Part C")], 1):
        lines.append(f"### Track {idx}: {part_title}")
        for b_idx, (spk, style, txt) in enumerate(tpl[part_key]["dialogue"], 1):
            lines.append(f"* **Speech Block {b_idx}** | **Speaker:** `{spk}` | **Style:** `{style}`")
            lines.append(f"  {txt}")
        lines.append("")

    lines.extend(["---", "---", "", "## بخش سوم: کلید سوالات و راهنمای تصحیح (Answer Key & Scoring)", ""])
    lines.append("### Part A: True / False (2.5 Points)")
    for i, (_, ans) in enumerate(tpl["part_a"]["questions"], 1):
        lines.append(f"{i}. **{ans}** (0.5 pt)")

    lines.append("\n### Part B: Multiple Choice (2.5 Points)")
    for i, (_, _, ans) in enumerate(tpl["part_b"]["questions"], 6):
        lines.append(f"{i}. **{ans}** (0.5 pt)")

    lines.append("\n### Part C: Fill in the Blanks (5.0 Points)")
    for i, (_, ans) in enumerate(tpl["part_c"]["questions"], 11):
        lines.append(f"{i}. **{ans}** (1.0 pt)")

    return "\n".join(lines) + "\n"


def generate_full_exam_package(
    conn: sqlite3.Connection,
    grade: int,
    term: int,
    out_dir: str,
    school_name: str = "دبیرستان نمونه دولتی",
) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    prefix = f"grade{grade}_term{term}_listening"
    md_path = os.path.join(out_dir, f"{prefix}.md")
    student_pdf = os.path.join(out_dir, f"{prefix}_student.pdf")
    student_docx = os.path.join(out_dir, f"{prefix}_student.docx")
    key_pdf = os.path.join(out_dir, f"{prefix}_answer_key.pdf")

    tpl = GRADE_EXAM_TEMPLATES.get((grade, term))
    if tpl and ("existing_md" in tpl or " existing_md" in tpl):
        src_md = tpl.get("existing_md") or tpl.get(" existing_md")
        if os.path.exists(src_md):
            with open(src_md, "r", encoding="utf-8") as f:
                md_content = f.read()
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
    elif tpl:
        md_content = build_markdown_from_template(grade, term, tpl)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
    else:
        # Fallback to Grade 10 Term 1 template structure
        fallback_tpl = GRADE_EXAM_TEMPLATES[(7, 1)]
        md_content = build_markdown_from_template(grade, term, fallback_tpl)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    generate_exam_pdf(md_path, student_pdf, school_name=school_name)
    generate_exam_docx(md_path, student_docx, school_name=school_name)
    generate_answer_key_pdf(md_path, key_pdf, school_name=school_name)

    return {
        "grade": grade,
        "term": term,
        "markdown": md_path,
        "student_pdf": student_pdf,
        "student_docx": student_docx,
        "answer_key_pdf": key_pdf,
    }
