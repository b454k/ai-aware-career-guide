"""Tests for how Job Zones are shown (ROADMAP 2.8, D13). Run from the project root:

    python -m unittest discover -s tests
"""

import unittest

from career_rag.ui_i18n import job_zone_label, job_zone_number, job_zone_preparation


class JobZoneTextTest(unittest.TestCase):
    def test_zones_one_and_two_are_onets_merged_zone(self):
        self.assertEqual(job_zone_number(1), "1-2")
        self.assertEqual(job_zone_number(2), "1-2")
        self.assertEqual(job_zone_number(4), "4")
        self.assertEqual(job_zone_label(1, "en"), job_zone_label(2, "en"))

    def test_education_is_never_stated_as_required(self):
        # O*NET says "usually" / "most", so our short texts must not say "required" / "gerekir".
        for zone in (2, 3, 4, 5):
            self.assertNotIn("required", job_zone_preparation(zone, "en"))
            self.assertTrue(job_zone_preparation(zone, "en").startswith("usually"))
            self.assertTrue(job_zone_preparation(zone, "tr").startswith("genellikle"))


if __name__ == "__main__":
    unittest.main()
