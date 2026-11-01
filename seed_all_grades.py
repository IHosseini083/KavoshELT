from __future__ import annotations

import glob
import json
import os
from typing import Set, Tuple

from sqlalchemy import delete, text
from models import (
    ConceptEdge,
    ConceptNode,
    DbTarget,
    ExamQuestionItem,
    L1ErrorPattern,
    Lesson,
    NationalExamPaper,
    Passage,
    Rubric,
    Vocabulary,
    session_scope,
)
from rag import compute_embedding
from schema import init_db
from seed_vision1 import PROSPECT_BASE_LEMMAS

DEFAULT_DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "curriculum.db")


def seed_curriculum(target: DbTarget, datasets_dir: str = DEFAULT_DATASETS_DIR) -> None:
    with session_scope(target) as session:
        session.execute(delete(ExamQuestionItem))
        session.execute(delete(NationalExamPaper))
        session.execute(delete(L1ErrorPattern))
        session.execute(delete(ConceptEdge))
        session.execute(delete(ConceptNode))
        session.execute(delete(Passage))
        session.execute(delete(Vocabulary))
        session.execute(delete(Lesson))
        session.execute(delete(Rubric))
        session.execute(text("DELETE FROM passages_fts"))
        session.execute(text("DELETE FROM exam_items_fts"))

        seen_vocab: Set[Tuple[str, int, int]] = set()

        for word in PROSPECT_BASE_LEMMAS:
            key = (word.lower(), 6, 0)
            if key in seen_vocab:
                continue
            seen_vocab.add(key)
            session.add(
                Vocabulary(
                    word=word,
                    lemma=word,
                    pos="base",
                    grade=6,
                    lesson_num=0,
                    definition_fa="واژگان پایه مشترک",
                    example_en=f"This is {word}.",
                    embedding_json=None,
                )
            )

        json_files = sorted(glob.glob(os.path.join(datasets_dir, "grade*.json")))
        for jf in json_files:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)

            grade = int(data["grade"])

            for l_item in data.get("lessons", []):
                session.add(
                    Lesson(
                        grade=grade,
                        lesson_num=int(l_item["lesson_num"]),
                        title=str(l_item["title"]),
                        theme=str(l_item["theme"]),
                        allowed_grammar=json.dumps(l_item["allowed_grammar"]),
                        forbidden_grammar=json.dumps(l_item["forbidden_grammar"]),
                    )
                )

            for v_item in data.get("vocabulary", []):
                w_str, l_str, pos_str, l_num, def_fa, ex_en = (
                    str(v_item[0]),
                    str(v_item[1]),
                    str(v_item[2]),
                    int(v_item[3]),
                    str(v_item[4]),
                    str(v_item[5]),
                )
                key = (l_str.lower(), grade, l_num)
                if key in seen_vocab:
                    continue
                seen_vocab.add(key)
                vec = compute_embedding(f"{w_str} {l_str} {def_fa} {ex_en}")
                session.add(
                    Vocabulary(
                        word=w_str,
                        lemma=l_str,
                        pos=pos_str,
                        grade=grade,
                        lesson_num=l_num,
                        definition_fa=def_fa,
                        example_en=ex_en,
                        embedding_json=json.dumps(vec),
                    )
                )

            for p_item in data.get("passages", []):
                l_num = int(p_item["lesson_num"])
                sec_type = str(p_item["section_type"])
                title = str(p_item["title"])
                content = str(p_item["content"])
                vec = compute_embedding(f"{title} {content}")
                session.add(
                    Passage(
                        grade=grade,
                        lesson_num=l_num,
                        section_type=sec_type,
                        title=title,
                        content=content,
                        embedding_json=json.dumps(vec),
                    )
                )
                session.execute(
                    text(
                        "INSERT INTO passages_fts (grade, lesson_num, section_type, title, content) VALUES (:g, :l, :s, :t, :c)"
                    ),
                    {
                        "g": str(grade),
                        "l": l_num,
                        "s": sec_type,
                        "t": title,
                        "c": content,
                    },
                )

            for r_item in data.get("rubrics", []):
                session.add(
                    Rubric(
                        id=str(r_item["id"]),
                        grade=grade,
                        term=int(r_item["term"]),
                        exam_type=str(r_item["exam_type"]),
                        total_points=float(r_item["total_points"]),
                        structure_json=json.dumps(r_item["structure"]),
                    )
                )

        # Seed Pedagogical Knowledge Graph
        graph_file = os.path.join(datasets_dir, "concept_graph_grade12.json")
        if os.path.exists(graph_file):
            with open(graph_file, "r", encoding="utf-8") as f:
                gdata = json.load(f)

            for n in gdata.get("nodes", []):
                vec = compute_embedding(
                    f"{n['title_en']} {n['title_fa']} {n['description']}"
                )
                session.add(
                    ConceptNode(
                        id=str(n["id"]),
                        grade=int(n["grade"]),
                        lesson_num=int(n["lesson_num"]),
                        category=str(n["category"]),
                        title_en=str(n["title_en"]),
                        title_fa=str(n["title_fa"]),
                        description=str(n["description"]),
                        embedding_json=json.dumps(vec),
                    )
                )
            session.flush()

            for e in gdata.get("edges", []):
                session.add(
                    ConceptEdge(
                        source_id=str(e["source_id"]),
                        target_id=str(e["target_id"]),
                        relation_type=str(e["relation_type"]),
                        weight=float(e.get("weight", 1.0)),
                        notes=str(e.get("notes", "")),
                    )
                )

            for lp in gdata.get("l1_patterns", []):
                session.add(
                    L1ErrorPattern(
                        id=str(lp["id"]),
                        concept_id=str(lp["concept_id"]),
                        error_title_fa=str(lp["error_title_fa"]),
                        incorrect_pattern_en=str(lp["incorrect_pattern_en"]),
                        correct_pattern_en=str(lp["correct_pattern_en"]),
                        l1_root_cause_fa=str(lp["l1_root_cause_fa"]),
                        remedial_drill_template=str(lp["remedial_drill_template"]),
                    )
                )

        # Seed National Exams Bank
        exams_file = os.path.join(datasets_dir, "national_exams_grade12_1397_1405.json")
        if os.path.exists(exams_file):
            with open(exams_file, "r", encoding="utf-8") as f:
                edata = json.load(f)

            for p in edata.get("papers", []):
                session.add(
                    NationalExamPaper(
                        id=str(p["id"]),
                        grade=int(p["grade"]),
                        shamsi_year=int(p["shamsi_year"]),
                        session=str(p["session"]),
                        total_written_points=float(p["total_written_points"]),
                        blueprint_version=str(p["blueprint_version"]),
                        source_origin=str(p.get("source_origin", "Markaz-e-Sanjesh")),
                        is_verified=bool(p.get("is_verified", True)),
                    )
                )
            session.flush()

            for it in edata.get("items", []):
                vec = compute_embedding(f"{it['stem_text']} {it['canonical_answer']}")
                session.add(
                    ExamQuestionItem(
                        id=str(it["id"]),
                        paper_id=str(it["paper_id"]),
                        section_code=str(it["section_code"]),
                        item_type=str(it["item_type"]),
                        grade=int(it["grade"]),
                        lesson_num=int(it["lesson_num"]),
                        bloom_level=str(it.get("bloom_level", "apply")),
                        difficulty=str(it.get("difficulty", "medium")),
                        points=float(it["points"]),
                        instruction_en=str(it["instruction_en"]),
                        stem_text=str(it["stem_text"]),
                        passage_text=str(it.get("passage_text", "")) or None,
                        options_json=str(it.get("options_json", "")) or None,
                        canonical_answer=str(it["canonical_answer"]),
                        acceptable_variants_json=str(
                            it.get("acceptable_variants_json", "[]")
                        ),
                        rubric_breakdown_json=str(
                            it.get("rubric_breakdown_json", "{}")
                        ),
                        distractor_analysis=str(it.get("distractor_analysis", ""))
                        or None,
                        concept_ids_json=str(it.get("concept_ids_json", "[]")),
                        embedding_json=json.dumps(vec),
                        is_synthetic_twin=bool(it.get("is_synthetic_twin", False)),
                        parent_item_id=str(it.get("parent_item_id", "")) or None,
                    )
                )
                session.execute(
                    text(
                        """
                        INSERT INTO exam_items_fts (item_id, paper_id, section_code, stem_text, canonical_answer, concept_keywords)
                        VALUES (:iid, :pid, :sec, :stem, :ans, :kw)
                        """
                    ),
                    {
                        "iid": str(it["id"]),
                        "pid": str(it["paper_id"]),
                        "sec": str(it["section_code"]),
                        "stem": str(it["stem_text"]),
                        "ans": str(it["canonical_answer"]),
                        "kw": str(it.get("concept_ids_json", "")),
                    },
                )

        session.commit()


def build_database(db_path: str = DEFAULT_DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    init_db(db_path)
    seed_curriculum(db_path)
    print(f"Full 6-grade curriculum and national exams database seeded at: {db_path}")


if __name__ == "__main__":
    build_database()
