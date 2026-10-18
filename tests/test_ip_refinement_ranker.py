"""Tests for career_rag/ip_refinement_ranker.py. Run from the project root:

    python -m unittest discover -s tests
"""

import unittest
from unittest.mock import patch

from career_rag import ip_refinement_ranker

OCCUPATION_ROWS = [
    {"doc_type": "ai_occupation_impact", "metric_name": "observed_exposure", "metric_value": 0.3},
    {"doc_type": "ai_occupation_impact", "metric_name": "pct", "metric_value": 4.2, "metric_unit": "percent"},
]


def preferences_from(answer):
    return ip_refinement_ranker.extract_structured_preferences({"questions_asked": [{"answer": answer}]})


class KeywordMatchingTest(unittest.TestCase):
    # (answer, preference label, should it be detected?)
    CASES = [
        ("I enjoy training new staff and paying attention to detail", "ai-aware career planning", False),
        ("I want to understand how AI will change my job", "ai-aware career planning", True),
        ("I like to start small projects and take part in things", "creative design or writing", False),
        ("I am an artistic person", "creative design or writing", True),
        ("Artificial intelligence interests me", "creative design or writing", False),
        ("I read about space before breakfast", "fast-paced projects", False),
        ("I like a fast paced day", "fast-paced projects", True),
        ("I like fixing bikes", "hands-on technical work", True),
        ("The aftermath of the project taught me patience", "data and numbers", False),
        ("I studied mathematics", "data and numbers", True),
    ]

    def test_keywords_match_words_not_parts_of_words(self):
        for answer, label, expected in self.CASES:
            self.assertEqual(label in preferences_from(answer), expected, answer)

    def test_interest_letters_in_the_summaries_are_not_an_ai_preference(self):
        # "AI" here means Artistic + Investigative (ROADMAP 10.12)
        refinement = {
            "questions_asked": [{"id": "structure_preference", "answer": "no clear agenda sounds good"}],
            "final_refinement": {"key_sub_preferences": ["structure_preference: AI - no clear agenda sounds good"]},
        }
        self.assertNotIn("ai-aware career planning", ip_refinement_ranker.extract_structured_preferences(refinement))
        self.assertEqual(ip_refinement_ranker._preference_text(refinement), "no clear agenda sounds good")

    def test_training_is_not_an_ai_preference(self):
        with patch.object(ip_refinement_ranker, "_local_ai_rows_for_soc", return_value=OCCUPATION_ROWS):
            self.assertEqual(ip_refinement_ranker._ai_preference_score("I enjoy training people", "x"), 0.5)


class AiPreferenceScoreTest(unittest.TestCase):
    def score(self, preference_text):
        with patch.object(ip_refinement_ranker, "_local_ai_rows_for_soc", return_value=OCCUPATION_ROWS):
            return ip_refinement_ranker._ai_preference_score(preference_text, "13-2011.00")

    def test_stability_preference_uses_observed_exposure_only(self):
        self.assertAlmostEqual(self.score("I want job stability"), 0.7)

    def test_automation_interest_uses_observed_exposure_only(self):
        self.assertAlmostEqual(self.score("future proof technology work"), 0.3)


class CommonWordsTest(unittest.TestCase):
    """Words in at least a quarter of the careers' texts don't count (CHANGELOG 102)."""

    def test_words_in_almost_every_career_are_listed(self):
        common = ip_refinement_ranker._common_words()
        self.assertTrue({"making", "people", "data"} <= common["tasks"])  # 96%, 69%, 57% of careers
        self.assertNotIn("music", common["tasks"])  # 2%: it tells careers apart
        self.assertNotIn("software", common["tasks"])

    def test_a_common_word_shared_with_a_career_scores_nothing(self):
        common = ip_refinement_ranker._common_words()["tasks"]
        activity = ["Making Decisions and Solving Problems"]
        self.assertAlmostEqual(ip_refinement_ranker._text_similarity("making it up as i go", activity), 1 / 6)  # before
        self.assertEqual(ip_refinement_ranker._text_similarity("making it up as i go", activity, common), 0.0)
        self.assertAlmostEqual(ip_refinement_ranker._text_similarity("I love music", ["Compose music."], common), 1 / 6)


class WorkSettingTest(unittest.TestCase):
    """The work-setting part reads O*NET's ratings, not the work-context texts (CHANGELOG 103)."""

    STATISTICIANS = {"Outdoors, Exposed to All Weather Conditions": 1.1, "Outdoors, Under Cover": 1.1,
                     "Contact With Others": 3.38, "Freedom to Make Decisions": 4.19}
    REGISTERED_NURSES = {"Outdoors, Exposed to All Weather Conditions": 1.05, "Outdoors, Under Cover": 1.61,
                         "Contact With Others": 4.89, "Freedom to Make Decisions": 4.1}
    FARMWORKERS = {"Outdoors, Exposed to All Weather Conditions": 4.3, "Outdoors, Under Cover": 3.12,
                   "Contact With Others": 3.68, "Freedom to Make Decisions": 3.18}

    def fit(self, preferences, ratings):
        return ip_refinement_ranker._work_context_fit(preferences, ratings)

    def test_outdoor_work_follows_how_often_the_job_is_outdoors(self):
        # the old text rule gave Statisticians 0.85 through "Outdoors, Exposed to All Weather Conditions: Never"
        self.assertAlmostEqual(self.fit(["outdoor or field work"], self.STATISTICIANS), 0.025)
        self.assertAlmostEqual(self.fit(["outdoor or field work"], self.FARMWORKERS), 0.825)

    def test_less_contact_prefers_jobs_with_less_contact(self):
        # the old rule lowered every career, since every career has "Contact With Others"
        self.assertGreater(self.fit(["lower social intensity"], self.STATISTICIANS),
                           self.fit(["lower social intensity"], self.REGISTERED_NURSES))

    def test_no_setting_preference_or_no_rating_is_neutral(self):
        self.assertEqual(self.fit(["data and numbers"], self.STATISTICIANS), 0.5)
        self.assertEqual(self.fit(["outdoor or field work"], {}), 0.5)

    def test_little_human_interaction_is_a_wish_for_less_contact(self):
        refinement = {"questions_asked": [{"answer": "draining, little human interaction"}]}
        self.assertIn("lower social intensity", ip_refinement_ranker.extract_structured_preferences(refinement))


if __name__ == "__main__":
    unittest.main()
