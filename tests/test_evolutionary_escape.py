from __future__ import annotations

import unittest

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.evolutionary_escape import compute_evolutionary_escape_features
from tests.helpers import PROJECT_ROOT


class EvolutionaryEscapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(PROJECT_ROOT / "config" / "params.yaml")

    def test_conserved_essential_non_redundant_node_has_high_space_constraint(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0001"],
                "essentiality_score": [0.95],
                "contextual_essentiality_score": [0.90],
                "conservation_score": [0.95],
                "pleiotropy_score": [0.85],
                "redundancy_penalty": [0.05],
                "variant_burden": [0.05],
                "known_escape_mutation_score": [0.0],
                "inferred_functional_tolerance_score": [0.10],
                "module_participation_score": [0.90],
                "paralog_count_score": [0.05],
                "alternative_pathway_score": [0.05],
                "network_centrality": [0.90],
                "biofilm_escape_penalty": [0.0],
                "horizontal_transfer_penalty": [0.0],
                "collateral_sensitivity_score": [0.75],
            }
        )

        result = compute_evolutionary_escape_features(df, self.config)

        self.assertGreaterEqual(float(result.loc[0, "evolutionary_space_constraint_score"]), 0.80)
        self.assertLessEqual(float(result.loc[0, "evolutionary_escape_risk_score"]), 0.25)

    def test_variable_redundant_biofilm_node_has_high_escape_risk(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0002"],
                "essentiality_score": [0.10],
                "contextual_essentiality_score": [0.15],
                "conservation_score": [0.10],
                "pleiotropy_score": [0.15],
                "redundancy_penalty": [0.90],
                "variant_burden": [0.90],
                "known_escape_mutation_score": [0.85],
                "inferred_functional_tolerance_score": [0.85],
                "module_participation_score": [0.10],
                "paralog_count_score": [0.90],
                "alternative_pathway_score": [0.90],
                "network_centrality": [0.15],
                "biofilm_escape_penalty": [0.90],
                "horizontal_transfer_penalty": [0.65],
                "collateral_sensitivity_score": [0.10],
            }
        )

        result = compute_evolutionary_escape_features(df, self.config)

        self.assertGreaterEqual(float(result.loc[0, "evolutionary_escape_risk_score"]), 0.75)
        self.assertLessEqual(float(result.loc[0, "evolutionary_space_constraint_score"]), 0.35)

    def test_missing_columns_do_not_break_computation_and_are_audited(self) -> None:
        df = pd.DataFrame({"protein_id": ["PA0003"], "essential": [1]})

        result = compute_evolutionary_escape_features(df, self.config)

        for column in [
            "mutational_tolerance_score",
            "fitness_cost_score",
            "compensation_difficulty_score",
            "evolutionary_escape_risk_score",
            "evolutionary_space_constraint_score",
        ]:
            self.assertIn(column, result.columns)
            self.assertTrue(result[column].between(0, 1).all(), column)
        self.assertIn("audit_flags", result.columns)
        self.assertIn("evolutionary_escape_defaults_used=", result.loc[0, "audit_flags"])

    def test_scores_are_clamped_between_zero_and_one(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0004"],
                "essentiality_score": [2.0],
                "contextual_essentiality_score": [2.0],
                "conservation_score": [-1.0],
                "pleiotropy_score": [2.0],
                "redundancy_penalty": [2.0],
                "variant_burden": [2.0],
                "biofilm_escape_penalty": [2.0],
                "horizontal_transfer_penalty": [2.0],
            }
        )

        result = compute_evolutionary_escape_features(df, self.config)

        for column in [
            "mutational_tolerance_score",
            "fitness_cost_score",
            "compensation_difficulty_score",
            "evolutionary_escape_risk_score",
            "evolutionary_space_constraint_score",
        ]:
            self.assertTrue(result[column].between(0, 1).all(), column)

    def test_penalties_reduce_evolutionary_space_constraint(self) -> None:
        base = {
            "protein_id": "PA0005",
            "essentiality_score": 0.85,
            "contextual_essentiality_score": 0.85,
            "conservation_score": 0.85,
            "pleiotropy_score": 0.80,
            "variant_burden": 0.20,
            "known_escape_mutation_score": 0.10,
            "inferred_functional_tolerance_score": 0.20,
            "module_participation_score": 0.80,
            "paralog_count_score": 0.20,
            "alternative_pathway_score": 0.20,
            "network_centrality": 0.80,
            "collateral_sensitivity_score": 0.50,
        }
        low_penalty = dict(base, redundancy_penalty=0.10, biofilm_escape_penalty=0.0, horizontal_transfer_penalty=0.0)
        high_penalty = dict(base, redundancy_penalty=0.90, biofilm_escape_penalty=0.90, horizontal_transfer_penalty=0.90)
        result = compute_evolutionary_escape_features(pd.DataFrame([low_penalty, high_penalty]), self.config)

        self.assertGreater(
            float(result.loc[0, "evolutionary_space_constraint_score"]),
            float(result.loc[1, "evolutionary_space_constraint_score"]),
        )


if __name__ == "__main__":
    unittest.main()
