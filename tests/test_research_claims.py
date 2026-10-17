"""Tests for the research claims a career shows (ROADMAP 4.1c). Run from the project root:

    python -m unittest discover -s tests
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from career_rag import ip_ai_impact
from career_rag.ip_final_report import CitationManager

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "research"))

from check_claim_relevance import select_shown  # noqa: E402


class SelectShownTest(unittest.TestCase):
    def test_only_relevant_claims_by_centered_score(self):
        candidates = [("a", "A.", 0.10), ("b", "B.", 0.20), ("c", "C.", 0.30)]
        self.assertEqual(select_shown(candidates, {"a", "b"}), ["b", "a"])

    def test_negative_centered_score_is_never_shown(self):
        # Judged relevant, but it fits careers on average better than this one.
        self.assertEqual(select_shown([("a", "A.", -0.01)], {"a"}), [])

    def test_same_text_shown_once_and_at_most_three(self):
        candidates = [("a", "Same.", 0.5), ("b", "Same.", 0.4), ("c", "C.", 0.3), ("d", "D.", 0.2), ("e", "E.", 0.1)]
        self.assertEqual(select_shown(candidates, {"a", "b", "c", "d", "e"}), ["a", "c", "d"])


class CorrectionsTest(unittest.TestCase):
    def test_every_hand_correction_reaches_the_shown_claims(self):
        import csv

        from check_claim_relevance import SHOWN, load_corrections

        with SHOWN.open(encoding="utf-8", newline="") as handle:
            shown = list(csv.DictReader(handle))
        for claim_id, corrected in load_corrections().items():
            for row in (row for row in shown if row["claim_id"] == claim_id):
                for column, value in corrected.items():  # claim_text and/or evidence_quote
                    self.assertEqual(row[column], value, claim_id)

    def test_every_shown_quote_reads_on_its_own(self):
        # a bare number from a table ("-19.2") once passed as a quote: it matched the source exactly
        import csv
        import re

        from check_claim_relevance import SHOWN

        with SHOWN.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                self.assertGreaterEqual(len(re.findall(r"[^\W\d_]{3,}", row["evidence_quote"])), 3, row["claim_id"])


class ResearchClaimsTest(unittest.TestCase):
    def claims(self, rows):
        citations = CitationManager()
        with patch.object(ip_ai_impact, "_research_claims_by_occupation", return_value={"15-2051.00": rows}):
            return ip_ai_impact._research_claims("15-2051.00", citations), citations.sources()

    def row(self, page_start, page_end):
        return {"claim_text": "AI helps.", "evidence_quote": "AI helps a lot", "title": "Report", "authors": "Org",
                "year": "2026", "final_url": "https://example.org/report.pdf", "page_start": page_start, "page_end": page_end}

    def test_pages_and_source(self):
        claims, sources = self.claims([self.row("3", "3"), self.row("4", "6")])
        self.assertEqual([item["pages"] for item in claims], ["3", "4-6"])
        self.assertEqual(len(sources), 1)  # one source, cited by both claims
        self.assertEqual(sources[0]["url"], "https://example.org/report.pdf")  # final_url, not the page it was found on
        self.assertEqual(claims[0]["source_ids"], [sources[0]["id"]])

    def test_career_without_claims(self):
        claims, sources = self.claims([])
        self.assertEqual((claims, sources), ([], []))


if __name__ == "__main__":
    unittest.main()
