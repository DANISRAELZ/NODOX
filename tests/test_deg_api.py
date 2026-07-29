from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.deg_api import fetch_deg_essentiality
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.online


class DegApiTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "data_raw").mkdir(parents=True, exist_ok=True)
        (root / "data_external").mkdir(parents=True, exist_ok=True)
        (root / "results").mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", root / "config" / "params.yaml")
        shutil.copy2(PROJECT_ROOT / "data_raw" / "essentiality.csv", root / "data_raw" / "essentiality.csv")
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def write_dataset(self, workspace: Path, rows: list[dict]) -> None:
        pd.DataFrame(rows).to_csv(workspace / "data_external" / "deg.csv", index=False)
        (workspace / "data_external" / "deg.version.txt").write_text(
            "DEG local test fixture",
            encoding="utf-8",
        )

    def test_cache_hit_returns_without_api_call(self) -> None:
        workspace = self.make_workspace("deg_cache")
        config = load_config(workspace / "config" / "params.yaml")
        self.write_dataset(workspace, [{"gene": "gyrB", "evidence": "TnSeq"}])
        fetch_deg_essentiality(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        with patch("urllib.request.urlopen") as urlopen_mock:
            result = fetch_deg_essentiality(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        urlopen_mock.assert_not_called()
        self.assertEqual(result["manifest"]["source_used"], "cache")

    def test_local_dataset_success_returns_correct_schema(self) -> None:
        workspace = self.make_workspace("deg_success")
        config = load_config(workspace / "config" / "params.yaml")
        self.write_dataset(workspace, [{"protein_id": "PA0001", "gene": "gyrB", "evidence": "TnSeq"}])
        result = fetch_deg_essentiality(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        df = result["essentiality_data"]
        self.assertEqual(list(df.columns), ["protein_id", "gene", "essential", "evidence", "database"])
        self.assertTrue(df["essential"].eq(1).all())
        self.assertEqual(result["manifest"]["source_used"], "local_dataset")
        self.assertTrue(result["manifest"]["provider_success"])
        self.assertFalse(result["manifest"]["api_attempted"])
        self.assertEqual(result["manifest"]["dataset_version"], "DEG local test fixture")

    def test_missing_local_dataset_is_non_blocking_and_never_calls_network(self) -> None:
        workspace = self.make_workspace("deg_failure")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("urllib.request.urlopen") as urlopen_mock:
            result = fetch_deg_essentiality(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        urlopen_mock.assert_not_called()
        self.assertFalse(result["manifest"]["api_success"])
        self.assertTrue(result["essentiality_data"].empty)
        self.assertEqual(result["manifest"]["retrieval_status"], "local_dataset_missing")
        self.assertFalse(result["manifest"]["affects_score"])

    def test_invalid_local_dataset_is_conservative_unresolved(self) -> None:
        workspace = self.make_workspace("deg_invalid")
        config = load_config(workspace / "config" / "params.yaml")
        self.write_dataset(workspace, [{"description": "no supported identifier"}])
        result = fetch_deg_essentiality(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        manifest = result["manifest"]
        self.assertTrue(result["essentiality_data"].empty)
        self.assertEqual(manifest["retrieval_status"], "local_dataset_invalid")

    def test_unmatched_candidates_are_omitted_not_encoded_as_nonessential(self) -> None:
        workspace = self.make_workspace("deg_unmatched")
        config = load_config(workspace / "config" / "params.yaml")
        self.write_dataset(workspace, [{"gene": "unrelatedGene", "evidence": "knockout"}])
        result = fetch_deg_essentiality(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        manifest = result["manifest"]
        self.assertTrue(result["essentiality_data"].empty)
        self.assertEqual(manifest["retrieval_status"], "local_dataset_no_candidate_matches")

    def test_offline_mode_reports_missing_local_dataset_without_raising(self) -> None:
        workspace = self.make_workspace("deg_offline")
        config = load_config(workspace / "config" / "params.yaml")
        result = fetch_deg_essentiality(workspace, "Pseudomonas aeruginosa", "287", config, "offline_only")
        self.assertEqual(result["manifest"]["retrieval_status"], "local_dataset_missing")

    def test_disabled_provider_ignores_available_dataset(self) -> None:
        workspace = self.make_workspace("deg_disabled")
        config = load_config(workspace / "config" / "params.yaml")
        config["online_sources"]["deg"]["enabled"] = False
        self.write_dataset(workspace, [{"gene": "gyrB", "evidence": "knockout"}])

        result = fetch_deg_essentiality(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")

        self.assertTrue(result["essentiality_data"].empty)
        self.assertEqual(result["manifest"]["retrieval_status"], "provider_disabled")


if __name__ == "__main__":
    unittest.main()
