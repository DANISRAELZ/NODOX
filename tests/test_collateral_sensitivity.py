from __future__ import annotations

import unittest

import pandas as pd

from src.nodos_funcionales.collateral_sensitivity import compute_collateral_sensitivity_features
from src.nodos_funcionales.config import load_config
from tests.helpers import PROJECT_ROOT


class CollateralSensitivityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(PROJECT_ROOT / "config" / "params.yaml")

    def test_biofilm_node_recommends_antibiofilm_or_beta_lactam_combination(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0001"],
                "gene": ["algD"],
                "product": ["alginate biofilm matrix biosynthesis enzyme"],
                "biofilm_persistence_score": [0.90],
            }
        )

        result = compute_collateral_sensitivity_features(df, self.config)

        self.assertEqual(
            result.loc[0, "recommended_combination_class"],
            "antibiofilm_or_beta_lactam_combination",
        )
        self.assertIn("beta-lactams", result.loc[0, "combination_rationale"])
        self.assertIn("collateral_sensitivity_rule_based_inference", result.loc[0, "audit_flags"])

    def test_oxidative_stress_node_recommends_oxidative_damage_adjuvant(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0002"],
                "gene": ["katA"],
                "product": ["catalase oxidative stress response protein"],
                "oxidative_stress_relevance_score": [0.85],
            }
        )

        result = compute_collateral_sensitivity_features(df, self.config)

        self.assertEqual(result.loc[0, "recommended_combination_class"], "oxidative_damage_adjuvant")
        self.assertIn("oxidative damage", result.loc[0, "combination_rationale"])

    def test_iron_node_generates_nutritional_immunity_rationale(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0003"],
                "gene": ["pvdA"],
                "product": ["pyoverdine siderophore iron acquisition enzyme"],
                "nutritional_immunity_escape_score": [0.95],
            }
        )

        result = compute_collateral_sensitivity_features(df, self.config)

        self.assertEqual(
            result.loc[0, "recommended_combination_class"],
            "nutritional_immunity_or_siderophore_strategy",
        )
        self.assertIn("nutritional-immunity", result.loc[0, "combination_rationale"])

    def test_unknown_rule_does_not_break_pipeline(self) -> None:
        df = pd.DataFrame({"protein_id": ["PA0004"], "gene": ["hypothetical"]})

        result = compute_collateral_sensitivity_features(df, self.config)

        self.assertEqual(result.loc[0, "recommended_combination_class"], "unknown")
        self.assertFalse(bool(result.loc[0, "escape_creates_vulnerability"]))
        self.assertEqual(float(result.loc[0, "collateral_sensitivity_score"]), 0.0)
        self.assertIn("collateral_sensitivity_no_rule_available", result.loc[0, "audit_flags"])


if __name__ == "__main__":
    unittest.main()
