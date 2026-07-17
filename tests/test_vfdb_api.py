from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.vfdb_api import fetch_vfdb_virulence
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.online


class FakeResponse:
    def __init__(self, payload, content_type: str = "application/json"):
        self._payload = payload
        self._content_type = content_type
        self.status = 200

    def read(self) -> bytes:
        if isinstance(self._payload, bytes):
            return self._payload
        if isinstance(self._payload, str):
            return self._payload.encode("utf-8")
        return json.dumps(self._payload).encode("utf-8")

    def getheader(self, name: str, default: str = "") -> str:
        return self._content_type if name.lower() == "content-type" else default

    def geturl(self) -> str:
        return "http://example.test/provider"

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class VfdbApiTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "data_raw").mkdir(parents=True, exist_ok=True)
        (root / "results").mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", root / "config" / "params.yaml")
        shutil.copy2(PROJECT_ROOT / "data_raw" / "virulence.csv", root / "data_raw" / "virulence.csv")
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_cache_hit_returns_without_api_call(self) -> None:
        workspace = self.make_workspace("vfdb_cache")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.vfdb_api.urlopen", return_value=FakeResponse({"results": [{"gene": "lasB", "category": "toxin"}]})):
            fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        with patch("src.nodos_funcionales.vfdb_api.urlopen") as urlopen_mock:
            result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        urlopen_mock.assert_not_called()
        self.assertEqual(result["manifest"]["source_used"], "cache")

    def test_api_success_returns_correct_schema(self) -> None:
        workspace = self.make_workspace("vfdb_success")
        config = load_config(workspace / "config" / "params.yaml")
        payload = {"results": [{"protein_id": "PA0008", "gene": "lasB", "category": "toxin"}]}
        with patch("src.nodos_funcionales.vfdb_api.urlopen", return_value=FakeResponse(payload)):
            result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        df = result["virulence_data"]
        self.assertEqual(list(df.columns), ["protein_id", "gene", "virulence_score", "virulence_factor", "database"])
        self.assertTrue(df["virulence_score"].between(0, 1).all())
        self.assertEqual(result["manifest"]["source_used"], "api_real")

    def test_api_failure_returns_empty_dataframe(self) -> None:
        workspace = self.make_workspace("vfdb_failure")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.vfdb_api.urlopen", side_effect=URLError("offline")):
            result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        self.assertFalse(result["manifest"]["api_success"])
        self.assertTrue(result["virulence_data"].empty)
        self.assertFalse(result["manifest"]["affects_score"])

    def test_html_or_changed_endpoint_does_not_infer_virulence(self) -> None:
        workspace = self.make_workspace("vfdb_html")
        config = load_config(workspace / "config" / "params.yaml")
        html = "<html><body>VFDB portal changed</body></html>"
        with patch("src.nodos_funcionales.vfdb_api.urlopen", return_value=FakeResponse(html, "text/html")):
            result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        manifest = result["manifest"]
        self.assertTrue(result["virulence_data"].empty)
        self.assertFalse(manifest["api_success"])
        self.assertEqual(manifest["retrieval_status"], "deprecated_or_changed")
        self.assertEqual(manifest["payload_type"], "html")
        self.assertFalse(manifest["affects_score"])

    def test_unexpected_payload_does_not_infer_virulence(self) -> None:
        workspace = self.make_workspace("vfdb_unexpected")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.vfdb_api.urlopen", return_value=FakeResponse("free text", "text/plain")):
            result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        manifest = result["manifest"]
        self.assertTrue(result["virulence_data"].empty)
        self.assertFalse(manifest["api_success"])
        self.assertEqual(manifest["retrieval_status"], "deprecated_or_changed")
        self.assertEqual(manifest["payload_type"], "unexpected_text")
        self.assertFalse(manifest["affects_score"])

    def test_http_404_is_not_found_without_virulence_evidence(self) -> None:
        workspace = self.make_workspace("vfdb_404")
        config = load_config(workspace / "config" / "params.yaml")
        error = HTTPError("http://example.test/vfdb", 404, "not found", {}, None)
        with patch("src.nodos_funcionales.vfdb_api.urlopen", side_effect=error):
            result = fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        manifest = result["manifest"]
        self.assertTrue(result["virulence_data"].empty)
        self.assertFalse(manifest["api_success"])
        self.assertEqual(manifest["retrieval_status"], "not_found")
        self.assertFalse(manifest["affects_score"])

    def test_offline_mode_without_cache_raises(self) -> None:
        workspace = self.make_workspace("vfdb_offline")
        config = load_config(workspace / "config" / "params.yaml")
        with self.assertRaises(FileNotFoundError):
            fetch_vfdb_virulence(workspace, "Pseudomonas aeruginosa", "287", config, "offline_only")


if __name__ == "__main__":
    unittest.main()
