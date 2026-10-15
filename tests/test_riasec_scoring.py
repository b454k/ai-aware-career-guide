"""Tests for the Interest Profiler scoring in career_rag/interest_profiler_local.py (ROADMAP 5.5).
Run from the project root:

    python -m pytest
"""

import copy
import unittest

from career_rag.config import QUESTIONS_PATH
from career_rag.interest_profiler_local import (
    calculate_riasec_scores,
    detect_ambiguous_categories,
    get_top_interests,
    load_interest_profiler_questions,
    make_holland_code,
    validate_interest_profiler_questions,
)

QUESTIONS = load_interest_profiler_questions(QUESTIONS_PATH)


def ids_of(area):
    return [question["id"] for question in QUESTIONS if question["area"] == area]


class QuestionsTest(unittest.TestCase):
    def test_short_form_has_ten_activities_per_area(self):
        self.assertEqual(len(QUESTIONS), 60)
        for area in ("Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"):
            self.assertEqual(len(ids_of(area)), 10, area)

    def test_wrong_area_count_is_rejected(self):
        questions = copy.deepcopy(QUESTIONS)
        questions[0].update(area="Artistic", area_code="A")  # was Realistic: now 9 R and 11 A
        with self.assertRaises(ValueError):
            validate_interest_profiler_questions(questions)


class ScoringTest(unittest.TestCase):
    def test_each_checked_activity_is_one_point_for_its_area(self):
        scores = calculate_riasec_scores(QUESTIONS, ids_of("Realistic") + ids_of("Social")[:3])
        self.assertEqual(scores, {"Realistic": 10, "Investigative": 0, "Artistic": 0, "Social": 3,
                                  "Enterprising": 0, "Conventional": 0})

    def test_ids_as_text_and_repeats_count_once(self):
        first = ids_of("Investigative")[0]
        scores = calculate_riasec_scores(QUESTIONS, [first, str(first), first])
        self.assertEqual(scores["Investigative"], 1)

    def test_unknown_or_malformed_ids_are_rejected(self):
        for bad in ([61], ["seven"], [None]):
            with self.assertRaises(ValueError):
                calculate_riasec_scores(QUESTIONS, bad)

    def test_nothing_checked_scores_zero(self):
        self.assertEqual(set(calculate_riasec_scores(QUESTIONS, []).values()), {0})


class ProfileTest(unittest.TestCase):
    def test_ties_follow_riasec_order(self):
        scores = {"Realistic": 2, "Investigative": 7, "Artistic": 7, "Social": 7, "Enterprising": 1, "Conventional": 0}
        top = get_top_interests(scores)
        self.assertEqual(top, ["Investigative", "Artistic", "Social"])
        self.assertEqual(make_holland_code(top), "IAS")

    def test_close_scores_are_ambiguous(self):
        self.assertEqual(
            detect_ambiguous_categories({"Realistic": 8, "Investigative": 7, "Artistic": 3})["ambiguous_categories"],
            ["Realistic", "Investigative"],
        )
        self.assertFalse(detect_ambiguous_categories({"Realistic": 8, "Investigative": 6})["has_ambiguity"])


if __name__ == "__main__":
    unittest.main()
