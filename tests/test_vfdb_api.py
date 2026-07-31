from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.vfdb_api import fetch_vfdb_virulence
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.online


class VfdbApiTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "data_raw").mkdir(parents=True, exist_ok=True)
        (root / "data_external").mkdir(parents=True, exist_ok=True)
        (root / "results").mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", root / "config" / "params.yaml")
        shutil.copy2(PROJECT_ROOT / "data_raw" / "virulence.csv", root / "data_raw" / "virulence.csv")
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def write_dataset(self, workspace: Path, rows: list[dict]) -> None:
        import pandas as pd

        pd.DataFrame(rows).to_csv(workspace / "data_external" / "vfdb.csv", index=False)
        (workspace / "data_external" / "vfdb.version.txt").write_text(
            "VFDB local test fixture",
            encoding="utf-8",
        )

    def test_cache_hit_returns_without_api_call(self) -> None:
        workspace = self.make_workspace("vfdb_cache")
        config = load_config(workspace / "config" / "params.yaml")
        self.write_dataset(workspace, [{"gene": "lasB", "category": "toxin"}])
        fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        with patch("urllib.request.urlopen") as urlopen_mock:
            result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        urlopen_mock.assert_not_called()
        self.assertEqual(result["manifest"]["source_used"], "cache")

    def test_local_dataset_success_returns_correct_schema(self) -> None:
        workspace = self.make_workspace("vfdb_success")
        config = load_config(workspace / "config" / "params.yaml")
        self.write_dataset(workspace, [{"protein_id": "PA0008", "gene": "lasB", "category": "toxin"}])
        result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        df = result["virulence_data"]
        self.assertEqual(list(df.columns), ["protein_id", "gene", "virulence_score", "virulence_factor", "database"])
        self.assertTrue(df["virulence_score"].between(0, 1).all())
        self.assertEqual(result["manifest"]["source_used"], "local_dataset")
        self.assertTrue(result["manifest"]["provider_success"])
        self.assertFalse(result["manifest"]["api_attempted"])
        self.assertEqual(result["manifest"]["dataset_version"], "VFDB local test fixture")

    def test_missing_local_dataset_is_non_blocking_and_never_calls_network(self) -> None:
        workspace = self.make_workspace("vfdb_failure")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("urllib.request.urlopen") as urlopen_mock:
            result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        urlopen_mock.assert_not_called()
        self.assertFalse(result["manifest"]["api_success"])
        self.assertTrue(result["virulence_data"].empty)
        self.assertEqual(result["manifest"]["retrieval_status"], "local_dataset_missing")
        self.assertFalse(result["manifest"]["affects_score"])

    def test_invalid_local_dataset_does_not_infer_virulence(self) -> None:
        workspace = self.make_workspace("vfdb_invalid")
        config = load_config(workspace / "config" / "params.yaml")
        self.write_dataset(workspace, [{"description": "no supported identifier"}])
        result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        manifest = result["manifest"]
        self.assertTrue(result["virulence_data"].empty)
        self.assertEqual(manifest["retrieval_status"], "local_dataset_invalid")

    def test_unmatched_candidates_are_omitted_not_encoded_as_negative(self) -> None:
        workspace = self.make_workspace("vfdb_unmatched")
        config = load_config(workspace / "config" / "params.yaml")
        self.write_dataset(workspace, [{"gene": "unrelatedGene", "category": "toxin"}])
        result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        manifest = result["manifest"]
        self.assertTrue(result["virulence_data"].empty)
        self.assertEqual(manifest["retrieval_status"], "local_dataset_no_candidate_matches")

    def test_offline_mode_reports_missing_local_dataset_without_raising(self) -> None:
        workspace = self.make_workspace("vfdb_offline")
        config = load_config(workspace / "config" / "params.yaml")
        result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "offline_only")
        self.assertEqual(result["manifest"]["retrieval_status"], "local_dataset_missing")

    def test_disabled_provider_ignores_available_dataset(self) -> None:
        workspace = self.make_workspace("vfdb_disabled")
        config = load_config(workspace / "config" / "params.yaml")
        config["online_sources"]["vfdb"]["enabled"] = False
        self.write_dataset(workspace, [{"gene": "lasB", "category": "toxin"}])

        result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")

        self.assertTrue(result["virulence_data"].empty)
        self.assertEqual(result["manifest"]["retrieval_status"], "provider_disabled")


if __name__ == "__main__":
    unittest.main()
