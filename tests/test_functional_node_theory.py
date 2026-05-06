from __future__ import annotations

import unittest

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.functional_node_theory import compute_functional_node_theory_score
from tests.helpers import PROJECT_ROOT


class FunctionalNodeTheoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(PROJECT_ROOT / "config" / "params.yaml")

    def test_strong_node_has_high_functional_node_theory_score(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0001"],
                "functional_node_score": [0.95],
                "contextual_essentiality_score": [0.90],
                "pleiotropy_score": [0.85],
                "conservation_score": [0.90],
                "evolutionary_space_constraint_score": [0.92],
                "evidence_quality_score": [0.90],
                "confidence_ceiling": [0.95],
                "redundancy_penalty": [0.05],
                "evolutionary_escape_risk_score": [0.05],
                "biofilm_escape_penalty": [0.0],
                "horizontal_transfer_penalty": [0.0],
                "host_similarity_penalty": [0.0],
            }
        )

        result = compute_functional_node_theory_score(df, self.config)

        self.assertGreaterEqual(float(result.loc[0, "functional_node_theory_score"]), 0.75)
        self.assertEqual(result.loc[0, "functional_node_theory_label"], "high_confidence_functional_node")

    def test_central_but_redundant_node_is_penalized(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0002"],
                "functional_node_score": [0.95],
                "contextual_essentiality_score": [0.75],
                "pleiotropy_score": [0.70],
                "conservation_score": [0.70],
                "evolutionary_space_constraint_score": [0.70],
                "evidence_quality_score": [0.80],
                "confidence_ceiling": [0.90],
                "redundancy_penalty": [0.90],
                "evolutionary_escape_risk_score": [0.20],
            }
        )

        result = compute_functional_node_theory_score(df, self.config)

        self.assertLess(float(result.loc[0, "functional_node_theory_score"]), 0.75)
        self.assertEqual(result.loc[0, "functional_node_theory_label"], "central_but_redundant")
        self.assertIn("functional_node_theory_high_redundancy", result.loc[0, "audit_flags"])

    def test_high_escape_risk_lowers_score_and_label(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0003"],
                "functional_node_score": [0.85],
                "contextual_essentiality_score": [0.80],
                "pleiotropy_score": [0.75],
                "conservation_score": [0.70],
                "evolutionary_space_constraint_score": [0.65],
                "evidence_quality_score": [0.75],
                "confidence_ceiling": [0.85],
                "evolutionary_escape_risk_score": [0.90],
            }
        )

        result = compute_functional_node_theory_score(df, self.config)

        self.assertLess(float(result.loc[0, "functional_node_theory_score"]), 0.70)
        self.assertEqual(result.loc[0, "functional_node_theory_label"], "promising_but_evolutionary_risk")
        self.assertIn("functional_node_theory_high_evolutionary_risk", result.loc[0, "audit_flags"])

    def test_good_evidence_increases_reported_confidence(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0004"],
                "functional_node_score": [0.60],
                "evidence_quality_score": [0.85],
                "confidence_ceiling": [0.95],
            }
        )

        result = compute_functional_node_theory_score(df, self.config)

        self.assertEqual(float(result.loc[0, "functional_node_theory_confidence"]), 0.85)
        self.assertNotEqual(result.loc[0, "functional_node_theory_label"], "insufficient_evidence")

    def test_demo_data_limits_reported_confidence(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0005"],
                "functional_node_score": [0.90],
                "contextual_essentiality_score": [0.90],
                "evolutionary_space_constraint_score": [0.90],
                "evidence_quality_score": [0.90],
                "confidence_ceiling": [0.40],
            }
        )

        result = compute_functional_node_theory_score(df, self.config)

        self.assertEqual(float(result.loc[0, "functional_node_theory_confidence"]), 0.40)
        self.assertIn("functional_node_theory_confidence_limited", result.loc[0, "audit_flags"])

    def test_score_is_between_zero_and_one(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0006", "PA0007"],
                "functional_node_score": [2.0, -1.0],
                "contextual_essentiality_score": [2.0, -1.0],
                "evidence_quality_score": [2.0, -1.0],
                "redundancy_penalty": [2.0, -1.0],
                "evolutionary_escape_risk_score": [2.0, -1.0],
            }
        )

        result = compute_functional_node_theory_score(df, self.config)

        self.assertTrue(result["functional_node_theory_score"].between(0, 1).all())
        self.assertTrue(result["functional_node_theory_confidence"].between(0, 1).all())


if __name__ == "__main__":
    unittest.main()
