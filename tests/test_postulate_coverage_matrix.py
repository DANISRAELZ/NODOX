from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "audit_integrated_validation.py"


def load_module():
    spec = importlib.util.spec_from_file_location("integrated_validation_audit_matrix", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AUDIT = load_module()


class PostulateCoverageMatrixTests(unittest.TestCase):
    def test_matrix_always_contains_six_postulates(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "src" / "nodos_funcionales").mkdir(parents=True)
            rows = AUDIT.build_postulate_coverage(root)
            self.assertEqual([row["postulate_id"] for row in rows], ["P1", "P2", "P3", "P4", "P5", "P6"])

    def test_detects_partial_and_implemented_coverage_conservatively(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "src" / "nodos_funcionales"
            source.mkdir(parents=True)
            (source / "functional_node_theory.py").write_text(
                "\n".join(
                    [
                        "functional_node_score = 0",
                        "network_centrality = 0",
                        "pathway_bottleneck_score = 0",
                        "functional_dependency_score = 0",
                        "evolutionary_escape_risk_score = 0",
                        "evolutionary_constraint_score = 0",
                        "mutation_tolerance_score = 0",
                        "functional_redundancy_escape_score = 0",
                        "compensatory_pathway_score = 0",
                        "fitness_cost_of_escape = 0",
                    ]
                ),
                encoding="utf-8",
            )
            (source / "evolutionary_escape_risk.py").write_text(
                "missing_input = insufficient_evidence = unresolved = None\n",
                encoding="utf-8",
            )
            rows = {row["postulate_id"]: row for row in AUDIT.build_postulate_coverage(root)}
            self.assertEqual(rows["P1"]["status"], "implemented_requires_evidence_audit")
            self.assertEqual(rows["P5"]["status"], "implemented_requires_evidence_audit")
            self.assertIn(rows["P6"]["status"], {"partially_operationalized", "implemented_requires_evidence_audit"})

    def test_csv_writer_preserves_utf8_and_headers(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "matrix.csv"
            AUDIT.write_csv(output, [{"postulate_id": "P1", "postulate": "Nodo funcional"}])
            text = output.read_text(encoding="utf-8")
            self.assertIn("postulate_id,postulate", text)
            self.assertIn("Nodo funcional", text)


if __name__ == "__main__":
    unittest.main()
