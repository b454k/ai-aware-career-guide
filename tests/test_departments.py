"""Tests for the department path (ROADMAP 9.1). Run from the project root:

    python -m pytest
"""

import unittest

from career_rag.departments import department_codes, department_label, load_departments
from career_rag.ip_career_matcher import build_career_matches, department_fit_list

USER = {"Realistic": 0, "Investigative": 9, "Artistic": 0, "Social": 0, "Enterprising": 0, "Conventional": 7}


def occupation(title, scores):
    return {"career_title": title, "interest_scores": scores}


class DepartmentTablesTest(unittest.TestCase):
    def test_every_department_has_careers_and_both_names(self):
        for row in load_departments():
            self.assertTrue(department_codes(row["name_tr"]), row["name_tr"])
            self.assertTrue(row["name_en"])
            self.assertEqual(department_label(row["name_tr"], "tr"), row["name_tr"])

    def test_statistics_leads_to_statisticians_not_legal_secretaries(self):
        codes = department_codes("İstatistik")
        self.assertIn("15-2041.00", codes)  # Statisticians
        self.assertIn("15-2051.00", codes)  # Data Scientists
        self.assertNotIn("43-6012.00", codes)  # Legal Secretaries and Administrative Assistants


class DepartmentFitListTest(unittest.TestCase):
    def test_keeps_every_career_and_labels_a_negative_fit_weak(self):
        # O*NET's own list drops careers below r = 0; inside a department nothing is dropped.
        occupations = [occupation("Same shape", [1, 7, 1, 1, 1, 5]), occupation("Opposite", [7, 1, 7, 7, 7, 1])]
        result = department_fit_list(USER, occupations)
        self.assertEqual([m["career_title"] for m in result], ["Same shape", "Opposite"])
        self.assertEqual([m["fit"] for m in result], ["Best fit", "Weak fit"])

    def test_a_department_replaces_the_job_zone_lists(self):
        matches = build_career_matches(USER, 4, 4, department_codes=department_codes("Hukuk"))
        self.assertEqual(list(matches), ["department"])
        self.assertEqual({m["onet_soc_code"] for m in matches["department"]}, set(department_codes("Hukuk")))


if __name__ == "__main__":
    unittest.main()
