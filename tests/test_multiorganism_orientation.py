from __future__ import annotations

import contextlib
import io
import json
import shutil
import unittest
import uuid
from pathlib import Path

import pandas as pd
import pytest

from run_pipeline import build_parser
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

    def test_readme_labels_pao1_as_demo_not_default(self) -> None:
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("PAO1 unicamente como organismo demo reproducible", readme)
        self.assertIn("El flujo no esta acoplado a PAO1", readme)
        self.assertIn('python run_pipeline.py --organism "Organism name" --strain "Strain name"', readme)
        self.assertNotIn("PAO1 es el organismo por defecto", readme)
        self.assertNotIn("organismo base obligatorio", readme)

    def test_cli_help_keeps_demo_data_optional_and_not_default(self) -> None:
        help_text = build_parser().format_help()
        normalized_help = " ".join(help_text.split())
        self.assertIn("--organism", help_text)
        self.assertIn("--strain", help_text)
        self.assertIn("no define un organismo por defecto", normalized_help)

    def test_maturity_audit_records_templates_as_neutral(self) -> None:
        text = (PROJECT_ROOT / "docs" / "multiorganism_maturity_audit.md").read_text(encoding="utf-8")
        self.assertIn("user_defined_organism", text)
        self.assertIn("ya no sugiere PAO1 como organismo por defecto", text)
        self.assertNotIn("Algunas plantillas contienen PAO1 como ejemplo concreto", text)

    def test_multiorganism_architecture_preserves_evolutionary_contract(self) -> None:
        text = (PROJECT_ROOT / "docs" / "multiorganism_architecture.md").read_text(encoding="utf-8")
        normalized = text.casefold()

        self.assertIn("contrato evolutivo multi-organismo", normalized)
        self.assertIn("Teoria de Nodos Funcionales", text)
        self.assertIn("cualquier organismo bacteriano", text)
        self.assertIn("no debe interpretarse como bajo riesgo de escape", text)
        self.assertIn("no sustituyen evidencia real del usuario", text)

        for term in [
            "evolutionary_escape_risk",
            "evolutionary_constraint",
            "mutation_tolerance",
            "pathway_redundancy",
            "paralog_count",
            "mobile_context",
            "hgt_context",
            "recombination_context",
            "resistance_association",
        ]:
            self.assertIn(term, text)

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
                "--offline-only",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue((workspace / "results" / "organism_profile.json").exists())
        self.assertTrue((workspace / "data_raw" / "essentiality.csv").exists())
        profile = json.loads((workspace / "results" / "organism_profile.json").read_text(encoding="utf-8"))
        manifest = json.loads((workspace / "results" / "acquisition_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["organism_canonical_name"], "Example bacterium")
        self.assertEqual(profile["strain_canonical"], "strain A")
        self.assertEqual(manifest["demo_files_copied"], [])
        self.assertFalse(manifest["allow_demo_data"])
        serialized_manifest = json.dumps(manifest, ensure_ascii=False)
        self.assertNotIn("Pseudomonas aeruginosa", serialized_manifest)
        self.assertNotIn("PAO1", serialized_manifest)

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
