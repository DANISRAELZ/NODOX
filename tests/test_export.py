from __future__ import annotations

import unittest

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.reporting import (
    _build_top10_scientific_markdown,
    _export_functional_node_theory_outputs,
    _select_functional_node_theory_universe,
    export_results,
)
from src.nodos_funcionales.scoring import build_features_and_scores, compute_sensitivity
from src.nodos_funcionales.user_explanations import THEORY_V3_NOT_ASSESSED_NOTE
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import make_temp_project

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_functional_node_export_uses_full_therapeutic_universe_when_phase3_has_placeholders(tmp_path) -> None:
    processed_dir = tmp_path / "data_processed"
    results_dir = tmp_path / "results"
    processed_dir.mkdir(parents=True)
    results_dir.mkdir(parents=True)
    config = load_config(make_temp_project() / "config" / "params.yaml")
    config["phase3"]["enabled"] = False

    ranking = pd.DataFrame(
        {
            "protein_id": [f"HP{i:04d}" for i in range(200)],
            "gene": [f"gene{i:04d}" for i in range(200)],
            "organism": ["Helicobacter pylori"] * 200,
            "taxon_id": [210] * 200,
            "strain": ["not_reported"] * 200,
            "meta_priority_score": [0.50] * 200,
            "therapeutic_priority_score": [0.25] * 200,
            "functional_node_score": [0.20] * 200,
            "evidence_level": ["unresolved"] * 200,
            "source_used": ["provider_not_found"] * 200,
        }
    )
    scored = ranking[["protein_id", "gene", "meta_priority_score", "therapeutic_priority_score", "functional_node_score"]].copy()
    phase3_placeholders = pd.DataFrame(
        {
            "protein_id": ["PA0001", "PA0002", "PA0003"],
            "gene": ["online_seed_placeholder_1", "online_seed_placeholder_2", "online_seed_placeholder_3"],
            "audit_flags": ["phase3_not_enabled"] * 3,
            "functional_node_theory_score": [0.0, 0.0, 0.0],
        }
    )
    ranking.to_csv(results_dir / "ranking_nodos.csv", index=False)
    scored.to_csv(processed_dir / "scored_nodes.csv", index=False)
    phase3_placeholders.to_csv(processed_dir / "phase3_features.csv", index=False)

    universe = _select_functional_node_theory_universe(
        tmp_path,
        ranking,
        ranking,
        {"organism": "Helicobacter pylori", "taxon_id": "210", "strain": "not_reported"},
    )
    functional, audit = _export_functional_node_theory_outputs(universe, results_dir, config, top_n=10)

    assert len(universe) == 200
    assert len(functional) == 200
    assert len(audit) == 200
    assert functional["protein_id"].str.startswith("HP").all()
    assert not functional["functional_node_theory_label"].eq("high_confidence_functional_node").any()
    assert set(functional["organism"]) == {"Helicobacter pylori"}
    assert set(functional["taxon_id"].astype(str)) == {"210"}


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
        self.assertTrue((project_dir / "results" / "ranking_nodos_by_gene.csv").exists())
        self.assertTrue((project_dir / "results" / "ranking_functional_nodes.csv").exists())
        self.assertTrue((project_dir / "results" / "ranking_functional_nodes_by_gene.csv").exists())
        self.assertTrue((project_dir / "results" / "ranking_nodos_legacy.csv").exists())
        self.assertTrue((project_dir / "results" / "functional_node_theory_audit.csv").exists())
        self.assertTrue((project_dir / "results" / "functional_node_theory_audit.md").exists())
        self.assertTrue((project_dir / "results" / "theory_of_nodes_report.md").exists())
        self.assertTrue((project_dir / "results" / "curated_real_evidence_manifest.json").exists())
        self.assertTrue((project_dir / "results" / "curated_real_evidence_summary.csv").exists())
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
        functional_ranking = pd.read_csv(project_dir / "results" / "ranking_functional_nodes.csv")
        functional_by_gene = pd.read_csv(project_dir / "results" / "ranking_functional_nodes_by_gene.csv")
        functional_audit = pd.read_csv(project_dir / "results" / "functional_node_theory_audit.csv")
        self.assertIn("therapeutic_priority_score", ranking.columns)
        self.assertIn("functional_node_theory_score", functional_ranking.columns)
        self.assertIn("functional_node_theory_confidence", functional_ranking.columns)
        self.assertIn("functional_node_therapeutic_exploitability_score", functional_ranking.columns)
        self.assertIn("meets_minimum_functional_node_evidence", functional_audit.columns)
        self.assertIn("functional_impact_component", functional_audit.columns)
        self.assertIn("dependency_component", functional_audit.columns)
        self.assertIn("redundancy_constraint_component", functional_audit.columns)
        self.assertIn("interpretation", functional_audit.columns)
        self.assertIn("accessions_collapsed", functional_by_gene.columns)
        for metadata_column in ["organism", "taxon_id", "strain"]:
            self.assertIn(metadata_column, functional_ranking.columns)
            self.assertIn(metadata_column, functional_by_gene.columns)
        for column in [
            "therapeutic_priority_score",
            "therapeutic_priority_contribution_summary",
            "therapeutic_priority_components",
            "therapeutic_priority_meta_priority_score_contribution",
            "therapeutic_priority_host_safety_score_contribution",
            "therapeutic_priority_host_damage_score_contribution",
            "therapeutic_priority_infection_site_access_score_contribution",
            "therapeutic_priority_infection_context_score_contribution",
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
            "provenance_status",
            "retrieval_mode",
            "cache_status",
        ]:
            self.assertIn(column, ranking.columns)
        contribution_columns = [
            "therapeutic_priority_meta_priority_score_contribution",
            "therapeutic_priority_host_safety_score_contribution",
            "therapeutic_priority_host_damage_score_contribution",
            "therapeutic_priority_infection_site_access_score_contribution",
            "therapeutic_priority_infection_context_score_contribution",
        ]
        pd.testing.assert_series_equal(
            ranking[contribution_columns].sum(axis=1).round(6),
            ranking["therapeutic_priority_score"].round(6),
            check_names=False,
        )
        pd.testing.assert_series_equal(
            ranking["therapeutic_priority_components"],
            ranking["therapeutic_priority_contribution_summary"],
            check_names=False,
        )

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
        self.assertEqual(
            list(ranking.columns),
            ["rank", "protein_id", "gene", "organism", "strain", "taxon_id", "legacy_score_final"],
        )

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
        self.assertIn("therapeutic_priority_contribution_summary", audit.columns)
        self.assertIn("therapeutic_priority_components", audit.columns)
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
        pd.testing.assert_series_equal(
            audit["therapeutic_priority_components"],
            audit["therapeutic_priority_contribution_summary"],
            check_names=False,
        )
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

        explanations = pd.read_csv(project_dir / "results" / "candidate_explanations_simple.csv")
        self.assertIn("therapeutic_priority_components", explanations.columns)
        self.assertIn("theory_context", explanations.columns)
        self.assertIn("provenance_context", explanations.columns)
        self.assertTrue(explanations["therapeutic_priority_components"].str.contains("meta_priority_score=").all())

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
        top10_md = (project_dir / "results" / "top10_scientific_audit.md").read_text(encoding="utf-8")
        report = (project_dir / "results" / "report_phase2.md").read_text(encoding="utf-8")
        evolutionary_audit_md = (project_dir / "results" / "evolutionary_escape_risk_audit.md").read_text(encoding="utf-8")
        self.assertEqual(len(scientific), 10)
        for column in [
            "rank",
            "protein_id",
            "preferred_strategy",
            "therapeutic_role",
            "therapeutic_priority_contribution_summary",
            "therapeutic_priority_components",
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
        pd.testing.assert_series_equal(
            scientific["therapeutic_priority_components"],
            scientific["therapeutic_priority_contribution_summary"],
            check_names=False,
        )
        self.assertTrue(scientific["methodological_risk"].str.contains("Seguridad hospedero:").all())
        self.assertTrue(scientific["host_risk_interpretation"].str.contains("Seguridad hospedero:").all())
        self.assertIn("literature_interpretation", scientific.columns)
        self.assertTrue(scientific["literature_interpretation"].str.contains("no afecta el ranking").all())
        self.assertIn("therapeutic_priority_components", top10_md)
        self.assertIn("no es validacion experimental", top10_md)
        self.assertIn("no constituye recomendacion terapeutica", top10_md)
        self.assertIn("validacion experimental y clinica", top10_md)
        self.assertIn("evidencia real, curada, cache, proxy, demo o faltante", top10_md)
        self.assertIn("therapeutic_priority_components", report)
        self.assertIn("interpretacion computacional", report)
        self.assertIn("therapeutic_priority_score", report)
        self.assertIn("evidence_confidence_score", report)
        self.assertIn("score alto no equivale a confianza alta", report.lower())
        self.assertIn("user_curated", report)
        self.assertIn("no equivale automaticamente a evidencia externa verificada", report)
        self.assertIn("pending_review", report)
        self.assertIn("no equivalen a validacion experimental", report)
        self.assertIn("Lectura conservadora", report)
        self.assertIn("subcapa evolutiva modula robustez y escape", report)
        self.assertIn("no constituye recomendacion terapeutica", report)
        self.assertIn("evaluacion medica, microbiologica o farmacologica", report)
        self.assertIn("ausencia o insuficiencia de evidencia no equivale a bajo riesgo", report.lower())
        self.assertIn("no sustituyen evidencia real del usuario ni evidencia externa trazable", evolutionary_audit_md)
        self.assertIn("faltante o insuficiente no equivale a bajo riesgo", evolutionary_audit_md)
        self.assertIn("Nota theory-first/v3", top10_md)
        self.assertIn(THEORY_V3_NOT_ASSESSED_NOTE, top10_md)
        self.assertIn("Nota theory-first/v3", report)
        self.assertIn(THEORY_V3_NOT_ASSESSED_NOTE, report)

    def test_scientific_markdown_omits_theory_v3_note_when_assessed(self) -> None:
        scientific = pd.DataFrame(
            {
                "rank": [1],
                "gene": ["geneA"],
                "protein_id": ["A"],
                "therapeutic_role": ["bactericidal_candidate"],
                "therapeutic_priority_score": [0.7],
                "therapeutic_priority_components": ["meta_priority_score=0.300"],
                "rank_phase3_real_candidates": [1],
                "meta_priority_score_v3": [0.8],
                "therapeutic_role_v3": ["antivirulence_candidate"],
                "evidence_quality_score": [0.9],
                "confidence_ceiling": [0.9],
                "functional_node_theory_score": [0.7],
                "evolutionary_escape_risk_score": [0.2],
                "host_similarity_risk": [0.1],
                "preferred_strategy": ["antibiotic"],
                "audit_class": ["robust"],
                "audit_confidence": ["high"],
                "biological_interpretation": ["interpretacion"],
                "main_positive_drivers": ["meta_priority_score=0.300"],
                "methodological_risk": ["riesgo"],
                "literature_support_status": ["not_loaded"],
                "literature_support_score": [0.0],
                "literature_source_quality": [0.0],
                "phase3_evidence_explanation": ["not_reported"],
                "demo_dependency_assessment": ["sin dependencia dominante"],
                "sensitivity_assessment": ["estable"],
                "recommended_next_evidence": ["curar evidencia"],
                "theory_v3_assessment_note": ["not_reported"],
            }
        )

        markdown = _build_top10_scientific_markdown(scientific, pd.DataFrame())

        self.assertNotIn("Nota theory-first/v3", markdown)
        self.assertNotIn(THEORY_V3_NOT_ASSESSED_NOTE, markdown)

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
