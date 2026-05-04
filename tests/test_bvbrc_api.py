from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import pytest

from src.nodos_funcionales.bvbrc_api import fetch_bvbrc_strain_conservation
from src.nodos_funcionales.config import load_config
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.online


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class BvbrcApiTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "data_raw").mkdir(parents=True, exist_ok=True)
        (root / "results").mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", root / "config" / "params.yaml")
        shutil.copy2(PROJECT_ROOT / "data_raw" / "essentiality.csv", root / "data_raw" / "essentiality.csv")
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def _payload(self) -> dict:
        return {
            "results": [
                {"patric_id": "PA0001", "gene": "gyrB", "pgfam_id": "PGF_1", "figfam_id": "FIG_1", "genome_id": "g1"},
                {"patric_id": "PA0001", "gene": "gyrB", "pgfam_id": "PGF_1", "figfam_id": "FIG_1", "genome_id": "g2"},
                {"patric_id": "PA0002", "gene": "rpoB", "pgfam_id": "PGF_2", "figfam_id": "FIG_2", "genome_id": "g1"},
            ]
        }

    def test_cache_hit_returns_without_api_call(self) -> None:
        workspace = self.make_workspace("bvbrc_cache")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.bvbrc_api.urlopen", return_value=FakeResponse(self._payload())):
            fetch_bvbrc_strain_conservation(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        with patch("src.nodos_funcionales.bvbrc_api.urlopen") as urlopen_mock:
            result = fetch_bvbrc_strain_conservation(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        urlopen_mock.assert_not_called()
        self.assertEqual(result["manifest"]["source_used"], "cache")

    def test_api_success_returns_correct_schema(self) -> None:
        workspace = self.make_workspace("bvbrc_success")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.bvbrc_api.urlopen", return_value=FakeResponse(self._payload())):
            result = fetch_bvbrc_strain_conservation(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        df = result["strain_conservation_data"]
        self.assertEqual(
            list(df.columns),
            ["protein_id", "gene", "core_genome_presence", "strain_coverage_score", "allelic_conservation", "variant_burden", "database"],
        )
        self.assertTrue(df["core_genome_presence"].between(0, 1).all())
        self.assertEqual(result["manifest"]["source_used"], "api_real")

    def test_api_failure_returns_empty_dataframe(self) -> None:
        workspace = self.make_workspace("bvbrc_failure")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.bvbrc_api.urlopen", side_effect=URLError("offline")):
            result = fetch_bvbrc_strain_conservation(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        self.assertFalse(result["manifest"]["api_success"])
        self.assertTrue(result["strain_conservation_data"].empty)

    def test_offline_mode_without_cache_raises(self) -> None:
        workspace = self.make_workspace("bvbrc_offline")
        config = load_config(workspace / "config" / "params.yaml")
        with self.assertRaises(FileNotFoundError):
            fetch_bvbrc_strain_conservation(workspace, "Pseudomonas aeruginosa", "287", config, "offline_only")


if __name__ == "__main__":
    unittest.main()
