from __future__ import annotations

import unittest
import uuid
import shutil
from unittest.mock import patch

from src.nodos_funcionales.discovery import prepare_discovery_workspace, resolve_taxon
from tests.helpers import PROJECT_ROOT, make_temp_project


class DiscoveryTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_resolve_taxon_alias(self) -> None:
        profile = resolve_taxon(PROJECT_ROOT, "P. aeruginosa", "pao1", resolution_mode="offline_only", refresh_cache=True, no_write_cache=True)
        self.assertEqual(profile["organism_canonical_name"], "Pseudomonas aeruginosa")
        self.assertEqual(profile["strain_canonical"], "PAO1")
        self.assertEqual(profile["taxon_resolution_status"], "alias_local_match")

    def test_resolve_taxon_rejects_empty_name(self) -> None:
        with self.assertRaises(ValueError):
            resolve_taxon(PROJECT_ROOT, "   ")

    def test_semi_auto_generates_profile_manifest_and_templates(self) -> None:
        workspace = self.make_workspace("cpseudo")
        result = prepare_discovery_workspace(
            project_root=PROJECT_ROOT,
            organism_name="Corynebacterium pseudotuberculosis",
            acquisition_mode="semi_auto",
            workspace=workspace,
            no_write_taxon_cache=True,
        )
        self.assertTrue(result["profile_path"].exists())
        self.assertTrue(result["manifest_path"].exists())
        self.assertTrue(result["report_path"].exists())
        self.assertFalse(result["manifest"]["can_run_pipeline"])
        self.assertIn("essentiality.csv", result["manifest"]["missing_required_datasets"])
        self.assertTrue((workspace / "data_raw" / "essentiality.csv").exists())

    def test_manual_mode_with_demo_can_prepare_runnable_workspace(self) -> None:
        workspace = self.make_workspace("paeruginosa")
        result = prepare_discovery_workspace(
            project_root=PROJECT_ROOT,
            organism_name="Pseudomonas aeruginosa",
            strain="PAO1",
            acquisition_mode="manual",
            workspace=workspace,
            allow_demo_data=True,
            no_write_taxon_cache=True,
        )
        self.assertTrue(result["manifest"]["can_run_pipeline"])
        datasets = {entry["filename"]: entry for entry in result["manifest"]["datasets"]}
        self.assertEqual(datasets["essentiality.csv"]["generated_by"], "packaged_demo")
        self.assertEqual(datasets["essentiality.csv"]["source_type"], "demo")

    def test_allow_demo_data_does_not_default_to_pao1_for_generic_organism(self) -> None:
        workspace = self.make_workspace("generic_no_demo_default")
        result = prepare_discovery_workspace(
            project_root=PROJECT_ROOT,
            organism_name="Example bacterium",
            strain="strain A",
            acquisition_mode="manual",
            workspace=workspace,
            allow_demo_data=True,
            no_write_taxon_cache=True,
        )
        self.assertFalse(result["manifest"]["can_run_pipeline"])
        self.assertEqual(result["manifest"]["demo_files_copied"], [])
        datasets = {entry["filename"]: entry for entry in result["manifest"]["datasets"]}
        self.assertFalse(datasets["essentiality.csv"]["present"])
        self.assertEqual(datasets["essentiality.csv"]["generated_by"], "not_generated")
        self.assertEqual(datasets["essentiality.csv"]["source_type"], "missing")
        self.assertIn("no hay demo empaquetado", " | ".join(result["manifest"]["warnings"]))

    def test_cache_first_resolution_uses_local_cache(self) -> None:
        project_root = make_temp_project()
        profile_first = resolve_taxon(
            project_root,
            "Mycobacterium tuberculosis",
            "H37Rv",
            resolution_mode="local",
            refresh_cache=True,
        )
        profile_cached = resolve_taxon(
            project_root,
            "Mycobacterium tuberculosis",
            "H37Rv",
            resolution_mode="cache_first",
        )
        self.assertEqual(profile_first["organism_canonical_name"], profile_cached["organism_canonical_name"])
        self.assertEqual(profile_cached["taxon_resolution_status"], "cache_hit")

    @patch("src.nodos_funcionales.discovery.query_ncbi_taxonomy")
    def test_online_optional_resolution_success(self, query_mock) -> None:
        query_mock.return_value = {
            "provider_name": "ncbi_eutils",
            "provider_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            "provider_docs_url": "https://www.ncbi.nlm.nih.gov/home/develop/api/",
            "matched_name": "Pseudomonas aeruginosa",
            "taxon_id": "287",
            "rank": "species",
            "status": "online_exact_name_match",
            "resolution_confidence": 0.95,
            "notes": "Resolucion por API publica NCBI E-utilities usando termino `Pseudomonas aeruginosa`.",
            "api_error_notes": [],
            "timestamp_utc": "2026-04-22T00:00:00+00:00",
        }
        profile = resolve_taxon(
            PROJECT_ROOT,
            "Pseudomonas aeruginosa",
            "PAO1",
            resolution_mode="online_optional",
            refresh_cache=True,
            no_write_cache=True,
        )
        self.assertEqual(profile["source_used"], "api_real")
        self.assertTrue(profile["api_success"])
        self.assertEqual(profile["taxon_id"], "287")
        self.assertEqual(profile["rank"], "species")

    @patch("src.nodos_funcionales.discovery.query_ncbi_taxonomy")
    def test_online_optional_resolution_fallback(self, query_mock) -> None:
        query_mock.return_value = {
            "provider_name": "ncbi_eutils",
            "provider_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            "provider_docs_url": "https://www.ncbi.nlm.nih.gov/home/develop/api/",
            "matched_name": None,
            "taxon_id": None,
            "rank": None,
            "status": "online_no_match",
            "resolution_confidence": 0.0,
            "notes": "La API publica no devolvio una coincidencia taxonomica utilizable.",
            "api_error_notes": ["Timeout during esearch for `Corynebacterium pseudotuberculosis`"],
            "timestamp_utc": "2026-04-22T00:00:00+00:00",
        }
        profile = resolve_taxon(
            PROJECT_ROOT,
            "Corynebacterium pseudotuberculosis",
            resolution_mode="online_optional",
            refresh_cache=True,
            no_write_cache=True,
        )
        self.assertEqual(profile["source_used"], "local_catalog")
        self.assertTrue(profile["api_attempted"])
        self.assertFalse(profile["api_success"])
        self.assertEqual(profile["fallback_reason"], "api_no_match")
        self.assertEqual(profile["taxon_resolution_status"], "online_fallback_local_no_match")


if __name__ == "__main__":
    unittest.main()
