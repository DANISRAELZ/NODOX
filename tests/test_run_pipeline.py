from __future__ import annotations

import unittest
from pathlib import Path
import shutil
import uuid
from unittest.mock import patch

import pytest

from run_pipeline import main
from tests.helpers import PROJECT_ROOT

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.slow]


class RunPipelineTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_run_pipeline_dry_run(self) -> None:
        workspace = self.make_workspace("dry_run_case")
        exit_code = main(
            [
                "--organism",
                "Corynebacterium pseudotuberculosis",
                "--acquisition-mode",
                "semi_auto",
                "--workspace",
                str(workspace),
                "--dry-run",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue((workspace / "results" / "organism_profile.json").exists())
        self.assertTrue((workspace / "results" / "acquisition_manifest.json").exists())

    def test_run_pipeline_with_packaged_demo_executes_existing_engine(self) -> None:
        workspace = self.make_workspace("demo_run_case")
        exit_code = main(
            [
                "--organism",
                "Pseudomonas aeruginosa",
                "--strain",
                "PAO1",
                "--acquisition-mode",
                "manual",
                "--workspace",
                str(workspace),
                "--allow-demo-data",
                "--mode",
                "compare",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue((workspace / "results" / "ranking_nodos.csv").exists())
        self.assertTrue((workspace / "results" / "report_phase2.md").exists())

    @patch("src.nodos_funcionales.discovery.query_ncbi_taxonomy")
    def test_run_pipeline_online_optional_dry_run(self, query_mock) -> None:
        query_mock.return_value = {
            "provider_name": "ncbi_eutils",
            "provider_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            "provider_docs_url": "https://www.ncbi.nlm.nih.gov/home/develop/api/",
            "matched_name": "Mycobacterium tuberculosis",
            "taxon_id": "1773",
            "rank": "species",
            "status": "online_exact_name_match",
            "resolution_confidence": 0.95,
            "notes": "Resolucion por API publica NCBI E-utilities usando termino `Mycobacterium tuberculosis`.",
            "api_error_notes": [],
            "timestamp_utc": "2026-04-22T00:00:00+00:00",
        }
        workspace = self.make_workspace("online_optional_case")
        exit_code = main(
            [
                "--organism",
                "Mycobacterium tuberculosis",
                "--strain",
                "H37Rv",
                "--taxon-resolution-mode",
                "online_optional",
                "--refresh-taxon-cache",
                "--workspace",
                str(workspace),
                "--dry-run",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue((workspace / "results" / "organism_profile.json").exists())


if __name__ == "__main__":
    unittest.main()
