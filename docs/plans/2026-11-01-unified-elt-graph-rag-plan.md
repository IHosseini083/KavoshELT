# Implementation Plan: Unified ELT Graph-RAG Platform (v2.0)

Date: 2026-11-01
Design Reference: `docs/plans/2026-11-01-unified-elt-graph-rag-design.md`
Workspace: `/home/ubuntu/vision_kb`
Python Interpreter: `/home/ubuntu/vision_kb/venv/bin/python`

---

## Goal
Build and verify the Unified Relational Graph-RAG Engine (v2.0) inside `/home/ubuntu/vision_kb` with:
1. SQLAlchemy 2.0 ORM models for the Pedagogical Knowledge Graph (`ConceptNode`, `ConceptEdge`), Grade 12 National Final Exam Archive 1397-1405 (`NationalExamPaper`, `ExamQuestionItem` + `exam_items_fts`), and L1 Interference Error Registry (`L1ErrorPattern`).
2. A 4-rule deterministic verification gate (`verify_exam_bank.py`) enforcing 0.25-point rubric precision, *Vision 3* syllabus compliance, graph integrity, and answer-key completeness.
3. A comprehensive, verified dataset (`datasets/national_exams_grade12_1397_1405.json` & `datasets/concept_graph_grade12.json`) covering 1397-1405 (Khordad, Shahrivar, Dey) across all written sections (`vocabulary`, `grammar`, `writing`, `cloze`, `reading`) and lessons (Lessons 1-3).
4. The Graph-RAG Retrieval & Multi-Mode Exam Composer (`exam_rag_engine.py` & `exam_composer.py`) supporting 4 composition modes (`full_mock`, `skill_worksheet`, `custom_quiz`, `interactive_slot`) and 3 sourcing modes (`past_papers`, `ai_twins`, `hybrid`) with direct PDF/DOCX/HTML export.

---

## Numbered Implementation Tasks (TDD Cycle per Task)

### Task 1: Extend SQLAlchemy 2.0 Models & FTS5 Schema for Graph-RAG
**Files:**
- Modify: `/home/ubuntu/vision_kb/models.py`
- Modify: `/home/ubuntu/vision_kb/schema.py`
- Create test: `/home/ubuntu/vision_kb/tests/test_graph_models.py`

**Steps:**
1. **Red:** Write `tests/test_graph_models.py` testing creation and querying of `ConceptNode`, `ConceptEdge`, `NationalExamPaper`, `ExamQuestionItem`, `L1ErrorPattern`, and the `exam_items_fts` virtual table. Run `venv/bin/python -m unittest tests/test_graph_models.py` and verify `ImportError`.
2. **Green:** Add `ConceptNode`, `ConceptEdge`, `NationalExamPaper`, `ExamQuestionItem`, and `L1ErrorPattern` with strict `Mapped[...]` annotations to `models.py`, and add `CREATE VIRTUAL TABLE IF NOT EXISTS exam_items_fts USING fts5(...)` to `schema.py`.
3. **Verify:**
   - Run `/home/ubuntu/vision_kb/venv/bin/python -m unittest tests/test_graph_models.py` -> `OK`
   - Run `/home/ubuntu/vision_kb/venv/bin/python -m mypy --ignore-missing-imports models.py schema.py tests/test_graph_models.py` -> `Success: no issues found`

---

### Task 2: Build the 4-Layer Exam Bank Verification Gate (`verify_exam_bank.py`)
**Files:**
- Create: `/home/ubuntu/vision_kb/verify_exam_bank.py`
- Create test: `/home/ubuntu/vision_kb/tests/test_verify_exam_bank.py`

**Steps:**
1. **Red:** Write `tests/test_verify_exam_bank.py` testing:
   - `Rule V1 (Point Precision):` Rejects an item with `points=0.3` or where `rubric_breakdown` sub-points sum to `0.75` instead of `1.0`.
   - `Rule V2 (Syllabus Alignment):` Rejects a Grade 12 item containing out-of-syllabus vocabulary not in *Prospect 1-3* / *Vision 1-3* (unless whitelisted in reading passage proper nouns).
   - `Rule V3 (Graph Integrity):` Rejects an item referencing a non-existent `ConceptNode.id`.
   - `Rule V4 (Answer Key Completeness):` Rejects an MC item whose `canonical_answer` is missing from `options`, or a writing item with an empty rubric breakdown.
2. **Green:** Implement `verify_item()`, `verify_paper()`, and `audit_national_exam_bank()` in `verify_exam_bank.py`.
3. **Verify:**
   - Run `/home/ubuntu/vision_kb/venv/bin/python -m unittest tests/test_verify_exam_bank.py` -> `OK`
   - Run `/home/ubuntu/vision_kb/venv/bin/python -m mypy --ignore-missing-imports verify_exam_bank.py tests/test_verify_exam_bank.py` -> `Success`

---

### Task 3: Curate & Seed the Pedagogical Knowledge Graph and 1397-1405 Grade 12 National Exam Bank
**Files:**
- Create: `/home/ubuntu/vision_kb/datasets/concept_graph_grade12.json`
- Create: `/home/ubuntu/vision_kb/datasets/national_exams_grade12_1397_1405.json`
- Modify: `/home/ubuntu/vision_kb/seed_all_grades.py`
- Create test: `/home/ubuntu/vision_kb/tests/test_national_exam_seed.py`

**Steps:**
1. **Red:** Write `tests/test_national_exam_seed.py` asserting that:
   - Every Shamsi year from `1397` to `1405` (`1397, 1398, 1399, 1400, 1401, 1402, 1403, 1404, 1405`) and all three sessions (`Khordad`, `Shahrivar`, `Dey`) are represented in `NationalExamPaper`.
   - All 5 written sections (`vocabulary`, `grammar`, `writing`, `cloze`, `reading`), all 3 lessons of *Vision 3* (Lesson 1: *Sense of Appreciation*, Lesson 2: *Look it Up!*, Lesson 3: *Renewable Energy*), and all Bloom levels (`remember` through `create`) are populated in `ExamQuestionItem`.
   - `ConceptNode` and `ConceptEdge` connect Grade 12 concepts to prerequisite concepts in Grades 9, 10, and 11 (e.g., `g12.l1.grammar.passive_voice` -> `g9.l5.grammar.simple_past` and `g11.l1.grammar.present_perfect`).
   - `L1ErrorPattern` contains curated Persian interference patterns linked to `ConceptNode`s.
   - `audit_national_exam_bank()` passes with `0` validation errors (`100%` verified ground truth).
2. **Green:** Author `datasets/concept_graph_grade12.json` and `datasets/national_exams_grade12_1397_1405.json`, update `seed_all_grades.py` to seed the graph, exam papers, atomic question items, embeddings, and `exam_items_fts`, and rebuild `data/curriculum.db`.
3. **Verify:**
   - Run `/home/ubuntu/vision_kb/venv/bin/python seed_all_grades.py`
   - Run `/home/ubuntu/vision_kb/venv/bin/python -m unittest tests/test_national_exam_seed.py` -> `OK`

---

### Task 4: Implement Graph-RAG Hybrid Retrieval & Closed-Loop Twin Generator (`exam_rag_engine.py`)
**Files:**
- Create: `/home/ubuntu/vision_kb/exam_rag_engine.py`
- Create test: `/home/ubuntu/vision_kb/tests/test_exam_rag_engine.py`

**Steps:**
1. **Red:** Write `tests/test_exam_rag_engine.py` testing:
   - `retrieve_exam_items()`: Filtering by `lessons=[1, 2]`, `sections=["grammar", "writing"]`, `sessions=["Khordad"]`, `year_min=1400`, `year_max=1405`, `difficulty="medium"`, and ranking via hybrid score (Concept Graph + Prerequisite 1-hop boost + Cosine Embedding + FTS5 BM25).
   - `traverse_prerequisites()`: Returning upstream prerequisite concepts and associated `L1ErrorPattern` entries for any target `ConceptNode`.
   - `synthesize_twin_item()`: Taking a reference `ExamQuestionItem`, generating a parallel twin question that tests the same `ConceptNode` and `points` with fresh in-syllabus surface text, and passing `verify_item()` + `validate_exam_text()`.
2. **Green:** Implement `exam_rag_engine.py` with full type annotations.
3. **Verify:**
   - Run `/home/ubuntu/vision_kb/venv/bin/python -m unittest tests/test_exam_rag_engine.py` -> `OK`
   - Run `/home/ubuntu/vision_kb/venv/bin/python -m mypy --ignore-missing-imports exam_rag_engine.py tests/test_exam_rag_engine.py` -> `Success`

---

### Task 5: Implement the 4-Mode Exam Composer & Official Written Exam Styler (`exam_composer.py`)
**Files:**
- Create: `/home/ubuntu/vision_kb/exam_composer.py`
- Modify: `/home/ubuntu/vision_kb/exam_styler.py`
- Modify: `/home/ubuntu/vision_kb/curriculum_kb.py`
- Create test: `/home/ubuntu/vision_kb/tests/test_exam_composer.py`

**Steps:**
1. **Red:** Write `tests/test_exam_composer.py` testing all 4 teacher modes and 3 sourcing modes:
   - Mode 1 (`full_mock`): Assembles a complete Grade 12 written national exam summing to the exact target score (`28.0`, `20.0`, or `40.0` points) with official section distribution.
   - Mode 2 (`skill_worksheet`): Assembles a single-skill worksheet (e.g., `section="writing"`, `target_points=5.0`).
   - Mode 3 (`custom_quiz`): Assembles a lesson-scoped quiz (e.g., `lessons=[1]`, `target_points=10.0`) across `past_papers`, `ai_twins`, and `hybrid` modes.
   - Mode 4 (`interactive_slot` / `swap_item`): Replaces a single question slot with an alternative candidate of identical point value and lesson scope while preserving the exact total score.
   - Exports the composed exam and its 0.25-point itemized Teacher Scoring Key to PDF, DOCX, and HTML.
2. **Green:** Implement `exam_composer.py`, extend `exam_styler.py` to render item provenance badges (e.g., `[خرداد ۱۴۰۳ - ۰.۵ نمره]` or `[سوال هم‌تراز - ۰.۵ نمره]`) and 0.25-point rubric breakdowns in the Answer Key, and add `compose-exam` and `graph-query` subcommands to `curriculum_kb.py`.
3. **Verify:**
   - Run `/home/ubuntu/vision_kb/venv/bin/python -m unittest discover -s tests` -> All tests `OK`
   - Run `/home/ubuntu/vision_kb/venv/bin/python -m mypy --ignore-missing-imports models.py schema.py verify_exam_bank.py exam_rag_engine.py exam_composer.py curriculum_kb.py` -> `Success`
   - Update `README.md` and `docs/ARCHITECTURE.md` (100% English, zero emojis) and commit to Git.
