"""Tests for the robot study panel (ROADMAP 10.14). Run from the project root:

    python -m unittest discover -s tests
"""

import csv
import unittest
from collections import defaultdict

from career_rag.config import ROBOT_EXPOSURE_PATH, ROBOT_TASKS_PATH
from career_rag.ip_ai_impact import ai_snapshot
from career_rag.ui_i18n import robot_exposure_lines

WELDERS = {"index": 0.962, "physical_share": 0.9253, "e1_share": 0.839, "e2_share": 0.0616, "e3_share": 0.0, "tasks": []}
STATISTICIANS = {"index": 0.0, "physical_share": 0.0, "e1_share": 0.0, "e2_share": 0.0, "e3_share": 0.0, "tasks": []}


class RobotLinesTest(unittest.TestCase):
    def test_shares_by_setting_and_the_index(self):
        self.assertEqual(robot_exposure_lines(WELDERS, "en"), [
            "93% of this job's working time goes to physical tasks.",
            "Robots have been shown doing tasks worth 90% of its working time: 84% only in a purpose-built robot "
            "cell, 6% in a structured workplace.",
            "The study's robot exposure index: 0.96 of 3.",
        ])
        self.assertIn("3 üzerinden 0,96", robot_exposure_lines(WELDERS, "tr")[-1])

    def test_a_job_without_physical_tasks_gets_one_line(self):
        self.assertEqual(len(robot_exposure_lines(STATISTICIANS, "en")), 1)
        self.assertEqual(ai_snapshot({"robot_exposure": STATISTICIANS})["robot_level"], "not_physical")
        self.assertEqual(ai_snapshot({"robot_exposure": WELDERS})["robot_level"], "some")
        self.assertIsNone(ai_snapshot({})["robot_level"])  # a report saved before the panel


class RobotFilesTest(unittest.TestCase):
    def test_index_is_the_time_weighted_tier_score(self):
        # E1 = 1, E2 = 2, E3 = 3, each weighted by its share of working time (the study's README)
        with ROBOT_EXPOSURE_PATH.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 923)
        for row in rows:
            shares = [float(row[key]) for key in ("e1_share", "e2_share", "e3_share")]
            self.assertAlmostEqual(float(row["robot_exposure_index"]), shares[0] + 2 * shares[1] + 3 * shares[2],
                                   delta=0.002, msg=row["onetsoc_code"])
            self.assertLessEqual(sum(shares), float(row["physical_share"]) + 0.001, row["onetsoc_code"])

    def test_at_most_five_exposed_tasks_largest_share_first_each_with_a_robot(self):
        tasks = defaultdict(list)
        with ROBOT_TASKS_PATH.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                tasks[row["onetsoc_code"]].append(row)
                self.assertIn(row["exposure_tier"], ("E1", "E2", "E3"))
                self.assertIn(row["robot_maturity"], ("deployed", "commercial", "demo"))
                self.assertTrue(row["robot_system"] and row["robot_url"].startswith("http"), row["task_id"])
        for code, rows in tasks.items():
            shares = [float(row["time_share"]) for row in rows]
            self.assertLessEqual(len(rows), 5, code)
            self.assertEqual(shares, sorted(shares, reverse=True), code)


if __name__ == "__main__":
    unittest.main()
