"""When an LLM call fails, the app falls back to template text. These tests check
that the fallback still works and that the failure is logged, not swallowed.

Run from the project root:

    python -m unittest discover -s tests
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from career_rag.interest_profiler_local import build_profile_result
from career_rag.ip_final_report import _day_in_life
from career_rag.ip_followup_agent import complete_followup_refinement
from career_rag.ui_i18n import _translate_to_turkish_cached


class FailingProvider:
    available = True

    def complete(self, *args, **kwargs):
        raise RuntimeError("quota exceeded")


class LlmFallbackTest(unittest.TestCase):
    def test_day_in_life_logs_and_uses_template(self):
        details = {"occupation_title": "Accountants", "tasks": ["Prepare tax returns."], "work_context": []}
        with self.assertLogs("career_rag.ip_final_report", level="WARNING") as logs:
            text = _day_in_life(details, FailingProvider())
        self.assertIn("quota exceeded", logs.output[0])
        self.assertTrue(text)

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

    def test_translation_logs_and_returns_english(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("rate limit")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch("openai.OpenAI", return_value=client):
            with self.assertLogs("career_rag.ui_i18n", level="WARNING") as logs:
                text = _translate_to_turkish_cached("A unique sentence for this test.", "test")
        self.assertIn("rate limit", logs.output[0])
        self.assertEqual(text, "A unique sentence for this test.")


if __name__ == "__main__":
    unittest.main()
