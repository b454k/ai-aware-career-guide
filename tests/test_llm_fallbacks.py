"""When an LLM call fails, the app falls back to template text. These tests check
that the fallback still works and that the failure is logged, not swallowed.

Run from the project root:

    python -m unittest discover -s tests
"""

import unittest

from career_rag.interest_profiler_local import build_profile_result
from career_rag.ip_followup_agent import complete_followup_refinement


class FailingProvider:
    available = True

    def complete(self, *args, **kwargs):
        raise RuntimeError("quota exceeded")


class LlmFallbackTest(unittest.TestCase):
    def test_followup_analysis_logs_and_uses_template(self):
        profile = build_profile_result(
            scores={"Realistic": 1, "Investigative": 9, "Artistic": 2, "Social": 3, "Enterprising": 2, "Conventional": 7},
            current_job_zone=3,
            future_job_zone=4,
            career_matches=None,
        )
        questions = [{"id": "q1", "question": "What work do you enjoy?", "answer": "Working with data."}]
        with self.assertLogs("career_rag.ip_followup_agent", level="WARNING") as logs:
            result = complete_followup_refinement(profile, questions, provider=FailingProvider())
        self.assertIn("quota exceeded", logs.output[0])
        self.assertEqual(result["method"], "template_fallback")


if __name__ == "__main__":
    unittest.main()
