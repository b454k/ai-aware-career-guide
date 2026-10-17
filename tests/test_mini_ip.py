"""Tests for O*NET's 30-item Mini-IP (ROADMAP 9.8). Run from the project root:

    python -m pytest
"""

import unittest
from collections import Counter

from career_rag.config import MINI_IP_QUESTIONS_PATH, QUESTIONS_PATH
from career_rag.interest_profiler_local import (
    calculate_mini_ip_scores,
    load_interest_profiler_questions,
    load_mini_ip_questions,
)
from career_rag.ip_career_matcher import build_career_matches

QUESTIONS = load_interest_profiler_questions(QUESTIONS_PATH)
MINI = load_mini_ip_questions(MINI_IP_QUESTIONS_PATH, QUESTIONS)


class MiniIpTest(unittest.TestCase):
    def test_thirty_activities_five_per_area_in_onets_order(self):
        self.assertEqual(len(MINI), 30)
        self.assertEqual(set(Counter(question["area"] for question in MINI).values()), {5})
        self.assertEqual([question["area_code"] for question in MINI[:6]], list("RIASEC"))  # O*NET alternates the areas

    def test_scores_are_doubled_to_the_sixty_item_scale(self):
        realistic = [question["id"] for question in MINI if question["area"] == "Realistic"]
        scores = calculate_mini_ip_scores(QUESTIONS, realistic[:3])
        self.assertEqual(scores["Realistic"], 6)
        self.assertEqual(sum(scores.values()), 6)

    def test_doubling_does_not_change_the_matches(self):
        # O*NET's rule is a correlation with the career's profile, which a common factor doesn't change
        raw = {"Realistic": 1, "Investigative": 4, "Artistic": 2, "Social": 0, "Enterprising": 3, "Conventional": 5}
        doubled = {area: 2 * score for area, score in raw.items()}
        codes = lambda scores: {  # noqa: E731
            group: [(m.get("onet_soc_code"), m.get("fit")) for m in matches]
            for group, matches in build_career_matches(scores=scores, current_job_zone=3, future_job_zone=4).items()
        }
        self.assertEqual(codes(raw), codes(doubled))


if __name__ == "__main__":
    unittest.main()
