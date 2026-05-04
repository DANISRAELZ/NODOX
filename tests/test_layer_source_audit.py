from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.layer_resolver import resolve_layer_inputs
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.reporting import export_results
from src.nodos_funcionales.scoring import build_features_and_scores, compute_sensitivity
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import PROJECT_ROOT

pytestmark = [pytest.mark.integration, pytest.mark.slow]


REQUIRED_LAYERS = {
    "essentiality",
    "virulence",
    "human_homologs",
    "localization",
    "strain_conservation",
    "functional_network",
    "clinical_impact",
    "curated_disease_context",
    "therapy_site_context",
    "host_annotation",
    "literature_support",
}

REQUIRED_FIELDS = {
    "layer",
    "status",
    "labels",
    "primary_source",
    "secondary_source",
    "external_database_connected",
    "cache_supported",
    "demo_available",
    "proxy_or_controlled",
    "manual_curation_required",
    "participates_in_scoring",
    "modifies_ranking",
    "evidence_priority_level",
    "evidence_priority_reason",
    "scientific_risk",
    "evidence_files",
    "recommendation",
}

ALLOWED_RISKS = {"low", "medium", "high"}

ALLOWED_PRIORITY_LEVELS = {
    "1_user_curated_organism_specific",
    "2_external_real_traceable",
    "3_internally_computed_from_user_data",
    "4_raw_local",
    "5_external_general",
    "6_proxy_or_controlled",
    "7_demo",
    "8_missing_or_template_only",
}


class LayerSourceAuditTests(unittest.TestCase):
    def test_audit_markdown_exists(self) -> None:
        self.assertTrue((PROJECT_ROOT / "docs" / "layer_source_audit.md").exists())

    def test_audit_json_exists_and_is_valid(self) -> None:
        path = PROJECT_ROOT / "docs" / "layer_source_audit.json"
        self.assertTrue(path.exists())
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsInstance(payload, list)
        self.assertGreaterEqual(len(payload), len(REQUIRED_LAYERS))

    def test_audit_json_contains_required_layers_and_fields(self) -> None:
        payload = json.loads((PROJECT_ROOT / "docs" / "layer_source_audit.json").read_text(encoding="utf-8"))
        by_layer = {entry["layer"]: entry for entry in payload}

        self.assertTrue(REQUIRED_LAYERS.issubset(by_layer))
        for layer in REQUIRED_LAYERS:
            with self.subTest(layer=layer):
                entry = by_layer[layer]
                self.assertTrue(REQUIRED_FIELDS.issubset(entry))
                self.assertIsInstance(entry["labels"], list)
                self.assertIsInstance(entry["external_database_connected"], bool)
                self.assertIsInstance(entry["cache_supported"], bool)
                self.assertIsInstance(entry["demo_available"], bool)
                self.assertIsInstance(entry["proxy_or_controlled"], bool)
                self.assertIsInstance(entry["manual_curation_required"], bool)
                self.assertIsInstance(entry["participates_in_scoring"], bool)
                self.assertIsInstance(entry["modifies_ranking"], bool)
                self.assertIsInstance(entry["evidence_files"], list)
                self.assertIn(entry["scientific_risk"], ALLOWED_RISKS)
                self.assertIn(entry["evidence_priority_level"], ALLOWED_PRIORITY_LEVELS)
                self.assertTrue(str(entry["evidence_priority_reason"]).strip())
                self.assertTrue(str(entry["recommendation"]).strip())

    def test_audit_docs_do_not_modify_scores_or_ranking(self) -> None:
        workspace = self._make_workspace()
        config = load_config(workspace / "config" / "params.yaml")
        resolve_layer_inputs(workspace, config)
        load_and_validate_all(workspace, config)
        normalize_all(workspace, config)
        integrate_tables(workspace)
        features, scored = build_features_and_scores(workspace, config)
        compute_sensitivity(features, config).to_csv(workspace / "results" / "sensitivity_analysis.csv", index=False)
        export_results(workspace, config)

        ranking_before = pd.read_csv(workspace / "results" / "ranking_nodos.csv")
        scored_before = scored.copy()
        json.loads((PROJECT_ROOT / "docs" / "layer_source_audit.json").read_text(encoding="utf-8"))
        export_results(workspace, config)
        ranking_after = pd.read_csv(workspace / "results" / "ranking_nodos.csv")
        scored_after = pd.read_csv(workspace / "data_processed" / "scored_nodes.csv")

        pd.testing.assert_frame_equal(ranking_before, ranking_after)
        pd.testing.assert_frame_equal(scored_before.reset_index(drop=True), scored_after.reset_index(drop=True))
        self.assertNotIn("evidence_priority_level", ranking_after.columns)
        self.assertNotIn("evidence_priority_level", scored_after.columns)

    def _make_workspace(self) -> Path:
        workspace = PROJECT_ROOT / ".tmp_tests" / f"layer_source_audit_{uuid.uuid4().hex[:8]}"
        for relative in ["config", "data_raw", "data_user", "data_cache", "data_external", "data_processed", "results"]:
            (workspace / relative).mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", workspace / "config" / "params.yaml")
        for source in (PROJECT_ROOT / "data_demo").glob("*.csv"):
            if source.name == "literature_support.csv":
                continue
            shutil.copy2(source, workspace / "data_raw" / source.name)
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))
        return workspace


if __name__ == "__main__":
    unittest.main()
