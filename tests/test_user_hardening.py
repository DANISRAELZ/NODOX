from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from scripts.clean_generated import collect_generated
from src.nodos_funcionales.io_errors import explain_io_error, read_csv
from src.nodos_funcionales.online.cache import cache_status
from src.nodos_funcionales.online.fallback import online_failure_message
from src.nodos_funcionales.organism_profile import validate_organism_profile
from src.nodos_funcionales.phase3_evidence import build_layer_evidence_audit
from src.nodos_funcionales.provenance_user_summary import build_provenance_user_summary
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.unit


class UserHardeningTests(unittest.TestCase):
    def make_workspace(self) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"hardening_{uuid.uuid4().hex[:8]}"
        (root / "results").mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_provenance_summary_explains_missing_without_negative_evidence(self) -> None:
        features = pd.DataFrame({"protein_id": ["A"], "essentiality_source_type": ["missing"]})
        layer_resolution = pd.DataFrame({"layer": ["essentiality"], "source_type": ["missing"], "retrieval_status": ["missing"]})

        table, markdown = build_provenance_user_summary(features, layer_resolution)

        self.assertIn("missing", table["Tipo principal de evidencia"].tolist())
        self.assertIn("no significa que el blanco sea malo", markdown)

    def test_phase3_audit_has_explicit_missing_and_negative_reasons(self) -> None:
        df = pd.DataFrame({"protein_id": ["A"], "gene": ["a"], "human_homolog": [pd.NA]})

        audit = build_layer_evidence_audit(df)
        human = audit.loc[(audit["layer_name"] == "human_homologs") & (audit["variable_name"] == "human_homolog")].iloc[0]

        self.assertTrue(bool(human["evidence_is_missing"]))
        self.assertTrue(bool(human["evidence_is_unknown"]))
        self.assertFalse(bool(human["evidence_is_negative"]))
        self.assertIn("no es evidencia negativa", human["missing_evidence_reason"])

    def test_real_negative_evidence_requires_real_source(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["A"],
                "gene": ["a"],
                "human_homolog": [1],
                "human_homologs_source_type": ["external"],
                "human_homologs_source_name": ["uniprot"],
                "human_homologs_is_external": [True],
            }
        )

        audit = build_layer_evidence_audit(df)
        human = audit.loc[(audit["layer_name"] == "human_homologs") & (audit["variable_name"] == "human_homolog")].iloc[0]

        self.assertTrue(bool(human["evidence_is_negative"]))
        self.assertIn("human_homologs.human_homolog", human["negative_evidence_reason"])

    def test_organism_profile_classifies_demo_workspace(self) -> None:
        workspace = self.make_workspace()
        features = pd.DataFrame({"protein_id": ["EXAMPLE_PROTEIN"], "essentiality_source_type": ["demo"]})

        summary, markdown = validate_organism_profile(workspace, features)

        self.assertIn("demo_run", summary["readiness_level"].tolist())
        self.assertIn("no debe interpretarse", markdown)

    def test_io_error_message_mentions_onedrive_and_excel(self) -> None:
        message = explain_io_error(PermissionError("locked"), Path("C:/Users/x/OneDrive/results/ranking.csv"), "escribir")

        self.assertIn("Excel", message)
        self.assertIn("OneDrive", message)

    def test_read_csv_wraps_permission_error(self) -> None:
        with patch("pandas.read_csv", side_effect=PermissionError("locked")):
            with self.assertRaises(PermissionError) as ctx:
                read_csv("C:/Users/x/OneDrive/data.csv")

        self.assertIn("bloqueado por OneDrive", str(ctx.exception))

    def test_clean_generated_dry_run_does_not_include_source_data(self) -> None:
        workspace = self.make_workspace()
        (workspace / "data_processed").mkdir()
        (workspace / "data_raw").mkdir()
        (workspace / "data_raw" / "essentiality.csv").write_text("protein_id\nA\n", encoding="utf-8")

        targets = collect_generated(workspace)

        self.assertIn(workspace / "data_processed", targets)
        self.assertNotIn(workspace / "data_raw", targets)

    def test_online_helper_messages_are_clear_without_network(self) -> None:
        self.assertEqual(cache_status("missing-cache-file.json"), "cache_missing")
        self.assertIn("offline_only", online_failure_message("UniProt", "offline_only"))


if __name__ == "__main__":
    unittest.main()
