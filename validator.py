from __future__ import annotations

import re
from typing import Any

from sqlalchemy import and_, or_, select

from models import DbTarget, Vocabulary, session_scope

COMMON_PROPER_NOUNS = {
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
    # Platform & exam template labels
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

IRREGULAR_VERB_MAP = {
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
}

CONTRACTION_MAP = {
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

STOP_CONTRACTIONS = {"'s", "'re", "'m", "'ve", "'ll", "'d", "n't", "s", "d", "t"}


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

    allowed: set[str] = set()
    for lemma_val, word_val in rows:
        if lemma_val:
            allowed.add(str(lemma_val).lower().strip())
        if word_val:
            allowed.add(str(word_val).lower().strip())

    extra: set[str] = set()
    for item in allowed:
        if " " in item:
            for part in item.split():
                extra.add(part)
    return allowed | extra | COMMON_PROPER_NOUNS


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

    # Suffix stripping attempts
    candidates = []

    # -ing
    if w.endswith("ing"):
        base = w[:-3]
        candidates.extend([base, base + "e"])
        if w.endswith("ying"):
            candidates.append(w[:-4] + "ie")
        if len(base) > 2 and base[-1] == base[-2]:
            candidates.append(base[:-1])

    # -ed
    elif w.endswith("ed"):
        base = w[:-2]
        candidates.extend([base, base + "e", w[:-1]])
        if w.endswith("ied"):
            candidates.append(w[:-3] + "y")
        if len(base) > 2 and base[-1] == base[-2]:
            candidates.append(base[:-1])

    # -s / -es / -ies
    elif w.endswith("s"):
        if w.endswith("ies"):
            candidates.append(w[:-3] + "y")
        if w.endswith("es"):
            candidates.extend([w[:-2], w[:-1]])
        candidates.append(w[:-1])
        # Multi-suffix check (e.g. workers -> worker -> work)
        base_s = w[:-1]
        if base_s.endswith("er"):
            candidates.extend([base_s[:-2], base_s[:-1]])
            if len(base_s) > 4 and base_s[-3] == base_s[-4]:
                candidates.append(base_s[:-3])

    # -er / -est
    elif w.endswith("er"):
        candidates.extend([w[:-2], w[:-1]])
        if len(w) > 4 and w[-3] == w[-4]:
            candidates.append(w[:-3])
    elif w.endswith("est"):
        candidates.extend([w[:-3], w[:-2]])
        if len(w) > 5 and w[-4] == w[-5]:
            candidates.append(w[:-4])

    # -ly
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
    hits = []
    clean_text = text.replace("\n", " ")

    # 1. Present Perfect (introduced in Grade 11 Vision 2 Lesson 1)
    if max_grade < 11:
        present_perf_regex = re.compile(
            r"\b(have|has|haven't|hasn't)\s+(\w+ed|\w+en|been|seen|done|gone|taken|written|visited|found|built|made|lived|worked|dedicated)\b",
            re.IGNORECASE,
        )
        for match in present_perf_regex.finditer(clean_text):
            hits.append(
                {
                    "type": "present_perfect",
                    "match": match.group(0),
                    "reason": f"Present Perfect is forbidden in Grade {max_grade} (introduced in Grade 11 Vision 2).",
                }
            )

    # 2. Past Progressive (was/were + ing) (introduced in Grade 10 Lesson 3)
    if max_grade < 10 or (max_grade == 10 and max_lesson < 3):
        past_prog_regex = re.compile(
            r"\b(was|were|wasn't|weren't)\s+(\w+ing)\b", re.IGNORECASE
        )
        for match in past_prog_regex.finditer(clean_text):
            hits.append(
                {
                    "type": "past_progressive",
                    "match": match.group(0),
                    "reason": "Past Progressive is forbidden before Grade 10 Lesson 3.",
                }
            )

    # 3. Passive Voice (introduced in Grade 12 Vision 3 Lesson 1)
    if max_grade < 12:
        passive_regex = re.compile(
            r"\b(is|are|was|were|be|been|being)\s+(\w+ed|\w+en|built|made|done|seen|taken|found|developed)\s+by\b|\b(is|are|was|were)\s+being\s+\w+",
            re.IGNORECASE,
        )
        for match in passive_regex.finditer(clean_text):
            hits.append(
                {
                    "type": "passive_voice",
                    "match": match.group(0),
                    "reason": f"Passive Voice is forbidden in Grade {max_grade} (introduced in Grade 12 Vision 3).",
                }
            )

    # 4. Second Conditionals (if + past, would) (introduced in Grade 12 Vision 3 Lesson 2)
    if max_grade < 12 or (max_grade == 12 and max_lesson < 2):
        cond2_regex = re.compile(r"\bif\b[^\.\?!;]+?\bwould\b", re.IGNORECASE)
        for match in cond2_regex.finditer(clean_text):
            hits.append(
                {
                    "type": "conditional_type_2",
                    "match": match.group(0),
                    "reason": "Conditional Type 2 is forbidden before Grade 12 Lesson 2.",
                }
            )

    return hits


def clean_markdown_and_metadata(text: str) -> str:
    # Remove markdown code block fences and language tags
    t = re.sub(r"```[a-zA-Z]*", "", text)
    # Remove inline audio/TTS metadata tags like <short pause>, <long pause>, <laugh>, [pause: ...]
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\[[^\]]+\]", " ", t)
    # Remove Persian characters so they don't produce false token splits
    t = re.sub(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]", " ", t)
    # Remove markdown formatting symbols
    t = re.sub(r"[*#_`|~=>\-]", " ", t)
    return t


def validate_exam_text(
    conn: DbTarget, max_grade: int, max_lesson: int, text: str
) -> dict[str, Any]:
    allowed_vocab = get_allowed_vocabulary(conn, max_grade, max_lesson)

    cleaned_text = clean_markdown_and_metadata(text)
    # Tokenize words
    raw_tokens = re.findall(r"\b[A-Za-z]+(?:'[A-Za-z]+)?\b", cleaned_text)

    out_of_syllabus = []
    seen = set()
    for token in raw_tokens:
        clean_tok = re.sub(r"'s$", "", token.lower()).strip("'")
        if not clean_tok or clean_tok in STOP_CONTRACTIONS or clean_tok.isdigit():
            continue
        if not lemmatize_word(clean_tok, allowed_vocab):
            if clean_tok not in seen:
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
