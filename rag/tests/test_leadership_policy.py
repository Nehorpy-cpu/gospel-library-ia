from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.leadership import (  # noqa: E402
    CURRENT_LEADERSHIP_REFERENCE,
    is_current_leadership_query,
    leadership_system_policy,
)
from app.rag.prompts import QUERY_REWRITE_SYSTEM, SYSTEM_PROMPT  # noqa: E402


class LeadershipPolicyTest(unittest.TestCase):
    def test_current_leadership_reference_contains_2026_first_presidency(self):
        names = [leader["name"] for leader in CURRENT_LEADERSHIP_REFERENCE["first_presidency"]]

        self.assertEqual(CURRENT_LEADERSHIP_REFERENCE["reference_year"], 2026)
        self.assertIn("Dallin H. Oaks", names)
        self.assertIn("Henry B. Eyring", names)
        self.assertIn("D. Todd Christofferson", names)

    def test_current_leadership_reference_contains_current_twelve(self):
        twelve = CURRENT_LEADERSHIP_REFERENCE["quorum_of_the_twelve"]

        self.assertIn("David A. Bednar", twelve)
        self.assertIn("Patrick Kearon", twelve)
        self.assertIn("Gérald Caussé", twelve)
        self.assertIn("Clark G. Gilbert", twelve)

    def test_system_prompt_requires_official_verification(self):
        policy = leadership_system_policy()

        self.assertIn("informacion sensible al tiempo", policy)
        self.assertIn("fuentes oficiales recientes", policy)
        self.assertIn("Dallin H. Oaks", SYSTEM_PROMPT)
        self.assertIn("Russell M. Nelson", SYSTEM_PROMPT)

    def test_leadership_queries_are_detected(self):
        self.assertTrue(is_current_leadership_query("Quienes integran la Primera Presidencia actual?"))
        self.assertTrue(is_current_leadership_query("Current leadership of the Quorum of the Twelve"))
        self.assertFalse(is_current_leadership_query("Explica Alma 32 sobre la fe"))

    def test_query_rewrite_includes_official_leadership_terms(self):
        self.assertIn("liderazgo general vigente", QUERY_REWRITE_SYSTEM)
        self.assertIn("fuentes oficiales", QUERY_REWRITE_SYSTEM)
        self.assertIn("recientes", QUERY_REWRITE_SYSTEM)


if __name__ == "__main__":
    unittest.main()
