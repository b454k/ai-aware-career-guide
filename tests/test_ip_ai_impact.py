"""Tests for career_rag/ip_ai_impact.py. Run from the project root:

    python -m unittest discover -s tests
"""

import unittest

from career_rag.ip_ai_impact import _future_outlook_summary, _observed_exposure

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

    def test_summary_reports_the_observed_exposure_value(self):
        summary = _future_outlook_summary(
            display_title="Accountants",
            resolved_onet_title="Accountants",
            occupation_rows=OCCUPATION_ROWS,
            used_retrieved=True,
            anthropic_id=1,
            nber_id=2,
        )
        self.assertIn("observed exposure of 0.31", summary)
        self.assertNotIn("4.2", summary)


if __name__ == "__main__":
    unittest.main()
