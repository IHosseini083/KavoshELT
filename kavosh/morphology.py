"""English inflection handling used to avoid false out-of-syllabus flags.

The syllabus vocabulary stores base forms (``protect``, ``child``).  Students are
expected to recognise regular and common irregular inflections of those words
(``protected``, ``protecting``, ``children``), so the validator resolves a token to
candidate base forms and accepts it when any candidate is known.
"""

from __future__ import annotations

from collections.abc import Collection

_IRREGULAR_PAIRS = """
was:be were:be been:be being:be am:be did:do done:do doing:do had:have having:have
went:go gone:go going:go came:come coming:come saw:see seen:see seeing:see
took:take taken:take taking:take made:make making:make built:build building:build
found:find finding:find gave:give given:give giving:give read:read reading:read
wrote:write written:write writing:write spoke:speak spoken:speak speaking:speak
heard:hear hearing:hear ran:run running:run ate:eat eaten:eat eating:eat
drank:drink drunk:drink drinking:drink slept:sleep sleeping:sleep felt:feel
feeling:feel chose:choose chosen:choose choosing:choose met:meet meeting:meet
taught:teach teaching:teach bought:buy buying:buy brought:bring bringing:bring
paid:pay paying:pay got:get getting:get kept:keep keeping:keep held:hold
holding:hold began:begin begun:begin beginning:begin knew:know known:know
knowing:know grew:grow grown:grow growing:grow born:bear borne:bear
children:child men:man women:woman feet:foot teeth:tooth better:good best:good
worse:bad worst:bad became:become becoming:become wove:weave woven:weave
weaving:weave rode:ride riding:ride ridden:ride fell:fall falling:fall
fallen:fall bled:bleed bleeding:bleed swam:swim swimming:swim swum:swim
drove:drive driving:drive driven:drive flew:fly flying:fly flown:fly broke:break
breaking:break broken:break hurt:hurt hurting:hurt cut:cut cutting:cut put:put
putting:put set:set setting:set let:let letting:let leaves:leaf
craftspeople:craftsperson people:person
mice:mouse geese:goose oxen:ox lives:life wives:wife knives:knife halves:half
shelves:shelf wolves:wolf thieves:thief loaves:loaf calves:calf selves:self
sang:sing sung:sing singing:sing stood:stand standing:stand sat:sit sitting:sit
lost:lose losing:lose won:win winning:win told:tell telling:tell sold:sell
selling:sell said:say saying:say left:leave leaving:leave sent:send sending:send
spent:spend spending:spend thought:think thinking:think caught:catch catching:catch
fought:fight fighting:fight sought:seek wore:wear worn:wear wearing:wear
tore:tear torn:tear threw:throw thrown:throw throwing:throw drew:draw drawn:draw
drawing:draw showed:show shown:show hid:hide hidden:hide hiding:hide
forgot:forget forgotten:forget forgetting:forget woke:wake woken:wake
stole:steal stolen:steal froze:freeze frozen:freeze shook:shake shaken:shake
shaking:shake risen:rise sank:sink sunk:sink rang:ring rung:ring shut:shut
shutting:shut hit:hit hitting:hit spread:spread beat:beat beaten:beat
led:lead leading:lead fed:feed feeding:feed dealt:deal meant:mean dug:dig
digging:dig hung:hang hanging:hang struck:strike swept:sweep sweeping:sweep
understood:understand understanding:understand lay:lie lying:lie dying:die
tying:tie
""".split()

IRREGULAR_FORMS: dict[str, str] = dict(p.split(":", 1) for p in _IRREGULAR_PAIRS)
"""Irregular inflected form -> base form."""

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
    "wouldn't": "would",
    "mustn't": "must",
    "needn't": "need",
}

# Words that merely *look* inflected; deriving a base form would wrongly accept
# them (``thing`` -> ``the``, ``shed`` -> ``she``).
NON_DERIVABLE: frozenset[str] = frozenset(
    """thing king ring sing wing bring spring string sting swing during morning
    evening nothing something anything everything shed bed red need seed feed speed
    weed breed indeed hundred sacred naked wicked bless""".split()
)

_VOWELS = "aeiou"


def _undouble(stem: str) -> list[str]:
    if len(stem) > 2 and stem[-1] == stem[-2] and stem[-1] not in _VOWELS:
        return [stem[:-1]]
    return []


def suffix_candidates(w: str) -> list[str]:
    """Return plausible base forms obtained by stripping one inflectional suffix."""
    if w in NON_DERIVABLE:
        return []
    n = len(w)
    out: list[str] = []
    if w.endswith("ies") and n > 4:
        out.append(w[:-3] + "y")
    if w.endswith("ves") and n > 4:
        out += [w[:-3] + "f", w[:-3] + "fe"]
    if w.endswith("es") and n > 3:
        out += [w[:-2], w[:-1]]
    if w.endswith("s") and not w.endswith("ss") and n > 2:
        out.append(w[:-1])
    if w.endswith("ing") and n > 4:
        stem = w[:-3]
        out += [stem, stem + "e", *_undouble(stem)]
    if w.endswith("ed") and n > 3:
        stem = w[:-2]
        out += [stem, stem + "e", *_undouble(stem)]
        if w.endswith("ied"):
            out.append(w[:-3] + "y")
    if w.endswith("er") and n > 4:
        stem = w[:-2]
        out += [stem, stem + "e", *_undouble(stem)]
        if w.endswith("ier"):
            out.append(w[:-3] + "y")
    if w.endswith("est") and n > 5:
        stem = w[:-3]
        out += [stem, stem + "e", *_undouble(stem)]
        if w.endswith("iest"):
            out.append(w[:-4] + "y")
    if w.endswith("ly") and n > 4:
        stem = w[:-2]
        out += [stem, stem + "e", w[:-1] + "e"]
        if w.endswith("ily"):
            out.append(w[:-3] + "y")
    return out


def is_known_form(word: str, allowed: Collection[str]) -> bool:
    """True when ``word`` is allowed directly or via a regular/irregular inflection."""
    w = word.lower().strip()
    if not w or w.isdigit() or len(w) == 1:
        return True
    if w in allowed:
        return True
    contracted = CONTRACTION_MAP.get(w)
    if contracted is not None and contracted in allowed:
        return True
    irregular = IRREGULAR_FORMS.get(w)
    if irregular is not None and irregular in allowed:
        return True

    frontier = suffix_candidates(w)
    for depth in range(2):  # depth 2 resolves e.g. teachers -> teacher -> teach
        deeper: list[str] = []
        for cand in frontier:
            if cand in allowed:
                return True
            base = IRREGULAR_FORMS.get(cand)
            if base is not None and base in allowed:
                return True
            if depth == 0:
                deeper.extend(suffix_candidates(cand))
        frontier = deeper
    return False
