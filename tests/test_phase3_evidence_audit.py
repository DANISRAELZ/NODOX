from __future__ import annotations

import unittest

import pandas as pd

from src.nodos_funcionales.evolutionary_escape_risk import compute_evolutionary_escape_risk_features
from src.nodos_funcionales.phase3_evidence import apply_phase3_evidence_audit, build_layer_evidence_audit
from src.nodos_funcionales.scoring import build_phase3_scores
from tests.helpers import PROJECT_ROOT
from src.nodos_funcionales.config import load_config


class Phase3EvidenceAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(PROJECT_ROOT / "config" / "params.yaml")

    def test_demo_default_only_cannot_be_strongly_supported(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["A"],
                "gene": ["a"],
                "essential": [1],
                "essentiality_source_name": ["example_demo"],
                "virulence_score": [0.9],
                "virulence_source_name": ["example_demo"],
            }
        )
        features, _, _ = apply_phase3_evidence_audit(df, self.config)
        self.assertLessEqual(float(features.loc[0, "confidence_ceiling"]), 0.10)
        self.assertEqual(int(features.loc[0, "phase3_real_evidence_layer_count"]), 0)

    def test_partial_real_evidence_has_nonzero_quality(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["A"],
                "gene": ["a"],
                "essential": [1],
                "essentiality_is_external": [True],
                "essentiality_source_name": ["deg_database"],
                "virulence_score": [0.7],
                "virulence_source_name": ["controlled_therapeutic_context_v2"],
            }
        )
        features, _, _ = apply_phase3_evidence_audit(df, self.config)
        self.assertGreater(float(features.loc[0, "evidence_quality_score"]), 0.0)
        self.assertGreaterEqual(int(features.loc[0, "phase3_real_evidence_layer_count"]), 1)

    def test_real_convergent_evidence_can_be_high_quality(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["A"],
                "gene": ["a"],
                "essential": [1],
                "virulence_score": [0.9],
                "network_centrality": [0.8],
                "infection_context_score": [0.8],
                "essentiality_is_user_supplied": [True],
                "virulence_is_external": [True],
                "virulence_source_name": ["vfdb_database"],
                "functional_network_is_external": [True],
                "functional_network_source_name": ["string_db"],
                "curated_disease_context_source_name": ["curated_literature"],
            }
        )
        features, _, _ = apply_phase3_evidence_audit(df, self.config)
        self.assertGreaterEqual(float(features.loc[0, "confidence_ceiling"]), 0.85)
        self.assertGreaterEqual(int(features.loc[0, "phase3_real_evidence_layer_count"]), 4)

    def test_real_human_homology_is_negative_evidence(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["A"],
                "gene": ["a"],
                "human_homolog": [1],
                "human_homologs_source_name": ["local_reproducible_orthology"],
            }
        )
        audit = build_layer_evidence_audit(df, self.config)
        row = audit.loc[audit["variable_name"] == "human_homolog"].iloc[0]
        self.assertTrue(bool(row["evidence_is_negative"]))
        self.assertEqual(row["evidence_source_type"], "computed_from_real_data")

    def test_missing_escape_is_unknown_not_low(self) -> None:
        result = compute_evolutionary_escape_risk_features(pd.DataFrame({"protein_id": ["A"], "gene": ["a"]}), self.config)
        self.assertEqual(result.loc[0, "evolutionary_escape_risk_status"], "unknown_missing_evidence")
        self.assertIn("Riesgo desconocido", result.loc[0, "evolutionary_escape_risk_interpretation"])


if __name__ == "__main__":
    unittest.main()
