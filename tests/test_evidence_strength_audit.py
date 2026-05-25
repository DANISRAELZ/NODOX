from __future__ import annotations

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


ALLOWED_STRENGTH = {"strong", "moderate", "weak", "insufficient"}


class EvidenceStrengthAuditTests(unittest.TestCase):
    def test_framework_document_exists(self) -> None:
        path = PROJECT_ROOT / "docs" / "evidence_strength_framework.md"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        for label in ALLOWED_STRENGTH:
            self.assertIn(label, text)

    def test_export_generates_evidence_strength_audit_without_changing_scores(self) -> None:
        workspace = self._make_workspace("evidence_strength")
        config = load_config(workspace / "config" / "params.yaml")
        resolve_layer_inputs(workspace, config)
        load_and_validate_all(workspace, config)
        normalize_all(workspace, config)
        integrate_tables(workspace)
        features, scored = build_features_and_scores(workspace, config)
        scored_before = scored[["protein_id", "meta_priority_score", "therapeutic_priority_score"]].copy()
        compute_sensitivity(features, config).to_csv(workspace / "results" / "sensitivity_analysis.csv", index=False)
        export_results(workspace, config)

        audit = pd.read_csv(workspace / "results" / "evidence_strength_audit.csv")
        audit_md = (workspace / "results" / "evidence_strength_audit.md").read_text(encoding="utf-8")
        self.assertIn("evidence_strength", audit.columns)
        self.assertIn("evidence_strength_reason", audit.columns)
        self.assertIn("evidence_strength_scope_note", audit.columns)
        self.assertIn("weak_evidence_flags", audit.columns)
        self.assertTrue(set(audit["evidence_strength"]).issubset(ALLOWED_STRENGTH))
        self.assertTrue(audit["weak_evidence_flags"].str.contains("demo|proxy", regex=True).any())
        self.assertTrue(audit["evidence_strength_scope_note"].str.contains("no modifica therapeutic_priority_score").all())
        self.assertTrue(audit["evidence_strength_scope_note"].str.contains("user_curated significa evidencia aportada").all())
        self.assertTrue(audit["evidence_strength_scope_note"].str.contains("no evidencia externa verificada automaticamente").all())
        self.assertTrue(audit["evidence_strength_scope_note"].str.contains("pending_review, local_note").all())
        self.assertTrue(audit["evidence_strength_scope_note"].str.contains("Evidencia insuficiente no equivale a bajo riesgo").all())
        self.assertTrue(audit["evidence_strength_scope_note"].str.contains("No constituye recomendacion clinica").all())
        self.assertIn("no equivale a validacion experimental", audit_md)
        self.assertIn("no equivale a bajo riesgo", audit_md)

        scored_after = pd.read_csv(workspace / "data_processed" / "scored_nodes.csv")[
            ["protein_id", "meta_priority_score", "therapeutic_priority_score"]
        ]
        pd.testing.assert_frame_equal(scored_before.reset_index(drop=True), scored_after.reset_index(drop=True))

    def test_user_curated_layers_can_improve_interpretive_flags(self) -> None:
        workspace = self._make_workspace("evidence_strength_user")
        user_dir = workspace / "data_user"
        user_dir.mkdir(exist_ok=True)
        shutil.copy2(workspace / "data_raw" / "essentiality.csv", user_dir / "essentiality.csv")
        shutil.copy2(workspace / "data_raw" / "virulence.csv", user_dir / "virulence.csv")
        shutil.copy2(workspace / "data_raw" / "localization.csv", user_dir / "localization.csv")

        config = load_config(workspace / "config" / "params.yaml")
        resolve_layer_inputs(workspace, config)
        load_and_validate_all(workspace, config)
        normalize_all(workspace, config)
        integrate_tables(workspace)
        features, _ = build_features_and_scores(workspace, config)
        export_results(workspace, config)

        audit = pd.read_csv(workspace / "results" / "evidence_strength_audit.csv")
        self.assertTrue(audit["strong_evidence_flags"].str.contains("user_curated_layer_present").any())

    def _make_workspace(self, name: str) -> Path:
        workspace = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
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
