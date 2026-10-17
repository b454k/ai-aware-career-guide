"""Tests for the next steps per career, built by a stated rule (ROADMAP 9.7). Run from the project root:

    python -m pytest
"""

import unittest

from career_rag.ip_final_report import _next_steps

STATISTICIANS = "15-2041.00"  # in-demand tools include SAS JMP (1 occupation) and Microsoft Excel (about 340)
SHIP_CAPTAINS = "53-5021.00"  # in demand: Microsoft Office software only
DETAILS = {"knowledge": ["Transportation [2]", "Public Safety and Security [2]", "Geography [2]"]}


def breakdown(*rows):
    return {"task_breakdown": [{"task": task, "ai_coverage": coverage} for task, coverage in rows]}


class NextStepsTest(unittest.TestCase):
    def test_specific_tools_first_and_no_general_office_software(self):
        tools = _next_steps(STATISTICIANS, {}, {})[0]
        self.assertIn("SAS JMP", tools)
        self.assertNotIn("Microsoft Excel", tools)

    def test_a_career_with_only_office_software_gets_its_knowledge_areas(self):
        step = _next_steps(SHIP_CAPTAINS, DETAILS, {})[0]
        self.assertIn("Transportation, Public Safety and Security", step)
        self.assertNotIn("Geography", step)

    def test_the_ai_step_quotes_a_covered_task_and_the_try_step_another(self):
        steps = _next_steps(SHIP_CAPTAINS, DETAILS, breakdown(("Steer the ship.", "Not covered"), ("Keep logs.", "Covered: mostly automation")))
        self.assertIn("Claude for “Keep logs”", steps[1])
        self.assertIn("includes “Steer the ship”", steps[2])

    def test_no_ai_step_without_a_covered_task(self):
        steps = _next_steps(SHIP_CAPTAINS, DETAILS, breakdown(("Steer the ship.", "Not covered"), ("Keep logs.", "No data")))
        self.assertEqual(len(steps), 2)
        self.assertIn("“Steer the ship”", steps[1])

    def test_turkish(self):
        step = _next_steps(SHIP_CAPTAINS, DETAILS, {}, "tr")[0]
        self.assertIn("bilgi alanlarını geliştir", step)


if __name__ == "__main__":
    unittest.main()
