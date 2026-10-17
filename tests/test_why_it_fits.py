"""Tests for "why it fits", built from the student's own answers (ROADMAP 9.4). Run from the project root:

    python -m pytest
"""

import unittest

from career_rag.ip_final_report import _why_it_fits

STATISTICIANS = "15-2041.00"  # O*NET: Investigative, Conventional
MATH_TEACHERS = "25-1022.00"  # O*NET: Social, Investigative


def profile(interests, liked=(), department=None):
    used = {"final_top_interests": interests, "liked_activity_ids": list(liked), "profile_citation": "[1]"}
    if department:
        used["department"] = department
    return used


class WhyItFitsTest(unittest.TestCase):
    def test_both_strongest_areas_shared_and_the_activities_quoted(self):
        bullets = _why_it_fits(STATISTICIANS, profile(["Investigative", "Conventional", "Realistic"], liked=[11, 12]))
        self.assertIn("are both among yours", bullets[0])
        self.assertIn("“Develop a new medicine”", bullets[1])

    def test_one_shared_area_is_named_as_one(self):
        bullets = _why_it_fits(MATH_TEACHERS, profile(["Investigative", "Conventional", "Realistic"]))
        self.assertIn("Investigative is among yours", bullets[0])

    def test_no_shared_area_says_it_fits_less_well(self):
        bullets = _why_it_fits(STATISTICIANS, profile(["Artistic", "Social", "Enterprising"]))
        self.assertIn("fits your answers less well", bullets[0])

    def test_activities_of_the_careers_strongest_area_come_first(self):
        # Math teachers are Social first: a Social yes-answer comes before an Investigative one
        bullets = _why_it_fits(MATH_TEACHERS, profile(["Social", "Investigative", "Artistic"], liked=[11, 31]))
        self.assertLess(bullets[1].index("Teach an individual"), bullets[1].index("Develop a new medicine"))

    def test_department_line_only_with_a_department(self):
        self.assertTrue(any("your department" in b for b in _why_it_fits(STATISTICIANS, profile(["Investigative"], department="İstatistik"))))
        self.assertFalse(any("your department" in b for b in _why_it_fits(STATISTICIANS, profile(["Investigative"]))))

    def test_turkish(self):
        bullets = _why_it_fits(STATISTICIANS, profile(["Investigative", "Conventional", "Realistic"], liked=[11]), "tr")
        self.assertIn("senin alanlarının arasında", bullets[0])
        self.assertNotIn("Develop a new medicine", bullets[1])  # the activity in Turkish


if __name__ == "__main__":
    unittest.main()
