from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import pandas as pd
import pytest

from fetch_online_data import main as fetch_online_main
from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.pipeline import run_pipeline
from src.nodos_funcionales.uniprot_api import (
    fetch_uniprot_annotations,
    invalidate_uniprot_cache_entry,
    invalidate_uniprot_cache_entries_for_protein,
    load_uniprot_cache,
)

pytestmark = pytest.mark.online
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import PROJECT_ROOT


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class UniProtApiTests(unittest.TestCase):
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

    def _uniprot_payload(self, gene: str) -> dict:
        return {
            "results": [
                {
                    "primaryAccession": f"ACC_{gene}",
                    "uniProtkbId": f"ID_{gene}",
                    "entryType": "UniProtKB reviewed (Swiss-Prot)",
                    "annotationScore": 5.0,
                    "organism": {"scientificName": "Pseudomonas aeruginosa"},
                    "genes": [{"geneName": {"value": gene}}],
                    "proteinDescription": {"recommendedName": {"fullName": {"value": f"Protein {gene}"}}},
                }
            ]
        }

    def test_fetch_uniprot_annotations_success(self) -> None:
        workspace = self.make_workspace("uniprot_success")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.uniprot_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [FakeResponse(self._uniprot_payload(gene)) for gene in ["gyrB", "rpoB", "ftsZ", "murA", "fabI", "acpP", "oprD", "lasB", "algD", "pvdA"]]
            result = fetch_uniprot_annotations(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
            )
        self.assertTrue((workspace / "data_raw" / "uniprot_annotations.csv").exists())
        self.assertEqual(result["manifest"]["source"], "uniprot")
        df = pd.read_csv(workspace / "data_raw" / "uniprot_annotations.csv")
        self.assertIn("uniprot_accession", df.columns)
        self.assertEqual(len(df), 10)

    def test_fetch_uniprot_annotations_offline_uses_cache(self) -> None:
        workspace = self.make_workspace("uniprot_cache")
        config = load_config(workspace / "config" / "params.yaml")
        genes = ["gyrB", "rpoB", "ftsZ", "murA", "fabI", "acpP", "oprD", "lasB", "algD", "pvdA"]
        with patch("src.nodos_funcionales.uniprot_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [FakeResponse(self._uniprot_payload(gene)) for gene in genes]
            fetch_uniprot_annotations(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
            )
        with patch("src.nodos_funcionales.uniprot_api.urlopen", side_effect=URLError("offline")):
            result = fetch_uniprot_annotations(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="offline_only",
            )
        self.assertEqual(result["manifest"]["source_used"], "cache")
        self.assertTrue(result["manifest"]["cache_hit"])
        self.assertFalse(result["manifest"]["api_attempted"])
        self.assertFalse(result["manifest"]["api_success"])
        self.assertTrue(load_uniprot_cache(workspace, config)["entries"])

    def test_invalidate_uniprot_cache_entry(self) -> None:
        workspace = self.make_workspace("uniprot_invalidate")
        config = load_config(workspace / "config" / "params.yaml")
        genes = ["gyrB", "rpoB", "ftsZ", "murA", "fabI", "acpP", "oprD", "lasB", "algD", "pvdA"]
        with patch("src.nodos_funcionales.uniprot_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [FakeResponse(self._uniprot_payload(gene)) for gene in genes]
            fetch_uniprot_annotations(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
            )
        cache = load_uniprot_cache(workspace, config)
        cache_key = next(iter(cache["entries"].keys()))
        self.assertTrue(invalidate_uniprot_cache_entry(workspace, config, cache_key))
        self.assertFalse(load_uniprot_cache(workspace, config)["entries"])

    def test_invalidate_uniprot_cache_entries_for_protein(self) -> None:
        workspace = self.make_workspace("uniprot_invalidate_protein")
        config = load_config(workspace / "config" / "params.yaml")
        genes = ["gyrB", "rpoB", "ftsZ", "murA", "fabI", "acpP", "oprD", "lasB", "algD", "pvdA"]
        with patch("src.nodos_funcionales.uniprot_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [FakeResponse(self._uniprot_payload(gene)) for gene in genes]
            fetch_uniprot_annotations(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
            )
        removed_count = invalidate_uniprot_cache_entries_for_protein(workspace, config, "PA0001")
        self.assertEqual(removed_count, 1)
        self.assertFalse(load_uniprot_cache(workspace, config)["entries"])

    def test_uniprot_annotations_enrich_normalization(self) -> None:
        workspace = self.make_workspace("uniprot_pipeline")
        config = load_config(workspace / "config" / "params.yaml")
        genes = ["gyrB", "rpoB", "ftsZ", "murA", "fabI", "acpP", "oprD", "lasB", "algD", "pvdA"]
        with patch("src.nodos_funcionales.uniprot_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [FakeResponse(self._uniprot_payload(gene)) for gene in genes]
            fetch_uniprot_annotations(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                mode="online_optional",
            )
        load_and_validate_all(workspace, config)
        normalize_all(workspace, config)
        integrated = integrate_tables(workspace)
        self.assertIn("uniprot_accession", integrated.columns)
        self.assertIn("uniprot_match_status", integrated.columns)

    @patch("src.nodos_funcionales.uniprot_api.urlopen")
    def test_fetch_online_data_cli_supports_uniprot(self, urlopen_mock) -> None:
        workspace = self.make_workspace("uniprot_cli")
        run_pipeline(workspace, workspace / "config" / "params.yaml", mode="compare")
        genes = ["gyrB", "rpoB", "ftsZ", "murA", "fabI", "acpP", "oprD", "lasB", "algD", "pvdA"]
        urlopen_mock.side_effect = [FakeResponse(self._uniprot_payload(gene)) for gene in genes]
        exit_code = fetch_online_main(
            [
                "--organism",
                "Pseudomonas aeruginosa",
                "--workspace",
                str(workspace),
                "--source",
                "uniprot",
                "--mode",
                "online_optional",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue((workspace / "data_raw" / "uniprot_annotations.csv").exists())
        self.assertTrue((workspace / "results" / "online_source_history.jsonl").exists())
        self.assertTrue((workspace / "results" / "online_source_comparison.csv").exists())
        impact = pd.read_csv(workspace / "results" / "online_enrichment_impact.csv")
        self.assertIn("rank_before_online", impact.columns)
        self.assertIn("rank_after_online", impact.columns)
        self.assertIn("impact_scope", impact.columns)
        self.assertTrue(impact["impact_scope"].isin(["ranking_changed", "annotation_or_provenance_only"]).all())


if __name__ == "__main__":
    unittest.main()
