# KavoshELT Architecture & Technical Specification

## Overview

KavoshELT is engineered as an in-process, zero-external-service pedagogical intelligence system. Rather than relying on separate graph databases (e.g., Neo4j) or vector databases (e.g., Pinecone/Qdrant), KavoshELT implements an embedded **Unified Relational Graph-RAG Architecture** on top of SQLAlchemy 2.0 and SQLite.

This guarantees:
1. **Sub-millisecond latency:** Queries execute entirely in-memory or against local SQLite tables.
2. **Deterministic execution:** No stochastic prompt drift or LLM hallucination in core mathematical scores or syllabus checks.
3. **Zero cloud lock-in:** The entire repository runs self-contained on Linux, macOS, or Windows using Python 3.10+.

---

## 1. Relational & Knowledge-Graph Data Layer (`models.py`)

The data layer models syllabus concepts, pedagogical prerequisites, historical exams, atomic test items, and negative L1 language transfer patterns.

```text
  [ ConceptNode ] <──── (prerequisite_of) ──── [ ConceptNode ]
         │                                            │
         ├──────────────────────┐                     │
         ▼                      ▼                     ▼
[ ExamQuestionItem ]   [ L1ErrorPattern ]   [ Vocabulary / Passages ]
         ▲
         │ (contains)
[ NationalExamPaper ] (1397 - 1405)
```

### Key SQLAlchemy 2.0 Models

* **`ConceptNode`:** Represents an atomic curriculum concept (e.g., `g12.l1.grammar.passive_voice`, `g12.l2.vocab.dictionaries`).
  * `id`: Unique hierarchical slug (`grade.lesson.category.concept_name`).
  * `grade`, `lesson_num`, `category`: Category is one of `vocabulary`, `grammar`, `writing`, `reading`, or `pronunciation`.
  * `title_en`, `title_fa`, `description`: Dual-language pedagogical summaries.
  * `embedding_json`: 64-dimensional float vector for conceptual similarity lookup.

* **`ConceptEdge`:** Represents directed prerequisite relationships.
  * `source_concept_id`: Prerequisite concept (e.g., `g9.l5.grammar.simple_past`).
  * `target_concept_id`: Dependent concept (e.g., `g12.l1.grammar.passive_voice`).
  * `relationship_type`: Directed relationship type (`prerequisite_of`, `reinforces`, `contrasts_with`).
  * `pedagogical_notes`: Explanation of why the prerequisite is required.

* **`NationalExamPaper`:** Represents an official nation-wide examination paper from the Ministry of Education.
  * `id`: Composite identifier (e.g., `paper_1404_khordad`).
  * `grade`: Target grade (Grade 12).
  * `shamsi_year`: Examination academic year (1397 to 1405).
  * `session`: Examination administration session (`Khordad`, `Shahrivar`, `Dey`).
  * `total_written_points`: Official written score (28.0 points standard).
  * `blueprint_version`: `1397-1401_classic` or `1402-1405_conceptual`.

* **`ExamQuestionItem`:** Atomic question items cataloged from national exams.
  * `id`: Unique item slug.
  * `section_code`: One of `vocabulary`, `grammar`, `writing`, `cloze`, `reading`.
  * `item_type`: Format (`fill_blank`, `multiple_choice`, `unscramble`, `true_false`, `open_ended`).
  * `bloom_level`: Cognitive depth (`remember`, `understand`, `apply`, `analyze`).
  * `points`: Item score as an exact multiple of 0.25 (e.g., 0.5, 0.75, 1.0, 2.0).
  * `instruction_en`, `stem_text`, `passage_text`: Question prompt and stimulus.
  * `options_json`: Distractors and choices for multiple-choice items.
  * `canonical_answer`: Official scoring key answer.
  * `rubric_breakdown_json`: Explicit sub-point distribution (e.g., `{"choice": 0.5}` or `{"word_order": 1.0, "syntax": 1.0}`).
  * `distractor_analysis`: Diagnostic explanation of common student errors.
  * `concept_ids_json`: JSON list of referenced `ConceptNode` identifiers.

* **`L1ErrorPattern`:** First-language (Persian) negative transfer patterns.
  * `id`: Error pattern slug (e.g., `l1_passive_aux_omission`).
  * `concept_id`: Associated `ConceptNode`.
  * `error_title_fa`: Persian diagnosis.
  * `incorrect_pattern_en`, `correct_pattern_en`: Contrastive examples.
  * `l1_root_cause_fa`: Linguistic root cause in Persian syntax/morphology.
  * `remedial_drill_template`: Practice prompt for remedial instruction.

---

## 2. Four-Layer Exam Bank Verification Gate (`verify_exam_bank.py`)

Every exam paper and question item must clear four strict verification rules before entering the database:

1. **Rule V1: Mathematical Scoring Precision**
   * $\forall \text{item}: \text{points} \equiv 0 \pmod{0.25}$
   * $\sum \text{rubric\_breakdown} = \text{points}$ (with floating-point tolerance $< 10^{-4}$)
   * $\sum_{\text{items}} \text{points} = 28.0$ for complete national papers.

2. **Rule V2: Curriculum Boundary Enforcement**
   * Stems, passages, choices, and canonical answers are lemmatized against `get_allowed_vocabulary(conn, grade, lesson)`.
   * Any vocabulary or grammar structure beyond the target grade boundary triggers an immediate verification rejection.

3. **Rule V3: Knowledge Graph Integrity**
   * All referenced `concept_ids` must resolve to existing records in the `concept_nodes` table.

4. **Rule V4: Answer Key Completeness**
   * Multiple-choice items must contain the canonical answer in their options list.
   * Constructed response items must supply structured rubrics for partial credit.

---

## 3. Retrieval & Twin Question Synthesis (`exam_rag_engine.py`)

### Multi-Criteria Item Retrieval (`retrieve_exam_items`)
Filters the question pool using combinations of:
* Grade and lesson numbers
* Section codes (`vocabulary`, `grammar`, `writing`, `cloze`, `reading`)
* Calendar year ranges (`year_min`, `year_max`)
* Administration sessions (`Khordad`, `Shahrivar`, `Dey`)
* Bloom taxonomy depth (`remember` through `analyze`)

When a query string is supplied, the engine combines vector dot-product similarity against concept embeddings with FTS5 BM25 lexical ranking:
$$\text{Score} = 0.6 \times \text{SemanticScore} + 0.4 \times \text{LexicalScore}$$

### Prerequisite Graph Traversal (`traverse_prerequisites`)
Given a target concept, recursively traverses upstream `ConceptEdge` records to extract foundational grammar/vocabulary learned in earlier grades, while pulling associated `L1ErrorPattern` records for diagnostic reporting.

### Twin Question Synthesizer (`synthesize_twin_item`)
To prevent test predictability and eliminate cheating across terms, the synthesizer constructs parallel items:
1. Retrieves target concept variations matching identical Bloom depth and question format.
2. Swaps context nouns and subjects while strictly maintaining target grammatical structures.
3. Passes the synthesized twin through the Rule V2 validation gate to guarantee 100% in-syllabus vocabulary.
4. Marks the item with `is_synthetic_twin: True` and assigns equivalent rubric breakdown values.

---

## 4. Exam Composition Engine (`exam_composer.py`)

Supports four compositional modes:
* **`full_mock`:** Follows the official 28.0-point blueprint:
  * Vocabulary: 6.0 points
  * Grammar: 5.0 points
  * Writing: 6.0 points
  * Cloze Test: 3.0 points
  * Reading Comprehension: 8.0 points
* **`skill_worksheet`:** Gathers items for a specific skill (e.g., Writing or Grammar) up to a requested target point threshold.
* **`custom_quiz`:** Uses round-robin selection across active sections to assemble balanced classroom quizzes matching an exact point target (e.g., 10.0 points).
* **`swap_slot_item`:** Replaces an individual question slot in an assembled exam with an alternate item of identical point value and section code.

---

## 5. Right-to-Left (RTL) Print & Export Engine (`exam_styler.py`)

Iranian school exams require bilingual layouts (English question stems paired with Persian exam headers, instructions, and scoring notes). Standard PDF and Word libraries often mangle Persian text by failing to reverse bidirectional character runs or align tables correctly.

KavoshELT resolves this natively:

### Microsoft Word (`.docx`)
* Injects native OpenXML attributes:
  * Paragraphs: `<w:bidi w:val="1"/>` and `<w:rFonts w:cs="Vazirmatn"/>`
  * Header and Score Tables: `<w:bidiVisual w:val="1"/>` ensures column 1 starts on the right side of the page.

### PDF Documents (`.pdf`)
* Embeds the true-type **Vazirmatn** font directly into ReportLab.
* Pre-processes Persian strings through `arabic_reshaper` and `python-bidi` before rendering, guaranteeing correct character shaping and ligature joining.

### Printable Web Pages (`.html`)
* Applies `dir="rtl"` to container elements and includes `@media print` CSS stylesheets with page breaks between student sheets and teacher keys.
