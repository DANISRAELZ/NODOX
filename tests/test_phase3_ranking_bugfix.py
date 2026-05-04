from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.scoring import build_phase3_scores
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.unit


class Phase3RankingBugfixTests(unittest.TestCase):
    def _workspace(self) -> Path:
        workspace = PROJECT_ROOT / ".tmp_tests" / f"phase3_bugfix_{uuid.uuid4().hex[:8]}"
        for dirname in ["config", "data_processed", "results"]:
            (workspace / dirname).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / "config" / "params.yaml", workspace / "config" / "params.yaml")
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))
        return workspace

    def _config(self, workspace: Path) -> dict:
        return load_config(workspace / "config" / "params.yaml")

    def _base_features(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "protein_id": ["PA0001", "PA0002", "EXAMPLE_PROTEIN"],
                "gene": ["realA", "realB", "EXAMPLE_GENE"],
                "legacy_score_final": [0.50, 0.50, 0.95],
                "meta_priority_score": [0.60, 0.55, 0.99],
                "antibiotic_target_score": [0.82, 0.40, 1.00],
                "antivirulence_target_score": [0.30, 0.78, 1.00],
                "functional_node_score": [0.82, 0.70, 1.00],
                "contextual_essentiality_score": [0.82, 0.70, 1.00],
                "conservation_score": [0.80, 0.65, 1.00],
                "evolutionary_space_constraint_score": [0.82, 0.68, 1.00],
                "evolutionary_escape_risk_score": [0.05, 0.20, 0.00],
                "redundancy_penalty": [0.10, 0.20, 0.00],
                "combination_opportunity_score": [0.20, 0.70, 1.00],
                "evidence_quality_score": [0.70, 0.62, 0.90],
                "confidence_ceiling": [0.85, 0.80, 0.90],
                "essentiality_source_type": ["external", "external", "demo"],
                "virulence_source_type": ["external", "external", "demo"],
                "functional_network_source_type": ["external", "external", "demo"],
                "localization_source_type": ["external", "external", "demo"],
                "source_database": ["computed_uniprot_string", "computed_uniprot_string", "example_curated_demo"],
            }
        )

    def test_meta_priority_score_v3_not_all_zero_for_non_demo_candidates(self) -> None:
        workspace = self._workspace()

        phase3, _ = build_phase3_scores(workspace, self._config(workspace), self._base_features())

        real_scores = phase3.loc[phase3["included_in_therapeutic_ranking"], "meta_priority_score_v3"]
        self.assertGreater(len(real_scores), 0)
        self.assertFalse(real_scores.eq(0.0).all())

    def test_meta_priority_score_v3_uses_defaults_when_workspace_config_is_stale(self) -> None:
        workspace = self._workspace()
        config = self._config(workspace)
        config["phase3"]["meta_priority_v3"] = {}

        phase3, _ = build_phase3_scores(workspace, config, self._base_features())

        real_scores = phase3.loc[phase3["included_in_therapeutic_ranking"], "meta_priority_score_v3"]
        self.assertFalse(real_scores.eq(0.0).all())

    def test_meta_priority_score_v3_persists_after_export(self) -> None:
        workspace = self._workspace()

        build_phase3_scores(workspace, self._config(workspace), self._base_features())
        ranking = pd.read_csv(workspace / "results" / "ranking_nodos_phase3.csv")

        self.assertIn("meta_priority_score_v3", ranking.columns)
        self.assertFalse(ranking.loc[ranking["included_in_therapeutic_ranking"], "meta_priority_score_v3"].eq(0.0).all())

    def test_phase3_ranking_sorted_by_v3_score(self) -> None:
        workspace = self._workspace()

        build_phase3_scores(workspace, self._config(workspace), self._base_features())
        ranking = pd.read_csv(workspace / "results" / "ranking_nodos_phase3_real_candidates.csv")

        observed = ranking["meta_priority_score_v3"].tolist()
        self.assertEqual(observed, sorted(observed, reverse=True))

    def test_example_protein_excluded_from_real_ranking(self) -> None:
        workspace = self._workspace()

        build_phase3_scores(workspace, self._config(workspace), self._base_features())
        ranking = pd.read_csv(workspace / "results" / "ranking_nodos_phase3.csv")
        example = ranking.loc[ranking["protein_id"] == "EXAMPLE_PROTEIN"].iloc[0]
        real = pd.read_csv(workspace / "results" / "ranking_nodos_phase3_real_candidates.csv")

        self.assertTrue(bool(example["is_template_or_demo_record"]))
        self.assertFalse(bool(example["included_in_therapeutic_ranking"]))
        self.assertTrue(pd.isna(example["rank_phase3_real_candidates"]))
        self.assertNotIn("EXAMPLE_PROTEIN", set(real["protein_id"]))

    def test_demo_records_do_not_raise_confidence(self) -> None:
        workspace = self._workspace()

        phase3, _ = build_phase3_scores(workspace, self._config(workspace), self._base_features())
        example = phase3.loc[phase3["protein_id"] == "EXAMPLE_PROTEIN"].iloc[0]

        self.assertLessEqual(float(example["evidence_quality_score"]), 0.10)
        self.assertLessEqual(float(example["confidence_ceiling"]), 0.10)

    def test_literature_template_only_does_not_increase_score(self) -> None:
        workspace = self._workspace()
        features = self._base_features().head(1).copy()
        features["literature_support_score"] = [0.80]
        features["literature_evidence_type"] = ["pending_manual_curation"]
        features["citation"] = ["TO_BE_CURATED"]
        features["doi"] = ["pending_manual_curation"]
        features["literature_support_database"] = ["demo_pending_curation"]

        phase3, _ = build_phase3_scores(workspace, self._config(workspace), features)
        row = phase3.iloc[0]

        self.assertEqual(float(row["literature_support_score"]), 0.0)
        self.assertEqual(row["literature_support_status"], "missing_or_template_only")

    def test_literature_curated_evidence_can_increase_quality(self) -> None:
        workspace = self._workspace()
        features = self._base_features().head(1).copy()
        features["literature_support_score"] = [0.80]
        features["literature_evidence_type"] = ["curated_positive_contextual"]
        features["citation"] = ["Curated synthetic test citation"]
        features["doi"] = ["10.1234/curated.phase3"]
        features["literature_support_database"] = ["curated_literature_manual_catalog"]
        features["evidence_quality_score"] = [0.20]

        phase3, _ = build_phase3_scores(workspace, self._config(workspace), features)
        row = phase3.iloc[0]

        self.assertEqual(row["literature_support_status"], "curated_evidence_present")
        self.assertGreater(float(row["literature_source_quality"]), 0.0)
        self.assertGreater(float(row["evidence_quality_score"]), 0.20)


if __name__ == "__main__":
    unittest.main()
