from __future__ import annotations

import importlib.util
import sys
import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "audit_integrated_validation.py"


def load_module():
    spec = importlib.util.spec_from_file_location("integrated_validation_audit", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AUDIT = load_module()


class IntegratedValidationAuditTests(unittest.TestCase):
    def test_source_classification_preserves_scientific_distinctions(self) -> None:
        cases = [
            ("tests/fixtures/synthetic.csv", "", "synthetic_fixture"),
            ("data_external/online_seed_snapshots/hp/snapshot_manifest.json", "", "versioned_snapshot"),
            ("results/demo_run/manifest.json", "", "demo"),
            ("results/live/manifest.json", "source_used: api_real", "real_external_online"),
            ("results/cache/manifest.json", "", "cache"),
            ("results/unresolved/manifest.json", "", "unresolved"),
        ]
        for raw_path, content, expected in cases:
            with self.subTest(path=raw_path):
                self.assertEqual(AUDIT.classify_source(Path(raw_path), content), expected)

    def test_repository_state_records_sha_branch_and_dirty_status(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.org"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "README.md").write_text("test\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)

            clean = AUDIT.collect_repository_state(root)
            self.assertEqual(clean.branch, "main")
            self.assertEqual(len(clean.head_sha), 40)
            self.assertFalse(clean.dirty)

            (root / "README.md").write_text("changed\n", encoding="utf-8")
            dirty = AUDIT.collect_repository_state(root)
            self.assertTrue(dirty.dirty)

    def test_run_inventory_and_provider_coverage_use_manifests(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            run = root / "results" / "20260806_hpylori"
            result_dir = run / "workspace" / "results"
            result_dir.mkdir(parents=True)
            manifest = {
                "organism_name": "Helicobacter pylori",
                "taxon_id": 210,
                "candidate_count": 25,
                "provider": "string",
                "provider_attempted": True,
                "provider_success": True,
                "mapping_success": True,
                "usable_evidence": False,
                "affects_score": False,
                "raw_edge_count": 1,
                "usable_edge_count": 0,
                "source_used": "api_real",
            }
            (result_dir / "online_only_run_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            (result_dir / "ranking_nodos.csv").write_text(
                "protein_id,gene,meta_priority_score\nP1,g1,0.5\n",
                encoding="utf-8",
            )
            (result_dir / "online_only_provider_audit.csv").write_text(
                "provider,provider_attempted,provider_success,mapping_success,usable_evidence,affects_score\n"
                "string,true,true,true,false,false\n",
                encoding="utf-8",
            )

            runs = AUDIT.discover_runs(root)
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["organism"], "Helicobacter pylori")
            self.assertEqual(runs[0]["candidate_count"], "25")
            self.assertTrue(runs[0]["has_ranking"])

            providers = {row["provider"]: row for row in AUDIT.build_provider_coverage(root)}
            self.assertGreaterEqual(providers["string"]["observation_count"], 1)
            self.assertIn(providers["string"]["usable_evidence"], {"false", "not_reported"})

    def test_run_audit_writes_expected_files(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.org"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "src" / "nodos_funcionales").mkdir(parents=True)
            (root / "src" / "nodos_funcionales" / "functional_node_theory.py").write_text(
                "functional_node_score = evolutionary_escape_risk_score\n",
                encoding="utf-8",
            )
            (root / "src" / "nodos_funcionales" / "evolutionary_escape_risk.py").write_text(
                "mutation_tolerance_score = 0\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)

            output = root / "audit_output"
            AUDIT.run_audit(root, output)
            expected = {
                "repository_state.json",
                "available_runs_inventory.csv",
                "provider_coverage_matrix.csv",
                "evidence_source_inventory.csv",
                "functional_node_postulates_matrix.csv",
                "evolutionary_escape_variables.csv",
                "manuscript_supported_claims.csv",
                "manuscript_unsupported_claims.csv",
                "integrated_validation_readiness_report.md",
            }
            self.assertEqual({path.name for path in output.iterdir()}, expected)


if __name__ == "__main__":
    unittest.main()
