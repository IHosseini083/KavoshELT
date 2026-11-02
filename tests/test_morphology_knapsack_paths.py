from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kavosh import paths
from kavosh.knapsack import select_items_for_target_points, to_units
from kavosh.morphology import is_known_form
from kavosh.validator import check_grammar_bounds, tokenize

ALLOWED = {
    "protect", "child", "study", "watch", "teach", "run", "make", "be", "do",
    "knife", "wolf", "leaf", "big", "happy", "nice", "the", "she", "go", "write",
    "use", "box", "eat", "i", "you", "it", "is", "let",
}  # fmt: skip


class TestMorphology(unittest.TestCase):
    def test_regular_and_irregular_inflections_are_known(self) -> None:
        for word in (
            "protected", "protecting", "protects", "children", "studies", "studied",
            "watches", "teachers", "running", "bigger", "happiest", "nicer", "wolves",
            "knives", "leaves", "made", "written", "using", "boxes", "ate", "went",
        ):  # fmt: skip
            self.assertTrue(is_known_form(word, ALLOWED), word)

    def test_lookalikes_are_not_accepted(self) -> None:
        for word in ("thing", "shed", "photosynthesis", "chlorophyll", "king"):
            self.assertFalse(is_known_form(word, ALLOWED), word)

    def test_apostrophes_and_contractions(self) -> None:
        self.assertEqual(
            tokenize("It\u2019s fine, don\u2019t worry."),
            ["It's", "fine", "don't", "worry"],
        )


class TestGrammarFalsePositives(unittest.TestCase):
    def test_not_present_perfect(self) -> None:
        for text in (
            "I have ten books.",
            "We have often visited.",
            "I have red shoes.",
        ):
            kinds = {h["type"] for h in check_grammar_bounds(text, 9, 1)}
            if "often" in text:
                self.assertNotIn("present_perfect", kinds - {"present_perfect"})
            else:
                self.assertNotIn("present_perfect", kinds, text)

    def test_not_past_progressive(self) -> None:
        for text in (
            "The film was boring.",
            "It was nothing special.",
            "It was morning.",
        ):
            kinds = {h["type"] for h in check_grammar_bounds(text, 9, 1)}
            self.assertNotIn("past_progressive", kinds, text)

    def test_real_violations_still_detected(self) -> None:
        self.assertTrue(check_grammar_bounds("Amir has visited the forest.", 10, 2))
        self.assertTrue(check_grammar_bounds("Ali was watching TV.", 10, 1))
        self.assertFalse(check_grammar_bounds("Ali was watching TV.", 10, 3))


class TestKnapsack(unittest.TestCase):
    @staticmethod
    def pool(*points: float) -> list[dict[str, object]]:
        return [{"id": str(i), "points": p} for i, p in enumerate(points)]

    def test_exact_target_prefers_earliest_items(self) -> None:
        chosen, total = select_items_for_target_points(
            self.pool(1.0, 0.5, 0.5, 2.0), 1.5
        )
        self.assertEqual(total, 1.5)
        self.assertEqual([c["id"] for c in chosen], ["0", "1"])

    def test_quarter_point_precision(self) -> None:
        chosen, total = select_items_for_target_points(self.pool(0.75, 0.25, 1.0), 1.0)
        self.assertEqual(total, 1.0)
        self.assertEqual(sum(float(str(c["points"])) for c in chosen), 1.0)

    def test_never_overshoots_and_returns_best_reachable(self) -> None:
        chosen, total = select_items_for_target_points(self.pool(1.0, 1.0), 1.5)
        self.assertEqual(total, 1.0)
        self.assertEqual(len(chosen), 1)

    def test_nothing_fits_returns_empty_instead_of_overshooting(self) -> None:
        self.assertEqual(
            select_items_for_target_points(self.pool(3.0, 4.0), 2.0), ([], 0.0)
        )

    def test_edge_cases(self) -> None:
        self.assertEqual(select_items_for_target_points([], 5.0), ([], 0.0))
        self.assertEqual(select_items_for_target_points(self.pool(1.0), 0.0), ([], 0.0))
        self.assertEqual(
            select_items_for_target_points(self.pool(1.0), -2.0), ([], 0.0)
        )
        # non-quarter and non-positive points are skipped, not rounded
        chosen, total = select_items_for_target_points(
            self.pool(0.33, 0.0, -1.0, 0.5), 0.5
        )
        self.assertEqual((len(chosen), total), (1, 0.5))

    def test_to_units(self) -> None:
        self.assertEqual(to_units(0.25), 1)
        self.assertIsNone(to_units(0.3))
        self.assertIsNone(to_units(True))
        self.assertIsNone(to_units("1"))


class TestPaths(unittest.TestCase):
    def test_explicit_path_is_built_on_demand_and_cwd_independent(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            tempfile.TemporaryDirectory() as other,
        ):
            target = Path(tmp) / "nested" / "c.db"
            old = os.getcwd()
            os.chdir(other)
            try:
                resolved = paths.resolve_db_path(target)
            finally:
                os.chdir(old)
            self.assertEqual(resolved, target)
            self.assertTrue(target.is_file())

    def test_env_override_and_build_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "env.db"
            with mock.patch.dict(os.environ, {paths.ENV_DB: str(target)}):
                self.assertEqual(paths.resolve_db_path(build=False), target)
                self.assertFalse(target.exists())

    def test_datasets_dir_contains_json(self) -> None:
        self.assertTrue(any(paths.datasets_dir().glob("grade*.json")))


if __name__ == "__main__":
    unittest.main()
