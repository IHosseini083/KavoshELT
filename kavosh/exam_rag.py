from __future__ import annotations

import json
import re
import uuid
from typing import Any

from sqlalchemy import and_, select, text

from kavosh.models import (
    ConceptEdge,
    ConceptNode,
    DbTarget,
    ExamQuestionItem,
    L1ErrorPattern,
    NationalExamPaper,
    session_scope,
)
from kavosh.rag import _normalize_tokens, compute_embedding, cosine_similarity
from kavosh.verifier import verify_item


def retrieve_exam_items(
    conn: DbTarget,
    grade: int = 12,
    lessons: list[int] | None = None,
    sections: list[str] | None = None,
    sessions: list[str] | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    difficulty: str | None = None,
    bloom_level: str | None = None,
    item_type: str | None = None,
    concept_id: str | None = None,
    query: str | None = None,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    query_vec: list[float] | None = compute_embedding(query) if query else None
    query_terms = [t for t in _normalize_tokens(query) if len(t) > 2] if query else []

    with session_scope(conn) as session:
        # Build query joining ExamQuestionItem and NationalExamPaper
        stmt = (
            select(ExamQuestionItem, NationalExamPaper)
            .join(NationalExamPaper, ExamQuestionItem.paper_id == NationalExamPaper.id)
            .where(ExamQuestionItem.grade == grade)
        )

        if lessons:
            stmt = stmt.where(ExamQuestionItem.lesson_num.in_(lessons))
        if sections:
            stmt = stmt.where(ExamQuestionItem.section_code.in_(sections))
        if sessions:
            stmt = stmt.where(NationalExamPaper.session.in_(sessions))
        if year_min is not None:
            stmt = stmt.where(NationalExamPaper.shamsi_year >= year_min)
        if year_max is not None:
            stmt = stmt.where(NationalExamPaper.shamsi_year <= year_max)
        if difficulty:
            stmt = stmt.where(ExamQuestionItem.difficulty == difficulty)
        if bloom_level:
            stmt = stmt.where(ExamQuestionItem.bloom_level == bloom_level)
        if item_type:
            stmt = stmt.where(ExamQuestionItem.item_type == item_type)

        matched_rows = session.execute(stmt).all()

        # FTS5 matches if query exists
        fts_hits: dict[str, float] = {}
        if query_terms:
            fts_query = " OR ".join(f'"{t}"' for t in query_terms[:8])
            try:
                fts_rows = session.execute(
                    text(
                        """
                        SELECT item_id, bm25(exam_items_fts)
                        FROM exam_items_fts
                        WHERE exam_items_fts MATCH :q
                        """
                    ),
                    {"q": fts_query},
                ).fetchall()
                for rank_idx, r in enumerate(fts_rows):
                    fts_hits[str(r[0])] = 1.0 / (rank_idx + 1.0)
            except Exception:
                pass

        results: list[dict[str, Any]] = []
        for item, paper in matched_rows:
            # Concept ID filter
            c_ids: list[str] = []
            if item.concept_ids_json:
                try:
                    c_ids = json.loads(item.concept_ids_json)
                except Exception:
                    pass
            if concept_id and concept_id not in c_ids:
                continue

            sem_score = 0.0
            if query_vec:
                item_vec: list[float] = []
                if item.embedding_json:
                    try:
                        item_vec = json.loads(item.embedding_json)
                    except Exception:
                        pass
                if not item_vec:
                    item_vec = compute_embedding(
                        f"{item.stem_text} {item.canonical_answer}"
                    )
                sem_score = max(0.0, cosine_similarity(query_vec, item_vec))

            lex_score = fts_hits.get(item.id, 0.0)
            concept_match = 1.0 if (concept_id and concept_id in c_ids) else 0.0

            if query:
                hybrid_score = round(
                    0.55 * sem_score + 0.35 * lex_score + 0.10 * concept_match, 4
                )
            else:
                hybrid_score = round(1.0 + (0.1 * concept_match), 4)

            results.append(
                {
                    "id": item.id,
                    "paper_id": item.paper_id,
                    "shamsi_year": paper.shamsi_year,
                    "session": paper.session,
                    "section_code": item.section_code,
                    "item_type": item.item_type,
                    "grade": item.grade,
                    "lesson_num": item.lesson_num,
                    "bloom_level": item.bloom_level,
                    "difficulty": item.difficulty,
                    "points": float(item.points),
                    "instruction_en": item.instruction_en,
                    "stem_text": item.stem_text,
                    "passage_text": item.passage_text,
                    "options_json": item.options_json,
                    "canonical_answer": item.canonical_answer,
                    "acceptable_variants_json": item.acceptable_variants_json,
                    "rubric_breakdown_json": item.rubric_breakdown_json,
                    "distractor_analysis": item.distractor_analysis,
                    "concept_ids": c_ids,
                    "is_synthetic_twin": item.is_synthetic_twin,
                    "semantic_score": round(sem_score, 4),
                    "lexical_score": round(lex_score, 4),
                    "hybrid_score": hybrid_score,
                }
            )

        results.sort(key=lambda x: (x["hybrid_score"], x["shamsi_year"]), reverse=True)
        return results[:top_k]


def traverse_prerequisites(conn: DbTarget, concept_id: str) -> dict[str, Any]:
    with session_scope(conn) as session:
        concept = session.get(ConceptNode, concept_id)
        if not concept:
            return {"concept": None, "prerequisites": [], "l1_errors": []}

        # Find prerequisite edges
        edges = list(
            session.scalars(
                select(ConceptEdge).where(
                    and_(
                        ConceptEdge.source_id == concept_id,
                        ConceptEdge.relation_type == "prerequisite_of",
                    )
                )
            ).all()
        )

        prereq_nodes: list[dict[str, Any]] = []
        for e in edges:
            target_node = session.get(ConceptNode, e.target_id)
            if target_node:
                prereq_nodes.append(
                    {
                        "id": target_node.id,
                        "grade": target_node.grade,
                        "lesson_num": target_node.lesson_num,
                        "category": target_node.category,
                        "title_en": target_node.title_en,
                        "title_fa": target_node.title_fa,
                        "description": target_node.description,
                        "edge_notes": e.notes,
                    }
                )
            else:
                # Upstream target concept in lower grade
                match = re.search(r"g(\d+)", e.target_id)
                gr = int(match.group(1)) if match else 10
                prereq_nodes.append(
                    {
                        "id": e.target_id,
                        "grade": gr,
                        "lesson_num": 1,
                        "category": "grammar",
                        "title_en": e.target_id,
                        "title_fa": e.target_id,
                        "description": e.notes or "Prerequisite concept",
                        "edge_notes": e.notes,
                    }
                )

        # Find L1 error patterns
        l1_errs = list(
            session.scalars(
                select(L1ErrorPattern).where(L1ErrorPattern.concept_id == concept_id)
            ).all()
        )
        l1_list = [
            {
                "id": err.id,
                "error_title_fa": err.error_title_fa,
                "incorrect_pattern_en": err.incorrect_pattern_en,
                "correct_pattern_en": err.correct_pattern_en,
                "l1_root_cause_fa": err.l1_root_cause_fa,
                "remedial_drill_template": err.remedial_drill_template,
            }
            for err in l1_errs
        ]

        return {
            "concept": {
                "id": concept.id,
                "grade": concept.grade,
                "lesson_num": concept.lesson_num,
                "category": concept.category,
                "title_en": concept.title_en,
                "title_fa": concept.title_fa,
                "description": concept.description,
            },
            "prerequisites": prereq_nodes,
            "l1_errors": l1_list,
        }


# Curated parallel sentence substitutions for closed-loop twin synthesis
TWIN_VARIATION_MAP: dict[str, list[dict[str, Any]]] = {
    "g12.l1.vocab.appreciation": [
        {
            "stem": "We must show gratitude and appreciation to our parents for their devotion.",
            "ans": "appreciation",
        },
        {
            "stem": "Many young volunteers visit the elderly who live in the nursing home.",
            "ans": "elderly",
        },
    ],
    "g12.l2.vocab.dictionaries": [
        {
            "stem": "If you do not know the exact definition of this word, look it up in your dictionary.",
            "ans": "definition",
        },
        {
            "stem": "Each dictionary entry gives the correct pronunciation and part of speech of the word.",
            "ans": "entry",
        },
    ],
    "g12.l3.vocab.renewable_energy": [
        {
            "stem": "Solar panels convert clean sunlight into electricity without air pollution.",
            "ans": "electricity",
        },
        {
            "stem": "Clean wind power can replace dangerous fossil fuels to protect our environment.",
            "ans": "replace",
        },
    ],
    "g12.l1.grammar.passive_voice": [
        {
            "stem": "The modern hospital .......... two years ago by generous volunteers.",
            "options": ["a) was built", "b) is built", "c) built", "d) has built"],
            "ans": "a) was built",
            "distractor": "Option c omits passive auxiliary was; option b uses wrong present tense.",
        },
        {
            "stem": "The new library .......... last month to help school students.",
            "options": ["a) was opened", "b) is opened", "c) opened", "d) has opened"],
            "ans": "a) was opened",
            "distractor": "Option c omits passive auxiliary was.",
        },
    ],
    "g12.l1.grammar.tag_questions": [
        {
            "stem": "Mina is helping her grandparents at home, ..........?",
            "options": ["a) isn't she", "b) is she", "c) doesn't she", "d) does she"],
            "ans": "a) isn't she",
            "distractor": "Option b fails opposite polarity; option c uses wrong auxiliary verb.",
        },
        {
            "stem": "The children were very polite yesterday, ..........?",
            "options": [
                "a) weren't they",
                "b) were they",
                "c) didn't they",
                "d) did they",
            ],
            "ans": "a) weren't they",
            "distractor": "Option b fails opposite polarity rule.",
        },
    ],
    "g12.l1.grammar.compound_sentences": [
        {
            "stem": "Reza studied hard for the English exam, .......... he got a great mark.",
            "options": ["a) so", "b) but", "c) or", "d) because"],
            "ans": "a) so",
            "distractor": "Tests coordinating conjunction result relationship.",
        },
    ],
    "g12.l2.grammar.conditional_type_2": [
        {
            "stem": "If we lived near the city center, we .......... visit that library often.",
            "options": ["a) would", "b) will", "c) had", "d) are"],
            "ans": "a) would",
            "distractor": "Tests conditional type 2 hypothetical would auxiliary.",
        },
    ],
    "g12.l2.grammar.relative_clauses": [
        {
            "stem": "I know a generous doctor. He helps poor elderly patients for free.",
            "ans": "I know a generous doctor who helps poor elderly patients for free.",
        },
    ],
    "g12.l3.grammar.past_perfect": [
        {
            "stem": "By the time the bell rang, the students .......... their classroom.",
            "options": ["a) had cleaned", "b) have cleaned", "c) clean", "d) cleaned"],
            "ans": "a) had cleaned",
            "distractor": "Tests past perfect sequence before another past action.",
        },
    ],
}


def synthesize_twin_item(
    conn: DbTarget,
    base_item_id: str,
    variation_index: int = 0,
) -> dict[str, Any] | None:
    with session_scope(conn) as session:
        base_item = session.get(ExamQuestionItem, base_item_id)
        if not base_item:
            return None

        concept_ids: list[str] = []
        if base_item.concept_ids_json:
            try:
                concept_ids = json.loads(base_item.concept_ids_json)
            except Exception:
                pass

        primary_concept = (
            concept_ids[0] if concept_ids else "g12.l1.grammar.passive_voice"
        )
        twin_id = f"twin_{base_item.id}_{uuid.uuid4().hex[:6]}"

        variations = TWIN_VARIATION_MAP.get(primary_concept, [])
        if variations:
            var_data = variations[variation_index % len(variations)]
            twin_stem = var_data["stem"]
            twin_ans = var_data["ans"]
            twin_options = (
                json.dumps(var_data["options"])
                if "options" in var_data and var_data["options"] is not None
                else (
                    base_item.options_json if base_item.options_json != "None" else None
                )
            )
            twin_distractor = var_data.get("distractor", base_item.distractor_analysis)
        else:
            # Parallel fallback variation: replace nouns while preserving syntax
            twin_stem = base_item.stem_text.replace("palace", "hospital").replace(
                "bridge", "library"
            )
            twin_ans = base_item.canonical_answer
            twin_options = (
                base_item.options_json if base_item.options_json != "None" else None
            )
            twin_distractor = base_item.distractor_analysis

        twin_item = ExamQuestionItem(
            id=twin_id,
            paper_id=base_item.paper_id,
            section_code=base_item.section_code,
            item_type=base_item.item_type,
            grade=base_item.grade,
            lesson_num=base_item.lesson_num,
            bloom_level=base_item.bloom_level,
            difficulty=base_item.difficulty,
            points=base_item.points,
            instruction_en=base_item.instruction_en,
            stem_text=twin_stem,
            passage_text=base_item.passage_text,
            options_json=twin_options,
            canonical_answer=twin_ans,
            acceptable_variants_json=base_item.acceptable_variants_json,
            rubric_breakdown_json=base_item.rubric_breakdown_json,
            distractor_analysis=twin_distractor,
            concept_ids_json=base_item.concept_ids_json,
            embedding_json=None,
            is_synthetic_twin=True,
            parent_item_id=base_item.id,
        )

        rep = verify_item(conn, twin_item)
        twin_dict = {
            "id": twin_item.id,
            "parent_item_id": base_item.id,
            "section_code": twin_item.section_code,
            "item_type": twin_item.item_type,
            "grade": twin_item.grade,
            "lesson_num": twin_item.lesson_num,
            "bloom_level": twin_item.bloom_level,
            "difficulty": twin_item.difficulty,
            "points": float(twin_item.points),
            "instruction_en": twin_item.instruction_en,
            "stem_text": twin_item.stem_text,
            "passage_text": twin_item.passage_text,
            "options_json": twin_item.options_json,
            "canonical_answer": twin_item.canonical_answer,
            "rubric_breakdown_json": twin_item.rubric_breakdown_json,
            "distractor_analysis": twin_item.distractor_analysis,
            "concept_ids": concept_ids,
            "is_synthetic_twin": True,
            "is_valid": rep["is_valid"],
            "validation_errors": rep["errors"],
        }
        return twin_dict
