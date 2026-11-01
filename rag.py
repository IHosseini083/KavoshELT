from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import and_, or_, select, text
from models import DbTarget, Lesson, Passage, Vocabulary, session_scope

EMBEDDING_DIM = 64

# 16 semantic concept clusters covering the 6-grade Iranian English syllabus
SEMANTIC_CLUSTERS: List[Tuple[str, ...]] = [
    ("nature", "wildlife", "animal", "cheetah", "endangered", "forest", "plain", "hunt", "hunter", "protect", "save", "habitat", "earth", "tree", "plant", "panda", "whale", "wolf", "leopard", "alive", "die"),
    ("body", "heart", "blood", "cell", "vessel", "oxygen", "pump", "organ", "brain", "microbe", "defend", "healthy", "health", "exercise", "pain", "fever", "headache", "sick", "illness", "disease", "cure", "patient", "hospital", "doctor", "nurse", "medicine"),
    ("planet", "star", "moon", "sun", "sky", "space", "solar", "telescope", "observatory", "ring", "saturn", "mars", "wonder", "creation", "distance", "far", "near"),
    ("scientist", "knowledge", "inventor", "physician", "laboratory", "experiment", "discover", "vaccine", "research", "success", "successful", "famous", "invent", "pediatrics", "tirelessly", "study", "learn"),
    ("travel", "tourist", "tourism", "trip", "vacation", "destination", "hotel", "receptionist", "passport", "ticket", "train", "plane", "airport", "bag", "pack", "historical", "ancient", "monument", "pilgrim", "shrine", "mosque", "tomb", "bazaar", "souvenir"),
    ("art", "culture", "handicraft", "handmade", "carpet", "rug", "tile", "pottery", "calligraphy", "poet", "poetry", "heritage", "custom", "festival", "ceremony", "nowruz", "yalda", "fireworks", "gift"),
    ("family", "father", "mother", "brother", "sister", "grandfather", "grandmother", "uncle", "aunt", "child", "children", "son", "daughter", "parent", "elder", "appreciation", "respect", "kind", "generous", "patient", "brave", "talkative", "quiet", "neat", "messy"),
    ("school", "class", "classmate", "teacher", "student", "friend", "book", "read", "write", "dictionary", "word", "language", "english", "deaf", "sign", "communicate", "communication", "understand", "look", "entry"),
    ("energy", "renewable", "solar", "wind", "water", "power", "electricity", "clean", "pollution", "environment", "coal", "oil", "fossil", "fuel", "replace", "reduce", "tide"),
    ("food", "meal", "lunch", "dinner", "breakfast", "bread", "rice", "meat", "milk", "tea", "water", "drink", "fruit", "vegetable", "diet", "nutrition", "cook", "bake", "hungry", "thirsty", "delicious"),
    ("city", "village", "town", "country", "nationality", "street", "road", "bridge", "park", "bank", "post", "police", "fire", "station", "service", "house", "home", "room", "kitchen"),
    ("time", "day", "week", "month", "year", "morning", "afternoon", "evening", "night", "today", "tomorrow", "yesterday", "schedule", "weekend", "holiday", "age", "birthday"),
    ("job", "work", "engineer", "pilot", "dentist", "driver", "farmer", "firefighter", "ranger", "worker", "office", "shop", "market", "buy", "sell", "pay", "money", "exchange"),
    ("hobby", "sport", "play", "run", "swim", "walk", "ride", "watch", "movie", "media", "internet", "computer", "phone", "number", "news", "newspaper"),
    ("ability", "can", "skill", "fast", "slow", "strong", "powerful", "big", "small", "tiny", "huge", "tall", "short", "young", "old", "new"),
    ("lifestyle", "habit", "stress", "sleep", "rest", "active", "calm", "happy", "glad", "angry", "careful", "careless", "danger", "safe", "accident", "injure", "injury", "help"),
]


def _normalize_tokens(text_str: str) -> List[str]:
    raw = re.findall(r"[a-zA-Z\u0600-\u06FF]+", text_str.lower())
    out: List[str] = []
    for tok in raw:
        out.append(tok)
        if len(tok) > 4 and tok.endswith("ing"):
            out.append(tok[:-3])
        elif len(tok) > 3 and tok.endswith("ed"):
            out.append(tok[:-2])
        elif len(tok) > 3 and tok.endswith("es"):
            out.append(tok[:-2])
        elif len(tok) > 3 and tok.endswith("s"):
            out.append(tok[:-1])
    return out


def compute_embedding(text_str: str) -> List[float]:
    vec = [0.0] * EMBEDDING_DIM
    tokens = _normalize_tokens(text_str)
    if not tokens:
        return vec

    token_set = set(tokens)

    # Dimensions 0..15: Semantic concept clusters
    for idx, cluster in enumerate(SEMANTIC_CLUSTERS):
        matches = sum(1 for word in cluster if word in token_set)
        if matches > 0:
            vec[idx] = float(matches) * 2.5

    # Dimensions 16..63: Hashed token + character 3-gram projections
    remaining_dims = EMBEDDING_DIM - 16
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16)
        bucket = 16 + (h % remaining_dims)
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[bucket] += sign * 1.5

        if len(tok) >= 3:
            for i in range(len(tok) - 2):
                trigram = tok[i : i + 3]
                th = int(hashlib.md5(trigram.encode("utf-8")).hexdigest()[:8], 16)
                tbucket = 16 + (th % remaining_dims)
                tsign = 1.0 if ((th >> 8) & 1) == 0 else -1.0
                vec[tbucket] += tsign * 0.4

    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 1e-9:
        vec = [round(x / norm, 6) for x in vec]
    return vec


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return float(dot / (norm_a * norm_b))


def hybrid_search_passages(
    target: DbTarget,
    query: str,
    max_grade: int = 12,
    max_lesson: int = 8,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    query_vec = compute_embedding(query)
    query_terms = [t for t in _normalize_tokens(query) if len(t) > 2]

    with session_scope(target) as session:
        # 1. Fetch all in-syllabus passages via SQLAlchemy 2.0 ORM
        stmt = select(Passage).where(
            or_(
                Passage.grade < max_grade,
                and_(Passage.grade == max_grade, Passage.lesson_num <= max_lesson),
            )
        )
        in_scope_passages = list(session.scalars(stmt).all())

        # 2. Check FTS5 lexical matches
        fts_Hits: Dict[Tuple[int, int, str], float] = {}
        if query_terms:
            fts_query = " OR ".join(f'"{t}"' for t in query_terms[:8])
            try:
                rows = session.execute(
                    text(
                        """
                        SELECT CAST(grade AS INTEGER), CAST(lesson_num AS INTEGER), title, bm25(passages_fts)
                        FROM passages_fts
                        WHERE passages_fts MATCH :q
                        """
                    ),
                    {"q": fts_query},
                ).fetchall()
                for rank_idx, r in enumerate(rows):
                    g_val, l_val, title_val = int(r[0]), int(r[1]), str(r[2])
                    if g_val < max_grade or (g_val == max_grade and l_val <= max_lesson):
                        fts_Hits[(g_val, l_val, title_val)] = 1.0 / (rank_idx + 1.0)
            except Exception:
                pass

        scored_results: List[Dict[str, Any]] = []
        for p in in_scope_passages:
            p_vec: List[float]
            if p.embedding_json:
                p_vec = json.loads(p.embedding_json)
            else:
                p_vec = compute_embedding(f"{p.title} {p.content}")

            sem_score = max(0.0, cosine_similarity(query_vec, p_vec))
            lex_score = fts_Hits.get((p.grade, p.lesson_num, p.title), 0.0)

            # Direct term overlap boost
            content_lower = f"{p.title} {p.content}".lower()
            overlap = sum(1 for t in set(query_terms) if t in content_lower)
            overlap_score = min(1.0, overlap * 0.25)

            hybrid_score = round(0.55 * sem_score + 0.30 * lex_score + 0.15 * overlap_score, 4)
            scored_results.append(
                {
                    "grade": p.grade,
                    "lesson_num": p.lesson_num,
                    "section_type": p.section_type,
                    "title": p.title,
                    "content": p.content,
                    "semantic_score": round(sem_score, 4),
                    "lexical_score": round(lex_score, 4),
                    "hybrid_score": hybrid_score,
                }
            )

        scored_results.sort(key=lambda item: item["hybrid_score"], reverse=True)
        return scored_results[:top_k]


def hybrid_search_vocabulary(
    target: DbTarget,
    query: str,
    max_grade: int = 12,
    max_lesson: int = 8,
    top_k: int = 15,
) -> List[Dict[str, Any]]:
    query_vec = compute_embedding(query)
    query_terms = set(_normalize_tokens(query))

    with session_scope(target) as session:
        stmt = select(Vocabulary).where(
            and_(
                Vocabulary.lesson_num > 0,
                or_(
                    Vocabulary.grade < max_grade,
                    and_(Vocabulary.grade == max_grade, Vocabulary.lesson_num <= max_lesson),
                ),
            )
        )
        vocab_items = list(session.scalars(stmt).all())

        scored: List[Dict[str, Any]] = []
        for v in vocab_items:
            v_vec: List[float]
            if v.embedding_json:
                v_vec = json.loads(v.embedding_json)
            else:
                v_vec = compute_embedding(f"{v.word} {v.lemma} {v.definition_fa or ''} {v.example_en or ''}")

            sem_score = max(0.0, cosine_similarity(query_vec, v_vec))
            v_text = f"{v.word} {v.lemma} {v.definition_fa or ''} {v.example_en or ''}".lower()
            exact_boost = 0.4 if any(qt in v_text for qt in query_terms) else 0.0
            total_score = round(0.7 * sem_score + exact_boost, 4)

            scored.append(
                {
                    "word": v.word,
                    "lemma": v.lemma,
                    "pos": v.pos,
                    "grade": v.grade,
                    "lesson_num": v.lesson_num,
                    "definition_fa": v.definition_fa,
                    "example_en": v.example_en,
                    "score": total_score,
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]


def retrieve_rag_context(
    target: DbTarget,
    query: str,
    max_grade: int = 10,
    max_lesson: int = 4,
    top_k_passages: int = 3,
    top_k_vocab: int = 15,
) -> Dict[str, Any]:
    passages = hybrid_search_passages(target, query, max_grade=max_grade, max_lesson=max_lesson, top_k=top_k_passages)
    vocab = hybrid_search_vocabulary(target, query, max_grade=max_grade, max_lesson=max_lesson, top_k=top_k_vocab)

    with session_scope(target) as session:
        stmt = (
            select(Lesson)
            .where(
                and_(
                    Lesson.grade == max_grade,
                    Lesson.lesson_num <= max_lesson,
                )
            )
            .order_by(Lesson.lesson_num.asc())
        )
        lessons = list(session.scalars(stmt).all())
        grammar_rules = [
            {
                "lesson_num": l.lesson_num,
                "title": l.title,
                "allowed_grammar": json.loads(l.allowed_grammar),
                "forbidden_grammar": json.loads(l.forbidden_grammar),
            }
            for l in lessons
        ]

    vocab_list_str = ", ".join(f"{v['word']} ({v['pos']})" for v in vocab)
    passages_str = "\n\n".join(
        f"[Grade {p['grade']} Lesson {p['lesson_num']} - {p['title']}]\n{p['content']}"
        for p in passages
    )
    prompt_context = (
        f"SYLLABUS BOUNDARY: Maximum Grade {max_grade}, Lesson {max_lesson}\n"
        f"QUERY TOPIC: {query}\n"
        f"RELEVANT IN-SYLLABUS VOCABULARY: {vocab_list_str}\n\n"
        f"GROUND-TRUTH TEXTBOOK PASSAGES:\n{passages_str}"
    )

    return {
        "query": query,
        "syllabus_boundary": {"max_grade": max_grade, "max_lesson": max_lesson},
        "retrieved_passages": passages,
        "retrieved_vocabulary": vocab,
        "grammar_constraints": grammar_rules,
        "prompt_context": prompt_context,
    }
