"""Tests for the education sentence (ROADMAP 2.10). Run from the project root:

    python -m unittest discover -s tests
"""

import unittest

from career_rag.ip_final_report import _education_needed_from_percentages, education_level


def level(category, label, percent):
    return {"category": category, "label": label, "percent": percent}


class EducationLevelTest(unittest.TestCase):
    def test_level_comes_from_the_category_number_not_the_words(self):
        # O*NET 30.3's label for category 3 mentions "high school" and category 9 "master".
        self.assertEqual(education_level(3), "other")
        self.assertEqual(education_level(9), "other")
        self.assertEqual(education_level(2), "high_school")
        self.assertEqual(education_level(6), "bachelor")
        self.assertEqual(education_level(8), "master")
        self.assertEqual(education_level(11), "doctoral")
        self.assertEqual(education_level(None), "other")

    def test_post_secondary_certificate_is_not_reported_as_high_school(self):
        # Computer Systems Engineers/Architects: 40.91% post-secondary certificate, 27.27% associate's.
        sentence = _education_needed_from_percentages([
            level(3, "Post-Secondary Certificate - awarded for training completed after high school", 40.91),
            level(5, "Associate's Degree (or other 2-year degree)", 27.27),
        ])
        self.assertNotIn("high-school", sentence)
        self.assertIn("post-secondary certificate", sentence)

    def test_post_masters_certificate_is_not_a_masters_degree(self):
        sentence = _education_needed_from_percentages([level(9, "Post-Master's Certificate", 50.0)])
        self.assertNotIn("master's degree", sentence)

    def test_turkish_sentence_has_no_english_category_name(self):
        from career_rag.ip_report_ui import _plain_education_summary

        sentence = _plain_education_summary([level(1, "Less than a High School Diploma", 65.71)], "tr")
        self.assertIn("lise diplomasının altındaki eğitim", sentence)
        self.assertNotIn("Less than", sentence)


if __name__ == "__main__":
    unittest.main()
