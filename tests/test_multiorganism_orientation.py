from __future__ import annotations

import contextlib
import io
import shutil
import unittest
import uuid
from pathlib import Path

import pandas as pd
import pytest

from run_pipeline import main as run_pipeline_main
from tests.helpers import PROJECT_ROOT

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class MultiorganismOrientationTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_organism_config_template_has_minimum_fields(self) -> None:
        text = (PROJECT_ROOT / "data_templates" / "organism_config_template.yaml").read_text(encoding="utf-8")
        for field in [
            "organism:",
            "strain:",
            "taxon_id:",
            "host:",
            "disease:",
            "infection_site:",
            "analysis_mode:",
            "allow_demo_data:",
            "external_sources:",
            "string:",
            "uniprot:",
            "notes:",
        ]:
            self.assertIn(field, text)

    def test_project_scope_declares_multiorganism_platform(self) -> None:
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        scope = (PROJECT_ROOT / "docs" / "project_scope.md").read_text(encoding="utf-8")
        self.assertIn("plataforma bioinformatica multiorganismo", readme)
        self.assertIn("cualquier organismo bacteriano", readme)
        self.assertIn("Objetivo general", scope)
        self.assertIn("workspaces independientes", scope)

    def test_generic_new_organism_workspace_can_be_created_without_demo(self) -> None:
        workspace = self.make_workspace("generic_bacterium")
        exit_code = run_pipeline_main(
            [
                "--organism",
                "Example bacterium",
                "--strain",
                "strain A",
                "--workspace",
                str(workspace),
                "--dry-run",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue((workspace / "results" / "organism_profile.json").exists())
        self.assertTrue((workspace / "data_raw" / "essentiality.csv").exists())

    def test_missing_candidate_message_is_clear_for_empty_workspace(self) -> None:
        workspace = self.make_workspace("empty_generic")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = run_pipeline_main(
                [
                    "--organism",
                    "Example bacterium",
                    "--workspace",
                    str(workspace),
                    "--acquisition-mode",
                    "manual",
                    "--mode",
                    "compare",
                ]
            )
        self.assertEqual(exit_code, 0)
        self.assertIn("No se encontraron candidatos terapeuticos de entrada", output.getvalue())

    def test_reports_include_organism_strain_and_workspace(self) -> None:
        workspace = self.make_workspace("pao1_multiorganism_report")
        exit_code = run_pipeline_main(
            [
                "--organism",
                "Pseudomonas aeruginosa",
                "--strain",
                "PAO1",
                "--workspace",
                str(workspace),
                "--allow-demo-data",
                "--mode",
                "compare",
                "--offline-only",
            ]
        )
        self.assertEqual(exit_code, 0)
        report = (workspace / "results" / "report_phase2.md").read_text(encoding="utf-8")
        executive = (workspace / "results" / "resumen_ejecutivo.md").read_text(encoding="utf-8")
        for text in [report, executive]:
            self.assertIn("Organismo analizado", text)
            self.assertIn("Pseudomonas aeruginosa", text)
            self.assertIn("PAO1", text)
            self.assertIn(str(workspace), text)
        ranking = pd.read_csv(workspace / "results" / "ranking_nodos.csv")
        self.assertIn("therapeutic_role", ranking.columns)


if __name__ == "__main__":
    unittest.main()
