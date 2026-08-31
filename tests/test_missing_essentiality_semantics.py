from __future__ import annotations

import math
import unittest

import pandas as pd

from src.nodos_funcionales.evolutionary_escape import (
    compute_evolutionary_escape_features,
    compute_fitness_cost_score,
    compute_mutational_tolerance_score,
)
from src.nodos_funcionales.evolutionary_escape_risk import compute_evolutionary_escape_risk_features
from src.nodos_funcionales.scoring_components import calculate_strategy_scores


class MissingEssentialitySemanticsTests(unittest.TestCase):
    def test_antibiotic_score_omits_unknown_essentiality_and_preserves_known_rows(self) -> None:
        features = pd.DataFrame(
            {
                "essential": [math.nan, 1.0, 0.0],
                "essentiality_support": [0.5, 1.0, 0.0],
                "host_safety_score": [0.8, 0.8, 0.8],
                "conservation_score": [0.8, 0.8, 0.8],
                "small_molecule_feasibility": [0.8, 0.8, 0.8],
                "low_redundancy_score": [0.8, 0.8, 0.8],
                "evidence_confidence_score": [0.8, 0.8, 0.8],
                "dummy_antivirulence": [0.2, 0.2, 0.2],
                "dummy_functional": [0.3, 0.3, 0.3],
            }
        )
        weights = {
            "antibiotic_target": {
                "essentiality_support": 0.28,
                "host_safety_score": 0.22,
                "conservation_score": 0.18,
                "small_molecule_feasibility": 0.16,
                "low_redundancy_score": 0.10,
                "evidence_confidence_score": 0.06,
            },
            "antivirulence_target": {"dummy_antivirulence": 1.0},
            "functional_node": {"dummy_functional": 1.0},
        }

        scores, contributions = calculate_strategy_scores(features, weights)
        antibiotic = scores["antibiotic_target_score"]

        self.assertAlmostEqual(float(antibiotic.iloc[0]), 0.8, places=12)
        self.assertAlmostEqual(float(antibiotic.iloc[1]), 0.856, places=12)
        self.assertAlmostEqual(float(antibiotic.iloc[2]), 0.576, places=12)
        self.assertEqual(float(contributions["antibiotic_target_score"]["essentiality_support"].iloc[0]), 0.0)
        self.assertAlmostEqual(float(scores["functional_node_score"].iloc[0]), 0.3, places=12)

    def test_first_escape_layer_renormalizes_fitness_cost_when_essentiality_is_unknown(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["unknown", "known"],
                "gene": ["unknown", "known"],
                "meta_priority_score": [0.5, 0.5],
                "essential": [math.nan, 1.0],
                "essentiality_support": [0.5, 1.0],
                "conservation_score": [0.8, 0.8],
                "low_redundancy_score": [0.7, 0.7],
                "fitness_cost_score": [0.6, 0.6],
            }
        )

        scored = compute_evolutionary_escape_risk_features(df, {})

        expected_unknown = (0.25 * 0.8 + 0.20 * 0.7 + 0.15 * 0.6) / 0.60
        expected_known = 0.40 * 1.0 + 0.25 * 0.8 + 0.20 * 0.7 + 0.15 * 0.6
        self.assertAlmostEqual(float(scored.loc[0, "fitness_cost_of_escape"]), expected_unknown, places=12)
        self.assertAlmostEqual(float(scored.loc[1, "fitness_cost_of_escape"]), expected_known, places=12)

    def test_phase3_mutational_and_fitness_scores_omit_unknown_essentiality(self) -> None:
        df = pd.DataFrame(
            {
                "essential": [math.nan, 1.0],
                "variant_burden": [0.8, 0.8],
                "conservation_score": [0.8, 0.8],
                "known_escape_mutation_score": [0.1, 0.1],
                "inferred_functional_tolerance_score": [0.4, 0.4],
                "pleiotropy_score": [0.7, 0.7],
                "redundancy_penalty": [0.2, 0.2],
                "module_participation_score": [0.6, 0.6],
            }
        )

        mutation = compute_mutational_tolerance_score(df)
        fitness = compute_fitness_cost_score(df)

        expected_mutation_unknown = (0.30 * 0.8 + 0.25 * 0.2 + 0.20 * 0.1 + 0.10 * 0.4) / 0.85
        expected_mutation_known = 0.30 * 0.8 + 0.25 * 0.2 + 0.20 * 0.1 + 0.15 * 0.0 + 0.10 * 0.4
        expected_fitness_unknown = (0.25 * 0.8 + 0.20 * 0.7 + 0.20 * 0.8 + 0.10 * 0.6) / 0.75
        expected_fitness_known = 0.25 * 1.0 + 0.25 * 0.8 + 0.20 * 0.7 + 0.20 * 0.8 + 0.10 * 0.6

        self.assertAlmostEqual(float(mutation.iloc[0]), expected_mutation_unknown, places=12)
        self.assertAlmostEqual(float(mutation.iloc[1]), expected_mutation_known, places=12)
        self.assertAlmostEqual(float(fitness.iloc[0]), expected_fitness_unknown, places=12)
        self.assertAlmostEqual(float(fitness.iloc[1]), expected_fitness_known, places=12)

    def test_unknown_essentiality_does_not_floor_contextual_essentiality_at_midpoint(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["unknown"],
                "essential": [math.nan],
                "contextual_essentiality_score": [0.30],
                "conservation_score": [0.75],
                "pleiotropy_score": [0.55],
                "redundancy_penalty": [0.25],
                "variant_burden": [0.35],
                "known_escape_mutation_score": [0.0],
                "inferred_functional_tolerance_score": [0.45],
                "module_participation_score": [0.50],
                "paralog_count_score": [0.20],
                "alternative_pathway_score": [0.20],
                "network_centrality": [0.60],
                "biofilm_escape_penalty": [0.0],
                "horizontal_transfer_penalty": [0.0],
                "collateral_sensitivity_score": [0.0],
            }
        )
        low_default = {"phase3": {"evolutionary_escape": {"defaults": {"essentiality_score": 0.10}}}}
        high_default = {"phase3": {"evolutionary_escape": {"defaults": {"essentiality_score": 0.90}}}}

        low = compute_evolutionary_escape_features(df, low_default)
        high = compute_evolutionary_escape_features(df, high_default)

        self.assertAlmostEqual(
            float(low.loc[0, "evolutionary_space_constraint_score"]),
            float(high.loc[0, "evolutionary_space_constraint_score"]),
            places=12,
        )
        self.assertAlmostEqual(
            float(low.loc[0, "mutational_tolerance_score"]),
            float(high.loc[0, "mutational_tolerance_score"]),
            places=12,
        )
        self.assertAlmostEqual(
            float(low.loc[0, "fitness_cost_score"]),
            float(high.loc[0, "fitness_cost_score"]),
            places=12,
        )


if __name__ == "__main__":
    unittest.main()
