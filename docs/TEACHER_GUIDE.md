# KavoshELT Teacher & Educator Guide

This guide explains how secondary English teachers can use KavoshELT to compose official final exam simulations, generate targeted skill worksheets, analyze first-language (L1) errors, and produce print-ready examination papers.

---

## 1. Core Teaching Scenarios

### Scenario A: Composing a Grade 12 National Mock Exam (28 Points)
Before official final exams in Khordad, teachers need authentic mock exams that mirror the official Ministry of Education (*Markaz-e-Sanjesh*) blueprint without accidental leakage of the exact same test items across sections.

Run this command in the terminal:
```bash
python -m kavosh compose-exam \
    --mode full_mock \
    --grade 12 \
    --points 28.0 \
    --sourcing hybrid \
    --school "Farhang High School" \
    --teacher "English Department" \
    --out-dir exports/grade12_mock_khordad
```

**What the system generates:**
* `exports/grade12_mock_khordad/student_sheet.docx`: Fully editable Word document with native RTL school header grid and student metadata fields.
* `exports/grade12_mock_khordad/student_sheet.pdf`: Clean A4 exam paper formatted with the Persian Vazirmatn font.
* `exports/grade12_mock_khordad/student_sheet.html`: Browser-printable exam sheet.
* `exports/grade12_mock_khordad/teacher_answer_key.pdf`: Official scoring key with 0.25-point sub-rubrics and item provenance notes.

---

### Scenario B: Generating a Single-Skill Remedial Worksheet
When students struggle with a specific area—such as paragraph writing or sentence unscramble tasks—generate a targeted worksheet:
```bash
python -m kavosh compose-exam \
    --mode skill_worksheet \
    --grade 12 \
    --section writing \
    --points 6.0 \
    --sourcing past_papers \
    --out-dir exports/writing_remedial
```
This isolates the writing section, pulling authentic past national exam questions for classroom practice.

---

### Scenario C: Creating Parallel Quizzes to Prevent Cheating
When administering a continuous classroom quiz for Grade 12 Lesson 1 across multiple class sections:
```bash
# Form A (Class 1) - Hybrid past papers and twin items:
python -m kavosh compose-exam \
    --mode custom_quiz \
    --grade 12 \
    --lessons 1 \
    --points 10.0 \
    --sourcing past_papers \
    --out-dir exports/quiz_class_a

# Form B (Class 2) - 100% Synthesized twin questions:
python -m kavosh compose-exam \
    --mode custom_quiz \
    --grade 12 \
    --lessons 1 \
    --points 10.0 \
    --sourcing ai_twins \
    --out-dir exports/quiz_class_b
```
Both forms test the exact same grammar concepts and vocabulary at identical difficulty, but use distinct sentence stems.

---

### Scenario D: Diagnosing Grammatical Errors & Persian L1 Transfer
When students repeatedly make mistakes on advanced structures (e.g., passive voice or tag questions), query the prerequisite knowledge graph:
```bash
python -m kavosh graph-query --concept g12.l1.grammar.passive_voice
```

**Output Diagnostics:**
1. **Foundational Prerequisites:** Explains that students must review Grade 9 Lesson 5 (Simple Past irregular forms) and Grade 11 Lesson 1 (Past Participle morphology) before mastering passive constructions.
2. **L1 Root Cause:** Highlights that in Persian, passive sentences (e.g., «پل ساخته شد») do not employ an explicit auxiliary `to be`, leading students to write `The bridge built` instead of `The bridge was built`.
3. **Remedial Practice Drill:** Supplies ready-to-use drill templates for lesson planning.

---

## 2. Real-Time Text Verification & Synonym Assistance

When drafting original exam questions or reading passages:

### Step 1: Check Syllabus Boundaries
Verify that your text does not introduce untaught vocabulary:
```bash
python -m kavosh validate \
    --grade 10 \
    --max-lesson 2 \
    --text "The patient visited the hospital for a checkup."
```
If an out-of-syllabus word is found (e.g., `patient`), the validator reports it immediately.

### Step 2: Get In-Syllabus Synonym Replacements
```bash
python -m kavosh adapt \
    --grade 10 \
    --max-lesson 2 \
    --text "The physician helped the ill person."
```
The advisor suggests substituting `doctor` (introduced in Grade 7) for `physician` (Grade 10 Lesson 3), ensuring fair and syllabus-compliant assessments.

---

## 3. Listening Comprehension Blueprint

For official listening assessments, KavoshELT configures acoustic directives for school listening audio tracks:

| Role | Recommended Voice | Tone & Character | Target Pacing |
|:---|:---|:---|:---|
| **Examiner / Narrator** | Female | Clear, articulate, instructional | 125–130 WPM |
| **Secondary Speaker / Dialogue** | Male | Natural, conversational, friendly | 130–135 WPM |

### Inline Pause Standards
* Between instruction sections: `<long pause>` (15-second inspection interval).
* Between repetitive listening rounds: `<medium pause>` (5-second transition).
* Between sentences: `<short pause>` (0.75-second cadence).
