"""Tests for the ILO exposure panel (D5 = B). Run from the project root:

    python -m pytest
"""

import unittest
from unittest.mock import patch

from career_rag import ip_ai_impact
from career_rag.ip_final_report import CitationManager
from career_rag.ui_i18n import ILO_GRADIENTS, ilo_exposure_lines

ILO = {"isco08_code": "2512", "isco08_title": "Software Developers", "gradient": "Gradient 3",
       "mean": 0.53, "sd": 0.07, "careers_in_group": 3}


class IloLinesTest(unittest.TestCase):
    def test_every_ilo_group_has_a_name_and_meaning_in_both_languages(self):
        groups = {"Gradient 4", "Gradient 3", "Gradient 2", "Gradient 1", "Minimal Exposure", "Not Exposed"}
        for language in ("en", "tr"):
            self.assertEqual(set(ILO_GRADIENTS[language]), groups)

    def test_lines_name_the_group_and_say_it_is_broader(self):
        lines = ilo_exposure_lines(ILO, "en")
        self.assertTrue(lines[0].startswith("Significant exposure (ILO gradient 3):"))
        self.assertIn("0.53", lines[1])
        self.assertIn("2 other careers", lines[2])
        self.assertIn("not observed use", lines[3])

    def test_a_group_with_one_career_does_not_mention_others(self):
        lines = ilo_exposure_lines({**ILO, "careers_in_group": 1}, "en")
        self.assertNotIn("other careers", lines[2])

    def test_turkish_uses_a_decimal_comma(self):
        self.assertIn("0,53", ilo_exposure_lines(ILO, "tr")[1])


class IloExposureTest(unittest.TestCase):
    def test_score_and_source_for_a_linked_career(self):
        row = {"isco08_code": "2512", "isco08_title": "Software Developers", "exposure_mean": "0.53",
               "exposure_sd": "0.07", "exposure_gradient": "Gradient 3", "careers_in_group": "3"}
        citations = CitationManager()
        with patch.object(ip_ai_impact, "_ilo_exposure_by_occupation", return_value={"15-1252.00": row}):
            ilo = ip_ai_impact._ilo_exposure("15-1252.00", citations)
            missing = ip_ai_impact._ilo_exposure("99-9999.00", citations)
        self.assertEqual((ilo["mean"], ilo["sd"], ilo["careers_in_group"]), (0.53, 0.07, 3))
        self.assertEqual(citations.sources()[0]["source_type"], "ilo")
        self.assertIsNone(missing)


if __name__ == "__main__":
    unittest.main()
