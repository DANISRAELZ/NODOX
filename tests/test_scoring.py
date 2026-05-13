from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.scoring import build_features_and_scores, compute_sensitivity
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import PROJECT_ROOT, make_temp_project


class ScoringTests(unittest.TestCase):
    def _make_workspace_with_raw_inputs(self) -> Path:
        workspace = PROJECT_ROOT / ".tmp_tests" / f"context_layers_{uuid.uuid4().hex[:8]}"
        raw_dir = workspace / "data_raw"
        config_dir = workspace / "config"
        processed_dir = workspace / "data_processed"
        results_dir = workspace / "results"

        for path in [raw_dir, config_dir, processed_dir, results_dir]:
            path.mkdir(parents=True, exist_ok=True)

        for filename in [
            "essentiality.csv",
            "virulence.csv",
            "human_homologs.csv",
            "localization.csv",
            "strain_conservation.csv",
            "functional_network.csv",
            "host_annotation.csv",
        ]:
            source = PROJECT_ROOT / "data_raw" / filename
            target = raw_dir / filename
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

        params_source = PROJECT_ROOT / "config" / "params.yaml"
        (config_dir / "params.yaml").write_text(params_source.read_text(encoding="utf-8"), encoding="utf-8")
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))
        return workspace

    def test_scores_are_generated_in_expected_range(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrate_tables(project_dir)
        _, scored = build_features_and_scores(project_dir, config)

        for column in [
            "legacy_score_final",
            "antibiotic_target_score",
            "antivirulence_target_score",
            "functional_node_score",
            "meta_priority_score",
            "therapeutic_priority_score",
        ]:
            self.assertTrue(scored[column].between(0, 1).all(), column)

        self.assertIn("top_positive_drivers", scored.columns)
        self.assertIn("top_negative_drivers", scored.columns)
        self.assertIn("missing_evidence_flags", scored.columns)
        self.assertIn("host_damage_reduction_potential", _.columns)
        self.assertIn("disease_severity_association", _.columns)
        self.assertIn("clinical_impact_score", _.columns)
        self.assertIn("host_damage_score", _.columns)
        self.assertIn("host_direct_damage_score", _.columns)
        self.assertIn("virulence_associated_severity_score", _.columns)
        self.assertIn("infection_site_access_score", _.columns)
        self.assertIn("infection_context_score", _.columns)
        self.assertIn("therapeutic_role", _.columns)
        self.assertIn("therapeutic_role_with_controlled_provider", _.columns)
        self.assertIn("therapeutic_role_without_controlled_provider", _.columns)
        self.assertIn("therapeutic_role_stability", _.columns)
        self.assertIn("therapeutic_role_stability_explanation", _.columns)
        self.assertIn("therapeutic_priority_controlled_delta", _.columns)
        self.assertIn("controlled_context_max_feature_delta", _.columns)
        self.assertIn("therapeutic_rule_boundary_margin", _.columns)
        self.assertIn("therapeutic_rule_boundary_proximity", _.columns)
        self.assertIn("confidence_source_class", _.columns)
        self.assertIn("confidence_evidence_tier", _.columns)
        self.assertIn("therapeutic_role_rule", _.columns)
        self.assertIn("therapeutic_priority_contribution_summary", _.columns)
        self.assertIn("therapeutic_priority_components", _.columns)
        self.assertIn("therapeutic_priority_components", scored.columns)
        pd.testing.assert_series_equal(
            _["therapeutic_priority_components"],
            _["therapeutic_priority_contribution_summary"],
            check_names=False,
        )
        therapeutic_priority_contribution_columns = [
            "therapeutic_priority_meta_priority_score_contribution",
            "therapeutic_priority_host_safety_score_contribution",
            "therapeutic_priority_host_damage_score_contribution",
            "therapeutic_priority_infection_site_access_score_contribution",
            "therapeutic_priority_infection_context_score_contribution",
        ]
        for contribution_column in therapeutic_priority_contribution_columns:
            self.assertIn(contribution_column, _.columns)
            self.assertIn(contribution_column, scored.columns)
            self.assertTrue(_[contribution_column].between(0, 1).all(), contribution_column)
        contribution_sum = _[therapeutic_priority_contribution_columns].sum(axis=1).round(6)
        pd.testing.assert_series_equal(
            contribution_sum,
            _["therapeutic_priority_score"].round(6),
            check_names=False,
        )
        self.assertTrue(scored["therapeutic_priority_contribution_summary"].str.contains("meta_priority_score=").all())
        self.assertTrue(scored["therapeutic_priority_components"].str.contains("meta_priority_score=").all())
        self.assertIn("therapeutic_context_missingness", _.columns)
        self.assertIn("contextual_essentiality_score", _.columns)
        self.assertIn("pleiotropy_score", _.columns)
        self.assertIn("conservation_score", _.columns)
        self.assertIn("functional_node_theory_score", _.columns)
        self.assertIn("mutational_tolerance_score", _.columns)
        self.assertIn("redundancy_penalty", _.columns)
        self.assertIn("fitness_cost_score", _.columns)
        self.assertIn("compensation_difficulty_score", _.columns)
        self.assertIn("collateral_sensitivity_score", _.columns)
        self.assertIn("biofilm_escape_penalty", _.columns)
        self.assertIn("horizontal_transfer_penalty", _.columns)
        self.assertIn("evolutionary_escape_risk_score", _.columns)
        self.assertIn("evolutionary_space_constraint_score", _.columns)
        self.assertIn("evidence_quality_score", _.columns)
        self.assertIn("confidence_ceiling", _.columns)
        self.assertIn("evidence_source_type", _.columns)
        self.assertIn("evidence_notes", _.columns)
        self.assertIn("therapeutic_role_v3", _.columns)
        self.assertIn("recommended_combination_class", _.columns)
        self.assertIn("combination_rationale", _.columns)
        self.assertIn("audit_flags", _.columns)
        self.assertIn("phase3_notes", _.columns)
        self.assertTrue(_["host_damage_reduction_potential"].between(0, 1).all())
        self.assertTrue(_["disease_severity_association"].between(0, 1).all())
        self.assertTrue(_["clinical_impact_score"].between(0, 1).all())
        self.assertTrue(_["host_damage_score"].between(0, 1).all())
        self.assertTrue(_["host_direct_damage_score"].between(0, 1).all())
        self.assertTrue(_["virulence_associated_severity_score"].between(0, 1).all())
        self.assertTrue(_["infection_site_access_score"].between(0, 1).all())
        self.assertTrue(_["infection_context_score"].between(0, 1).all())
        self.assertTrue(_["functional_node_score"].between(0, 1).all())
        self.assertTrue(_["biofilm_escape_penalty"].between(0, 1).all())
        self.assertTrue(_["horizontal_transfer_penalty"].between(0, 1).all())
        self.assertTrue(_["evidence_quality_score"].between(0, 1).all())
        self.assertTrue(_["confidence_ceiling"].between(0, 1).all())
        self.assertTrue(_["therapeutic_role_v3"].fillna("").astype(str).ne("").all())
        self.assertTrue(_["audit_flags"].fillna("").astype(str).ne("").all())
        self.assertGreater(_["functional_node_score"].nunique(), 1)
        self.assertFalse(_["network_centrality_is_placeholder"].any())
        self.assertFalse(_["core_genome_presence_is_placeholder"].any())
        self.assertTrue(_["domain_overlap_score_is_empirical"].all())
        self.assertTrue(_["host_criticality_penalty_is_empirical"].all())
        self.assertTrue(_["optional_data_quality_score"].between(0, 1).all())
        self.assertTrue(_["data_realism_flag"].isin(["demo_only", "mixed_or_computed"]).all())
        self.assertTrue(_["optional_data_source_summary"].str.contains("clinical_impact=controlled").all())
        self.assertTrue(_["optional_data_source_summary"].str.contains("disease_context=controlled").all())
        self.assertTrue(_["optional_data_source_summary"].str.contains("therapy_site_context=controlled").all())
        self.assertTrue(_["therapeutic_role_stability"].isin(["stable", "changed"]).all())
        self.assertTrue(
            _["therapeutic_role_stability_explanation"].isin(
                [
                    "role_changed_after_removing_controlled_context",
                    "stable_because_controlled_values_match_local_proxies",
                    "stable_because_role_rule_far_from_thresholds",
                    "stable_but_scores_sensitive_review",
                    "stable_with_moderate_score_shift",
                    "stable_without_active_controlled_context",
                ]
            ).all()
        )
        for column in [
            "clinical_impact_input_status",
            "curated_disease_context_input_status",
            "therapy_site_context_input_status",
            "therapeutic_context_input_summary",
        ]:
            self.assertIn(column, _.columns)
            self.assertIn(column, scored.columns)
        self.assertTrue(_["controlled_context_max_feature_delta"].between(0, 1).all())
        self.assertTrue(_["therapeutic_rule_boundary_margin"].between(0, 1).all())
        self.assertTrue(
            _["therapeutic_rule_boundary_proximity"].isin(
                ["near_rule_boundary", "moderate_rule_margin", "far_from_rule_boundary"]
            ).all()
        )
        self.assertTrue(_["confidence_source_class"].isin(["controlled", "curated", "experimental", "user", "proxy", "computed", "unknown"]).all())
        self.assertFalse(_["host_damage_score_is_proxy"].any())
        self.assertFalse(_["infection_site_access_score_is_proxy"].any())
        self.assertFalse(_["infection_context_score_is_proxy"].any())
        self.assertIn("candidate_audit_summary", _.columns)
        self.assertIn("host_risk_audit_summary", _.columns)
        self.assertIn("host_risk_audit_summary", scored.columns)
        self.assertTrue(_["host_risk_audit_summary"].str.contains("host_source=").all())
        self.assertTrue(scored["candidate_audit_summary"].str.contains("host_risk=").all())
        self.assertFalse(_["top_negative_drivers"].eq("none").all())
        self.assertTrue(_["missing_evidence_flags"].eq("none").all())
        self.assertTrue(
            set(_["therapeutic_role"].unique()).issubset(
                {
                    "bactericidal_candidate",
                    "antivirulence_candidate",
                    "sensitizer_candidate",
                    "mixed_strategy_candidate",
                    "low_priority_candidate",
                }
            )
        )

        sensitivity = compute_sensitivity(_, config)
        self.assertEqual(
            set(sensitivity["score_name"].unique()),
            {"meta_priority", "antibiotic_target", "antivirulence_target", "functional_node", "therapeutic_priority"},
        )
        self.assertTrue((sensitivity["rank"] >= 1).all())
        therapeutic = sensitivity.loc[sensitivity["score_name"] == "therapeutic_priority"]
        self.assertIn("therapeutic_role", therapeutic.columns)
        self.assertIn("role_changed_vs_base", therapeutic.columns)
        self.assertEqual(
            set(therapeutic["scenario"].unique()),
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
        self.assertEqual(by_protein.loc["PA0002", "therapeutic_role"], "low_priority_candidate")
        self.assertEqual(by_protein.loc["PA0002", "therapeutic_role_rule"], "poor_infection_site_access")
        self.assertEqual(by_protein.loc["PA0003", "therapeutic_role"], "low_priority_candidate")
        self.assertEqual(by_protein.loc["PA0003", "therapeutic_role_rule"], "poor_infection_site_access")
        self.assertEqual(by_protein.loc["PA0004", "therapeutic_role"], "bactericidal_candidate")
        self.assertEqual(
            by_protein.loc["PA0004", "therapeutic_role_rule"],
            "strong_bactericidal_signal_with_limited_access",
        )
        self.assertEqual(by_protein.loc["PA0007", "therapeutic_role"], "antivirulence_candidate")
        self.assertEqual(by_protein.loc["PA0010", "therapeutic_role"], "sensitizer_candidate")

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
