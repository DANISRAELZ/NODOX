from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest
import pandas as pd

from src.nodos_funcionales.bvbrc_api import _build_query_url, fetch_bvbrc_strain_conservation
from src.nodos_funcionales.config import load_config
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.online


class FakeResponse:
    def __init__(
        self,
        payload,
        content_type: str = "application/json",
        content_range: str = "",
    ):
        self._payload = payload
        self._content_type = content_type
        self.headers = {"Content-Type": content_type}
        if content_range:
            self.headers["Content-Range"] = content_range
        self.status = 200

    def read(self) -> bytes:
        if isinstance(self._payload, str):
            return self._payload.encode("utf-8")
        return json.dumps(self._payload).encode("utf-8")

    def getheader(self, name: str, default: str = "") -> str:
        return self.headers.get(name, self.headers.get(name.title(), default))

    def geturl(self) -> str:
        return "https://example.test/bvbrc"

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
        self.assertEqual(
            result["manifest"]["affected_candidate_count"],
            len(df),
        )
        self.assertEqual(
            result["manifest"]["updated_cell_count"],
            len(df) * 4,
        )
        self.assertTrue(result["manifest"]["affects_score"])

    def test_query_uses_supported_taxon_and_candidate_gene_filters(self) -> None:
        config = load_config(PROJECT_ROOT / "config" / "params.yaml")
        proteins = pd.DataFrame(
            [
                {"protein_id": "P1", "gene": "gyrB"},
                {"protein_id": "P2", "gene": "rpoB"},
            ]
        )

        url = _build_query_url("287", config["online_sources"]["bvbrc"], proteins)

        self.assertIn("eq(taxon_id,287)", url)
        self.assertIn("in(gene,(gyrB,rpoB))", url)
        self.assertIn("limit(25000)", url)
        self.assertNotIn("taxon_lineage_ids", url)

    def test_unmatched_candidates_are_omitted_not_encoded_as_zero(self) -> None:
        workspace = self.make_workspace("bvbrc_no_negative_rows")
        config = load_config(workspace / "config" / "params.yaml")
        genome_payload = {"results": [{"genome_id": "g1"}, {"genome_id": "g2"}]}
        feature_payload = {
            "results": [
                {"gene": "gyrB", "pgfam_id": "PGF_1", "genome_id": "g1"},
            ]
        }
        with patch(
            "src.nodos_funcionales.bvbrc_api.urlopen",
            side_effect=[FakeResponse(genome_payload), FakeResponse(feature_payload)],
        ):
            result = fetch_bvbrc_strain_conservation(
                workspace,
                "Pseudomonas aeruginosa",
                "287",
                config,
                "online_optional",
            )

        data = result["strain_conservation_data"]
        self.assertEqual(set(data["gene"]), {"gyrB"})
        self.assertEqual(data.iloc[0]["core_genome_presence"], 0.5)

    def test_content_range_is_paginated_before_conservation_is_derived(self) -> None:
        workspace = self.make_workspace("bvbrc_paginated")
        config = load_config(workspace / "config" / "params.yaml")
        genome_payload = {"results": [{"genome_id": "g1"}, {"genome_id": "g2"}]}
        first_page = [{"gene": "gyrB", "pgfam_id": "PGF_1", "genome_id": "g1"}]
        second_page = [{"gene": "gyrB", "pgfam_id": "PGF_1", "genome_id": "g2"}]
        with patch(
            "src.nodos_funcionales.bvbrc_api.urlopen",
            side_effect=[
                FakeResponse(genome_payload, content_range="items 0-2/2"),
                FakeResponse(first_page, content_range="items 0-1/2"),
                FakeResponse(second_page, content_range="items 1-2/2"),
            ],
        ) as urlopen_mock:
            result = fetch_bvbrc_strain_conservation(
                workspace,
                "Pseudomonas aeruginosa",
                "287",
                config,
                "online_optional",
            )

        self.assertEqual(urlopen_mock.call_count, 3)
        self.assertTrue(result["manifest"]["query_complete"])
        self.assertEqual(result["manifest"]["feature_pages_retrieved"], 2)
        self.assertEqual(result["manifest"]["feature_records_retrieved"], 2)
        self.assertEqual(result["strain_conservation_data"].iloc[0]["core_genome_presence"], 1.0)

    def test_api_failure_returns_empty_dataframe(self) -> None:
        workspace = self.make_workspace("bvbrc_failure")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.bvbrc_api.urlopen", side_effect=URLError("offline")):
            result = fetch_bvbrc_strain_conservation(workspace, "Pseudomonas aeruginosa", "287", config, "cache_first")
        self.assertFalse(result["manifest"]["api_success"])
        self.assertTrue(result["strain_conservation_data"].empty)
        self.assertFalse(result["manifest"]["affects_score"])

    def test_empty_payload_is_verified_empty_not_negative_evidence(self) -> None:
        workspace = self.make_workspace("bvbrc_empty")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.bvbrc_api.urlopen", return_value=FakeResponse([])):
            result = fetch_bvbrc_strain_conservation(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        manifest = result["manifest"]
        self.assertTrue(result["strain_conservation_data"].empty)
        self.assertTrue(manifest["api_success"])
        self.assertEqual(manifest["retrieval_status"], "verified_empty_payload")
        self.assertEqual(manifest["payload_type"], "json")
        self.assertFalse(manifest["affects_score"])

    def test_auth_error_is_non_blocking_provider_status(self) -> None:
        workspace = self.make_workspace("bvbrc_auth")
        config = load_config(workspace / "config" / "params.yaml")
        error = HTTPError("https://example.test/bvbrc", 403, "forbidden", {}, None)
        with patch("src.nodos_funcionales.bvbrc_api.urlopen", side_effect=error):
            result = fetch_bvbrc_strain_conservation(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        manifest = result["manifest"]
        self.assertTrue(result["strain_conservation_data"].empty)
        self.assertFalse(manifest["api_success"])
        self.assertEqual(manifest["retrieval_status"], "auth_or_permission_error")
        self.assertFalse(manifest["affects_score"])

    def test_404_is_not_found_without_negative_evidence(self) -> None:
        workspace = self.make_workspace("bvbrc_404")
        config = load_config(workspace / "config" / "params.yaml")
        error = HTTPError("https://example.test/bvbrc", 404, "not found", {}, None)
        with patch("src.nodos_funcionales.bvbrc_api.urlopen", side_effect=error):
            result = fetch_bvbrc_strain_conservation(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        manifest = result["manifest"]
        self.assertTrue(result["strain_conservation_data"].empty)
        self.assertFalse(manifest["api_success"])
        self.assertEqual(manifest["retrieval_status"], "not_found")
        self.assertFalse(manifest["affects_score"])

    def test_invalid_payload_is_unresolved_without_negative_evidence(self) -> None:
        workspace = self.make_workspace("bvbrc_invalid")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.bvbrc_api.urlopen", return_value=FakeResponse("free text", "text/plain")):
            result = fetch_bvbrc_strain_conservation(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        manifest = result["manifest"]
        self.assertTrue(result["strain_conservation_data"].empty)
        self.assertFalse(manifest["api_success"])
        self.assertEqual(manifest["retrieval_status"], "unresolved")
        self.assertFalse(manifest["affects_score"])

    def test_offline_mode_without_cache_raises(self) -> None:
        workspace = self.make_workspace("bvbrc_offline")
        config = load_config(workspace / "config" / "params.yaml")
        with self.assertRaises(FileNotFoundError):
            fetch_bvbrc_strain_conservation(workspace, "Pseudomonas aeruginosa", "287", config, "offline_only")

    def test_disabled_provider_never_calls_network(self) -> None:
        workspace = self.make_workspace("bvbrc_disabled")
        config = load_config(workspace / "config" / "params.yaml")
        config["online_sources"]["bvbrc"]["enabled"] = False
        with patch("src.nodos_funcionales.bvbrc_api.urlopen") as urlopen_mock:
            result = fetch_bvbrc_strain_conservation(
                workspace,
                "Pseudomonas aeruginosa",
                "287",
                config,
                "online_optional",
            )

        urlopen_mock.assert_not_called()
        self.assertEqual(result["manifest"]["retrieval_status"], "provider_disabled")


if __name__ == "__main__":
    unittest.main()
