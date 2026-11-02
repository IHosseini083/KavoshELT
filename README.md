# KavoshELT

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-91%20passed-brightgreen.svg)]()
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![ORM: SQLAlchemy 2.0](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-red.svg)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**KavoshELT** is an open-source, deterministic curriculum intelligence engine, knowledge-graph RAG system, and national exam authoring toolkit for the official Iranian Secondary English Curriculum (Grades 7–12: *Prospect 1–3* and *Vision 1–3*).

It serves as a ground-truth guardrail for English educators and AI systems—eliminating out-of-syllabus hallucinations, enforcing official Ministry of Education (*Markaz-e-Sanjesh*) scoring blueprints, synthesizing parallel exam questions, and exporting print-ready Persian/English test papers (Word DOCX with native bidirectional tables, Vazirmatn PDF, and HTML).

---

## Table of Contents

- [Key Features](#key-features)
- [Curriculum Scope](#curriculum-scope)
- [Installation](#installation)
- [Usage & CLI Reference](#usage--cli-reference)
  - [1. Compose National Mock Exams & Quizzes](#1-compose-national-mock-exams--quizzes)
  - [2. Query Prerequisite Knowledge Graph & L1 Errors](#2-query-prerequisite-knowledge-graph--l1-errors)
  - [3. Validate Text Against Syllabus Bounds](#3-validate-text-against-syllabus-bounds)
  - [4. Adapt Text with In-Syllabus Synonyms](#4-adapt-text-with-in-syllabus-synonyms)
  - [5. Hybrid Semantic & Lexical RAG Retrieval](#5-hybrid-semantic--lexical-rag-retrieval)
  - [6. Export Markdown to PDF, Word DOCX, and HTML](#6-export-markdown-to-pdf-word-docx-and-html)
  - [7. Database Statistics & Self-Consistency Audit](#7-database-statistics--self-consistency-audit)
  - [8. MCP Server for AI Agents](#8-mcp-server-for-ai-agents)
- [Project Architecture](#project-architecture)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [Documentation](#documentation)
- [License](#license)

---

## Key Features

* **Complete 6-Grade Syllabus Database:** Covers all 31 lessons across *Prospect 1–3* (Grades 7–9) and *Vision 1–3* (Grades 10–12), including 1,695 textbook vocabulary entries, progressive grammar boundaries, canonical passages, and official assessment rubrics.
* **Unified Relational Graph-RAG Engine:** Combines SQLAlchemy 2.0 relational constraints, directed prerequisite concept graphs (`ConceptNode` and `ConceptEdge`), Persian first-language interference patterns (`L1ErrorPattern`), and 64-dimensional semantic vectors with SQLite FTS5 indexing.
* **Grade 12 National Exam Archive (1397–1405):** Includes 27 official national examination papers across Khordad, Shahrivar, and Dey sessions, decomposed into atomic question items with Bloom taxonomy levels, 0.25-point rubric breakdowns, and distractor diagnostics. 135 diagnostics are source-authored; the other 162 (cloze and reading) carry `"distractor_status": "machine_drafted"` and are awaiting teacher review. The drafts live in [`datasets/distractor_drafts_grade12.json`](datasets/distractor_drafts_grade12.json) and are merged in at seed time, so the authentic exam file stays untouched.
* **4-Layer Verification Gate:** Validates every exam item against mathematical scoring rules (exact multiples of 0.25), 100% syllabus vocabulary/grammar compliance, concept graph integrity, and answer key completeness.
* **4-Mode Exam Composer (Exact DP Score Solver):** Assembles full 28.0-point mock exams (`full_mock`), single-skill worksheets (`skill_worksheet`), custom classroom quizzes (`custom_quiz`), and interactive item slot swaps (`swap_slot_item`) using dynamic programming over quarter-point units.
* **3 Question Sourcing Modes:** Supports authentic past exam items (`past_papers`), deterministic syllabus-compliant parallel items (`ai_twins`), and interleaved combinations (`hybrid`).
* **MCP Server (`kavosh-mcp`):** Exposes syllabus validation, in-syllabus synonyms, lesson bounds, curriculum search, national-exam retrieval, and Persian L1-interference patterns as [Model Context Protocol](https://modelcontextprotocol.io) tools for Claude Desktop, Cursor, and other agents.
* **Print-Ready RTL Document Exporter:** Generates editable Microsoft Word (`.docx`) files with native OpenXML right-to-left table metadata (`w:bidiVisual`), PDFs with embedded Persian Vazirmatn typography, printable HTML sheets, and standalone teacher answer keys.

---

## Curriculum Scope

| Grade | Textbook | Lessons | In-Scope Grammar & Structures | Forbidden Out-of-Scope Structures |
|:---:|:---:|:---:|:---|:---|
| **7** | Prospect 1 | 8 | *To Be* verbs, *What/Who* questions, possessives, Present Continuous | Past tenses, Future, modals, Passive voice, Perfect tenses |
| **8** | Prospect 2 | 7 | Simple Present (*do/does*), *can/can't*, health & routine expressions | Past tenses, Future, Present Perfect, Passive voice |
| **9** | Prospect 3 | 6 | Simple Past (regular/irregular), past of *To Be*, travel narratives | Future with *will*, Present Perfect, Passive voice, Conditionals |
| **10** | Vision 1 | 4 | Simple Future (*will / be going to*), Comparatives/Superlatives, Past Continuous | Present Perfect (*have/has + V3*), Passive voice, Conditionals |
| **11** | Vision 2 | 3 | Present Perfect (*have/has + V3*), Gerunds/Infinitives, Conditional Type 1 | Passive voice (*be + V3*), Conditional Type 2 |
| **12** | Vision 3 | 3 | Passive voice (all tenses), Tag questions, Relative clauses, Past Perfect, Conditional Type 2 | Full secondary curriculum scope |

---

## Installation

### Prerequisites
* Python 3.10 or higher
* `pip` and a virtual environment (recommended)

### Setup
```bash
# 1. Clone the repository
git clone https://github.com/IHosseini083/KavoshELT.git
cd KavoshELT

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies and package in editable mode
pip install -r requirements.txt
pip install -e .
```

No manual database setup is needed. The SQLite database is resolved in this order: `--db` / `KAVOSH_DB`, a database packaged inside the installed wheel, then a cached build (in the user cache directory, or `KAVOSH_CACHE_DIR`) that is rebuilt automatically whenever the dataset files change. To build one explicitly:
```bash
python -m kavosh.seeder
```

Install the development tools (pytest, ruff, mypy) with `pip install -e ".[dev]"`. Composed exams are written to `./exports/composed` unless `KAVOSH_EXPORTS_DIR` is set.

---

## Usage & CLI Reference

All features are available through the `python -m kavosh` (or `kavosh`) command-line interface.

### 1. Compose National Mock Exams & Quizzes

**Full 28-Point Grade 12 National Mock Exam:**
```bash
python -m kavosh compose-exam \
    --mode full_mock \
    --grade 12 \
    --points 28.0 \
    --sourcing hybrid \
    --school "Alborz High School" \
    --teacher "English Department" \
    --out-dir exports/mock_exam
```
Generates `exam.md`, `student_sheet.docx`, `student_sheet.pdf`, `student_sheet.html`, and `teacher_answer_key.pdf`.

**Single-Skill Remedial Worksheet:**
```bash
python -m kavosh compose-exam \
    --mode skill_worksheet \
    --grade 12 \
    --section writing \
    --points 6.0 \
    --sourcing past_papers \
    --out-dir exports/writing_worksheet
```

**Classroom Quiz with Synthesized Twin Questions:**
```bash
python -m kavosh compose-exam \
    --mode custom_quiz \
    --grade 12 \
    --lessons 1 \
    --points 10.0 \
    --sourcing ai_twins \
    --out-dir exports/lesson1_quiz
```

### 2. Query Prerequisite Knowledge Graph & L1 Errors
Inspect foundational concepts from earlier grades and common Persian L1 transfer errors:
```bash
python -m kavosh graph-query --concept g12.l1.grammar.passive_voice
```

### 3. Validate Text Against Syllabus Bounds
Check whether a draft question or reading passage contains untaught vocabulary or forbidden grammar:
```bash
python -m kavosh validate \
    --grade 10 \
    --max-lesson 2 \
    --text "The ancient palace was built two hundred years ago."
```

### 4. Adapt Text with In-Syllabus Synonyms
Identify out-of-syllabus words, see which future grade teaches them, and get in-syllabus replacements:
```bash
python -m kavosh adapt \
    --grade 7 \
    --max-lesson 8 \
    --text "The physician helped the patient."
```

### 5. Hybrid Semantic & Lexical RAG Retrieval
Retrieve syllabus-bounded passages, vocabulary, and grammar constraints for LLM prompting:
```bash
python -m kavosh rag --query "endangered wildlife cheetah" --grade 10 --max-lesson 2
```

### 6. Export Markdown to PDF, Word DOCX, and HTML
```bash
python -m kavosh export --file exam.md --format pdf --out exam.pdf --include-key
python -m kavosh export --file exam.md --format docx --out exam.docx
python -m kavosh export --file exam.md --format html --out exam.html
```

### 7. Database Statistics & Self-Consistency Audit
```bash
# View curriculum and national exam bank summary
python -m kavosh stats

# Verify that 100% of canonical passages pass their own grade boundary
python -m kavosh audit

# Audit dataset integrity (schema, duplicate IDs, answer keys, concept edges,
# missing distractor analyses, lessons without Listening scripts)
python -m kavosh integrity          # add --strict to fail on warnings too
python -m kavosh integrity --coverage   # per-lesson inventory as a Markdown table
```

### 8. MCP Server for AI Agents
```bash
kavosh-mcp            # stdio transport; or: python -m kavosh.mcp_server
```
Tools: `validate_text`, `suggest_synonyms`, `get_lesson_bounds`, `search_curriculum`, `retrieve_exam_questions`, `get_l1_interference`. Resources: `curriculum://grade/{grade}/lesson/{lesson}` and `curriculum://index`.

**Claude Desktop Configuration (`claude_desktop_config.json`):**
```json
{
  "mcpServers": {
    "kavosh-elt": {
      "command": "kavosh-mcp"
    }
  }
}
```

**Cursor Configuration (`.cursor/mcp.json`):**
```json
{
  "mcpServers": {
    "kavosh-elt": {
      "command": "kavosh-mcp"
    }
  }
}
```
See [docs/MCP_SERVER.md](docs/MCP_SERVER.md) and [`examples/`](examples/) for all tool arguments, environment variables, and client setup.

---

## Project Architecture

All core source code is cleanly isolated inside the `kavosh/` package:

```text
KavoshELT/
├── kavosh/                  # Core package directory
│   ├── __init__.py          # Package metadata
│   ├── __main__.py          # CLI module execution entry point
│   ├── cli.py               # Unified command-line interface
│   ├── models.py            # SQLAlchemy 2.0 ORM declarative models
│   ├── schema.py            # Database schema and FTS5 virtual tables
│   ├── seeder.py            # Dataset & exam archive database builder
│   ├── validator.py         # Syllabus-bounds and grammar engine
│   ├── validator_data.py    # Contraction mappings and irregular morphology data
│   ├── morphology.py        # Irregular forms and suffix-candidate lemmatization
│   ├── syllabus.py          # Cached per-grade/lesson vocabulary & grammar index
│   ├── advisor.py           # In-syllabus synonym advisor
│   ├── auditor.py           # Curriculum self-consistency auditor
│   ├── rag.py               # Hybrid vector + FTS5 RAG retrieval engine
│   ├── exam_rag.py          # Multi-criteria exam retrieval, graph traversal & twin synthesis
│   ├── verifier.py          # 4-layer national exam verification gate
│   ├── composer.py          # 4-mode exam composer
│   ├── knapsack.py          # Exact quarter-point subset-sum solver
│   ├── paths.py             # Portable database/cache path resolution
│   ├── fts.py               # Typed SQLite FTS5 access
│   ├── integrity.py         # Dataset integrity audit (`kavosh integrity`)
│   ├── service.py           # Shared tool logic used by the MCP server
│   ├── mcp_server.py        # `kavosh-mcp` stdio MCP server
│   └── styler.py            # RTL Word DOCX, Vazirmatn PDF, and HTML exporter
├── assets/
│   └── fonts/               # Embedded Vazirmatn Persian/Latin fonts
├── datasets/                # Curriculum datasets (Grades 7–12) & national exam bank
├── docs/                    # Technical and pedagogical documentation
│   ├── ARCHITECTURE.md
│   ├── CURRICULUM_MAP.md
│   ├── MCP_SERVER.md
│   └── TEACHER_GUIDE.md
├── examples/                # Sample MCP client configurations
├── tests/                   # Automated test suite (91 tests, incl. MCP stdio end-to-end)
├── setup.py                 # Bundles datasets and a prebuilt database into wheels
├── pyproject.toml           # Package configuration & tool settings
├── requirements.txt         # Runtime and development dependencies
└── LICENSE                  # MIT License
```

---

## Testing & Quality Assurance

Run the full unit test suite:
```bash
pytest
```
(`python -m unittest discover -s tests` also works.)

Run static type checking and code formatting:
```bash
mypy kavosh tests
ruff check .
ruff format --check .
```

---

## Documentation

* [Architecture & Technical Specification](docs/ARCHITECTURE.md)
* [Complete Curriculum Map (Grades 7–12)](docs/CURRICULUM_MAP.md)
* [Teacher & Educator Guide](docs/TEACHER_GUIDE.md)
* [MCP Server Guide](docs/MCP_SERVER.md)

---

## License

Released under the [MIT License](LICENSE).
