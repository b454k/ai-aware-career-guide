"""Tests for the new job titles and their closest O*NET roles (ROADMAP 6.6, 10.2). Run from the project root:

    python -m pytest
"""

import unittest

from career_rag import new_titles
from career_rag.ip_career_matcher import load_occupations_by_code


class NewTitlesTest(unittest.TestCase):
    def test_every_title_has_both_names_a_known_source_and_one_to_three_roles(self):
        rows = new_titles.load_new_titles()
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row["title_en"] and row["title_tr"], row)
            self.assertIn(row["source"], new_titles.SOURCE_KEYS)
            self.assertTrue(1 <= len(row["onet_codes"].split(";")) <= 3, row)
        self.assertEqual(len({row["title_en"] for row in rows}), len(rows))

    def test_every_role_is_an_onet_occupation(self):
        codes = {code for row in new_titles.load_new_titles() for code in row["onet_codes"].split(";")}
        found = {occupation["onet_soc_code"] for occupation in load_occupations_by_code(sorted(codes))}
        self.assertEqual(found, codes)

    def test_a_career_lists_the_titles_it_is_closest_to(self):
        # shown in that career's detail (ROADMAP 10.2)
        titles = [row["title_en"] for row in new_titles.titles_for_career("15-1221.00")]
        self.assertIn("AI Engineer", titles)
        self.assertEqual(new_titles.titles_for_career("47-2061.00"), [])  # construction laborers: none


if __name__ == "__main__":
    unittest.main()
