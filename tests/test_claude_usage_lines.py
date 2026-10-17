"""Tests for the Anthropic usage sentences (ROADMAP 2.5, D14 = C). Run from the project root:

    python -m unittest discover -s tests
"""

import unittest

from career_rag.ip_ai_impact import claude_share_standing
from career_rag.ui_i18n import claude_usage_lines, claude_usage_notes, month_label, percent_text

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
        for expected in ("35 were about this job's tasks (0.35%)", "In Turkey: 43 of every 10,000 (0.43%)",
                         "to Claude 61% of the time", "39% of the time", "about 5.9 hours", "about 48 minutes"):
            self.assertIn(expected, text)
        # the caveats are said once, under About the data (ROADMAP 9.5)
        for caveat in ("not how many jobs change", "not measured productivity"):
            self.assertNotIn(caveat, text)

    def test_turkish_uses_percent_first_and_decimal_comma(self):
        text = " ".join(claude_usage_lines(USAGE, "tr"))
        self.assertIn("%0,35", text)
        self.assertIn("Türkiye'de: 10.000 konuşmada 43 (%0,43)", text)
        self.assertIn("yaklaşık 5,9 saat", text)
        self.assertEqual(month_label("2026-05-01", "tr"), "Mayıs 2026")

    def test_missing_turkey_value_is_said_not_hidden(self):
        lines = claude_usage_lines({**USAGE, "turkey_pct": None}, "en")
        self.assertIn("Turkey: not published", " ".join(lines))

    def test_zero_share_is_below_rounding_not_zero(self):
        # Anthropic rounds to two decimals, so 0.0 means "under 0.01%".
        text = " ".join(claude_usage_lines({**USAGE, "global_pct": 0.0}, "en"))
        self.assertIn("fewer than 1 were about this job's tasks (under 0.01%)", text)
        self.assertEqual(percent_text(0.01, "tr"), "%0,01")


class ClaudeUsageNotesTest(unittest.TestCase):
    """The explanation under each figure (ROADMAP 10.4)."""

    def test_one_note_per_line_in_the_same_order(self):
        for usage in (USAGE, {**USAGE, "turkey_pct": None}, {"global_pct": 0.35, "turkey_pct": 0.43}):
            self.assertEqual(len(claude_usage_notes(usage, 40, 718)), len(claude_usage_lines(usage)))

    def test_turkey_is_compared_with_the_world(self):
        note = lambda turkey: claude_usage_notes({**USAGE, "turkey_pct": turkey}, 40, 718)[1]  # noqa: E731
        self.assertIn("more often", note(0.9))
        self.assertIn("about as often", note(0.36))
        self.assertIn("less often", note(0.1))

    def test_the_share_is_ranked_among_all_occupations(self):
        rank, total = claude_share_standing(0.35)
        self.assertTrue(1 < rank < total)  # 0.35% is far above the typical 0.02%, but not the top
        self.assertEqual(claude_share_standing(100.0)[0], 1)
        self.assertIn(f"number {rank} of the {total} occupations", claude_usage_notes(USAGE, rank, total)[0])


if __name__ == "__main__":
    unittest.main()
