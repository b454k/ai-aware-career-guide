"""Tests for the alternatives at every preparation level (ROADMAP 10.1). Run from the project root:

    python -m pytest
"""

import unittest

from career_rag.ip_final_report import ALTERNATIVES_PER_ZONE, CitationManager, _build_alternatives_by_level

# Artistic first, Conventional zero: a Statistics student whose department's careers all fit weakly
SCORES = {"Realistic": 4, "Investigative": 6, "Artistic": 8, "Social": 6, "Enterprising": 6, "Conventional": 0}
STATISTICIANS = "15-2041.00"


class AlternativesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        profile_used = {"final_top_interests": ["Artistic", "Investigative", "Social"], "department": "İstatistik"}
        cls.alternatives = _build_alternatives_by_level(
            {"riasec_scores": SCORES}, profile_used, {STATISTICIANS}, CitationManager("en")
        )

    def test_the_best_three_at_each_preparation_level(self):
        zones = [match["target_job_zone"] for match in self.alternatives]
        self.assertEqual(sorted(set(zones)), [2, 3, 4, 5])
        self.assertTrue(all(zones.count(zone) <= ALTERNATIVES_PER_ZONE for zone in set(zones)))

    def test_only_onets_positive_fits_and_not_the_top_matches(self):
        self.assertTrue(all(match["fit_label"] in {"Best fit", "Great fit", "Good fit"} for match in self.alternatives))
        self.assertNotIn(STATISTICIANS, [match["onet_soc_code"] for match in self.alternatives])

    def test_no_department_line_and_no_day_in_the_life(self):
        for match in self.alternatives:
            self.assertFalse(any("department" in line for line in match["why_it_fits"]), match["display_title"])
            self.assertEqual(match["day_in_the_life"], "")


if __name__ == "__main__":
    unittest.main()
