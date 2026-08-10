from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.pipeline import run_pipeline
from src.nodos_funcionales.scoring import build_phase3_scores
from tests.helpers import PROJECT_ROOT

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class Phase3ScoringTests(unittest.TestCase):
    def _make_workspace(self) -> Path:
        workspace = PROJECT_ROOT / ".tmp_tests" / f"phase3_{uuid.uuid4().hex[:8]}"
        for dirname in ["data_raw", "config", "data_processed", "results"]:
            (workspace / dirname).mkdir(parents=True, exist_ok=True)
        for path in (PROJECT_ROOT / "data_raw").glob("*.csv"):
            shutil.copyfile(path, workspace / "data_raw" / path.name)
        shutil.copyfile(PROJECT_ROOT / "config" / "params.yaml", workspace / "config" / "params.yaml")
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))
        return workspace

    def test_phase3_pipeline_generates_parallel_outputs_without_breaking_phase2(self) -> None:
        workspace = self._make_workspace()

        result = run_pipeline(workspace, workspace / "config" / "params.yaml", mode="phase3")

        self.assertGreater(result["score_rows"], 0)
        self.assertTrue((workspace / "data_processed" / "scored_nodes.csv").exists())
        self.assertTrue((workspace / "data_processed" / "phase3_features.csv").exists())
        self.assertTrue((workspace / "data_processed" / "scored_nodes_phase3.csv").exists())
        self.assertTrue((workspace / "results" / "ranking_nodos.csv").exists())
        self.assertTrue((workspace / "results" / "ranking_nodos_phase3.csv").exists())
        self.assertTrue((workspace / "results" / "phase2_vs_phase3_comparison.csv").exists())
        self.assertTrue((workspace / "results" / "theory_of_nodes_report.md").exists())
        self.assertTrue((workspace / "results" / "evolutionary_escape_audit.csv").exists())
        self.assertTrue((workspace / "results" / "top10_functional_node_theory_audit.md").exists())
        self.assertTrue((workspace / "results" / "therapeutic_role_stability_audit.csv").exists())
        self.assertTrue((workspace / "results" / "therapeutic_role_stability_report.md").exists())
        self.assertTrue((workspace / "results" / "evolutionary_coverage_evidence_records.csv").exists())
        self.assertTrue((workspace / "results" / "evolutionary_coverage_by_candidate.csv").exists())
        self.assertTrue((workspace / "results" / "evolutionary_coverage_distribution.csv").exists())
        self.assertTrue((workspace / "results" / "evolutionary_coverage_manifest.json").exists())
        self.assertTrue((workspace / "results" / "evolutionary_coverage_report.md").exists())

        phase2 = pd.read_csv(workspace / "data_processed" / "scored_nodes.csv")
        phase3 = pd.read_csv(workspace / "data_processed" / "scored_nodes_phase3.csv")
        comparison = pd.read_csv(workspace / "results" / "phase2_vs_phase3_comparison.csv")
        escape_audit = pd.read_csv(workspace / "results" / "evolutionary_escape_audit.csv")
        stability_audit = pd.read_csv(workspace / "results" / "therapeutic_role_stability_audit.csv")
        report_text = (workspace / "results" / "theory_of_nodes_report.md").read_text(encoding="utf-8")
        top10_text = (workspace / "results" / "top10_functional_node_theory_audit.md").read_text(encoding="utf-8")
        stability_text = (workspace / "results" / "therapeutic_role_stability_report.md").read_text(encoding="utf-8")
        self.assertIn("meta_priority_score", phase2.columns)
        self.assertIn("meta_priority_score_v3", phase3.columns)
        self.assertIn("rank_delta", comparison.columns)
        self.assertIn("evolutionary_escape_risk_score", escape_audit.columns)
        self.assertIn("audit_flags", escape_audit.columns)
        self.assertIn("stability_label", stability_audit.columns)
        self.assertIn("Therapeutic Role Stability Audit", stability_text)
        self.assertIn("Top 10 por meta_priority_score_v3", report_text)
        self.assertIn("Datos demo", report_text)
        self.assertIn("Interpretacion final", top10_text)

    def test_phase3_can_be_skipped_by_config_in_compare_mode(self) -> None:
        workspace = self._make_workspace()

        run_pipeline(workspace, workspace / "config" / "params.yaml", mode="compare")

        self.assertFalse((workspace / "data_processed" / "scored_nodes_phase3.csv").exists())
        self.assertFalse((workspace / "results" / "ranking_nodos_phase3.csv").exists())

    def test_phase3_scores_are_between_zero_and_one(self) -> None:
        features = pd.DataFrame(
            {
                "protein_id": ["A", "B"],
                "gene": ["a", "b"],
                "legacy_score_final": [0.5, 0.5],
                "meta_priority_score": [0.6, 0.6],
                "antibiotic_target_score": [0.8, 0.2],
                "antivirulence_target_score": [0.2, 0.8],
                "functional_node_score": [0.9, 0.9],
                "contextual_essentiality_score": [0.9, 0.9],
                "conservation_score": [0.9, 0.9],
                "evidence_quality_score": [0.9, 0.9],
                "confidence_ceiling": [0.9, 0.9],
            }
        )
        workspace = self._make_workspace()
        config = load_config(workspace / "config" / "params.yaml")

        with pytest.warns(RuntimeWarning, match="only demo/template or missing candidates"):
            phase3, _ = build_phase3_scores(workspace, config, features)

        self.assertTrue(phase3["meta_priority_score_v3"].between(0, 1).all())
        self.assertTrue(phase3["functional_node_theory_score"].between(0, 1).all())

    def test_high_escape_risk_lowers_phase3_score(self) -> None:
        features = pd.DataFrame(
            {
                "protein_id": ["low_escape", "high_escape"],
                "gene": ["low", "high"],
                "legacy_score_final": [0.5, 0.5],
                "meta_priority_score": [0.7, 0.7],
                "antibiotic_target_score": [0.8, 0.8],
                "antivirulence_target_score": [0.6, 0.6],
                "functional_node_score": [0.8, 0.8],
                "contextual_essentiality_score": [0.8, 0.8],
                "conservation_score": [0.8, 0.8],
                "evolutionary_space_constraint_score": [0.8, 0.8],
                "evidence_quality_score": [0.8, 0.8],
                "confidence_ceiling": [0.9, 0.9],
                "evolutionary_escape_risk_score": [0.05, 0.95],
            }
        )
        workspace = self._make_workspace()
        config = load_config(workspace / "config" / "params.yaml")

        with pytest.warns(RuntimeWarning, match="only demo/template or missing candidates"):
            phase3, _ = build_phase3_scores(workspace, config, features)
        scores = phase3.set_index("protein_id")["meta_priority_score_v3"]

        self.assertGreater(float(scores.loc["low_escape"]), float(scores.loc["high_escape"]))

    def test_high_evolutionary_constraint_raises_phase3_score(self) -> None:
        features = pd.DataFrame(
            {
                "protein_id": ["low_constraint", "high_constraint"],
                "gene": ["low", "high"],
                "legacy_score_final": [0.5, 0.5],
                "meta_priority_score": [0.6, 0.6],
                "antibiotic_target_score": [0.5, 0.5],
                "antivirulence_target_score": [0.5, 0.5],
                "functional_node_score": [0.6, 0.6],
                "contextual_essentiality_score": [0.6, 0.6],
                "conservation_score": [0.6, 0.6],
                "evolutionary_space_constraint_score": [0.10, 0.95],
                "evidence_quality_score": [0.8, 0.8],
                "confidence_ceiling": [0.9, 0.9],
            }
        )
        workspace = self._make_workspace()
        config = load_config(workspace / "config" / "params.yaml")

        with pytest.warns(RuntimeWarning, match="only demo/template or missing candidates"):
            phase3, _ = build_phase3_scores(workspace, config, features)
        scores = phase3.set_index("protein_id")["meta_priority_score_v3"]

        self.assertGreater(float(scores.loc["high_constraint"]), float(scores.loc["low_constraint"]))


if __name__ == "__main__":
    unittest.main()
