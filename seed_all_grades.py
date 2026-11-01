from __future__ import annotations

import glob
import json
import os
from typing import Set, Tuple

from sqlalchemy import delete, text
from models import DbTarget, Lesson, Passage, Rubric, Vocabulary, session_scope
from rag import compute_embedding
from schema import init_db
from seed_vision1 import PROSPECT_BASE_LEMMAS

DEFAULT_DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "curriculum.db")


def seed_curriculum(target: DbTarget, datasets_dir: str = DEFAULT_DATASETS_DIR) -> None:
    with session_scope(target) as session:
        session.execute(delete(Passage))
        session.execute(delete(Vocabulary))
        session.execute(delete(Lesson))
        session.execute(delete(Rubric))
        session.execute(text("DELETE FROM passages_fts"))

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
                    {"g": str(grade), "l": l_num, "s": sec_type, "t": title, "c": content},
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

        session.commit()


def build_database(db_path: str = DEFAULT_DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    init_db(db_path)
    seed_curriculum(db_path)
    print(f"Full 6-grade curriculum database seeded at: {db_path}")


if __name__ == "__main__":
    build_database()
