"""Tests for the new job titles and their closest O*NET roles (ROADMAP 6.6). Run from the project root:

    python -m pytest
"""

import unittest
from unittest.mock import patch

from career_rag import new_titles


class NewTitlesTest(unittest.TestCase):
    def test_every_title_has_both_names_a_known_source_and_one_to_three_roles(self):
        rows = new_titles.load_new_titles()
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row["title_en"] and row["title_tr"], row)
            self.assertIn(row["source"], new_titles.SOURCE_KEYS)
            self.assertTrue(1 <= len(row["onet_codes"].split(";")) <= 3, row)
        self.assertEqual(len({row["title_en"] for row in rows}), len(rows))

    def test_every_role_builds_a_card_with_tasks_and_no_llm_call(self):
        # A title's view must not call OpenAI: "a day in the life" falls back to the template (6.6 is free to use).
        with patch("openai.resources.chat.completions.Completions.create", side_effect=AssertionError("OpenAI called")):
            for row in new_titles.load_new_titles():
                for language in ("en", "tr"):
                    view = new_titles.build_new_title_view(row["title_en"], language)
                    self.assertEqual(len(view["roles"]), len(row["onet_codes"].split(";")))
                    for role in view["roles"]:
                        self.assertTrue(role["onet_details"].get("tasks"), role["onet_soc_code"])
                        self.assertEqual(role["why_it_fits"], [])
                    self.assertTrue(view["sources"])


if __name__ == "__main__":
    unittest.main()
