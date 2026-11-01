# Architecture & Design Document

## Overview
The Iranian Secondary English Curriculum Knowledge Base is designed following the **Zero External Dependencies** principle. It relies strictly on Python 3.10+ standard libraries (`sqlite3`, `re`, `json`, `argparse`, `unittest`) to guarantee maximum portability and determinism across cloud servers, local development machines, Docker containers, and edge devices.

---

## 1. Storage Layer (`schema.py` & SQLite)

Data is modeled across 4 relational and full-text search tables:

### `lessons`
Stores curriculum metadata and progressive grammar boundaries:
- `grade INTEGER` (7 to 12)
- `lesson_num INTEGER` (1 to 8 depending on grade)
- `title TEXT`
- `theme TEXT`
- `allowed_grammar TEXT` (JSON object defining tenses and structures)
- `forbidden_grammar TEXT` (JSON object defining strictly forbidden tenses and structures)
- Primary Key: `(grade, lesson_num)`

### `vocabulary`
Contains active lexis extracted from canonical textbooks:
- `id INTEGER PRIMARY KEY`
- `word TEXT` (Surface form)
- `lemma TEXT` (Dictionary base form)
- `pos TEXT` (noun, verb, adj, adv, phrase, interj)
- `grade INTEGER`
- `lesson_num INTEGER`
- `definition_fa TEXT` (Persian definition aligned with textbooks)
- `example_en TEXT` (Model sentence)
- Indexes on `lemma` and `(grade, lesson_num)`

### `passages_fts` (SQLite FTS5)
Full-text indexed corpus of official readings, dialogues, and listening scripts:
- Columns: `grade`, `lesson_num`, `section_type`, `title`, `content`
- Uses SQLite BM25 ranking algorithm for sub-millisecond keyword lookup.

### `rubrics`
Official national assessment blueprints from the Ministry of Education (*Daftar-e-Talif*):
- `id TEXT PRIMARY KEY`
- `grade INTEGER`, `term INTEGER`, `exam_type TEXT`, `total_points REAL`
- `structure_json TEXT`

---

## 2. Validation & Linguistic Engine (`validator.py`)

### Lemmatization Pipeline
To avoid heavy third-party NLP wheels (like `spacy` or `nltk`), the engine implements a rule-based English morphology processor:
1. **Direct Match:** Checks if surface word exists in allowed vocabulary for `(grade <= max_grade, lesson <= max_lesson)`.
2. **Proper Noun Whitelist:** Checks against common Iranian and international names (cities, poets, scientists, planets).
3. **Irregular Verb Mapper:** Maps past/participle forms (e.g. `went` -> `go`, `saw` -> `see`, `built` -> `build`, `kept` -> `keep`, `got` -> `get`) to their dictionary lemmas.
4. **Morphological Suffix Stripper:**
   - `-ing` with consonant doubling (`running` -> `run`) and `-ying` -> `-ie` (`dying` -> `die`).
   - `-ed` / `-ied` (`carried` -> `carry`, `visited` -> `visit`).
   - `-s` / `-es` / `-ies` / `-sses` (`classes` -> `class`, `illnesses` -> `illness`, `cities` -> `city`).
   - `-er` / `-est` (`faster` -> `fast`, `biggest` -> `big`).
   - `-ly` / `-ily` (`rapidly` -> `rapid`, `heavily` -> `heavy`).

### Progressive Grammar Guardrails
The engine evaluates regex patterns conditioned on the student's current grade and lesson index:
- **Present Perfect:** `have/has + V3` (forbidden if `max_grade < 11`).
- **Past Progressive:** `was/were + V-ing` (forbidden if `max_grade < 10` or `max_grade == 10 and max_lesson < 3`).
- **Passive Voice:** `be + V3 + by` or `is/are/was/were being V3` (forbidden if `max_grade < 12`).
- **Conditional Type 2:** `if + past ..., would` (forbidden if `max_grade < 12` or `max_grade == 12 and max_lesson < 2`).

---

## 3. In-Syllabus Synonym Advisor (`advisor.py`)

When an out-of-syllabus word is caught:
1. It queries the curriculum database to pinpoint exactly in which future grade/lesson that word will be introduced.
2. It queries a curated synonym knowledge graph + Persian semantic definitions to retrieve words of identical part of speech that the student *already knows* from earlier grades.
3. It suggests these alternatives directly in the JSON response, enabling AI agents or human teachers to rewrite the sentence seamlessly.
