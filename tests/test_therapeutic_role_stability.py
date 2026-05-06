from __future__ import annotations

import unittest

import pandas as pd

from src.nodos_funcionales.therapeutic_role_stability import (
    build_therapeutic_role_stability_audit,
    build_therapeutic_role_stability_report,
)


class TherapeuticRoleStabilityTests(unittest.TestCase):
    def test_unchanged_roles_are_stable(self) -> None:
        features = pd.DataFrame(
            {
                "protein_id": ["A"],
                "gene": ["a"],
                "therapeutic_role": ["antivirulence_candidate"],
                "therapeutic_role_v3": ["antivirulence_candidate"],
                "meta_priority_score_v2": [0.70],
                "meta_priority_score_v3": [0.72],
                "evidence_quality_score": [0.80],
                "confidence_ceiling": [0.85],
            }
        )

        audit = build_therapeutic_role_stability_audit(features)

        self.assertIn("gene_name/protein_id", audit.columns)
        self.assertEqual(audit.loc[0, "gene_name/protein_id"], "a")
        self.assertFalse(bool(audit.loc[0, "role_changed"]))
        self.assertEqual(audit.loc[0, "stability_label"], "stable_high_confidence")

    def test_high_escape_risk_marks_evolutionary_penalty_change(self) -> None:
        features = pd.DataFrame(
            {
                "protein_id": ["B"],
                "gene": ["b"],
                "therapeutic_role": ["bactericidal_candidate"],
                "therapeutic_role_v3": ["deprioritized_escape_risk"],
                "meta_priority_score_v2": [0.80],
                "meta_priority_score_v3": [0.45],
                "evolutionary_escape_risk_score": [0.90],
                "evidence_quality_score": [0.75],
                "confidence_ceiling": [0.80],
            }
        )

        audit = build_therapeutic_role_stability_audit(features)

        self.assertTrue(bool(audit.loc[0, "role_changed"]))
        self.assertEqual(audit.loc[0, "stability_label"], "changed_due_to_evolutionary_penalty")

    def test_contextual_essentiality_marks_contextual_change(self) -> None:
        features = pd.DataFrame(
            {
                "protein_id": ["C"],
                "gene": ["c"],
                "therapeutic_role": ["low_priority_candidate"],
                "therapeutic_role_v3": ["evolutionary_robust_node"],
                "meta_priority_score_v2": [0.35],
                "meta_priority_score_v3": [0.68],
                "contextual_essentiality_score": [0.92],
                "evidence_quality_score": [0.70],
                "confidence_ceiling": [0.80],
            }
        )

        audit = build_therapeutic_role_stability_audit(features)

        self.assertEqual(audit.loc[0, "stability_label"], "changed_due_to_contextual_essentiality")

    def test_controlled_provider_only_limits_confidence_label(self) -> None:
        features = pd.DataFrame(
            {
                "protein_id": ["D"],
                "gene": ["d"],
                "therapeutic_role": ["antivirulence_candidate"],
                "therapeutic_role_v3": ["antivirulence_candidate"],
                "meta_priority_score_v2": [0.60],
                "meta_priority_score_v3": [0.60],
                "evidence_quality_score": [0.30],
                "confidence_ceiling": [0.50],
                "evidence_source_type": ["controlled_provider"],
                "audit_flags": ["controlled_provider_only"],
            }
        )

        audit = build_therapeutic_role_stability_audit(features)

        self.assertTrue(bool(audit.loc[0, "controlled_provider_used"]))
        self.assertEqual(audit.loc[0, "stability_label"], "changed_due_to_controlled_provider")

    def test_report_is_generated(self) -> None:
        audit = pd.DataFrame(
            {
                "node_id": ["A"],
                "gene_name": ["a"],
                "protein_id": ["A"],
                "therapeutic_role_v2": ["x"],
                "therapeutic_role_v3": ["x"],
                "role_changed": [False],
                "role_change_type": ["unchanged"],
                "meta_priority_score_v2": [0.5],
                "meta_priority_score_v3": [0.5],
                "score_delta": [0.0],
                "controlled_provider_used": [False],
                "evidence_quality_score": [0.8],
                "confidence_ceiling": [0.8],
                "stability_label": ["stable_high_confidence"],
                "audit_flags": ["none"],
            }
        )

        report = build_therapeutic_role_stability_report(audit)

        self.assertIn("Therapeutic Role Stability Audit", report)
        self.assertIn("stable_high_confidence", report)


if __name__ == "__main__":
    unittest.main()
