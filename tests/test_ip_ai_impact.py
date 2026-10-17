"""Tests for career_rag/ip_ai_impact.py. Run from the project root:

    python -m unittest discover -s tests
"""

import unittest
from unittest.mock import patch

from career_rag import ip_ai_impact
from career_rag.ip_ai_impact import _coverage_label, _observed_exposure, ai_snapshot

TASK = "Return borrowed or rented items when productions are complete."


def task_breakdown(rows, task=TASK):
    """Run the real report function on hand-made Anthropic rows for one task."""
    with patch.object(ip_ai_impact, "_local_ai_rows_for_soc", return_value=rows), patch.object(
        ip_ai_impact, "_fetch_onet_task_records", return_value=[]
    ):
        result = ip_ai_impact.build_ai_impact_for_occupation(
            "39-3092.00", onet_tasks=[{"task_id": "8001", "task": task}]
        )
    return result["task_breakdown"][0]


def row(doc_type, metric_name, value, task=TASK):
    return {"doc_type": doc_type, "metric_name": metric_name, "metric_value": value, "onet_task_id": "8001", "task_text": task}


class CoverageLabelTest(unittest.TestCase):
    def test_labels_follow_anthropic_weights(self):
        cases = {None: "No data", 0.0: "Not covered", 0.5: "Covered: mostly augmentation",
                 0.6: "Covered: mostly augmentation", 0.75: "Covered: mixed",
                 0.9: "Covered: mostly automation", 1.0: "Covered: mostly automation"}
        for value, label in cases.items():
            self.assertEqual(_coverage_label(value), label, value)

    def test_directive_share_no_longer_decides(self):
        # Real baseline case: 86% of the task's few conversations were directive, but
        # Anthropic's coverage is 0.0. The old code showed "High".
        item = task_breakdown([
            row("ai_task_penetration", "penetration", 0.0),
            row("ai_task_impact", "directive", 0.857),
        ])
        self.assertEqual(item["ai_coverage"], "Not covered")
        self.assertEqual(item["score"], 0.0)

    def test_percent_metric_alone_gives_no_data(self):
        item = task_breakdown([row("ai_task_impact", "pct", 0.7)])
        self.assertEqual(item["ai_coverage"], "No data")

    def test_exact_wording_wins(self):
        # Anthropic's file has both wordings of this task with different values. The old
        # code kept the higher value (1.0); the wording shown to the user must win instead.
        displayed = "Maintain customer records using automated systems."
        item = task_breakdown([
            row("ai_task_penetration", "penetration", 1.0, "Maintain customer records, using automated systems."),
            row("ai_task_penetration", "penetration", 0.7239, displayed),
        ], task=displayed)
        self.assertEqual(item["score"], 0.7239)

OCCUPATION_ROWS = [
    {"metric_name": "observed_exposure", "metric_value": 0.31},
    {"metric_name": "pct", "metric_value": 4.2, "metric_unit": "percent"},
    {"metric_name": "percent_users", "metric_value": 0.5, "metric_unit": "percent"},
]


class ObservedExposureTest(unittest.TestCase):
    def test_ignores_metrics_that_are_not_observed_exposure(self):
        self.assertEqual(_observed_exposure(OCCUPATION_ROWS), 0.31)

    def test_none_without_an_observed_exposure_row(self):
        self.assertIsNone(_observed_exposure(OCCUPATION_ROWS[1:]))



def impact(scores, gradient=None, claims=0):
    """An ai_impact dict with these task coverage values (None: no Anthropic row) and this ILO gradient."""
    rows = [{"score_type": "anthropic_task_coverage", "score": s} if s is not None else {"score_type": "no_coverage_data"}
            for s in scores]
    return {"task_breakdown": rows, "ilo_exposure": {"gradient": gradient} if gradient else None,
            "research_claims": [{}] * claims}


class AiSnapshotTest(unittest.TestCase):
    """The snapshot's sentence compares the sources by a fixed rule, never averages them (ROADMAP 9.2, D5)."""

    def verdict(self, scores, gradient=None):
        return ai_snapshot(impact(scores, gradient))["verdict"]

    def test_counts_tasks_with_use_and_ignores_tasks_without_data(self):
        snapshot = ai_snapshot(impact([1, 0.5, 0, None], "Gradient 2", claims=2))
        self.assertEqual((snapshot["tasks_seen"], snapshot["tasks_scored"]), (2, 3))
        self.assertEqual((snapshot["ilo_level"], snapshot["research_count"]), ("medium", 2))

    def test_sources_agree_on_high_reach(self):
        self.assertEqual(self.verdict([1, 1, 0], "Gradient 4"), "high_reach")

    def test_no_claude_use_but_experts_say_exposed_is_a_disagreement_not_safety(self):
        # Legal Secretaries in your printout: every task 0, ILO gradient 3
        self.assertEqual(self.verdict([0, 0, 0], "Gradient 3"), "disagree_unseen")

    def test_much_claude_use_but_low_expert_rating_is_a_disagreement(self):
        self.assertEqual(self.verdict([1, 0.5], "Gradient 1"), "disagree_used")

    def test_little_reach_from_both(self):
        self.assertEqual(self.verdict([0, 0], "Not Exposed"), "low_reach")

    def test_one_source_alone_decides_when_the_other_is_missing(self):
        self.assertEqual(self.verdict([None, None], "Gradient 4"), "high_reach")
        self.assertEqual(self.verdict([0, 0]), "low_reach")

    def test_mixed_evidence_is_partial(self):
        self.assertEqual(self.verdict([1, 0, 0], "Gradient 3"), "partial")
        self.assertEqual(self.verdict([0, 0], "Gradient 2"), "partial")

    def test_no_evidence_at_all(self):
        self.assertEqual(self.verdict([None]), "none")


if __name__ == "__main__":
    unittest.main()
