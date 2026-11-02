from __future__ import annotations

import re
from typing import Any

from sqlalchemy import and_, or_, select

from kavosh.models import DbTarget, Vocabulary, session_scope

COMMON_PROPER_NOUNS: frozenset[str] = frozenset(
    {
        "iran",
        "iranian",
        "tehran",
        "shiraz",
        "isfahan",
        "esfahan",
        "golestan",
        "persepolis",
        "hafez",
        "saadi",
        "gharib",
        "pasteur",
        "edison",
        "france",
        "paris",
        "saturn",
        "mars",
        "earth",
        "neptune",
        "mercury",
        "jupiter",
        "venus",
        "allah",
        "god",
        "amir",
        "maryam",
        "ali",
        "sina",
        "neda",
        "sara",
        "zahra",
        "mahdi",
        "farhad",
        "david",
        "kian",
        "mina",
        "tehrani",
        "karimi",
        "ahmadi",
        "nima",
        "omid",
        "samaneh",
        "reza",
        "rezaei",
        "moradi",
        "mehrad",
        "mohammad",
        "louis",
        "naqsh",
        "jahan",
        "square",
        "si",
        "o",
        "se",
        "pol",
        "persian",
        "e",
        "mr",
        "mrs",
        "ms",
        "dr",
        "sir",
        "germany",
        "german",
        "china",
        "chinese",
        "japan",
        "japanese",
        "spain",
        "spanish",
        "lalejin",
        "unesco",
        "babak",
        "razavi",
        "alireza",
        "nasir",
        "al",
        "din",
        "tusi",
        "maragheh",
        "diego",
        "chehel",
        "sotoun",
        "pasargadae",
        "yazd",
        "mashhad",
        "carlos",
        "hindi",
        "quran",
        "asadi",
        "hamid",
        "asia",
        "asian",
        "speaker",
        "fola",
        "rami",
        "vision",
        "prospect",
        "gemini",
        "tts",
        "ai",
        "studio",
        "audio",
        "track",
        "block",
        "part",
        "sec",
        "min",
    }
)

IRREGULAR_VERB_MAP: dict[str, str] = {
    "was": "be",
    "were": "be",
    "been": "be",
    "being": "be",
    "did": "do",
    "done": "do",
    "doing": "do",
    "had": "have",
    "having": "have",
    "went": "go",
    "gone": "go",
    "going": "go",
    "came": "come",
    "coming": "come",
    "saw": "see",
    "seen": "see",
    "seeing": "see",
    "took": "take",
    "taken": "take",
    "taking": "take",
    "made": "make",
    "making": "make",
    "built": "build",
    "building": "build",
    "found": "find",
    "finding": "find",
    "gave": "give",
    "given": "give",
    "giving": "give",
    "read": "read",
    "reading": "read",
    "wrote": "write",
    "written": "write",
    "writing": "write",
    "spoke": "speak",
    "spoken": "speak",
    "speaking": "speak",
    "heard": "hear",
    "hearing": "hear",
    "ran": "run",
    "running": "run",
    "ate": "eat",
    "eaten": "eat",
    "eating": "eat",
    "drank": "drink",
    "drunk": "drink",
    "drinking": "drink",
    "slept": "sleep",
    "sleeping": "sleep",
    "felt": "feel",
    "feeling": "feel",
    "chose": "choose",
    "chosen": "choose",
    "choosing": "choose",
    "met": "meet",
    "meeting": "meet",
    "taught": "teach",
    "teaching": "teach",
    "bought": "buy",
    "buying": "buy",
    "brought": "bring",
    "bringing": "bring",
    "paid": "pay",
    "paying": "pay",
    "got": "get",
    "getting": "get",
    "kept": "keep",
    "keeping": "keep",
    "held": "hold",
    "holding": "hold",
    "began": "begin",
    "begun": "begin",
    "beginning": "begin",
    "knew": "know",
    "known": "know",
    "knowing": "know",
    "grew": "grow",
    "grown": "grow",
    "growing": "grow",
    "born": "bear",
    "borne": "bear",
    "children": "child",
    "men": "man",
    "women": "woman",
    "feet": "foot",
    "teeth": "tooth",
    "better": "good",
    "best": "good",
    "worse": "bad",
    "worst": "bad",
    "became": "become",
    "becoming": "become",
    "wove": "weave",
    "woven": "weave",
    "weaving": "weave",
    "craftspeople": "craftsperson",
    "people": "person",
}

CONTRACTION_MAP: dict[str, str] = {
    "aren't": "be",
    "isn't": "be",
    "wasn't": "be",
    "weren't": "be",
    "don't": "do",
    "doesn't": "do",
    "didn't": "do",
    "haven't": "have",
    "hasn't": "have",
    "hadn't": "have",
    "won't": "will",
    "can't": "can",
    "cannot": "can",
    "couldn't": "could",
    "shouldn't": "should",
    "mustn't": "must",
}

STOP_CONTRACTIONS: frozenset[str] = frozenset(
    {"'s", "'re", "'m", "'ve", "'ll", "'d", "n't", "s", "d", "t"}
)

_RE_PRESENT_PERF = re.compile(
    r"\b(have|has|haven't|hasn't)\s+(\w+ed|\w+en|been|seen|done|gone|taken|written|visited|found|built|made|lived|worked|dedicated)\b",
    re.IGNORECASE,
)
_RE_PAST_PROG = re.compile(
    r"\b(was|were|wasn't|weren't)\s+(\w+ing)\b",
    re.IGNORECASE,
)
_RE_PASSIVE = re.compile(
    r"\b(is|are|was|were|be|been|being)\s+(\w+ed|\w+en|built|made|done|seen|taken|found|developed)\s+by\b|\b(is|are|was|were)\s+being\s+\w+",
    re.IGNORECASE,
)
_RE_COND2 = re.compile(r"\bif\b[^\.\?!;]+?\bwould\b", re.IGNORECASE)

_RE_CODE_FENCE = re.compile(r"```[a-zA-Z]*")
_RE_TAG = re.compile(r"<[^>]+>")
_RE_BRACKET = re.compile(r"\[[^\]]+\]")
_RE_PERSIAN = re.compile(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]")
_RE_MARKDOWN_SYM = re.compile(r"[*#_`|~=>\-]")
_RE_TOKENIZE = re.compile(r"\b[A-Za-z]+(?:'[A-Za-z]+)?\b")
_RE_POSSESSIVE_S = re.compile(r"'s$")


def get_allowed_vocabulary(
    conn: DbTarget, max_grade: int = 10, max_lesson: int = 4
) -> set[str]:
    with session_scope(conn) as session:
        stmt = select(Vocabulary.lemma, Vocabulary.word).where(
            or_(
                Vocabulary.grade < max_grade,
                and_(
                    Vocabulary.grade == max_grade, Vocabulary.lesson_num <= max_lesson
                ),
            )
        )
        rows = session.execute(stmt).all()

    allowed: set[str] = set(COMMON_PROPER_NOUNS)
    for lemma_val, word_val in rows:
        if lemma_val:
            s_lemma = str(lemma_val).lower().strip()
            allowed.add(s_lemma)
            if " " in s_lemma:
                allowed.update(s_lemma.split())
        if word_val:
            s_word = str(word_val).lower().strip()
            allowed.add(s_word)
            if " " in s_word:
                allowed.update(s_word.split())

    return allowed


def lemmatize_word(word: str, allowed_set: set[str]) -> bool:
    w = word.lower().strip()
    if not w or w.isdigit():
        return True

    if w in allowed_set or w in COMMON_PROPER_NOUNS:
        return True

    if w in CONTRACTION_MAP and CONTRACTION_MAP[w] in allowed_set:
        return True

    if w in IRREGULAR_VERB_MAP and IRREGULAR_VERB_MAP[w] in allowed_set:
        return True

    candidates: list[str] = []

    if w.endswith("ing"):
        base = w[:-3]
        candidates.extend([base, base + "e"])
        if w.endswith("ying"):
            candidates.append(w[:-4] + "ie")
        if len(base) > 2 and base[-1] == base[-2]:
            candidates.append(base[:-1])
    elif w.endswith("ed"):
        base = w[:-2]
        candidates.extend([base, base + "e", w[:-1]])
        if w.endswith("ied"):
            candidates.append(w[:-3] + "y")
        if len(base) > 2 and base[-1] == base[-2]:
            candidates.append(base[:-1])
    elif w.endswith("s"):
        if w.endswith("ies"):
            candidates.append(w[:-3] + "y")
        if w.endswith("es"):
            candidates.extend([w[:-2], w[:-1]])
        candidates.append(w[:-1])
        base_s = w[:-1]
        if base_s.endswith("er"):
            candidates.extend([base_s[:-2], base_s[:-1]])
            if len(base_s) > 4 and base_s[-3] == base_s[-4]:
                candidates.append(base_s[:-3])
    elif w.endswith("er"):
        candidates.extend([w[:-2], w[:-1]])
        if len(w) > 4 and w[-3] == w[-4]:
            candidates.append(w[:-3])
    elif w.endswith("est"):
        candidates.extend([w[:-3], w[:-2]])
        if len(w) > 5 and w[-4] == w[-5]:
            candidates.append(w[:-4])
    elif w.endswith("ly"):
        candidates.extend([w[:-2], w[:-2] + "e", w[:-1]])
        if w.endswith("ily"):
            candidates.append(w[:-3] + "y")

    for cand in candidates:
        if cand in allowed_set or (
            cand in IRREGULAR_VERB_MAP and IRREGULAR_VERB_MAP[cand] in allowed_set
        ):
            return True

    return False


def check_grammar_bounds(
    text: str, max_grade: int, max_lesson: int
) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    clean_text = text.replace("\n", " ")

    if max_grade < 11:
        for match in _RE_PRESENT_PERF.finditer(clean_text):
            hits.append(
                {
                    "type": "present_perfect",
                    "match": match.group(0),
                    "reason": f"Present Perfect is forbidden in Grade {max_grade} (introduced in Grade 11 Vision 2).",
                }
            )

    if max_grade < 10 or (max_grade == 10 and max_lesson < 3):
        for match in _RE_PAST_PROG.finditer(clean_text):
            hits.append(
                {
                    "type": "past_progressive",
                    "match": match.group(0),
                    "reason": "Past Progressive is forbidden before Grade 10 Lesson 3.",
                }
            )

    if max_grade < 12:
        for match in _RE_PASSIVE.finditer(clean_text):
            hits.append(
                {
                    "type": "passive_voice",
                    "match": match.group(0),
                    "reason": f"Passive Voice is forbidden in Grade {max_grade} (introduced in Grade 12 Vision 3).",
                }
            )

    if max_grade < 12 or (max_grade == 12 and max_lesson < 2):
        for match in _RE_COND2.finditer(clean_text):
            hits.append(
                {
                    "type": "conditional_type_2",
                    "match": match.group(0),
                    "reason": "Conditional Type 2 is forbidden before Grade 12 Lesson 2.",
                }
            )

    return hits


def clean_markdown_and_metadata(text: str) -> str:
    t = _RE_CODE_FENCE.sub("", text)
    t = _RE_TAG.sub(" ", t)
    t = _RE_BRACKET.sub(" ", t)
    t = _RE_PERSIAN.sub(" ", t)
    return _RE_MARKDOWN_SYM.sub(" ", t)


def validate_exam_text(
    conn: DbTarget, max_grade: int, max_lesson: int, text: str
) -> dict[str, Any]:
    allowed_vocab = get_allowed_vocabulary(conn, max_grade, max_lesson)
    cleaned_text = clean_markdown_and_metadata(text)
    raw_tokens = _RE_TOKENIZE.findall(cleaned_text)

    out_of_syllabus: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        clean_tok = _RE_POSSESSIVE_S.sub("", token.lower()).strip("'")
        if not clean_tok or clean_tok in STOP_CONTRACTIONS or clean_tok.isdigit():
            continue
        if not lemmatize_word(clean_tok, allowed_vocab) and clean_tok not in seen:
            seen.add(clean_tok)
            out_of_syllabus.append(clean_tok)

    grammar_hits = check_grammar_bounds(text, max_grade, max_lesson)
    is_valid = (len(out_of_syllabus) == 0) and (len(grammar_hits) == 0)

    return {
        "is_valid": is_valid,
        "max_grade": max_grade,
        "max_lesson": max_lesson,
        "out_of_syllabus_words": out_of_syllabus,
        "forbidden_grammar_hits": grammar_hits,
        "word_count": len(raw_tokens),
    }
