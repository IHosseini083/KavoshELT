"""Static word lists shared by the syllabus validator."""

from __future__ import annotations

COMMON_PROPER_NOUNS: frozenset[str] = frozenset(
    """
    aban ahmadi ai al ali alireza allah amir asadi asia asian audio azar babak
    bahman block carlos chehel china chinese david dey diego din dr e earth edison
    erfan esfahan esfand farhad farvardin fola france french gemini german germany
    gharib god golestan hafez haft hamid hindi hossein iran iranian isfahan jahan
    japan japanese jean jupiter karimi khordad kian lalejin louis mahdi maragheh
    mars maryam mashhad mehdi mehr mehrad mercury min mina mohammad moradi mordad mr
    mrs ms naqsh nasir neda neptune nima nowruz o omid ordibehesht paris part
    pasargadae pasteur persepolis persian pol prospect quran rami razavi reza rezaei
    saadi samaneh sara saturn se sec seen shahrivar shiraz si sina sir sotoun spain
    spanish speaker square studio tehran tehrani tir track tts tusi unesco venus
    vision yalda yazd zahra
    """.split()
)
"""Names, places and workbook meta-words that are always acceptable in exam text."""
