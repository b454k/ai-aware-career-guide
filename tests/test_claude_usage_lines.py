"""Tests for the Anthropic usage sentences (ROADMAP 2.5, D14 = C). Run from the project root:

    python -m unittest discover -s tests
"""

import unittest

from career_rag.ui_i18n import claude_usage_lines, month_label, percent_text

USAGE = {
    "month": "2026-05-01",
    "global_pct": 0.35,
    "turkey_pct": 0.43,
    "automation_pct": 60.79,
    "augmentation_pct": 39.21,
    "human_only_hours": 5.9,
    "with_ai_minutes": 47.77,
}


class ClaudeUsageLinesTest(unittest.TestCase):
    def test_english_sentences_carry_the_numbers_and_not_the_caveats(self):
        text = " ".join(claude_usage_lines(USAGE, "en"))
        for expected in ("0.35%", "In Turkey: 0.43%", "61% automation-style", "39% augmentation-style",
                         "about 5.9 hours", "about 48 minutes"):
            self.assertIn(expected, text)
        # the caveats are said once, under About the data (ROADMAP 9.5)
        for caveat in ("not how many jobs change", "not measured productivity"):
            self.assertNotIn(caveat, text)

    def test_turkish_uses_percent_first_and_decimal_comma(self):
        text = " ".join(claude_usage_lines(USAGE, "tr"))
        self.assertIn("%0,35", text)
        self.assertIn("Türkiye'de: %0,43", text)
        self.assertIn("yaklaşık 5,9 saat", text)
        self.assertEqual(month_label("2026-05-01", "tr"), "Mayıs 2026")

    def test_missing_turkey_value_is_said_not_hidden(self):
        lines = claude_usage_lines({**USAGE, "turkey_pct": None}, "en")
        self.assertIn("Turkey: not published", " ".join(lines))

    def test_zero_share_is_below_rounding_not_zero(self):
        # Anthropic rounds to two decimals, so 0.0 means "under 0.01%".
        text = " ".join(claude_usage_lines({**USAGE, "global_pct": 0.0}, "en"))
        self.assertIn("under 0.01%", text)
        self.assertEqual(percent_text(0.01, "tr"), "%0,01")


if __name__ == "__main__":
    unittest.main()
