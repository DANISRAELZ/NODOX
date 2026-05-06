from __future__ import annotations

import unittest

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.contextual_essentiality import compute_contextual_essentiality_features
from tests.helpers import PROJECT_ROOT


class ContextualEssentialityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(PROJECT_ROOT / "config" / "params.yaml")

    def test_iron_node_increases_under_iron_limitation_context(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0001"],
                "gene": ["pvdA"],
                "product": ["pyoverdine siderophore biosynthesis protein"],
                "infection_site": ["blood"],
                "disease_context": ["nutritional immunity with iron limitation"],
                "infection_context_score": [0.85],
                "infection_site_access_score": [0.75],
            }
        )

        result = compute_contextual_essentiality_features(df, self.config)

        self.assertGreaterEqual(float(result.loc[0, "iron_limitation_relevance_score"]), 0.85)
        self.assertGreater(float(result.loc[0, "contextual_essentiality_score"]), 0.55)

    def test_biofilm_node_increases_in_chronic_biofilm_context(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0002"],
                "gene": ["algD"],
                "product": ["alginate matrix biofilm biosynthesis enzyme"],
                "infection_site": ["lung"],
                "disease_context": ["chronic biofilm infection"],
                "biofilm_relevance_score": [0.90],
                "infection_context_score": [0.80],
            }
        )

        result = compute_contextual_essentiality_features(df, self.config)

        self.assertGreaterEqual(float(result.loc[0, "biofilm_relevance_score"]), 0.90)
        self.assertGreater(float(result.loc[0, "contextual_essentiality_score"]), 0.50)

    def test_missing_context_does_not_break_and_is_audited(self) -> None:
        df = pd.DataFrame({"protein_id": ["PA0003"], "gene": ["unknown"]})

        result = compute_contextual_essentiality_features(df, self.config)

        for column in [
            "infection_site_relevance_score",
            "host_stress_relevance_score",
            "iron_limitation_relevance_score",
            "oxidative_stress_relevance_score",
            "intracellular_survival_score",
            "biofilm_relevance_score",
            "therapy_site_context_score",
            "contextual_essentiality_score",
        ]:
            self.assertIn(column, result.columns)
            self.assertTrue(result[column].between(0, 1).all(), column)
        self.assertIn("contextual_essentiality_context_missing", result.loc[0, "audit_flags"])

    def test_controlled_context_is_audited_without_confidence_boost(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0004"],
                "gene": ["katA"],
                "product": ["catalase oxidative stress response"],
                "infection_site": ["intracellular inflammatory niche"],
                "infection_context_score": [0.80],
                "therapy_site_context_database": ["computed_controlled_therapeutic_context_v1"],
                "evidence_quality_score": [0.20],
            }
        )

        result = compute_contextual_essentiality_features(df, self.config)

        self.assertEqual(float(result.loc[0, "evidence_quality_score"]), 0.20)
        self.assertIn(
            "contextual_essentiality_controlled_context_used_no_confidence_boost",
            result.loc[0, "audit_flags"],
        )


if __name__ == "__main__":
    unittest.main()
