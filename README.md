# Iranian Secondary English Curriculum Knowledge Base & Exam Validator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-27%20passed-brightgreen.svg)]()
[![Zero Dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-success.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An open-source, deterministic, and lightweight curriculum verification engine and exam authoring toolkit for the official Iranian National English Curriculum across all 6 secondary school grades:
* **Junior High School (Grades 7–9):** *Prospect 1, 2, 3* (21 official lessons)
* **Senior High School (Grades 10–12):** *Vision 1, 2, 3* (10 official lessons)

Designed to serve as a **Ground-Truth Guardrail** for AI agents (LLMs) and English language teachers, eliminating out-of-syllabus hallucination, validating vocabulary/grammar constraints, and automatically producing print-ready exam papers (PDF/DOCX) and studio-grade listening audio tracks.

---

## 🚀 Key Features

* **Complete 6-Grade Syllabus (31 Official Lessons):**
  Comprehensive SQLite database (`curriculum.db`) storing over 1,050 official textbook vocabulary entries, progressive grammar rules, canonical reading/listening passages with FTS5 full-text indexing, and official scoring blueprints from the Ministry of Education (*Daftar-e-Talif*).
* **Strict Out-of-Syllabus Validator:**
  Rule-based morphology parser and lemmatizer that checks word inflections (`-s`, `-ed`, `-ing`, `-er`, `-est`, `-ly`) and irregular verbs without bloated third-party NLP packages. Flags any vocabulary or grammar structure untaught at the target grade level (e.g., forbidding Present Perfect or Passive Voice before Grades 11 and 12).
* **In-Syllabus Synonym Advisor:**
  When an advanced or out-of-syllabus word is identified, the advisor explains which future grade introduces it and automatically suggests semantic replacements from vocabulary the student has already mastered.
* **Print-Ready Exam Styler (PDF & Word DOCX):**
  Transforms exam markdown scripts into standardized school exam sheets complete with official header tables, grading boxes, student metadata fields, and clean typography.
* **AI Speech Synthesis Blueprint (Gemini 3.8 Flash TTS):**
  Pre-configured multi-speaker speech metadata and pacing rules (`Fola` & `Rami` voices, 125–135 WPM target, natural pause tags) for generating official school listening audio.

---

## 📊 Curriculum Progression Overview

| Grade | Textbook | Lessons | In-Scope Grammar & Structures | Forbidden Out-of-Scope Structures |
|:---:|:---:|:---:|:---|:---|
| **7** | Prospect 1 | 8 | To Be verbs, What/Who questions, possessives, basic Present Continuous | Past tenses, Future, modals, Passive voice, Perfect tenses |
| **8** | Prospect 2 | 7 | Simple Present (do/does), Can/Can't, health problems, routine actions | Past tenses, Future, Present Perfect, Passive voice |
| **9** | Prospect 3 | 6 | Simple Past (regular and irregular), past forms of To Be, travel routines | Future with will, Present Perfect, Passive voice, Conditionals |
| **10** | Vision 1 | 4 | Simple Future (*will / be going to*), Comparatives/Superlatives, Past Continuous | Present Perfect (*have/has + V3*), Passive voice, Conditionals |
| **11** | Vision 2 | 3 | Present Perfect (*have/has + V3*), Gerunds and Infinitives, Conditional Type 1 | Passive voice (*be + V3*), Conditional Type 2 |
| **12** | Vision 3 | 3 | Passive voice (all tenses), Tag questions, Relative clauses, Past Perfect | — (Full secondary grammar scope) |

---

## 🛠️ Quick Start & CLI Reference

All CLI commands run directly using Python's standard library:

### 1. Database Overview & Statistics
```bash
python3 curriculum_kb.py stats
```

### 2. Retrieve Curriculum Context for AI Prompting
Extract allowed vocabulary, active grammar rules, and official scoring rubrics for target lessons:
```bash
# Grade 10, Lessons 1 and 2 (Term 1):
python3 curriculum_kb.py context --grade 10 --lessons 1,2

# Grade 12, Lessons 1, 2, and 3:
python3 curriculum_kb.py context --grade 12 --lessons 1,2,3
```

### 3. Validate Exam Text Against Syllabus Bounds
```bash
python3 curriculum_kb.py validate --grade 10 --max-lesson 2 --text "The heart pumps blood through the body."
```

### 4. Adapt Text with In-Syllabus Synonym Suggestions
```bash
python3 curriculum_kb.py adapt --grade 7 --max-lesson 8 --text "The physician helped the patient."
```
*Output identifies that `physician` belongs to Grade 10 Lesson 3, and recommends `doctor` from the Grade 7 vocabulary pool.*

### 5. Search Official Textbook Passages (FTS5)
```bash
python3 curriculum_kb.py search --query "cheetah"
python3 curriculum_kb.py search --query "renewable energy"
```

### 6. Export to Printable PDF & Editable Word DOCX
```bash
# Generate A4 Print-Ready PDF
python3 curriculum_kb.py export --file exam.md --format pdf --out exam.pdf --school "Shahid Beheshti High School"

# Generate Editable Word Document
python3 curriculum_kb.py export --file exam.md --format docx --out exam.docx --school "Farhang High School"
```

### 7. Run Curriculum Self-Consistency Audit
Audits all 31 lessons to ensure 100% of textbook passages pass their own grade boundary:
```bash
python3 curriculum_kb.py audit
```

### 8. Generate Exam Blueprint & Gemini TTS Template
```bash
python3 curriculum_kb.py blueprint --grade 10 --term 1 --exam-type Listening
```

---

## 🧪 Test Suite

Run the full automated test suite (27 unit tests):
```bash
python3 -m unittest discover -s tests
```

---

## 📂 Repository Structure

```text
vision-kb/
├── curriculum_kb.py       # Unified Command-Line Interface (CLI)
├── schema.py              # SQLite relational schema and FTS5 virtual table
├── seed_all_grades.py     # Database builder from modular JSON datasets
├── validator.py           # Morphology parser and progressive grammar engine
├── advisor.py             # In-syllabus synonym advisor and diagnostics
├── auditor.py             # Self-consistency verification engine
├── exam_styler.py         # Printable PDF & Word DOCX sheet generator
├── datasets/              # Versioned curriculum datasets (Grades 7–12)
│   ├── grade7_prospect1.json
│   ├── grade8_prospect2.json
│   ├── grade9_prospect3.json
│   ├── grade10_vision1.json
│   ├── grade11_vision2.json
│   └── grade12_vision3.json
├── docs/                  # Detailed architectural & pedagogical specifications
│   ├── ARCHITECTURE.md    # Engine design, lemmatization, and database indexing
│   ├── CURRICULUM_MAP.md  # 31-lesson syllabus breakdown and grammar milestones
│   └── TEACHER_GUIDE.md   # Practical guide for educators and AI prompt engineers
├── scripts/               # Utility scripts for textbook verification
│   └── fetch_and_verify_pdfs.py
├── exports/               # Pre-generated sample exams (PDF & DOCX)
└── tests/                 # 27 unit tests (TDD verified)
```

---

## 📖 Documentation
- [Architecture & Design Details](docs/ARCHITECTURE.md)
- [Comprehensive Curriculum Map](docs/CURRICULUM_MAP.md)
- [Teacher & AI Authoring Guide](docs/TEACHER_GUIDE.md)

---

## 📄 License
This project is licensed under the [MIT License](LICENSE). Open-source and free for English teachers, schools, researchers, and students.
