from __future__ import annotations

import unittest

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.reporting import export_results
from src.nodos_funcionales.scoring import build_features_and_scores, compute_sensitivity
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import make_temp_project

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class ExportTests(unittest.TestCase):
    def test_export_creates_phase2_outputs(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrate_tables(project_dir)
        features, _ = build_features_and_scores(project_dir, config)
        sensitivity = compute_sensitivity(features, config)
        sensitivity.to_csv(project_dir / "results" / "sensitivity_analysis.csv", index=False)
        export_results(project_dir, config)

        self.assertTrue((project_dir / "results" / "ranking_nodos.csv").exists())
        self.assertTrue((project_dir / "results" / "ranking_nodos_legacy.csv").exists())
        self.assertTrue((project_dir / "results" / "phase_comparison.csv").exists())
        self.assertTrue((project_dir / "results" / "report_phase2.md").exists())
        self.assertTrue((project_dir / "results" / "resumen_ejecutivo.md").exists())
        self.assertTrue((project_dir / "results" / "literature_support_summary.csv").exists())
        self.assertTrue((project_dir / "results" / "literature_support_summary.md").exists())
        self.assertTrue((project_dir / "results" / "human_homologs_audit.csv").exists())
        self.assertTrue((project_dir / "results" / "human_homologs_audit.md").exists())
        self.assertTrue((project_dir / "results" / "therapeutic_context_separation_audit.csv").exists())
        self.assertTrue((project_dir / "results" / "therapeutic_context_separation_audit.md").exists())
        self.assertTrue((project_dir / "results" / "controlled_replacement_readiness.csv").exists())
        self.assertTrue((project_dir / "results" / "controlled_replacement_readiness.md").exists())
        self.assertTrue((project_dir / "results" / "clinical_impact_curation_queue.csv").exists())
        self.assertTrue((project_dir / "results" / "clinical_impact_curation_queue.md").exists())
        self.assertTrue((project_dir / "results" / "disease_context_curation_queue.csv").exists())
        self.assertTrue((project_dir / "results" / "disease_context_curation_queue.md").exists())
        self.assertTrue((project_dir / "results" / "therapy_site_context_curation_queue.csv").exists())
        self.assertTrue((project_dir / "results" / "therapy_site_context_curation_queue.md").exists())
        self.assertTrue((project_dir / "results" / "therapeutic_role_controlled_stability.csv").exists())
        self.assertTrue((project_dir / "results" / "therapeutic_role_controlled_stability_summary.csv").exists())
        self.assertTrue((project_dir / "results" / "therapeutic_role_controlled_stability.md").exists())
        self.assertTrue((project_dir / "results" / "data_provenance_summary.csv").exists())
        self.assertTrue((project_dir / "results" / "layer_resolution_summary.csv").exists())
        self.assertTrue((project_dir / "results" / "layer_resolution_summary.md").exists())
        self.assertTrue((project_dir / "results" / "therapeutic_role_summary.csv").exists())
        self.assertTrue((project_dir / "results" / "therapeutic_role_summary.md").exists())
        self.assertTrue((project_dir / "results" / "therapeutic_rule_summary.csv").exists())
        self.assertTrue((project_dir / "results" / "therapeutic_rule_summary.md").exists())
        self.assertTrue((project_dir / "results" / "candidate_audit.csv").exists())
        self.assertTrue((project_dir / "results" / "candidate_audit.md").exists())
        self.assertTrue((project_dir / "results" / "top10_candidate_review.csv").exists())
        self.assertTrue((project_dir / "results" / "top10_candidate_review.md").exists())
        self.assertTrue((project_dir / "results" / "top10_scientific_audit.csv").exists())
        self.assertTrue((project_dir / "results" / "top10_scientific_audit.md").exists())
        self.assertTrue((project_dir / "results" / "top10_scientific_summary.md").exists())

        ranking = pd.read_csv(project_dir / "results" / "ranking_nodos.csv")
        for column in [
            "therapeutic_priority_score",
            "therapeutic_role",
            "therapeutic_role_with_controlled_provider",
            "therapeutic_role_without_controlled_provider",
            "therapeutic_role_stability",
            "therapeutic_role_rule",
            "host_damage_score",
            "host_direct_damage_score",
            "virulence_associated_severity_score",
            "infection_site_access_score",
            "infection_context_score",
            "therapeutic_context_missingness",
            "confidence_source_class",
            "confidence_evidence_tier",
        ]:
            self.assertIn(column, ranking.columns)

    def test_export_legacy_mode_writes_legacy_ranking_as_primary_output(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrate_tables(project_dir)
        features, _ = build_features_and_scores(project_dir, config)
        sensitivity = compute_sensitivity(features, config)
        sensitivity.to_csv(project_dir / "results" / "sensitivity_analysis.csv", index=False)
        export_results(project_dir, config, mode="legacy")

        ranking = pd.read_csv(project_dir / "results" / "ranking_nodos.csv")
        self.assertEqual(list(ranking.columns), ["rank", "protein_id", "gene", "legacy_score_final"])

    def test_export_writes_candidate_audit_with_strategy_columns(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrate_tables(project_dir)
        features, _ = build_features_and_scores(project_dir, config)
        sensitivity = compute_sensitivity(features, config)
        sensitivity.to_csv(project_dir / "results" / "sensitivity_analysis.csv", index=False)
        export_results(project_dir, config)

        audit = pd.read_csv(project_dir / "results" / "candidate_audit.csv")
        self.assertIn("preferred_strategy", audit.columns)
        self.assertIn("therapeutic_role", audit.columns)
        self.assertIn("therapeutic_role_without_controlled_provider", audit.columns)
        self.assertIn("therapeutic_role_stability", audit.columns)
        self.assertIn("therapeutic_priority_score", audit.columns)
        self.assertIn("candidate_audit_summary", audit.columns)
        self.assertIn("optional_data_quality_score", audit.columns)
        self.assertIn("host_risk_audit_summary", audit.columns)
        self.assertIn("human_homology_audit_summary", audit.columns)
        self.assertIn("homology_evidence_tier", audit.columns)
        self.assertIn("homology_confidence_score", audit.columns)
        self.assertIn("therapy_site_context_audit_summary", audit.columns)
        self.assertIn("host_direct_damage_score", audit.columns)
        self.assertIn("virulence_associated_severity_score", audit.columns)
        self.assertIn("confidence_source_class", audit.columns)
        self.assertIn("confidence_evidence_tier", audit.columns)
        self.assertTrue(audit["host_risk_audit_summary"].str.contains("host_source=").all())
        self.assertTrue(audit["human_homology_audit_summary"].str.contains("tier=").all())
        self.assertTrue(audit["therapy_site_context_audit_summary"].str.contains("site=").all())
        review = pd.read_csv(project_dir / "results" / "top10_candidate_review.csv")
        self.assertIn("recommendation", review.columns)
        self.assertIn("therapeutic_role", review.columns)
        self.assertIn("meta_sensitivity_span", review.columns)
        self.assertTrue(review["review_note"].str.contains("host_risk=").all())
        role_summary = pd.read_csv(project_dir / "results" / "therapeutic_role_summary.csv")
        self.assertIn("therapeutic_role", role_summary.columns)
        self.assertIn("candidate_count", role_summary.columns)
        rule_summary = pd.read_csv(project_dir / "results" / "therapeutic_rule_summary.csv")
        self.assertIn("therapeutic_role", rule_summary.columns)
        self.assertIn("therapeutic_role_rule", rule_summary.columns)
        self.assertIn("candidate_count", rule_summary.columns)
        layer_summary = pd.read_csv(project_dir / "results" / "layer_resolution_summary.csv")
        self.assertIn("layer", layer_summary.columns)
        self.assertIn("source_type", layer_summary.columns)
        self.assertIn("retrieval_status", layer_summary.columns)
        homology_audit = pd.read_csv(project_dir / "results" / "human_homologs_audit.csv")
        self.assertIn("homology_evidence_tier", homology_audit.columns)
        self.assertIn("candidate_count", homology_audit.columns)
        self.assertIn("mean_homology_confidence_score", homology_audit.columns)
        context_audit = pd.read_csv(project_dir / "results" / "therapeutic_context_separation_audit.csv")
        self.assertIn("left_layer", context_audit.columns)
        self.assertIn("right_layer", context_audit.columns)
        self.assertIn("score_correlation", context_audit.columns)
        self.assertIn("input_key_overlap", context_audit.columns)
        self.assertIn("separation_status", context_audit.columns)
        self.assertTrue(context_audit["shared_candidates"].ge(1).all())
        replacement = pd.read_csv(project_dir / "results" / "controlled_replacement_readiness.csv")
        self.assertIn("layer", replacement.columns)
        self.assertIn("replacement_readiness_status", replacement.columns)
        self.assertIn("minimal_user_columns", replacement.columns)
        self.assertIn("therapy_site_context", set(replacement["layer"]))
        clinical_readiness = replacement.loc[replacement["layer"] == "clinical_impact"].iloc[0]
        self.assertIn("host_direct_damage_score", clinical_readiness["minimal_user_columns"])
        disease_readiness = replacement.loc[replacement["layer"] == "curated_disease_context"].iloc[0]
        self.assertIn("context_evidence_reference", disease_readiness["minimal_user_columns"])
        clinical_queue = pd.read_csv(project_dir / "results" / "clinical_impact_curation_queue.csv")
        self.assertIn("protein_id", clinical_queue.columns)
        self.assertIn("needs_curated_clinical_impact", clinical_queue.columns)
        self.assertIn("curated_host_direct_damage_score", clinical_queue.columns)
        self.assertIn("curated_virulence_associated_severity_score", clinical_queue.columns)
        self.assertIn("curated_clinical_impact_evidence_reference", clinical_queue.columns)
        self.assertTrue(clinical_queue["needs_curated_clinical_impact"].isin([True, False]).all())
        disease_queue = pd.read_csv(project_dir / "results" / "disease_context_curation_queue.csv")
        self.assertIn("protein_id", disease_queue.columns)
        self.assertIn("needs_curated_disease_context", disease_queue.columns)
        self.assertIn("curated_infection_context_score", disease_queue.columns)
        self.assertIn("curated_disease_context", disease_queue.columns)
        self.assertIn("curated_context_evidence_reference", disease_queue.columns)
        self.assertTrue(disease_queue["needs_curated_disease_context"].isin([True, False]).all())
        curation_queue = pd.read_csv(project_dir / "results" / "therapy_site_context_curation_queue.csv")
        self.assertIn("protein_id", curation_queue.columns)
        self.assertIn("needs_curated_site_context", curation_queue.columns)
        self.assertIn("curated_infection_site_access", curation_queue.columns)
        self.assertIn("curated_access_evidence_reference", curation_queue.columns)
        self.assertTrue(curation_queue["needs_curated_site_context"].isin([True, False]).all())
        role_stability = pd.read_csv(project_dir / "results" / "therapeutic_role_controlled_stability.csv")
        self.assertIn("therapeutic_role_with_controlled_provider", role_stability.columns)
        self.assertIn("therapeutic_role_without_controlled_provider", role_stability.columns)
        self.assertIn("therapeutic_role_stability", role_stability.columns)
        self.assertTrue(role_stability["therapeutic_role_stability"].isin(["stable", "changed"]).all())

    def test_export_writes_scientific_audit_with_required_columns(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrate_tables(project_dir)
        features, _ = build_features_and_scores(project_dir, config)
        sensitivity = compute_sensitivity(features, config)
        sensitivity.to_csv(project_dir / "results" / "sensitivity_analysis.csv", index=False)
        export_results(project_dir, config)

        scientific = pd.read_csv(project_dir / "results" / "top10_scientific_audit.csv")
        self.assertEqual(len(scientific), 10)
        for column in [
            "rank",
            "protein_id",
            "preferred_strategy",
            "therapeutic_role",
            "robustness_label",
            "biological_interpretation",
            "methodological_risk",
            "host_risk_audit_summary",
            "host_risk_interpretation",
            "recommended_next_evidence",
            "audit_class",
            "audit_confidence",
        ]:
            self.assertIn(column, scientific.columns)
        self.assertTrue(scientific["audit_class"].fillna("").str.len().gt(0).all())
        self.assertTrue(scientific["methodological_risk"].str.contains("Seguridad hospedero:").all())
        self.assertTrue(scientific["host_risk_interpretation"].str.contains("Seguridad hospedero:").all())
        self.assertIn("literature_interpretation", scientific.columns)
        self.assertTrue(scientific["literature_interpretation"].str.contains("no afecta el ranking").all())

    def test_export_scientific_audit_handles_missing_sensitivity_file(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrate_tables(project_dir)
        build_features_and_scores(project_dir, config)
        export_results(project_dir, config)

        scientific = pd.read_csv(project_dir / "results" / "top10_scientific_audit.csv")
        self.assertEqual(len(scientific), 10)
        self.assertIn("sensitivity_assessment", scientific.columns)


if __name__ == "__main__":
    unittest.main()
