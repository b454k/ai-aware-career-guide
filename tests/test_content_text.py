"""Tests for the build-time Turkish content table lookup (ROADMAP 6.1c). Run from the project root:

    python -m pytest
"""

import unittest
from unittest.mock import patch

from career_rag import ui_i18n
from career_rag.ip_report_ui import _format_education_entry
from career_rag.ui_i18n import content_text

TABLE = {"Explain testing procedures to patients.": "Hastalara test işlemlerini açıklar.",
         "Bachelor's Degree": "Lisans derecesi"}


class ContentTextTest(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(ui_i18n, "_content_translations", return_value=TABLE)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_english_is_unchanged(self):
        self.assertEqual(content_text("Explain testing procedures to patients.", "en"),
                         "Explain testing procedures to patients.")

    def test_turkish_comes_from_the_table_whatever_the_spacing(self):
        self.assertEqual(content_text("  Explain testing  procedures to patients. ", "tr"),
                         "Hastalara test işlemlerini açıklar.")

    def test_text_not_in_the_table_is_shown_as_it_is(self):
        # e.g. software names; nothing is translated at runtime any more (6.1c)
        self.assertEqual(content_text("Microsoft Excel", "tr"), "Microsoft Excel")

    def test_education_entry_translates_the_level_not_the_percentage(self):
        entry = {"label": "Bachelor's Degree", "percent": 45.5}
        self.assertEqual(_format_education_entry(entry, "tr"), "Lisans derecesi (45.5%)")
        self.assertEqual(_format_education_entry(entry, "en"), "Bachelor's Degree (45.5%)")


if __name__ == "__main__":
    unittest.main()
