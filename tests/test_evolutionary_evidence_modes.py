
from __future__ import annotations

import math
import unittest
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.evolutionary_escape_risk import (
    compute_evolutionary_escape_risk_features,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class EvolutionaryEvidenceModeTests(unittest.TestCase):
    def test_proxy_only_inputs_do_not_create_supported_penalty(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["p1"],
                "gene": ["g1"],
                "meta_priority_score": [0.8],
                "essentiality_support": [1.0],
                "conservation_score": [0.8],
            }
        )
        result = compute_evolutionary_escape_risk_features(df, {})
        self.assertEqual(
            result.loc[0, "evolutionary_escape_evidence_mode"],
            "proxy_hypothesis_only",
        )
        self.assertTrue(
            math.isnan(float(result.loc[0, "evolutionary_escape_supported_score"]))
        )
        self.assertGreater(
            float(result.loc[0, "evolutionary_escape_proxy_penalty_applied"]),
            0.0,
        )
        self.assertEqual(
            float(result.loc[0, "evolutionary_escape_supported_penalty_applied"]),
            0.0,
        )
        self.assertEqual(
            float(result.loc[0, "evolutionary_supported_adjusted_meta_priority_score"]),
            0.8,
        )

    def test_numeric_value_marked_derived_is_not_explicit(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["p1"],
                "gene": ["g1"],
                "meta_priority_score": [0.8],
                "functional_redundancy_escape_score": [0.0],
                "functional_redundancy_escape_score_is_explicit": [False],
                "functional_redundancy_escape_score_source_type": ["missing"],
            }
        )
        result = compute_evolutionary_escape_risk_features(df, {})
        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_explicit_variable_count"]),
            0,
        )
        self.assertEqual(
            result.loc[0, "evolutionary_escape_supported_status"],
            "unknown_missing_evidence",
        )
        self.assertEqual(
            float(result.loc[0, "evolutionary_escape_supported_penalty_applied"]),
            0.0,
        )

    def test_three_explicit_variables_enable_supported_score(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["p1"],
                "gene": ["g1"],
                "meta_priority_score": [0.8],
                "mutation_tolerance_score": [0.9],
                "functional_redundancy_escape_score": [0.7],
                "fitness_cost_of_escape": [0.2],
                "mutation_tolerance_score_is_explicit": [True],
                "functional_redundancy_escape_score_is_explicit": [True],
                "fitness_cost_of_escape_is_explicit": [True],
            }
        )
        result = compute_evolutionary_escape_risk_features(
            df,
            {"evolutionary_escape_risk": {"minimum_explicit_variables": 3}},
        )
        self.assertEqual(
            result.loc[0, "evolutionary_escape_evidence_mode"],
            "supported",
        )
        self.assertEqual(
            result.loc[0, "evolutionary_escape_supported_status"],
            "sufficient_explicit_evidence",
        )
        self.assertFalse(
            math.isnan(float(result.loc[0, "evolutionary_escape_supported_score"]))
        )
        self.assertGreater(
            float(result.loc[0, "evolutionary_escape_supported_penalty_applied"]),
            0.0,
        )
        self.assertLess(
            float(result.loc[0, "evolutionary_supported_adjusted_meta_priority_score"]),
            0.8,
        )

    def test_legacy_score_is_preserved_as_proxy_alias(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["p1"],
                "gene": ["g1"],
                "meta_priority_score": [0.8],
                "mutation_tolerance_score": [0.7],
                "functional_redundancy_escape_score": [0.6],
                "compensatory_pathway_score": [0.5],
                "fitness_cost_of_escape": [0.4],
                "evolutionary_constraint_score": [0.3],
                "resistance_emergence_risk": [0.6],
                "multi_node_dependency_score": [0.2],
            }
        )
        result = compute_evolutionary_escape_risk_features(df, {})
        self.assertAlmostEqual(
            float(result.loc[0, "evolutionary_escape_risk_score"]),
            float(result.loc[0, "evolutionary_escape_proxy_score"]),
            places=12,
        )
        self.assertAlmostEqual(
            float(result.loc[0, "evolutionary_escape_penalty_applied"]),
            float(result.loc[0, "evolutionary_escape_proxy_penalty_applied"]),
            places=12,
        )

    def test_scoring_exports_evidence_mode_columns(self) -> None:
        scoring_text = (
            PROJECT_ROOT / "src" / "nodos_funcionales" / "scoring.py"
        ).read_text(encoding="utf-8")
        for column in [
            "evolutionary_escape_proxy_score",
            "evolutionary_escape_supported_score",
            "evolutionary_escape_evidence_mode",
            "evolutionary_escape_supported_penalty_applied",
            "evolutionary_supported_adjusted_meta_priority_score",
        ]:
            with self.subTest(column=column):
                self.assertIn(f'"{column}"', scoring_text)


if __name__ == "__main__":
    unittest.main()
