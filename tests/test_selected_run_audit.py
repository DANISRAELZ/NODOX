from __future__ import annotations

import importlib.util
import json
import unittest
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_selected_run.py"
SPEC = importlib.util.spec_from_file_location("audit_selected_run", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class SelectedRunAuditTests(unittest.TestCase):
    def test_run_audit_selects_phase3_and_preserves_unknown_escape(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            run_dir = root / "results" / "run"
            review = run_dir / "review_package"
            review.mkdir(parents=True)
            pd.DataFrame(
                {
                    "protein_id": ["P1", "P2"],
                    "gene": ["a", "b"],
                    "functional_node_theory_score": [0.8, 0.6],
                    "evolutionary_escape_risk_score": [0.2, 0.5],
                    "evolutionary_escape_risk_status": ["sufficient_evidence", "unknown_missing_evidence"],
                    "mutation_tolerance_score": [0.1, 0.5],
                    "mutation_tolerance_score_is_explicit": [True, False],
                }
            ).to_csv(review / "ranking_nodos_phase3.csv", index=False)
            pd.DataFrame({"protein_id": ["legacy"], "functional_node_theory_score": [0.1]}).to_csv(
                run_dir / "ranking_nodos.csv", index=False
            )
            pd.DataFrame(
                {
                    "provider": ["string", "diamond"],
                    "retrieval_success": [True, True],
                    "mapping_success": [True, True],
                    "usable_evidence": [False, True],
                    "affects_score": [False, True],
                }
            ).to_csv(review / "online_only_provider_audit.csv", index=False)
            (review / "human_homology_diamond_manifest.json").write_text(
                json.dumps({"candidate_sequence_count": 2}), encoding="utf-8"
            )
            config = root / "config.yaml"
            config.write_text(
                "selected_run:\n  expected_candidate_count: 2\n",
                encoding="utf-8",
            )
            output_dir = root / "audit"
            manifest = MODULE.run_audit(
                repo_root=root,
                run_dir=run_dir,
                output_dir=output_dir,
                config_path=config,
            )
            self.assertEqual(manifest["candidate_count"], 2)
            self.assertTrue(manifest["candidate_count_matches_expected"])
            audit = pd.read_csv(output_dir / "selected_run_candidate_audit.csv")
            self.assertEqual(audit.loc[1, "scientific_interpretation_guard"], "unknown_is_not_low_risk")
            providers = pd.read_csv(output_dir / "selected_run_provider_audit.csv")
            self.assertEqual(providers.loc[0, "usable_evidence"], False)
            report = (output_dir / "selected_run_audit_report.md").read_text(encoding="utf-8")
            self.assertIn("Un no-hit de DIAMOND no demuestra seguridad", report)

    def test_missing_candidate_table_raises_clear_error(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            run_dir = root / "results" / "empty"
            run_dir.mkdir(parents=True)
            with self.assertRaises(FileNotFoundError):
                MODULE.run_audit(
                    repo_root=root,
                    run_dir=run_dir,
                    output_dir=root / "out",
                    config_path=None,
                    expected_candidates=None,
                )


if __name__ == "__main__":
    unittest.main()
