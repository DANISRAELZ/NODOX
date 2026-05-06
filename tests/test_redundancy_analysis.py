from __future__ import annotations

import unittest

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.redundancy_analysis import compute_redundancy_features
from tests.helpers import PROJECT_ROOT


class RedundancyAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(PROJECT_ROOT / "config" / "params.yaml")

    def test_high_paralog_count_increases_redundancy_penalty(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0001"],
                "paralog_count": [5],
                "pathway_alternative_count": [2],
                "functional_backup_score": [0.70],
                "metabolic_bypass_score": [0.60],
                "regulatory_bypass_score": [0.80],
                "conservation_score": [0.40],
                "essentiality_score": [0.30],
            }
        )

        result = compute_redundancy_features(df, self.config)

        self.assertGreaterEqual(float(result.loc[0, "redundancy_penalty"]), 0.60)

    def test_node_without_alternative_routes_has_low_redundancy_penalty(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0002"],
                "paralog_count": [0],
                "pathway_alternative_count": [0],
                "functional_backup_score": [0.0],
                "metabolic_bypass_score": [0.0],
                "regulatory_bypass_score": [0.0],
                "conservation_score": [0.95],
                "essentiality_score": [0.95],
            }
        )

        result = compute_redundancy_features(df, self.config)

        self.assertLessEqual(float(result.loc[0, "redundancy_penalty"]), 0.10)

    def test_missing_data_generates_audit_flags(self) -> None:
        df = pd.DataFrame({"protein_id": ["PA0003"]})

        result = compute_redundancy_features(df, self.config)

        self.assertIn("audit_flags", result.columns)
        self.assertIn("redundancy_data_missing", result.loc[0, "audit_flags"])
        self.assertTrue(result["redundancy_penalty"].between(0, 1).all())

    def test_scores_are_clamped_between_zero_and_one(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0004"],
                "paralog_count": [999],
                "pathway_alternative_count": [999],
                "functional_backup_score": [3.0],
                "metabolic_bypass_score": [2.0],
                "regulatory_bypass_score": [-1.0],
            }
        )

        result = compute_redundancy_features(df, self.config)

        for column in [
            "functional_backup_score",
            "metabolic_bypass_score",
            "regulatory_bypass_score",
            "redundancy_penalty",
        ]:
            self.assertTrue(result[column].between(0, 1).all(), column)


if __name__ == "__main__":
    unittest.main()
