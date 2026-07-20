from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.scoring import (
    HOST_RISK_AUDIT_COLUMNS,
    HUMAN_HOMOLOGY_AUDIT_COLUMNS,
    THERAPEUTIC_SEPARATION_COLUMNS,
    THERAPY_SITE_CONTEXT_AUDIT_COLUMNS,
    build_features_and_scores,
    compute_sensitivity,
)
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import PROJECT_ROOT, make_temp_project

pytestmark = pytest.mark.integration


class ScoringTests(unittest.TestCase):
    def _make_workspace_with_raw_inputs(self) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"scoring_workspace_{uuid.uuid4().hex[:8]}"
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "data_raw").mkdir(parents=True, exist_ok=True)
        (root / "data_processed").mkdir(parents=True, exist_ok=True)
        (root / "results").mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", root / "config" / "params.yaml")
        for filename in [
            "essentiality.csv",
            "virulence.csv",
            "human_homologs.csv",
            "localization.csv",
            "strain_conservation.csv",
            "functional_network.csv",
            "host_annotation.csv",
        ]:
            shutil.copy2(PROJECT_ROOT / "data_demo" / filename, root / "data_raw" / filename)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_scores_are_generated_in_expected_range(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrate_tables(project_dir)
        features, scored = build_features_and_scores(project_dir, config)

        self.assertEqual(len(features), len(scored))
        self.assertFalse(scored.empty)
        for column in [
            "legacy_score_final",
            "antibiotic_target_score",
            "antivirulence_target_score",
            "functional_node_score",
            "meta_priority_score",
            "evidence_confidence_score",
            "evidence_coverage_score",
            "optional_data_quality_score",
            "host_safety_score",
            "host_damage_score",
            "infection_site_access_score",
            "infection_context_score",
            "therapeutic_priority_score",
            "therapeutic_priority_score_without_controlled_provider",
            "controlled_context_max_feature_delta",
            "therapeutic_rule_boundary_margin",
            "host_direct_damage_score",
            "virulence_associated_severity_score",
        ]:
            self.assertTrue(features[column].between(0, 1).all(), column)
        self.assertTrue(
            features["therapeutic_priority_controlled_delta"].between(-1, 1).all(),
            "therapeutic_priority_controlled_delta",
        )

        for column in [
            "preferred_strategy",
            "strategy_margin_score",
            "top_positive_drivers",
            "top_negative_drivers",
            "missing_evidence_flags",
            "optional_data_source_summary",
            "data_realism_flag",
            "therapeutic_priority_components",
            "therapeutic_priority_contribution_summary",
            "therapeutic_role",
            "therapeutic_role_rule",
            "therapeutic_role_with_controlled_provider",
            "therapeutic_role_without_controlled_provider",
            "therapeutic_role_rule_without_controlled_provider",
            "therapeutic_role_stability",
            "therapeutic_role_stability_explanation",
            "therapeutic_rule_boundary_proximity",
            "clinical_impact_input_status",
            "curated_disease_context_input_status",
            "therapy_site_context_input_status",
            "therapeutic_context_input_summary",
            "controlled_dependency_flags",
            "host_damage_score_without_controlled_provider",
            "infection_site_access_score_without_controlled_provider",
            "infection_context_score_without_controlled_provider",
            "host_damage_score_controlled_delta",
            "infection_site_access_score_controlled_delta",
            "infection_context_score_controlled_delta",
            "therapeutic_context_missingness",
            "proxy_feature_count",
            "source_database",
            "confidence_summary",
            "confidence_source_class",
            "confidence_evidence_tier",
            "confidence_source_quality_score",
            "candidate_audit_summary",
            "organism",
            "strain",
            "taxon_id",
            "interpretation_warning",
        ]:
            self.assertIn(column, features.columns)

        optional_audit_columns = set(
            HUMAN_HOMOLOGY_AUDIT_COLUMNS
            + HOST_RISK_AUDIT_COLUMNS
            + THERAPY_SITE_CONTEXT_AUDIT_COLUMNS
            + THERAPEUTIC_SEPARATION_COLUMNS
        )
        for column in optional_audit_columns.intersection(features.columns):
            self.assertIn(column, scored.columns)

        self.assertIn("human_homology_audit_summary", features.columns)
        self.assertIn("host_risk_audit_summary", features.columns)
        self.assertIn("therapy_site_context_audit_summary", features.columns)
        self.assertIn("human_homology_audit_summary", scored.columns)
        self.assertIn("host_risk_audit_summary", scored.columns)
        self.assertIn("therapy_site_context_audit_summary", scored.columns)
        self.assertEqual(set(features["confidence_source_class"]), {"curated"})
        self.assertEqual(set(features["confidence_evidence_tier"]), {"curated_literature_or_catalog"})
        self.assertTrue(np.isclose(features["confidence_source_quality_score"], 0.86).all())
        self.assertFalse((features["confidence_source_class"] == "user").any())
        self.assertFalse(features["confidence_evidence_tier"].astype(str).str.contains("user_validated").any())
        self.assertTrue(features["clinical_impact_input_status"].isin(["active_input", "resolved_empty_or_not_normalized"]).all())
        self.assertTrue(features["curated_disease_context_input_status"].isin(["active_input", "resolved_empty_or_not_normalized"]).all())
        self.assertTrue(features["therapy_site_context_input_status"].isin(["active_input", "resolved_empty_or_not_normalized"]).all())
        self.assertFalse(features["controlled_dependency_flags"].eq("none").all())
        self.assertTrue((features["controlled_context_max_feature_delta"] >= 0).all())
        self.assertTrue(features["therapeutic_rule_boundary_proximity"].isin(["near_rule_boundary", "moderate_rule_margin", "far_from_rule_boundary"]).all())
        self.assertTrue(features["therapeutic_role_stability_explanation"].astype(str).str.len().gt(0).all())
        self.assertTrue(
            features["therapeutic_role_stability_explanation"].isin(
                [
                    "role_changed_after_removing_controlled_context",
                    "stable_without_active_controlled_context",
                    "stable_because_controlled_values_match_local_proxies",
                    "stable_because_role_rule_far_from_thresholds",
                    "stable_but_scores_sensitive_review",
                    "stable_with_moderate_score_shift",
                ]
            ).all()
        )
        for column in [
            "host_damage_score_is_proxy",
            "infection_site_access_score_is_proxy",
            "infection_context_score_is_proxy",
            "host_direct_damage_score_is_proxy",
            "virulence_associated_severity_score_is_proxy",
            "host_damage_reduction_potential_is_proxy",
            "disease_severity_association_is_proxy",
            "clinical_impact_score_is_proxy",
        ]:
            self.assertTrue(features[column].isin([True, False]).all(), column)
        self.assertTrue((features["proxy_feature_count"] >= 0).all())
        self.assertTrue(features["therapeutic_role"].isin([
            "bactericidal_candidate",
            "antivirulence_candidate",
            "sensitizer_candidate",
            "mixed_strategy_candidate",
            "low_priority_candidate",
        ]).all())
        self.assertTrue(features["therapeutic_role_stability"].isin(["stable", "changed"]).all())
        self.assertEqual(set(features["data_realism_flag"]), {"demo_only"})
        self.assertTrue(features["missing_evidence_flags"].eq("none").all())
        for token in [
            "preferred_strategy=",
            "therapeutic_role=",
            "role_stability=",
            "therapeutic_priority=",
            "therapeutic_priority_components=",
            "evolutionary_escape_risk=",
            "evolutionary_penalty=",
            "margin=",
            "source_quality=",
            "realism=",
            "host_risk=",
            "site_access=",
            "main_risk=",
        ]:
            self.assertTrue(features["candidate_audit_summary"].str.contains(token, regex=False).all(), token)
        self.assertTrue(features["host_risk_audit_summary"].str.contains("rule=").all())
        self.assertTrue(features["human_homology_audit_summary"].str.contains("confidence=").all())
        self.assertTrue(features["therapy_site_context_audit_summary"].str.contains("site=").all())
        self.assertTrue(features["interpretation_warning"].str.contains("no validacion experimental").all())
        self.assertTrue(features["interpretation_warning"].str.contains("no equivale a evidencia negativa").all())
        for database_column in [
            "clinical_impact_database",
            "disease_context_database",
            "therapy_site_context_database",
        ]:
            self.assertTrue(features[database_column].fillna("").astype(str).str.len().gt(0).all())
        for metadata_column in ["organism", "strain", "taxon_id"]:
            self.assertTrue(features[metadata_column].fillna("").astype(str).str.strip().ne("").all(), metadata_column)

    def test_sensitivity_analysis_returns_multiple_scenarios(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrate_tables(project_dir)
        features, _ = build_features_and_scores(project_dir, config)
        sensitivity = compute_sensitivity(features, config)

        expected_columns = {
            "score_name",
            "scenario",
            "protein_id",
            "gene",
            "score",
            "rank",
            "base_rank",
            "rank_delta_vs_base",
            "therapeutic_role",
            "role_changed_vs_base",
        }
        self.assertTrue(expected_columns.issubset(sensitivity.columns))
        self.assertFalse(sensitivity.empty)
        self.assertTrue(np.isfinite(sensitivity["score"]).all())
        self.assertTrue(np.isfinite(sensitivity["rank_delta_vs_base"]).all())

        scenarios = set(sensitivity["scenario"])
        for scenario in [
            "baseline_like",
            "antivirulence_focus",
            "network_focus",
            "antibiotic_target__safety_first",
            "antibiotic_target__penetration_first",
            "antivirulence_target__accessibility_first",
            "antivirulence_target__damage_reduction_first",
            "functional_node__centrality_first",
            "functional_node__dependency_first",
            "safety_first",
            "context_first",
            "bactericidal_first",
            "damage_control_first",
        ]:
            self.assertIn(scenario, scenarios)

        self.assertEqual(
            set(sensitivity["score_name"]),
            {
                "meta_priority_score",
                "antibiotic_target_score",
                "antivirulence_target_score",
                "functional_node_score",
                "therapeutic_priority_score",
            },
        )
        therapeutic = sensitivity.loc[sensitivity["score_name"].eq("therapeutic_priority_score")]
        self.assertFalse(therapeutic.empty)
        self.assertTrue(therapeutic["therapeutic_role"].astype(str).str.strip().ne("").all())
        self.assertTrue(therapeutic["role_changed_vs_base"].isin([True, False]).all())
        self.assertEqual(
            set(therapeutic["scenario"]),
            {"safety_first", "context_first", "bactericidal_first", "damage_control_first"},
        )

    def test_specific_therapeutic_rules_take_priority_over_mixed_fallback(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrate_tables(project_dir)
        features, _ = build_features_and_scores(project_dir, config)

        by_protein = features.set_index("protein_id")
        specific_rules = {
            "essentiality_access_and_host_safety_supported",
            "strong_bactericidal_signal_with_limited_access",
        }
        for protein_id in ["PA0002", "PA0004"]:
            self.assertEqual(by_protein.loc[protein_id, "therapeutic_role"], "bactericidal_candidate")
            self.assertIn(by_protein.loc[protein_id, "therapeutic_role_rule"], specific_rules)
            self.assertNotEqual(
                by_protein.loc[protein_id, "therapeutic_role_rule"],
                "multiple_strategies_supported",
            )

    def test_limited_access_exception_does_not_rescue_high_host_risk_profiles(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrate_tables(project_dir)
        features, _ = build_features_and_scores(project_dir, config)

        by_protein = features.set_index("protein_id")
        self.assertEqual(by_protein.loc["PA0006", "therapeutic_role"], "low_priority_candidate")
        self.assertEqual(by_protein.loc["PA0006", "therapeutic_role_rule"], "host_risk_too_high")

    def test_scoring_refactor_preserves_repeatable_outputs(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrate_tables(project_dir)

        first_features, first_scored = build_features_and_scores(project_dir, config)
        second_features, second_scored = build_features_and_scores(project_dir, config)

        feature_columns = [
            "protein_id",
            "legacy_score_final",
            "antibiotic_target_score",
            "antivirulence_target_score",
            "functional_node_score",
            "meta_priority_score",
            "therapeutic_priority_score",
            "therapeutic_role",
            "therapeutic_role_rule",
            "host_damage_score",
            "infection_site_access_score",
            "infection_context_score",
            "therapeutic_role_stability",
            "therapeutic_role_stability_explanation",
            "therapeutic_priority_controlled_delta",
            "controlled_context_max_feature_delta",
            "therapeutic_rule_boundary_margin",
            "confidence_source_class",
        ]
        scored_columns = [
            "protein_id",
            "legacy_score_final",
            "meta_priority_score",
            "therapeutic_priority_score",
            "therapeutic_role",
            "human_homology_audit_summary",
            "host_risk_audit_summary",
            "therapeutic_role_stability",
            "therapeutic_role_stability_explanation",
            "therapeutic_priority_controlled_delta",
            "controlled_context_max_feature_delta",
            "confidence_source_class",
        ]
        pd.testing.assert_frame_equal(
            first_features[feature_columns].reset_index(drop=True),
            second_features[feature_columns].reset_index(drop=True),
        )
        pd.testing.assert_frame_equal(
            first_scored[scored_columns].reset_index(drop=True),
            second_scored[scored_columns].reset_index(drop=True),
        )

    def test_empirical_context_layers_override_proxy_flags(self) -> None:
        workspace = self._make_workspace_with_raw_inputs()
        raw_dir = workspace / "data_raw"
        (raw_dir / "clinical_impact.csv").write_text(
            "\n".join(
                [
                    (
                        "protein_id,gene,host_damage_reduction_potential,disease_severity_association,"
                        "clinical_impact_score,host_damage_score,host_direct_damage_score,"
                        "virulence_associated_severity_score,clinical_impact_catalog_source,"
                        "clinical_impact_evidence_type,clinical_impact_evidence_reference,database"
                    ),
                    "PA0008,lasB,0.91,0.92,0.93,0.94,0.95,0.96,manual_catalog,curated_literature,doi:10.example/clinical,curated_context_v1",
                ]
            ),
            encoding="utf-8",
        )
        (raw_dir / "curated_disease_context.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,infection_context_score,database",
                    "PA0008,lasB,0.89,curated_context_v1",
                ]
            ),
            encoding="utf-8",
        )
        (raw_dir / "therapy_site_context.csv").write_text(
            "\n".join(
                [
                    (
                        "protein_id,gene,infection_site_access,infection_site,access_evidence_type,"
                        "access_evidence_reference,access_evidence_note,database"
                    ),
                    "PA0008,lasB,0.88,lung_abscess,curated_literature,doi:10.example/site,note,curated_context_v1",
                ]
            ),
            encoding="utf-8",
        )

        config = load_config(workspace / "config" / "params.yaml")
        load_and_validate_all(workspace, config)
        normalize_all(workspace, config)
        integrate_tables(workspace)
        features, scored = build_features_and_scores(workspace, config)
        row = features.set_index("protein_id").loc["PA0008"]
        self.assertEqual(row["clinical_impact_input_status"], "active_input")
        self.assertEqual(row["curated_disease_context_input_status"], "active_input")
        self.assertEqual(row["therapy_site_context_input_status"], "active_input")
        self.assertFalse(bool(row["host_damage_reduction_potential_is_proxy"]))
        self.assertFalse(bool(row["clinical_impact_score_is_proxy"]))
        self.assertFalse(bool(row["infection_site_access_is_proxy"]))
        self.assertFalse(bool(row["infection_context_score_is_proxy"]))
        self.assertEqual(row["infection_site"], "lung_abscess")
        self.assertEqual(row["access_evidence_type"], "curated_literature")
        self.assertEqual(row["access_evidence_reference"], "doi:10.example/site")
        self.assertEqual(float(row["host_direct_damage_score"]), 0.95)
        self.assertEqual(float(row["virulence_associated_severity_score"]), 0.96)
        self.assertIn("site=lung_abscess", row["therapy_site_context_audit_summary"])
        self.assertIn("reference=doi:10.example/site", row["therapy_site_context_audit_summary"])
        self.assertIn("therapy_site_context_audit_summary", scored.columns)


if __name__ == "__main__":
    unittest.main()
