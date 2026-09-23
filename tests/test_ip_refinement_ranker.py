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
