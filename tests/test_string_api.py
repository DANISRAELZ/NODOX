from __future__ import annotations

import json
import shutil
import ssl
import unittest
import uuid
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import pandas as pd
import pytest

from fetch_online_data import main as fetch_online_main
from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.online_sources import fetch_online_source
from src.nodos_funcionales.pipeline import run_pipeline
from src.nodos_funcionales.scoring import build_features_and_scores
from src.nodos_funcionales.string_api import (
    fetch_string_functional_network,
    invalidate_string_cache_entry,
    invalidate_string_cache_entries_for_protein,
    load_string_cache,
)

pytestmark = pytest.mark.online
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import PROJECT_ROOT


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def getheader(self, name: str, default: str = "") -> str:
        return "application/json" if name.lower() == "content-type" else default

    def geturl(self) -> str:
        return "https://string-db.org/api/json/mock"

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class StringApiTests(unittest.TestCase):
    def offline_ssl_context_patches(self) -> ExitStack:
        stack = ExitStack()
        for target in [
            "src.nodos_funcionales.human_essentiality_api.get_ssl_context",
            "src.nodos_funcionales.interpro_api.get_ssl_context",
            "src.nodos_funcionales.online_http.get_ssl_context",
            "src.nodos_funcionales.online_organism_enrichment.get_ssl_context",
            "src.nodos_funcionales.online_sources.get_ssl_context",
            "src.nodos_funcionales.taxonomy_api.get_ssl_context",
            "src.nodos_funcionales.uniprot_api.get_ssl_context",
        ]:
            stack.enter_context(patch(target, return_value=None))
        return stack

    def make_workspace(self, name: str) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "data_raw").mkdir(parents=True, exist_ok=True)
        (root / "results").mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", root / "config" / "params.yaml")
        for filename in ["essentiality.csv", "virulence.csv", "human_homologs.csv", "localization.csv"]:
            shutil.copy2(PROJECT_ROOT / "data_raw" / filename, root / "data_raw" / filename)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_fetch_string_functional_network_success(self) -> None:
        workspace = self.make_workspace("string_success")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.string_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [
                FakeResponse(
                    [
                        {"queryItem": "PA0001", "stringId": "287.PA0001", "preferredName": "gyrB"},
                        {"queryItem": "PA0002", "stringId": "287.PA0002", "preferredName": "rpoB"},
                    ]
                    + [
                        {"queryItem": f"PA000{i}", "stringId": f"287.PA000{i}", "preferredName": f"gene{i}"}
                        for i in range(3, 10)
                    ]
                    + [{"queryItem": "PA0010", "stringId": "287.PA0010", "preferredName": "pvdA"}]
                ),
                FakeResponse(
                    [
                        {"stringId_A": "287.PA0001", "stringId_B": "287.PA0002", "preferredName_A": "gyrB", "preferredName_B": "rpoB", "score": 0.91},
                        {"stringId_A": "287.PA0002", "stringId_B": "287.PA0003", "preferredName_A": "rpoB", "preferredName_B": "ftsZ", "score": 0.88},
                        {"stringId_A": "287.PA0003", "stringId_B": "287.PA0004", "preferredName_A": "ftsZ", "preferredName_B": "murA", "score": 0.77},
                    ]
                ),
            ]
            result = fetch_string_functional_network(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
                replace_existing=True,
            )

        self.assertTrue((workspace / "data_raw" / "functional_network.csv").exists())
        df = pd.read_csv(workspace / "data_raw" / "functional_network.csv")
        self.assertIn("network_centrality", df.columns)
        self.assertIn("provider", df.columns)
        self.assertIn("mapping_status", df.columns)
        self.assertTrue((workspace / "results" / "string_mapping_audit.csv").exists())
        audit = pd.read_csv(workspace / "results" / "string_mapping_audit.csv")
        self.assertIn("mapping_status", audit.columns)
        self.assertIn("preferred_name_mismatch", set(audit["mapping_status"]))
        self.assertEqual(result["manifest"]["source_used"], "api_real")
        self.assertTrue(result["manifest"]["api_success"])
        self.assertGreater(result["manifest"]["degraded_mapping_count"], 0)

    def test_fetch_string_functional_network_offline_uses_cache(self) -> None:
        workspace = self.make_workspace("string_cache")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.string_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [
                FakeResponse([{"queryItem": f"PA000{i}", "stringId": f"287.PA000{i}", "preferredName": f"gene{i}"} for i in range(1, 10)]
                             + [{"queryItem": "PA0010", "stringId": "287.PA0010", "preferredName": "pvdA"}]),
                FakeResponse([{"stringId_A": "287.PA0001", "stringId_B": "287.PA0002", "score": 0.9}]),
            ]
            fetch_string_functional_network(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
                replace_existing=True,
            )
        with patch("src.nodos_funcionales.string_api.urlopen", side_effect=URLError("offline")):
            result = fetch_string_functional_network(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="offline_only",
                replace_existing=True,
            )
        self.assertEqual(result["manifest"]["source_used"], "cache")
        self.assertTrue(result["manifest"]["cache_hit"])
        self.assertFalse(result["manifest"]["api_attempted"])
        self.assertFalse(result["manifest"]["api_success"])
        df = pd.read_csv(workspace / "data_raw" / "functional_network.csv")
        self.assertIn("mapping_status", df.columns)
        self.assertTrue(df["run_kind"].astype(str).eq("cache_reuse_run").all())
        self.assertTrue(df["cache_status"].astype(str).eq("cache_hit").all())
        cache = load_string_cache(workspace, config)
        self.assertTrue(cache["entries"])

    def test_string_mapping_audit_classifies_exact_mismatch_missing_and_taxon(self) -> None:
        workspace = self.make_workspace("string_mapping_status")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.string_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [
                FakeResponse(
                    [
                        {"queryItem": "PA0001", "stringId": "287.gyrB", "preferredName": "gyrB", "ncbiTaxonId": 287},
                        {"queryItem": "PA0002", "stringId": "287.PA0002", "preferredName": "dnaN", "ncbiTaxonId": 287},
                        {"queryItem": "PA0003", "stringId": "999.ftsZ", "preferredName": "ftsZ", "ncbiTaxonId": 999},
                    ]
                ),
                FakeResponse([]),
            ]
            fetch_string_functional_network(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
                replace_existing=True,
            )

        audit = pd.read_csv(workspace / "results" / "string_mapping_audit.csv")
        by_protein = dict(zip(audit["input_protein_id"], audit["mapping_status"]))
        self.assertEqual(by_protein["PA0001"], "exact_match")
        self.assertEqual(by_protein["PA0002"], "preferred_name_mismatch")
        self.assertEqual(by_protein["PA0003"], "taxon_mismatch")
        self.assertEqual(by_protein["PA0004"], "missing_mapping")
        confidence = dict(zip(audit["input_protein_id"], audit["mapping_confidence"]))
        self.assertGreater(confidence["PA0001"], confidence["PA0002"])
        self.assertEqual(confidence["PA0003"], 0.0)

    def test_string_mapping_audit_classifies_ambiguous_duplicate_mapping(self) -> None:
        workspace = self.make_workspace("string_mapping_ambiguous")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.string_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [
                FakeResponse(
                    [
                        {"queryItem": "PA0001", "stringId": "287.PA0001", "preferredName": "gyrB", "ncbiTaxonId": 287},
                        {"queryItem": "PA0001", "stringId": "287.PA0001_alt", "preferredName": "gyrB_alt", "ncbiTaxonId": 287},
                    ]
                    + [
                        {"queryItem": f"PA000{i}", "stringId": f"287.PA000{i}", "preferredName": f"gene{i}", "ncbiTaxonId": 287}
                        for i in range(2, 11)
                    ]
                ),
                FakeResponse([]),
            ]
            fetch_string_functional_network(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
                replace_existing=True,
            )

        audit = pd.read_csv(workspace / "results" / "string_mapping_audit.csv")
        row = audit.loc[audit["input_protein_id"] == "PA0001"].iloc[0]
        self.assertEqual(row["mapping_status"], "ambiguous_mapping")
        self.assertEqual(int(row["mapping_confidence"] * 100), 40)

    def test_invalidate_string_cache_entry(self) -> None:
        workspace = self.make_workspace("string_invalidate")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.string_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [
                FakeResponse([{"queryItem": f"PA000{i}", "stringId": f"287.PA000{i}", "preferredName": f"gene{i}"} for i in range(1, 10)]
                             + [{"queryItem": "PA0010", "stringId": "287.PA0010", "preferredName": "pvdA"}]),
                FakeResponse([{"stringId_A": "287.PA0001", "stringId_B": "287.PA0002", "score": 0.9}]),
            ]
            fetch_string_functional_network(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
                replace_existing=True,
            )
        cache = load_string_cache(workspace, config)
        cache_key = next(iter(cache["entries"].keys()))
        self.assertTrue(invalidate_string_cache_entry(workspace, config, cache_key))
        cache_after = load_string_cache(workspace, config)
        self.assertFalse(cache_after["entries"])

    def test_invalidate_string_cache_entries_for_protein(self) -> None:
        workspace = self.make_workspace("string_invalidate_protein")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.string_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [
                FakeResponse([{"queryItem": f"PA000{i}", "stringId": f"287.PA000{i}", "preferredName": f"gene{i}"} for i in range(1, 10)]
                             + [{"queryItem": "PA0010", "stringId": "287.PA0010", "preferredName": "pvdA"}]),
                FakeResponse([{"stringId_A": "287.PA0001", "stringId_B": "287.PA0002", "score": 0.9}]),
            ]
            fetch_string_functional_network(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
                replace_existing=True,
            )
        removed_count = invalidate_string_cache_entries_for_protein(workspace, config, "PA0001")
        self.assertEqual(removed_count, 1)
        self.assertFalse(load_string_cache(workspace, config)["entries"])

    def test_fetch_online_source_dispatches_string(self) -> None:
        workspace = self.make_workspace("string_dispatch")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.string_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [
                FakeResponse([{"queryItem": f"PA000{i}", "stringId": f"287.PA000{i}", "preferredName": f"gene{i}"} for i in range(1, 10)]
                             + [{"queryItem": "PA0010", "stringId": "287.PA0010", "preferredName": "pvdA"}]),
                FakeResponse([{"stringId_A": "287.PA0001", "stringId_B": "287.PA0002", "score": 0.9}]),
            ]
            result = fetch_online_source(
                source="string",
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
                replace_existing=True,
            )
        self.assertEqual(result["manifest"]["source"], "string")

    def test_fetch_string_functional_network_partial_network_response(self) -> None:
        workspace = self.make_workspace("string_partial")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.string_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [
                FakeResponse([{"queryItem": f"PA000{i}", "stringId": f"287.PA000{i}", "preferredName": f"gene{i}"} for i in range(1, 10)]
                             + [{"queryItem": "PA0010", "stringId": "287.PA0010", "preferredName": "pvdA"}]),
                FakeResponse([]),
            ]
            result = fetch_string_functional_network(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
                replace_existing=True,
            )
        self.assertEqual(len(result["functional_network"]), 10)
        self.assertIn("edge_count", result["manifest"])
        self.assertEqual(result["manifest"]["retrieval_status"], "connected_structured_payload")
        self.assertFalse(result["manifest"]["blocks_ranking"])

    def test_string_ssl_error_degrades_without_evidence(self) -> None:
        workspace = self.make_workspace("string_ssl_error")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.string_api.urlopen", side_effect=ssl.SSLError("OPENSSL_Applink")):
            with self.assertRaisesRegex(ValueError, "ssl_error"):
                fetch_string_functional_network(
                    workspace=workspace,
                    organism_name="Pseudomonas aeruginosa",
                    taxon_id="287",
                    config=config,
                    mode="online_optional",
                    replace_existing=True,
                )

    def test_string_network_error_degrades_without_evidence(self) -> None:
        workspace = self.make_workspace("string_network_error")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.string_api.urlopen", side_effect=URLError("offline")):
            with self.assertRaisesRegex(ValueError, "unresolved|network_error"):
                fetch_string_functional_network(
                    workspace=workspace,
                    organism_name="Pseudomonas aeruginosa",
                    taxon_id="287",
                    config=config,
                    mode="online_optional",
                    replace_existing=True,
                )

    def test_string_enrichment_integrates_with_pipeline_layers(self) -> None:
        workspace = self.make_workspace("string_pipeline")
        config = load_config(workspace / "config" / "params.yaml")
        config.setdefault("online_sources", {})["source_mode_effective"] = "offline_only"
        with patch("src.nodos_funcionales.string_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [
                FakeResponse([{"queryItem": f"PA000{i}", "stringId": f"287.PA000{i}", "preferredName": f"gene{i}"} for i in range(1, 10)]
                             + [{"queryItem": "PA0010", "stringId": "287.PA0010", "preferredName": "pvdA"}]),
                FakeResponse([{"stringId_A": "287.PA0001", "stringId_B": "287.PA0002", "score": 0.9}]),
            ]
            fetch_string_functional_network(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
                replace_existing=True,
            )

        with self.offline_ssl_context_patches():
            load_and_validate_all(workspace, config)
            normalize_all(workspace, config)
            integrate_tables(workspace)
            features, _ = build_features_and_scores(workspace, config)
        self.assertIn("network_source_type", features.columns)
        self.assertTrue(features["network_source_type"].eq("computed").all())

    @patch("src.nodos_funcionales.string_api.urlopen")
    def test_fetch_online_data_cli_generates_manifest(self, urlopen_mock) -> None:
        workspace = self.make_workspace("string_cli")
        with self.offline_ssl_context_patches():
            run_pipeline(workspace, workspace / "config" / "params.yaml", mode="compare", online_source_mode="offline_only")
        urlopen_mock.side_effect = [
            FakeResponse([{"queryItem": f"PA000{i}", "stringId": f"287.PA000{i}", "preferredName": f"gene{i}"} for i in range(1, 10)]
                         + [{"queryItem": "PA0010", "stringId": "287.PA0010", "preferredName": "pvdA"}]),
            FakeResponse([{"stringId_A": "287.PA0001", "stringId_B": "287.PA0002", "score": 0.9}]),
        ]
        exit_code = fetch_online_main(
            [
                "--organism",
                "Pseudomonas aeruginosa",
                "--workspace",
                str(workspace),
                "--source",
                "string",
                "--mode",
                "online_optional",
                "--replace-existing-functional-network",
                "--skip-pipeline-rerun",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue((workspace / "results" / "online_source_manifest.json").exists())
        self.assertTrue((workspace / "results" / "online_source_report.md").exists())
        self.assertTrue((workspace / "results" / "online_source_history.jsonl").exists())
        self.assertTrue((workspace / "results" / "online_source_comparison.csv").exists())
        impact = pd.read_csv(workspace / "results" / "online_enrichment_impact.csv")
        self.assertIn("rank_before_online", impact.columns)
        self.assertIn("rank_after_online", impact.columns)
        self.assertIn("impact_scope", impact.columns)


if __name__ == "__main__":
    unittest.main()
