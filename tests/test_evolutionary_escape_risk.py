from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.evolutionary_escape_risk import compute_evolutionary_escape_risk_features
from src.nodos_funcionales.validation import SCHEMAS, validate_table


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class EvolutionaryEscapeRiskTests(unittest.TestCase):
    def test_template_contains_expected_columns(self) -> None:
        template = pd.read_csv(PROJECT_ROOT / "data_templates" / "evolutionary_escape_risk_template.csv")
        expected = [
            "candidate_id",
            "gene",
            "protein_id",
            "organism",
            "strain",
            "mutation_tolerance_score",
            "functional_redundancy_escape_score",
            "compensatory_pathway_score",
            "fitness_cost_of_escape",
            "evolutionary_constraint_score",
            "resistance_emergence_risk",
            "multi_node_dependency_score",
            "evidence_source",
            "source_type",
            "confidence",
            "notes",
        ]
        self.assertEqual(expected, list(template.columns))
        self.assertIn("evolutionary_escape_risk", SCHEMAS)

    def test_score_rises_with_tolerance_redundancy_and_compensation(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["high", "low"],
                "gene": ["high", "low"],
                "meta_priority_score": [0.8, 0.8],
                "mutation_tolerance_score": [0.9, 0.1],
                "functional_redundancy_escape_score": [0.9, 0.1],
                "compensatory_pathway_score": [0.9, 0.1],
                "fitness_cost_of_escape": [0.1, 0.9],
                "evolutionary_constraint_score": [0.1, 0.9],
                "resistance_emergence_risk": [0.9, 0.1],
                "multi_node_dependency_score": [0.1, 0.9],
            }
        )
        scored = compute_evolutionary_escape_risk_features(df, {})
        scores = scored.set_index("protein_id")["evolutionary_escape_risk_score"]
        self.assertGreater(scores["high"], scores["low"])
        self.assertTrue(scored["evolutionary_escape_risk_score"].between(0, 1).all())

    def test_missing_explicit_data_is_calculated_with_low_confidence(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["p1"],
                "gene": ["g1"],
                "meta_priority_score": [0.7],
                "essentiality_support": [1.0],
                "conservation_score": [0.8],
            }
        )
        scored = compute_evolutionary_escape_risk_features(df, {})
        self.assertIn(
            scored.loc[0, "evolutionary_escape_risk_status"],
            {"unknown_missing_evidence", "insufficient_evidence", "derived_from_related_layers"},
        )
        self.assertEqual(scored.loc[0, "evolutionary_escape_risk_confidence"], "low")
        self.assertIn("functional_redundancy_escape_score", scored.loc[0, "evolutionary_escape_risk_missing_variables"])

    def test_penalty_is_moderate_and_can_be_disabled(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["p1"],
                "gene": ["g1"],
                "meta_priority_score": [0.8],
                "mutation_tolerance_score": [1.0],
                "functional_redundancy_escape_score": [1.0],
                "compensatory_pathway_score": [1.0],
                "fitness_cost_of_escape": [0.0],
                "evolutionary_constraint_score": [0.0],
                "resistance_emergence_risk": [1.0],
                "multi_node_dependency_score": [0.0],
            }
        )
        scored = compute_evolutionary_escape_risk_features(df, {})
        self.assertLess(scored.loc[0, "evolutionary_adjusted_meta_priority_score"], 0.8)
        self.assertLessEqual(scored.loc[0, "evolutionary_escape_penalty_applied"], 0.15)

        disabled = compute_evolutionary_escape_risk_features(
            df,
            {"evolutionary_escape_risk": {"enabled": False}},
        )
        self.assertEqual(disabled.loc[0, "evolutionary_escape_penalty_applied"], 0.0)
        self.assertEqual(disabled.loc[0, "evolutionary_adjusted_meta_priority_score"], 0.8)

    def test_validation_accepts_template_style_table(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["p1"],
                "gene": ["g1"],
                "mutation_tolerance_score": [0.2],
                "fitness_cost_of_escape": [0.9],
                "source_type": ["user"],
                "confidence": ["low"],
            }
        )
        validated, issues = validate_table(
            df,
            "evolutionary_escape_risk",
            {"validation": {"duplicate_policy": "keep_first", "strict_ranges": True}},
        )
        self.assertEqual(len(validated), 1)
        self.assertIsInstance(issues, list)


if __name__ == "__main__":
    unittest.main()
