"""Tests for career_rag/occupation_aliases.py. Run from the project root:

    python -m unittest discover -s tests
"""

import unittest

from career_rag.occupation_aliases import resolve_career_alias

# A tiny occupation index with the real trap: O*NET lists "Jockey" as an alternate
# title of Athletes and Sports Competitors, and the real occupation is named
# "Disc Jockeys, Except Radio".
INDEX = [
    {"title": "Athletes and Sports Competitors", "onet_soc_code": "27-2021.00", "aliases": ["Jockey"]},
    {"title": "Disc Jockeys, Except Radio", "onet_soc_code": "27-2091.00", "aliases": []},
    {"title": "Janitors and Cleaners, Except Maids and Housekeeping Cleaners", "onet_soc_code": "37-2011.00", "aliases": []},
    {"title": "Teachers, Except A", "onet_soc_code": "00-0001.00", "aliases": []},
    {"title": "Teachers, Except B", "onet_soc_code": "00-0002.00", "aliases": []},
]


class ResolveCareerAliasTest(unittest.TestCase):
    def resolve(self, title):
        return resolve_career_alias(title, INDEX)

    def test_listing_title_matches_its_except_occupation(self):
        result = self.resolve("Disc Jockeys")
        self.assertEqual(result["onet_soc_code"], "27-2091.00")
        self.assertEqual(result["resolution_method"], "official_title_except")

    def test_ampersand_in_listing_title(self):
        self.assertEqual(self.resolve("Janitors & Cleaners")["onet_soc_code"], "37-2011.00")

    def test_ambiguous_except_titles_are_not_guessed_by_this_rule(self):
        self.assertNotEqual(self.resolve("Teachers")["resolution_method"], "official_title_except")


if __name__ == "__main__":
    unittest.main()
