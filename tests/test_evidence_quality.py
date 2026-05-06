from __future__ import annotations

import unittest

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.evidence_quality import compute_evidence_quality_features
from tests.helpers import PROJECT_ROOT


class EvidenceQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(PROJECT_ROOT / "config" / "params.yaml")

    def test_demo_data_does_not_exceed_confidence_ceiling(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0001"],
                "source_database": ["example_curated_demo"],
                "data_realism_flag": ["demo_only"],
            }
        )

        result = compute_evidence_quality_features(df, self.config)

        self.assertLessEqual(float(result.loc[0, "confidence_ceiling"]), 0.40)
        self.assertLessEqual(float(result.loc[0, "evidence_quality_score"]), 0.40)
        self.assertIn("demo_data_used", result.loc[0, "audit_flags"])

    def test_controlled_provider_without_external_evidence_is_capped(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0002"],
                "clinical_impact_database": ["computed_controlled_therapeutic_context_v2"],
                "confidence_source_class": ["controlled"],
            }
        )

        result = compute_evidence_quality_features(df, self.config)

        self.assertLessEqual(float(result.loc[0, "confidence_ceiling"]), 0.50)
        self.assertLessEqual(float(result.loc[0, "evidence_quality_score"]), 0.50)
        self.assertEqual(result.loc[0, "evidence_source_type"], "controlled_provider")
        self.assertIn("controlled_provider_only", result.loc[0, "audit_flags"])

    def test_external_and_curated_sources_raise_evidence_quality(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0003"],
                "localization_database": ["computed_uniprot_api_v1"],
                "clinical_impact_evidence_type": ["curated_literature"],
                "clinical_impact_evidence_reference": ["doi:10.example/source"],
            }
        )

        result = compute_evidence_quality_features(df, self.config)

        self.assertGreater(float(result.loc[0, "evidence_quality_score"]), 0.35)
        self.assertGreaterEqual(float(result.loc[0, "confidence_ceiling"]), 0.80)
        self.assertIn("external_evidence_present", result.loc[0, "audit_flags"])
        self.assertIn("curated_literature_present", result.loc[0, "audit_flags"])

    def test_experimental_support_allows_high_confidence(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0004"],
                "evidence_source_type": ["experimental"],
                "evidence": ["validated knockout assay"],
                "experimental_support": [True],
            }
        )

        result = compute_evidence_quality_features(df, self.config)

        self.assertEqual(float(result.loc[0, "confidence_ceiling"]), 1.0)
        self.assertGreater(float(result.loc[0, "evidence_quality_score"]), 0.20)
        self.assertEqual(result.loc[0, "evidence_source_type"], "experimental")
        self.assertIn("experimental_support_present", result.loc[0, "audit_flags"])

    def test_conflicts_generate_audit_flags(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0005"],
                "localization_database": ["computed_uniprot_api_v1"],
                "clinical_impact_evidence_type": ["curated_literature"],
                "conflicting_evidence": [True],
            }
        )

        result = compute_evidence_quality_features(df, self.config)

        self.assertIn("conflicting_evidence", result.loc[0, "audit_flags"])
        self.assertIn("conflicting evidence", result.loc[0, "evidence_notes"])


if __name__ == "__main__":
    unittest.main()
