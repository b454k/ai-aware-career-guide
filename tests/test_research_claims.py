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
                    if column in row:  # show and hide_for decide where a claim appears, not what it says
                        self.assertEqual(row[column], value, claim_id)

    def test_a_claim_hidden_for_a_career_is_not_shown_there(self):
        import csv

        from check_claim_relevance import SHOWN, hidden_for, load_corrections

        corrections = load_corrections()
        self.assertTrue(hidden_for("claim_002177", "29-2092.00", corrections))  # the first use (10.9)
        self.assertFalse(hidden_for("claim_002177", "13-1071.00", corrections))
        with SHOWN.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                self.assertFalse(hidden_for(row["claim_id"], row["onetsoc_code"], corrections), row)

    def test_every_shown_quote_reads_on_its_own(self):
        # a bare number from a table ("-19.2") once passed as a quote: it matched the source exactly
        import csv
        import re

        from check_claim_relevance import SHOWN

        with SHOWN.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                self.assertGreaterEqual(len(re.findall(r"[^\W\d_]{3,}", row["evidence_quote"])), 3, row["claim_id"])


class AiLinkTest(unittest.TestCase):
    """Only findings about AI's effect on work are shown, in the check's rewrite when needed (ROADMAP 10.6)."""

    def test_shown_claims_follow_the_reviewed_ai_link_verdicts(self):
        import csv

        from check_claim_relevance import SHOWN, load_corrections

        review_path = SHOWN.parents[2] / "evaluation" / "claim_ai_link_review.csv"
        with review_path.open(encoding="utf-8", newline="") as handle:
            verdicts = {row["claim_id"]: row for row in csv.DictReader(handle)}
        corrections = load_corrections()
        with SHOWN.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                correction, verdict = corrections.get(row["claim_id"], {}), verdicts[row["claim_id"]]
                self.assertNotEqual(correction.get("show"), "no", row["claim_id"])
                if correction.get("claim_text"):
                    continue  # corrected by hand, so it wins
                self.assertNotEqual(verdict["verdict"], "none", row["claim_id"])
                if verdict["verdict"] == "context":
                    self.assertEqual(row["claim_text"], verdict["rewrite"], row["claim_id"])


    def test_relevance_is_asked_about_the_text_the_app_shows(self):
        # a hand text wins over the AI-link rewrite, which wins over the extracted text (10.7)
        from check_claim_relevance import shown_claim_text

        links = {"a": {"verdict": "context", "rewrite": "rewritten"}, "b": {"verdict": "direct", "rewrite": ""}}
        self.assertEqual(shown_claim_text("a", "extracted", links, {}), "rewritten")
        self.assertEqual(shown_claim_text("a", "extracted", links, {"a": {"claim_text": "by hand"}}), "by hand")
        self.assertEqual(shown_claim_text("b", "extracted", links, {}), "extracted")
        self.assertEqual(shown_claim_text("c", "extracted", links, {}), "extracted")  # never judged relevant


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
