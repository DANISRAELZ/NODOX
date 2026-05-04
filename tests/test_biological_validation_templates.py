from __future__ import annotations

import shutil
import unittest
import uuid

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.layer_resolver import resolve_layer_inputs
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.scoring import build_features_and_scores
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import PROJECT_ROOT

pytestmark = [pytest.mark.integration, pytest.mark.slow]


REQUIRED_COLUMNS = [
    "gene_id",
    "gene",
    "protein_name",
    "organism",
    "strain",
    "rank",
    "score",
    "essentiality_evidence",
    "conservation_evidence",
    "virulence_evidence",
    "resistance_or_tolerance_evidence",
    "human_homology_risk",
    "host_homology_risk",
    "localization_evidence",
    "functional_network_evidence",
    "literature_support",
    "known_inhibitors",
    "therapeutic_role",
    "validation_status",
    "experimental_priority",
    "notes",
    "curator",
    "date",
]


class BiologicalValidationTemplateTests(unittest.TestCase):
    def test_template_exists_with_required_columns(self) -> None:
        path = PROJECT_ROOT / "data_templates" / "biological_validation_targets.csv"
        self.assertTrue(path.exists())
        self.assertEqual(list(pd.read_csv(path).columns), REQUIRED_COLUMNS)

    def test_documents_exist_and_define_allowed_values(self) -> None:
        framework = PROJECT_ROOT / "docs" / "biological_validation_framework.md"
        summary = PROJECT_ROOT / "docs" / "biological_validation_summary_template.md"
        self.assertTrue(framework.exists())
        self.assertTrue(summary.exists())
        text = framework.read_text(encoding="utf-8")
        for value in [
            "not_evaluated",
            "computational_support_only",
            "literature_supported",
            "experimentally_supported",
            "deprioritized",
            "requires_manual_review",
            "high",
            "medium",
            "low",
            "not_ready",
        ]:
            self.assertIn(value, text)

    def test_validation_template_does_not_modify_scoring(self) -> None:
        workspace = PROJECT_ROOT / ".tmp_tests" / f"biological_validation_{uuid.uuid4().hex[:8]}"
        for relative in ["config", "data_raw", "data_user", "data_cache", "data_external", "data_processed", "results"]:
            (workspace / relative).mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", workspace / "config" / "params.yaml")
        for source in (PROJECT_ROOT / "data_demo").glob("*.csv"):
            if source.name == "literature_support.csv":
                continue
            shutil.copy2(source, workspace / "data_raw" / source.name)

        config = load_config(workspace / "config" / "params.yaml")
        resolve_layer_inputs(workspace, config)
        load_and_validate_all(workspace, config)
        normalize_all(workspace, config)
        integrate_tables(workspace)
        _, scored = build_features_and_scores(workspace, config)

        self.assertIn("meta_priority_score", scored.columns)
        self.assertIn("therapeutic_priority_score", scored.columns)
        self.assertNotIn("validation_status", scored.columns)
        self.assertNotIn("experimental_priority", scored.columns)


if __name__ == "__main__":
    unittest.main()
