from __future__ import annotations

import unittest

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.functional_node_theory import (
    build_functional_node_theory_audit,
    compute_functional_node_theory_score,
    meets_minimum_functional_node_evidence,
)
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
        self.assertNotEqual(result.loc[0, "functional_node_theory_label"], "high_confidence_functional_node")
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
        self.assertNotEqual(result.loc[0, "functional_node_theory_label"], "high_confidence_functional_node")
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
                "data_realism_flag": ["demo_only"],
            }
        )

        result = compute_functional_node_theory_score(df, self.config)

        self.assertEqual(float(result.loc[0, "functional_node_theory_confidence"]), 0.25)
        self.assertEqual(result.loc[0, "functional_node_theory_label"], "hypothesis_only_insufficient_evidence")
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

    def test_high_score_unresolved_evidence_is_not_high_confidence(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0008"],
                "gene": ["geneX"],
                "functional_node_score": [0.95],
                "contextual_essentiality_score": [0.95],
                "conservation_score": [0.90],
                "evolutionary_space_constraint_score": [0.90],
                "evidence_quality_score": [0.90],
                "confidence_ceiling": [0.95],
                "evidence_level": ["unresolved"],
                "source_used": ["provider_not_found"],
            }
        )

        result = compute_functional_node_theory_score(df, self.config)

        self.assertLessEqual(float(result.loc[0, "functional_node_theory_confidence"]), 0.30)
        self.assertFalse(bool(result.loc[0, "meets_minimum_functional_node_evidence"]))
        self.assertNotEqual(result.loc[0, "functional_node_theory_label"], "high_confidence_functional_node")
        self.assertIn(result.loc[0, "functional_node_theory_label"], {"unresolved_evidence_candidate", "hypothesis_only_insufficient_evidence"})

    def test_candidate_with_sufficient_multidimensional_evidence_can_be_supported(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0009"],
                "gene": ["geneY"],
                "functional_node_score": [0.88],
                "network_centrality": [0.80],
                "pathway_bottleneck_score": [0.76],
                "contextual_essentiality_score": [0.78],
                "virulence_score": [0.70],
                "conservation_score": [0.82],
                "evolutionary_space_constraint_score": [0.84],
                "redundancy_penalty": [0.10],
                "evolutionary_escape_risk_score": [0.10],
                "infection_context_score": [0.72],
                "infection_site_access_score": [0.70],
                "host_safety_score": [0.86],
                "selectivity_score": [0.82],
                "evidence_quality_score": [0.88],
                "confidence_ceiling": [0.90],
                "real_evidence_layer_count": [3],
                "data_realism_flag": ["real_or_curated"],
                "evidence_level": ["curated"],
            }
        )

        result = compute_functional_node_theory_score(df, self.config)

        self.assertTrue(bool(result.loc[0, "meets_minimum_functional_node_evidence"]))
        self.assertIn(
            result.loc[0, "functional_node_theory_label"],
            {"high_confidence_functional_node", "moderate_confidence_functional_node"},
        )
        self.assertGreater(float(result.loc[0, "functional_node_therapeutic_exploitability_score"]), 0.0)
        self.assertTrue(meets_minimum_functional_node_evidence(result.loc[0]))

    def test_audit_contains_required_interpretable_components(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0010"],
                "gene": ["geneZ"],
                "functional_node_score": [0.50],
                "evidence_quality_score": [0.50],
            }
        )

        result = compute_functional_node_theory_score(df, self.config)
        audit = build_functional_node_theory_audit(result)

        for column in [
            "functional_impact_component",
            "dependency_component",
            "redundancy_constraint_component",
            "evidence_quality_component",
            "interpretation",
        ]:
            self.assertIn(column, audit.columns)


if __name__ == "__main__":
    unittest.main()
