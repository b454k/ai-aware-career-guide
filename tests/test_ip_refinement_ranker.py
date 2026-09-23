"""Tests for career_rag/ip_refinement_ranker.py. Run from the project root:

    python -m unittest discover -s tests
"""

import unittest
from unittest.mock import patch

from career_rag import ip_refinement_ranker

OCCUPATION_ROWS = [
    {"doc_type": "ai_occupation_impact", "metric_name": "observed_exposure", "metric_value": 0.3},
    {"doc_type": "ai_occupation_impact", "metric_name": "pct", "metric_value": 4.2, "metric_unit": "percent"},
]


def preferences_from(answer):
    return ip_refinement_ranker.extract_structured_preferences({"questions_asked": [{"answer": answer}]})


class KeywordMatchingTest(unittest.TestCase):
    # (answer, preference label, should it be detected?)
    CASES = [
        ("I enjoy training new staff and paying attention to detail", "ai-aware career planning", False),
        ("I want to understand how AI will change my job", "ai-aware career planning", True),
        ("I like to start small projects and take part in things", "creative design or writing", False),
        ("I am an artistic person", "creative design or writing", True),
        ("Artificial intelligence interests me", "creative design or writing", False),
        ("I read about space before breakfast", "fast-paced projects", False),
        ("I like a fast paced day", "fast-paced projects", True),
        ("I like fixing bikes", "hands-on technical work", True),
        ("The aftermath of the project taught me patience", "data and numbers", False),
        ("I studied mathematics", "data and numbers", True),
    ]

    def test_keywords_match_words_not_parts_of_words(self):
        for answer, label, expected in self.CASES:
            self.assertEqual(label in preferences_from(answer), expected, answer)

    def test_training_is_not_an_ai_preference(self):
        with patch.object(ip_refinement_ranker, "_local_ai_rows_for_soc", return_value=OCCUPATION_ROWS):
            self.assertEqual(ip_refinement_ranker._ai_preference_score("I enjoy training people", "x"), 0.5)


class AiPreferenceScoreTest(unittest.TestCase):
    def score(self, preference_text):
        with patch.object(ip_refinement_ranker, "_local_ai_rows_for_soc", return_value=OCCUPATION_ROWS):
            return ip_refinement_ranker._ai_preference_score(preference_text, "13-2011.00")

    def test_stability_preference_uses_observed_exposure_only(self):
        self.assertAlmostEqual(self.score("I want job stability"), 0.7)

    def test_automation_interest_uses_observed_exposure_only(self):
        self.assertAlmostEqual(self.score("future proof technology work"), 0.3)


if __name__ == "__main__":
    unittest.main()
