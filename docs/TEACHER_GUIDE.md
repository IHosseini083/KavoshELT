# Teacher & AI Authoring Guide

This guide explains how educators and automated AI workflows use the Curriculum Knowledge Base to design valid, syllabus-bounded exams and generate professional listening audio tracks.

---

## 1. Exam Authoring Workflow (4 Standard Steps)

```text
[1. Fetch Bounds] ──> [2. Compose Draft] ──> [3. Validate & Adapt] ──> [4. Generate TTS Audio & Export]
```

### Step 1: Extract Curriculum Context and Vocabulary
Before drafting questions, retrieve the active vocabulary pool, allowed tenses, forbidden structures, and scoring rubrics:
```bash
python3 curriculum_kb.py context --grade 10 --lessons 1,2
```
This JSON output provides the exact constraints needed to prompt an LLM or guide manual drafting.

### Step 2: Compose Question Draft
Draft the listening scripts, reading comprehension passages, or vocabulary items using the retrieved syllabus boundaries.

### Step 3: Validate and Adapt Out-of-Syllabus Text
Submit the drafted markdown or text to the curriculum advisor:
```bash
python3 curriculum_kb.py adapt --grade 10 --max-lesson 2 --file my_exam_draft.md
```
If an out-of-syllabus word is identified:
- The command reports the exact word.
- It specifies in which future grade and lesson that word will actually be taught.
- It suggests **in-syllabus semantic alternatives** from vocabulary the student has already learned in earlier grades.

### Step 4: Export Printable Sheets & Generate Audio
Retrieve the official assessment blueprint:
```bash
python3 curriculum_kb.py blueprint --grade 10 --term 1 --exam-type Listening
```
Then export the finalized exam to print-ready PDF or editable Word DOCX:
```bash
python3 curriculum_kb.py export --file my_exam_draft.md --format pdf --out exam.pdf --school "Shahid Beheshti High School"
python3 curriculum_kb.py export --file my_exam_draft.md --format docx --out exam.docx --school "Shahid Beheshti High School"
```

---

## 2. Audio Generation with Gemini 3.8 Flash TTS

Google's **Gemini 3.8 Flash TTS** engine is pre-calibrated for school listening comprehension tests:

1. **Recommended Voice Configuration:**
   * **Speaker 1 (Female):** `Fola` (Formal, articulate, and instructional tone for the examiner, teacher, or narrator).
   * **Speaker 2 (Male):** `Rami` (Natural, warm, conversational tone for students, tourists, physicians, or secondary characters).
2. **Pacing Rules:**
   * For Iranian secondary learners (CEFR A2/B1), speed should target **125 to 135 words per minute (WPM)**.
   * Use native inline pause tags:
     - Sentence transitions: `<short pause>` (0.5 to 1.0s)
     - Question reading intervals: `<long pause>` (15s examinee inspection time)
3. **Verbatim Script Isolation:**
   * Sustained delivery styles must be assigned via `speechMetadata.style` (e.g. `"Clear, formal, and slow"`) rather than inline bracketed stage directions, preventing the synthetic voice from reading stage cues aloud.
