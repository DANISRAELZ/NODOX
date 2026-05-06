from __future__ import annotations

import unittest

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.validation import validate_table
from tests.helpers import PROJECT_ROOT


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(PROJECT_ROOT / "config" / "params.yaml")

    def test_rejects_invalid_virulence_range(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["P1"],
                "gene": ["gene1"],
                "virulence_score": [1.5],
            }
        )
        with self.assertRaises(ValueError):
            validate_table(df, "virulence", self.config)

    def test_rejects_invalid_localization_label(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["P1"],
                "gene": ["gene1"],
                "localization": ["nucleus"],
            }
        )
        with self.assertRaises(ValueError):
            validate_table(df, "localization", self.config)

    def test_phase3_evolutionary_escape_accepts_normalized_scores(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["P1"],
                "gene": ["gene1"],
                "mutational_tolerance_score": [0.20],
                "redundancy_penalty": [0.10],
                "fitness_cost_score": [0.80],
                "compensation_difficulty_score": [0.70],
                "biofilm_escape_penalty": [0.05],
                "horizontal_transfer_penalty": [0.15],
                "evolutionary_escape_risk_score": [0.25],
                "evolutionary_space_constraint_score": [0.75],
                "evidence_quality_score": [0.60],
                "confidence_ceiling": [0.65],
                "evidence_source_type": ["curated_literature"],
                "evidence_notes": ["example"],
                "audit_flags": ["manual_review"],
                "phase3_notes": ["phase3 optional input"],
            }
        )

        validated, issues = validate_table(df, "evolutionary_escape", self.config)

        self.assertFalse(any(issue["severity"] == "error" for issue in issues))
        self.assertEqual(float(validated.loc[0, "evolutionary_escape_risk_score"]), 0.25)

    def test_phase3_evolutionary_escape_rejects_out_of_range_scores(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["P1"],
                "gene": ["gene1"],
                "evolutionary_escape_risk_score": [1.20],
            }
        )

        with self.assertRaises(ValueError):
            validate_table(df, "evolutionary_escape", self.config)

    def test_human_homologs_accepts_reproducible_orthology_fields(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["P1"],
                "gene": ["gene1"],
                "human_homolog": [1],
                "evalue": [1.0e-40],
                "human_gene": ["HUMAN1"],
                "orthology_method": ["reciprocal_best_hit"],
                "orthology_tool": ["DIAMOND"],
                "orthology_version": ["2.1.0"],
                "orthology_reference": ["local_run_2026_05_01"],
                "orthology_query_coverage": [0.82],
                "orthology_subject_coverage": [0.79],
                "orthology_percent_identity": [46.0],
                "orthology_bitscore": [240.0],
                "orthology_confidence_score": [0.88],
            }
        )

        validated, _ = validate_table(df, "human_homologs", self.config)

        self.assertEqual(validated.loc[0, "orthology_method"], "reciprocal_best_hit")
        self.assertAlmostEqual(float(validated.loc[0, "orthology_confidence_score"]), 0.88)

    def test_redundancy_layer_accepts_curated_phase3_inputs(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["P1"],
                "gene": ["gene1"],
                "paralog_count": [2],
                "pathway_alternative_count": [1],
                "functional_backup_score": [0.40],
                "metabolic_bypass_score": [0.30],
                "regulatory_bypass_score": [0.20],
                "redundancy_evidence_quality_score": [0.70],
                "redundancy_confidence_ceiling": [0.80],
            }
        )

        validated, _ = validate_table(df, "redundancy", self.config)

        self.assertEqual(float(validated.loc[0, "paralog_count"]), 2.0)
        self.assertEqual(float(validated.loc[0, "functional_backup_score"]), 0.40)


if __name__ == "__main__":
    unittest.main()
