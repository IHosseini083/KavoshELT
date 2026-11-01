# Unified ELT Graph-RAG Platform Design Document

Date: 2026-11-01
Author: Seyed Iliya Hosseini & Hermes Agent
Status: Draft for User Approval
Sizing: Full Project (Multi-Phase Architecture; Phase 1 Targeted First)

---

## 1. Intent and the Why

Iranian secondary school English teachers (Grades 7 to 12, *Prospect 1-3* and *Vision 1-3*) face three daily pedagogical bottlenecks:
1. **High-Stakes National Exam Preparation:** Grade 12 (*Vision 3*) students take the national final exam (*Emtehan-e-Nahayi*), which carries a deterministic, high-stakes impact on university admission (*Konkur*). Teachers need to build mock exams, topic quizzes, and worksheets that match the exact 40-point (or 28-point written + 12-point listening) blueprint, 0.25-point rubric granularity, cognitive distribution, and distractor patterns of the Ministry of Education's Center for Educational Evaluation (*Markaz-e-Sanjesh*) across years 1397 to 1405 (Khordad, Shahrivar, Dey).
2. **Scarcity of Syllabus-Locked Reading Passages:** Teachers need fresh reading passages on contemporary topics that strictly obey the vocabulary and grammar ceiling of a target grade and lesson, paired with standard comprehension and critical-thinking items.
3. **L1 Interference (Persian-to-English Transfer Errors):** Iranian learners repeat predictable structural errors rooted in Persian syntax and morphology. Teachers need targeted remedial worksheets that trace a student's error back to its prerequisite concept in earlier grades.

While the initial `vision-kb` prototype proved out deterministic lemmatization, basic syllabus validation, and PDF/DOCX export, it lacks atomic question-level indexing of real national exams, a prerequisite knowledge graph, cognitive/difficulty metadata, and an interactive multi-mode exam composer. This platform replaces simple validation with a **Unified Relational Graph-RAG Engine** that combines exact mathematical rubric enforcement with a pedagogical knowledge graph and hybrid vector/lexical retrieval.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **Complete Grade 12 Written National Exam Archive (1397-1405):** Ingest, normalize, and verify written exam papers and official scoring keys across Khordad, Shahrivar, and Dey sessions from 1397 to 1405 into atomic question items.
- **Zero-Hallucination Ingestion & Two-Layer Verification:** Automatically harvest/ingest exam items from authoritative educational archives, then run programmatic sanity checks (exact point-sum verification, syllabus vocabulary/grammar cross-check against *Vision 3*, and answer-key consistency) before marking any record as `verified`.
- **Unified Relational Graph-RAG Engine:** Combine SQLAlchemy 2.0 relational tables, an embedded Pedagogical Knowledge Graph (`ConceptNode` and `ConceptEdge` for prerequisite and L1-error links), SQLite FTS5 lexical search, and in-process dense/concept embeddings.
- **Four Teacher Composition Workflows:**
  1. *Full National Mock Exam:* Complete standard written exam matching the official Ministry blueprint and exact point totals.
  2. *Skill-Specific Worksheet:* Focused practice on a single section/skill (e.g., 5-point Paragraph Writing, Cloze Test, Vocabulary, Grammar, Reading Comprehension).
  3. *Custom Classroom Quiz:* Teacher-defined total score (e.g., 10, 15, or 20 points) and lesson scope (Lesson 1, 2, 3, or combined).
  4. *Interactive Item-by-Item Composer:* Inspect retrieved/generated candidates per slot, swap individual items, or edit stems and point values manually.
- **Three Sourcing Modes (Teacher's Choice):**
  1. *Past Papers Only (`past_papers`):* Exact verbatim questions from 1397-1405 exams with year/session citations.
  2. *AI-Generated Twins (`ai_twins`):* Novel questions synthesized via LLM using retrieved national exam items as structural exemplars, gated by the syllabus validator.
  3. *Hybrid (`hybrid`):* Mix of verbatim past-paper questions and newly synthesized twin items per section.
- **Extensibility to Phase 2 & Phase 3:** Data schema natively includes entities for Graded Reading Passages (Phase 2) and L1 Interference Error Patterns (Phase 3) so later modules plug into the same graph without schema rewrites.

### Non-Goals (Phase 1)
- **Audio Synthesis and Listening Track Management:** Phase 1 focuses strictly on the written sections, transcripts/text items, answer keys, and scoring rubrics. Audio track synthesis/archiving is deferred out of Phase 1.
- **Student-Facing Accounts or Gamification:** The system is an authoring, retrieval, and publishing engine for teachers, not an LMS for student logins.

### Anti-Goals (Failure Conditions Even If Technically Working)
- **Unverified or Hallucinated "Past Paper" Items:** Labeling a synthetic question as an official 1402 Khordad exam question is a critical failure. Every `past_paper` item must carry provenance metadata and pass verification.
- **Approximate Point Totals:** A 20-point or 28-point written exam that sums to 19.75 or 20.5 points due to LLM arithmetic error is unacceptable. Point allocation must be enforced deterministically by code in 0.25-point increments.
- **Out-of-Syllabus Leakage in AI Twins:** Any AI-generated twin question containing untaught vocabulary or forbidden grammar for the selected grade/lesson must be caught and rejected or auto-adapted before reaching the teacher.
- **Heavy External Infrastructure:** Requiring external Docker databases (Neo4j, Milvus, Qdrant, Elasticsearch) that bloat VPS RAM is an anti-goal. Everything must run in-process on SQLite + SQLAlchemy 2.0.

---

## 3. Constraints

- **Tech Stack & Typing:** Python 3.10+, SQLAlchemy 2.0 ORM (`Mapped`, `mapped_column`), strict `mypy` type checking (`mypy --strict` / zero errors), and TDD (`unittest`).
- **Documentation & Repository Hygiene:** All repository documentation, code comments, and commit messages in English; zero decorative emojis anywhere in code, CLI, or UI.
- **Typography & Export Standards:** Print-ready PDF (`reportlab` + `arabic-reshaper` + `python-bidi` + embedded `Vazirmatn`), editable Word (`.docx` with native OpenXML `w:bidiVisual`, `w:bidi`, `w:rtl`), and RTL HTML following `DESIGN.md`.

---

## 4. Approaches Considered

### Approach 1: Modular Relational & FTS5 Engine
- **Description:** Model exams, atomic questions, and rubrics in SQLAlchemy 2.0 + SQLite FTS5 with deterministic SQL filters for grade, lesson, section, and score.
- **Pros:** Exact arithmetic, sub-20ms queries, zero external services, trivial deployment.
- **Cons:** Lacks explicit prerequisite graph traversal and multi-hop conceptual linking across grades.

### Approach 2: Dedicated Graph-RAG + External Vector DB (ChromaDB / NetworkX)
- **Description:** Store prerequisite trees and cognitive links in a graph layer and embeddings in ChromaDB with multi-step agentic retrieval.
- **Pros:** Rich semantic and prerequisite reasoning across lessons and grades.
- **Cons:** Higher memory footprint, synchronization overhead between relational metadata and external vector store.

### Approach 3: Document-Centric Context Stuffing
- **Description:** Store whole exam papers as Markdown files and let the LLM parse, slice, and assemble new exams in-prompt.
- **Pros:** Minimal schema code.
- **Cons:** Frequent arithmetic errors on 0.25-point rubrics, slow latency, high token cost, weak item-level provenance.

### Selected Architecture: Unified Relational Graph-RAG Engine (Best of Options 1 & 2)
- **Why Chosen:** Implements the **Pedagogical Knowledge Graph** (`ConceptNode`, `ConceptEdge` for prerequisites, grammar dependencies, and L1 interference) and **Hybrid Vector + FTS5 Retrieval** directly inside SQLAlchemy 2.0 + SQLite. We get multi-hop graph traversal and semantic twin generation (Option 2) alongside ACID transactions, zero-dependency deployment, and exact 0.25-point rubric math (Option 1).

---

## 5. User Decisions (Locked)

1. **Scope Vision:** A comprehensive 3-pillar platform (1. National Exams Archive & Composer, 2. Graded Reading & Critical Thinking Generator, 3. L1 Error-Driven Remedial Clinic) built on one shared Knowledge Engine, delivered modularly starting with Pillar 1.
2. **Target Grade & Historical Window:** Grade 12 (*Vision 3*) national final exams covering years **1397 to 1405** across all three official sessions (**Khordad, Shahrivar, Dey**).
3. **Granularity:** Atomic item-level indexing including cognitive level (Bloom's taxonomy), difficulty estimate, exact 0.25-point scoring rubric criteria, and distractor/error tags.
4. **Teacher Flexibility (Composer Modes):** Support all 4 modes: Full National Mock Exam, Skill-Specific Worksheet, Custom Score/Lesson Quiz, and Interactive Item-by-Item Composer.
5. **Question Sourcing Modes:** Teacher chooses between Verbatim Past Papers, AI-Generated Twin Questions, or Hybrid.
6. **Data Sourcing & Verification:** Autonomous ingestion and verification pipeline handled by the system with strict validation so no inaccurate exam data enters the ground-truth store.
7. **Phase 1 Modality Focus:** Written exam sections, reading/cloze passages, grammar/vocabulary/writing items, and official scoring keys first (Listening audio excluded from Phase 1).

---

## 6. System Architecture & Data Model

### 6.1 Core SQLAlchemy 2.0 Schema (`models.py` / `graph_rag_models.py`)

1. **`ConceptNode` (Pedagogical Knowledge Graph Vertex):**
   - `id` (`str`, PK, e.g., `"g12.l1.grammar.passive_voice"`, `"g12.l2.vocab.entry"`)
   - `grade` (`int`: 7..12), `lesson_num` (`int`: 1..8)
   - `category` (`str`: `"grammar"`, `"vocabulary"`, `"reading_skill"`, `"writing_skill"`, `"pronunciation"`)
   - `title_en` (`str`), `title_fa` (`str`), `description` (`str`)
   - `embedding_json` (`Optional[str]`)

2. **`ConceptEdge` (Pedagogical Knowledge Graph Edge):**
   - `source_id` (`str`, FK -> `ConceptNode.id`), `target_id` (`str`, FK -> `ConceptNode.id`)
   - `relation_type` (`str`: `"prerequisite_of"`, `"contrasts_with"`, `"l1_interference_with"`, `"co_occurs_with"`)
   - `weight` (`float`), `notes` (`Optional[str]`)

3. **`NationalExamPaper` (Official Exam Header):**
   - `id` (`str`, PK, e.g., `"g12_1403_khordad_standard"`)
   - `grade` (`int`), `shamsi_year` (`int`: 1397..1405), `session` (`str`: `"Khordad"`, `"Shahrivar"`, `"Dey"`)
   - `total_written_points` (`float`, e.g., `28.0` or `40.0` depending on year's official blueprint)
   - `blueprint_version` (`str`: `"1397-1401_classic"` vs `"1402-1405_conceptual"`)
   - `source_origin` (`str`), `is_verified` (`bool`)

4. **`ExamQuestionItem` (Atomic Question Unit):**
   - `id` (`str`, PK, e.g., `"g12_1403_khordad_q14"`)
   - `paper_id` (`str`, FK -> `NationalExamPaper.id`)
   - `section_code` (`str`: `"vocabulary"`, `"grammar"`, `"writing"`, `"cloze"`, `"reading"`, `"pronunciation"`)
   - `item_type` (`str`: `"multiple_choice"`, `"fill_blank"`, `"unscramble"`, `"error_correction"`, `"sentence_completion"`, `"paragraph_writing"`, `"matching"`, `"true_false"`, `"open_ended"`)
   - `grade` (`int`), `lesson_num` (`int`: 1, 2, or 3)
   - `bloom_level` (`str`: `"remember"`, `"understand"`, `"apply"`, `"analyze"`, `"evaluate"`, `"create"`)
   - `difficulty` (`str`: `"easy"`, `"medium"`, `"hard"`)
   - `points` (`float`, exact multiple of `0.25`)
   - `instruction_en` (`str`), `stem_text` (`str`), `passage_text` (`Optional[str]`), `options_json` (`Optional[str]`)
   - `canonical_answer` (`str`), `acceptable_variants_json` (`str`), `rubric_breakdown_json` (`str` - exact 0.25-pt scoring rules)
   - `distractor_analysis` (`Optional[str]` - why wrong options trap students)
   - `concept_ids_json` (`str` - linked `ConceptNode` IDs)
   - `embedding_json` (`Optional[str]`), `is_synthetic_twin` (`bool`), `parent_item_id` (`Optional[str]`)

5. **`L1ErrorPattern` (Phase 3 Ready - Persian Interference Registry):**
   - `id` (`str`, PK), `concept_id` (`str`, FK -> `ConceptNode.id`)
   - `error_title_fa` (`str`), `incorrect_pattern_en` (`str`), `correct_pattern_en` (`str`)
   - `l1_root_cause_fa` (`str`), `remedial_drill_template` (`str`)

### 6.2 Autonomous Ingestion & Two-Layer Verification Pipeline

1. **Curated & Scraped Corpus Builder (`ingest_national_exams.py`):**
   - Collects and structures Grade 12 (*Vision 3*) national final exam items from 1397 to 1405 (Khordad, Shahrivar, Dey), modeling the official shift from earlier objective formats (1397-1401) to the conceptual/communicative evaluation blueprints (1402-1405).
2. **Deterministic Verification Gate (`verify_exam_bank.py`):**
   - **Rule V1 (Point Precision):** Every item's `points` must be a positive multiple of `0.25`, and its `rubric_breakdown_json` sub-scores must sum exactly to `points`.
   - **Rule V2 (Syllabus Alignment):** Every item's `stem_text`, `options`, and `canonical_answer` (excluding reading passage proper nouns) must pass the Grade 12 *Vision 3* (`max_grade=12, max_lesson=3`) vocabulary and grammar validator.
   - **Rule V3 (Concept Graph Integrity):** Every `concept_id` referenced by an item must exist in `ConceptNode` and map to the item's `lesson_num`.
   - **Rule V4 (Answer Key Completeness):** Multiple-choice items must have the `canonical_answer` present in `options_json`; open-ended/writing items must have explicit 0.25-point rubric breakdowns.

### 6.3 Graph-RAG Retrieval & Twin Synthesis Engine (`exam_rag_engine.py`)

1. **Multi-Constraint Slot Solver:**
   - Given a target blueprint (e.g., Full 28-point Written National Exam, or a 10-point Lesson 1+2 Grammar/Vocab Quiz), the solver partitions the target score into exact slots `(section_code, item_type, lesson_num, bloom_level, points)`.
2. **Graph-Augmented Hybrid Search:**
   - Queries `ExamQuestionItem` filtered by `(grade, lesson_num, section_code, item_type, session, year_range)`, ranked by a weighted score of:
     - Concept Graph overlap (`ConceptNode` + 1-hop `PrerequisiteEdge` neighbors)
     - Dense/Cluster Cosine Similarity (`embedding_json`)
     - FTS5 BM25 keyword match (`exam_items_fts`)
3. **Closed-Loop AI Twin Generator:**
   - When `mode="ai_twins"` or `mode="hybrid"` is selected, the engine passes 2-3 retrieved past-paper items + their `ConceptNode` rules + allowed vocabulary from `vision-kb` to the LLM.
   - The generated twin item is immediately run through `validator.validate_exam_text(max_grade=12, max_lesson=target_lesson)` and `verify_item_rubric()`. If any out-of-syllabus word appears, the engine auto-adapts or regenerates before returning.

---

## 7. Agent Calls (Marked Decisions Made by Agent)

- **[Agent Call 1 - Blueprint Versioning (1397-1401 vs 1402-1405)]:** In the real Iranian national exams, the written vs. listening score split evolved (recent 1402-1405 exams allocate 12 points to Listening and 28 points to Written = 40 points total, or scaled to 20). The composer will support both the **28-point Written National Standard** (plus optional 40-point full written simulation) and **20-point Scaled Standard** so teachers can print exams ready for school gradebooks without manual math.
- **[Agent Call 2 - Coexistence Inside `/home/ubuntu/vision_kb`]:** Rather than fragmenting into a separate repository, we will evolve `/home/ubuntu/vision_kb` into v2.0 (adding `national_exams/` datasets, `graph_models.py`, `exam_composer.py`, and CLI/API subcommands) so it directly reuses the battle-tested `validator.py`, `advisor.py`, and `exam_styler.py` (Vazirmatn PDF/DOCX/HTML exporter).
- **[Agent Call 3 - Shamsi Year 1405 Coverage]:** Because we are in late 2026 (Shamsi 1405), 1405 includes Khordad 1405 and Shahrivar 1405 (and Dey 1404/1405), giving 9 full academic cycles (1397 through 1405).

---

## 8. What is Left to the Builder

- Exact CLI argument flags and JSON response formatting for the interactive item-swapping API.
- Internal helper naming and test fixture organization under `tests/`.
- Styling details of the rubric table inside the Teacher Answer Key PDF/DOCX export.
