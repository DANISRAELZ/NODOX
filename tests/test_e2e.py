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

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.slow]


class EndToEndTests(unittest.TestCase):
    def test_full_phase2_pipeline_runs_on_example_data(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrate_tables(project_dir)
        features, scored = build_features_and_scores(project_dir, config)
        sensitivity = compute_sensitivity(features, config)
        sensitivity.to_csv(project_dir / "results" / "sensitivity_analysis.csv", index=False)
        export_results(project_dir, config)

        ranking = pd.read_csv(project_dir / "results" / "ranking_nodos.csv")
        stability = pd.read_csv(project_dir / "results" / "therapeutic_role_controlled_stability.csv")
        self.assertGreater(len(features), 0)
        self.assertEqual(len(scored), len(features))
        self.assertIn("meta_priority_score", ranking.columns)
        self.assertIn("legacy_score_final", ranking.columns)
        self.assertIn("therapeutic_role_stability_explanation", stability.columns)
        self.assertIn("controlled_context_max_feature_delta", stability.columns)
        self.assertIn("therapeutic_rule_boundary_proximity", stability.columns)
        self.assertIn("clinical_impact_input_status", stability.columns)
        self.assertIn("curated_disease_context_input_status", stability.columns)
        self.assertIn("therapy_site_context_input_status", stability.columns)
        self.assertTrue(stability["clinical_impact_input_status"].isin(["active_input", "resolved_empty_or_not_normalized"]).all())
        self.assertTrue(stability["curated_disease_context_input_status"].isin(["active_input", "resolved_empty_or_not_normalized"]).all())
        self.assertTrue(stability["therapy_site_context_input_status"].isin(["active_input", "resolved_empty_or_not_normalized"]).all())
        self.assertEqual(ranking.iloc[0]["protein_id"], "PA0008")
        self.assertEqual(ranking.iloc[0]["gene"], "lasB")


if __name__ == "__main__":
    unittest.main()
