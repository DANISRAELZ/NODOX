from __future__ import annotations

import io
import shutil
import unittest
import uuid
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
import pytest

from run_pipeline import main
from tests.helpers import PROJECT_ROOT

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.slow]


class RunPipelinePhase3Tests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        workspace = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        workspace.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))
        return workspace

    def test_phase3_cli_runs_with_demo_data_and_writes_expected_outputs(self) -> None:
        workspace = self.make_workspace("phase3_cli_demo")
        stdout = io.StringIO()

        with redirect_stdout(stdout):
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
                    "phase3",
                ]
            )

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("[OK] Phase 3 enabled", output)
        self.assertIn("[OK] Evolutionary escape features computed", output)
        self.assertIn("[OK] Functional Node Theory score computed", output)
        self.assertIn("[OK] Phase 3 ranking written", output)
        self.assertIn("[WARN] Demo data used; confidence capped", output)
        self.assertTrue((workspace / "data_processed" / "phase3_features.csv").exists())
        self.assertTrue((workspace / "data_processed" / "scored_nodes_phase3.csv").exists())
        self.assertTrue((workspace / "results" / "ranking_nodos_phase3.csv").exists())
        self.assertTrue((workspace / "results" / "theory_of_nodes_report.md").exists())
        self.assertTrue((workspace / "results" / "therapeutic_role_stability_audit.csv").exists())

    def test_compare_mode_still_runs_without_phase3_outputs(self) -> None:
        workspace = self.make_workspace("compare_cli_demo")

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
        self.assertFalse((workspace / "results" / "ranking_nodos_phase3.csv").exists())

    def test_phase3_defaults_are_audited_when_optional_phase3_data_is_missing(self) -> None:
        workspace = self.make_workspace("phase3_defaults")

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
                "phase3",
            ]
        )

        self.assertEqual(exit_code, 0)
        features = pd.read_csv(workspace / "data_processed" / "phase3_features.csv")
        audit_text = " ".join(features["audit_flags"].fillna("").astype(str).tolist())
        self.assertIn("demo_data_used", audit_text)
        self.assertTrue(
            any(
                flag in audit_text
                for flag in [
                    "redundancy_data_missing",
                    "evolutionary_escape_defaults_used",
                    "functional_node_theory_missing",
                ]
            )
        )
        self.assertTrue(features["confidence_ceiling"].between(0, 1).all())

    def test_default_mode_is_compatible_alias_for_compare(self) -> None:
        workspace = self.make_workspace("default_cli_demo")

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
                "default",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue((workspace / "results" / "ranking_nodos.csv").exists())
        self.assertFalse((workspace / "results" / "ranking_nodos_phase3.csv").exists())


if __name__ == "__main__":
    unittest.main()
