# KavoshELT: Unified Knowledge-Graph RAG & National Exam Studio

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-62%20passed-brightgreen.svg)]()
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Architecture: SQLAlchemy 2.0](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-red.svg)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An open-source, deterministic curriculum intelligence engine and national exam authoring studio for the Iranian Secondary English Curriculum across all six grades:
* **Junior High School (Grades 7–9):** *Prospect 1, 2, 3* (21 official textbook lessons)
* **Senior High School (Grades 10–12):** *Vision 1, 2, 3* (10 official textbook lessons)

KavoshELT is built as a **zero-hallucination ground-truth guardrail** for English educators, pedagogical researchers, and AI agents. It integrates an in-process **Unified Relational Graph-RAG Engine**, a complete digital archive of **Grade 12 National Final Exams (1397–1405 / 2018–2026)**, an algorithmic twin question synthesizer, and automated print-ready document generators for Persian school standards (RTL Word DOCX, Vazirmatn PDF, and HTML).

---

## Core Capabilities

### 1. Unified Relational Knowledge-Graph RAG
Combines relational database constraints, prerequisite knowledge graph traversal, and semantic vector embeddings without requiring heavy external graph or vector databases:
* **Prerequisite Graph (`ConceptNode` & `ConceptEdge`):** Encodes pedagogical dependencies across lessons and grades (e.g., Grade 12 Passive Voice requires Grade 9 Simple Past and Grade 11 Past Participle morphology).
* **L1 Interference Clinic (`L1ErrorPattern`):** Catalogs common negative transfer errors specific to Persian native speakers (e.g., auxiliary `to be` omission in passive voice, tag question polarity errors) and links them directly to curriculum concept nodes.
* **Semantic & FTS5 Hybrid Search:** Sub-millisecond keyword and conceptual retrieval restricted by strict grade boundaries.

### 2. National Exam Archive (1397–1405 / 9 Academic Years)
A verified repository of **27 official national examination papers** from the Ministry of Education (*Markaz-e-Sanjesh*):
* **Sessions Covered:** Khordad (Main), Shahrivar (Remedial), and Dey (Adult/Winter) across 1397 to 1405.
* **Blueprint Standards:** Covers both the Classic format (1397–1401) and the New Conceptual format (1402–1405).
* **Atomic Item Catalog:** Hundreds of individual items cataloged across official skills:
  * Vocabulary (6.0 pts)
  * Grammar (5.0–7.0 pts)
  * Writing & Paragraph Structure (6.0 pts)
  * Cloze Test (3.0–4.0 pts)
  * Reading Comprehension (5.0–8.0 pts)
* **Metadata Richness:** Every question records its Bloom cognitive level (`remember`, `understand`, `apply`, `analyze`), question format, distractor rationale, official answer, and grading rubric with 0.25-point precision.

### 3. Four-Layer Exam Bank Verification Gate (`verify_exam_bank.py`)
Enforces strict mathematical and pedagogical rules:
* **Rule V1 (Mathematical Precision):** All item points and sub-rubrics must be exact multiples of 0.25, and the sum of rubric breakdown elements must equal the item score.
* **Rule V2 (Curriculum Alignment):** 100% of vocabulary and grammatical structures in question stems, options, and passages must reside within the target grade's syllabus.
* **Rule V3 (Graph Integrity):** Every item must link to registered concept nodes with verified prerequisite chains.
* **Rule V4 (Answer Key Completeness):** Multiple-choice questions must contain the canonical answer in their options, and constructive tasks must supply step-by-step scoring keys.

### 4. Four-Mode Exam Composer (`exam_composer.py`)
Allows teachers to assemble tailor-made assessments in seconds:
1. **`full_mock` (National Exam Simulator):** Generates a 28.0-point standardized written paper matching the official Ministry blueprint.
2. **`skill_worksheet` (Focused Worksheet):** Assembles targeted worksheets for specific skills (e.g., writing unscramble tasks or conditional sentences).
3. **`custom_quiz` (Classroom Quiz):** Composes quizzes across selected lessons and custom point totals (e.g., a 10.0-point Lesson 1 quiz).
4. **`item_composer` (Interactive Slot Editor):** Allows swapping individual items (`swap_slot_item`) with equivalent candidates from the bank or newly synthesized twins.

### 5. Three Question Sourcing Strategies
* **`past_papers`:** Uses authentic past exam questions with official session and year badges.
* **`ai_twins`:** Algorithmic parallel items synthesized from the same concept node, maintaining identical syntactic complexity while guaranteeing 100% in-syllabus vocabulary.
* **`hybrid`:** Interleaves past exam items with newly generated twins to prevent test copying while retaining historical exam style.

### 6. Production-Grade Print & RTL Exporter (`exam_styler.py`)
Generates standardized school test sheets without layout distortion:
* **Editable Word Documents (`.docx`):** Built with native OpenXML bidirectional attributes (`w:bidi`, `w:rtl`, `w:bidiVisual`) so tables and headers render right-to-left correctly in Microsoft Word.
* **Print-Ready PDFs (`.pdf`):** Styled with Persian typography using the embedded Vazirmatn font, two-column layout, and official header grids.
* **Printable HTML (`.html`):** Clean, responsive CSS with `@media print` rules for instant browser printing.
* **Teacher Answer Key (`teacher_answer_key.pdf`):** Standalone scoring key complete with 0.25-point grading breakdowns and question provenance notes.

### 7. Gemini TTS Listening Comprehension Studio
Pre-configured acoustic directives for Google's Gemini 3.8 Flash TTS engine:
* Voices: `Fola` & `Zephyr` (articulate female examiner/narrator), `Rami` & `Puck` (conversational male speakers).
* Delivery speed: Calibrated at 125–135 WPM for secondary EFL learners.
* Automatic timing: Inline pause tags for student reading time and question intervals.

---

## Curriculum Progression Map

| Grade | Series | Lessons | In-Scope Grammar & Structures | Forbidden Out-of-Scope Structures |
|:---:|:---:|:---:|:---|:---|
| **7** | Prospect 1 | 8 | To Be verbs, What/Who questions, possessives, basic Present Continuous | Past tenses, Future, modals, Passive voice, Perfect tenses |
| **8** | Prospect 2 | 7 | Simple Present (do/does), Can/Can't, health problems, routine actions | Past tenses, Future, Present Perfect, Passive voice |
| **9** | Prospect 3 | 6 | Simple Past (regular/irregular), past forms of To Be, travel routines | Future with will, Present Perfect, Passive voice, Conditionals |
| **10** | Vision 1 | 4 | Simple Future (*will / be going to*), Comparatives/Superlatives, Past Continuous | Present Perfect (*have/has + V3*), Passive voice, Conditionals |
| **11** | Vision 2 | 3 | Present Perfect (*have/has + V3*), Gerunds and Infinitives, Conditional Type 1 | Passive voice (*be + V3*), Conditional Type 2 |
| **12** | Vision 3 | 3 | Passive voice (all tenses), Tag questions, Relative clauses, Past Perfect | Full secondary curriculum scope |

---

## Command-Line Interface (CLI)

All operations are accessible through the unified CLI (`curriculum_kb.py`):

### 1. Compose a National Mock Exam (Full 28-Point Simulator)
```bash
python3 curriculum_kb.py compose-exam \
    --mode full_mock \
    --grade 12 \
    --points 28.0 \
    --sourcing hybrid \
    --school "Farhang High School" \
    --teacher "Seyed Iliya Hosseini" \
    --out-dir exports/grade12_mock
```
*Generates `exam.md`, `student_sheet.docx`, `student_sheet.pdf`, `student_sheet.html`, and `teacher_answer_key.pdf`.*

### 2. Compose a Classroom Skill Worksheet
```bash
python3 curriculum_kb.py compose-exam \
    --mode skill_worksheet \
    --grade 12 \
    --section writing \
    --points 6.0 \
    --sourcing past_papers \
    --out-dir exports/writing_worksheet
```

### 3. Query Prerequisite Knowledge Graph & L1 Error Patterns
```bash
python3 curriculum_kb.py graph-query --concept g12.l1.grammar.passive_voice
```
*Output returns pedagogical prerequisites across earlier grades, along with common Persian L1 interference patterns and remedial drill templates.*

### 4. Validate Arbitrary Text Against Grade Bounds
```bash
python3 curriculum_kb.py validate \
    --grade 10 \
    --max-lesson 2 \
    --text "The ancient palace was built two hundred years ago."
```
*Flags that Passive Voice (`was built`) is strictly forbidden before Grade 12 Lesson 1.*

### 5. Suggest In-Syllabus Synonyms for Advanced Words
```bash
python3 curriculum_kb.py adapt \
    --grade 7 \
    --max-lesson 8 \
    --text "The physician helped the patient."
```
*Identifies that `physician` belongs to Grade 10 Lesson 3, and recommends `doctor` from the Grade 7 vocabulary pool.*

### 6. Hybrid Vector & FTS5 Semantic RAG Search
```bash
python3 curriculum_kb.py rag --query "renewable clean solar energy" --grade 12 --max-lesson 3
```

### 7. Export Existing Markdown Exam to Print Formats
```bash
# Export to PDF with embedded Vazirmatn font
python3 curriculum_kb.py export --file exam.md --format pdf --out exam.pdf --school "Alborz High School"

# Export to Word DOCX with native RTL tables
python3 curriculum_kb.py export --file exam.md --format docx --out exam.docx --school "Alborz High School"
```

---

## Repository Structure

```text
KavoshELT/
├── curriculum_kb.py       # Unified Command-Line Interface (CLI)
├── models.py              # SQLAlchemy 2.0 type-safe ORM declarative models
├── schema.py              # SQLite database schema and FTS5 search indexes
├── exam_rag_engine.py     # Multi-criteria retrieval, graph traversal, and twin synthesizer
├── exam_composer.py       # 4-mode exam composer and multi-format document builder
├── verify_exam_bank.py    # 4-layer mathematical and curriculum verification gate
├── exam_styler.py         # RTL Word DOCX, Vazirmatn PDF, and HTML exporter
├── exam_generator.py      # Automated listening exam package generator
├── validator.py           # Morphology parser and progressive grammar validator
├── advisor.py             # In-syllabus synonym advisor and replacement suggestions
├── auditor.py             # Curriculum self-consistency verification engine
├── rag.py                 # Hybrid vector + lexical retrieval for prompt guardrails
├── web_app.py             # Self-hosted interactive web studio & REST API
├── datasets/              # Curriculum datasets & national exam archives
│   ├── concept_graph_grade12.json                # Grade 12 concept knowledge graph
│   ├── national_exams_grade12_1397_1405.json     # 27 national final exam papers
│   ├── grade7_prospect1.json                     # Prospect 1 syllabus dataset
│   ├── grade8_prospect2.json                     # Prospect 2 syllabus dataset
│   ├── grade9_prospect3.json                     # Prospect 3 syllabus dataset
│   ├── grade10_vision1.json                      # Vision 1 syllabus dataset
│   ├── grade11_vision2.json                      # Vision 2 syllabus dataset
│   └── grade12_vision3.json                      # Vision 3 syllabus dataset
├── docs/                  # In-depth architectural & pedagogical documentation
│   ├── ARCHITECTURE.md    # Graph-RAG architecture and verification gate design
│   ├── CURRICULUM_MAP.md  # 31-lesson syllabus breakdown and grammatical milestones
│   ├── TEACHER_GUIDE.md   # Practical authoring guide for secondary educators
│   └── plans/             # Architecture specifications and design blueprints
├── templates/             # Web application interface (HTML/CSS/JS)
├── exports/               # Generated test artifacts (Word, PDF, HTML, Markdown)
└── tests/                 # Comprehensive test suite (62 unit tests, TDD verified)
    ├── test_exam_composer.py
    ├── test_exam_rag_engine.py
    ├── test_verify_exam_bank.py
    ├── test_national_exam_seed.py
    ├── test_graph_models.py
    ├── test_exam_styler.py
    ├── test_validator.py
    ├── test_advisor.py
    ├── test_auditor.py
    ├── test_rag.py
    ├── test_all_grades_seed.py
    └── test_web_app.py
```

---

## Test Suite & Verification

The codebase is built strictly according to Test-Driven Development (TDD) principles. Run the complete automated test suite (62 test cases):

```bash
python3 -m unittest discover -s tests
```

### Static Analysis & Formatting
```bash
# Type checking
mypy --strict models.py exam_composer.py exam_rag_engine.py verify_exam_bank.py

# Code formatting and linting
ruff format .
ruff check .
```

---

## Web Studio

KavoshELT includes a built-in web studio for teachers who prefer a visual interface:
```bash
python3 web_app.py
```
Open `http://localhost:8090` in your browser to access:
* Real-time text validation with visual highlight tags for out-of-syllabus terms.
* One-click synonym substitution suggestions.
* Direct download of formatted Word and PDF examination sheets.
* Voice previews for Gemini TTS speakers (`Fola`, `Rami`, `Zephyr`, `Puck`).

---

## License

This project is licensed under the [MIT License](LICENSE). Free and open-source for teachers, schools, university researchers, and developers. Author: **Seyed Iliya Hosseini**, Farhangian University of Shiraz.
