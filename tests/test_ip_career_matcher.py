"""Tests for O*NET's matching rule in career_rag/ip_career_matcher.py. Run from the project root:

    python -m unittest discover -s tests
"""

import unittest

from career_rag.ip_career_matcher import onet_fit_list, pearson

USER = {"Realistic": 0, "Investigative": 9, "Artistic": 0, "Social": 0, "Enterprising": 0, "Conventional": 7}


def occupation(title, scores):
    return {"career_title": title, "interest_scores": scores}


class OnetFitListTest(unittest.TestCase):
    def test_labels_follow_onets_published_cutoffs(self):
        occupations = [
            occupation("Same shape", [1, 7, 1, 1, 1, 5]),  # r ~ 1.0
            occupation("Opposite", [7, 1, 7, 7, 7, 1]),  # r < 0
        ]
        result = onet_fit_list(USER, occupations)
        self.assertEqual([m["career_title"] for m in result], ["Same shape"])
        self.assertEqual(result[0]["fit"], "Best fit")
        self.assertNotIn("interest_scores", result[0])

    def test_sorted_by_similarity_not_alphabetically(self):
        occupations = [
            occupation("A weaker match", [1, 7, 3, 1, 1, 7]),
            occupation("Z stronger match", [1, 7, 1, 1, 1, 5]),
        ]
        titles = [m["career_title"] for m in onet_fit_list(USER, occupations)]
        self.assertEqual(titles, ["Z stronger match", "A weaker match"])

    def test_good_fit_only_fills_the_list_up_to_ten(self):
        weak = [occupation(f"Weak {i}", [3, 4, 3, 4, 3, 3]) for i in range(15)]  # r ~ 0.34: Good fit
        result = onet_fit_list(USER, weak)
        self.assertEqual(len(result), 10)
        self.assertTrue(all(m["fit"] == "Good fit" for m in result))

        strong = [occupation(f"Strong {i}", [1, 7, 1, 1, 1, 5]) for i in range(12)]
        result = onet_fit_list(USER, strong + weak)
        self.assertEqual(len(result), 12)  # no limit on Best/Great, and no Good added

    def test_flat_profile_has_no_correlation(self):
        self.assertIsNone(pearson([3, 3, 3, 3, 3, 3], [1, 7, 1, 1, 1, 5]))
        self.assertEqual(onet_fit_list({}, [occupation("Any", [1, 7, 1, 1, 1, 5])]), [])


if __name__ == "__main__":
    unittest.main()
