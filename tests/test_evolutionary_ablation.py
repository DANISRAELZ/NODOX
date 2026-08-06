from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_evolutionary_ablation.py"
SPEC = importlib.util.spec_from_file_location("run_evolutionary_ablation", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class EvolutionaryAblationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.theory = MODULE.DEFAULT_THEORY
        self.stage2 = {
            "ablation": {
                "reported_score_column": "functional_node_theory_score",
                "baseline_tolerance": 1e-9,
                "scenarios": {
                    "no_escape_penalty": {
                        "remove_positive_weights": [],
                        "remove_penalties": ["p_escape"],
                    },
                    "no_evolutionary_dimension": {
                        "remove_positive_weights": ["w_evolutionary_constraint"],
                        "remove_penalties": ["p_escape", "p_biofilm", "p_hgt"],
                    },
                },
                "sensitivity_multipliers": [0.8, 1.2],
                "sensitivity_positive_weights": ["w_evolutionary_constraint"],
                "sensitivity_penalties": ["p_escape", "p_biofilm", "p_hgt"],
                "supported_evidence": {
                    "minimum_explicit_variables": 3,
                    "unknown_statuses": [
                        "unknown_missing_evidence",
                        "unknown",
                        "missing",
                        "not_reported",
                        "unresolved",
                        "insufficient_evidence",
                        "derived_from_related_layers",
                    ],
                },
            }
        }

    @staticmethod
    def _base_frame() -> pd.DataFrame:
        return pd.DataFrame(
            {
                "protein_id": ["LOW_ESCAPE", "HIGH_ESCAPE"],
                "gene": ["low", "high"],
                "functional_node_score": [0.7, 0.9],
                "contextual_essentiality_score": [0.7, 0.9],
                "pleiotropy_score": [0.7, 0.9],
                "conservation_score": [0.7, 0.9],
                "evolutionary_space_constraint_score": [0.8, 0.2],
                "evidence_quality_score": [0.8, 0.8],
                "redundancy_penalty": [0.1, 0.2],
                "evolutionary_escape_risk_score": [0.05, 1.0],
                "biofilm_escape_penalty": [0.0, 0.6],
                "horizontal_transfer_penalty": [0.0, 0.6],
                "host_similarity_penalty": [0.0, 0.0],
            }
        )

    def test_high_escape_candidate_is_demoted_by_proxy_full_model(self) -> None:
        frame = self._base_frame()
        frame["evolutionary_escape_risk_status"] = "unknown_missing_evidence"
        frame["evolutionary_escape_risk_explicit_variable_count"] = 0
        frame["functional_node_theory_score"] = MODULE.compute_theory_score(
            frame,
            self.theory,
        )

        output, summary = MODULE.build_ablation(frame, self.theory, self.stage2)
        high = output.set_index("candidate_id").loc["HIGH_ESCAPE"]

        self.assertGreater(
            high["proxy_rank_shift_vs_without_evolutionary_information"],
            0,
        )
        self.assertEqual(high["evolutionary_rank_effect"], "demoted_by_evolution")
        self.assertEqual(summary["reported_baseline_mismatch_count"], 0)
        self.assertTrue(summary["all_candidates_proxy_only"])

    def test_unknown_evidence_does_not_apply_supported_dimension(self) -> None:
        frame = self._base_frame()
        frame["evolutionary_escape_risk_status"] = "unknown_missing_evidence"
        frame["evolutionary_escape_risk_explicit_variable_count"] = 0
        frame["functional_node_theory_score"] = MODULE.compute_theory_score(
            frame,
            self.theory,
        )

        output, _ = MODULE.build_ablation(frame, self.theory, self.stage2)

        pd.testing.assert_series_equal(
            output["ranking_with_supported_evolutionary_score"],
            output["ranking_without_evolutionary_information_score"],
            check_names=False,
        )
        self.assertTrue(output["evolutionary_escape_supported_score"].isna().all())
        self.assertFalse(output["supported_evolutionary_dimension_applied"].any())
        self.assertTrue(
            (output["evolutionary_evidence_mode"] == "proxy_hypothesis_only").all()
        )

    def test_sufficient_explicit_evidence_applies_supported_dimension(self) -> None:
        frame = self._base_frame().iloc[[0]].copy()
        frame["evolutionary_escape_risk_status"] = "sufficient_evidence"
        frame["evolutionary_escape_risk_explicit_variable_count"] = 3
        frame["functional_node_theory_score"] = MODULE.compute_theory_score(
            frame,
            self.theory,
        )

        output, summary = MODULE.build_ablation(frame, self.theory, self.stage2)

        self.assertTrue(bool(output.loc[0, "supported_evolutionary_dimension_applied"]))
        self.assertEqual(output.loc[0, "evolutionary_evidence_mode"], "supported_explicit")
        self.assertAlmostEqual(
            float(output.loc[0, "ranking_with_supported_evolutionary_score"]),
            float(output.loc[0, "ranking_with_proxy_evolutionary_score"]),
        )
        self.assertFalse(pd.isna(output.loc[0, "evolutionary_escape_supported_score"]))
        self.assertEqual(summary["supported_evolutionary_candidate_count"], 1)

    def test_missing_zero_redundancy_is_not_supported_evidence(self) -> None:
        frame = self._base_frame().iloc[[0]].copy()
        frame["functional_redundancy_escape_score"] = 0.0
        frame["functional_redundancy_escape_score_source_type"] = "missing"
        frame["functional_redundancy_escape_score_is_explicit"] = False
        frame["evolutionary_escape_risk_status"] = "unknown_missing_evidence"
        frame["functional_node_theory_score"] = MODULE.compute_theory_score(
            frame,
            self.theory,
        )

        output, _ = MODULE.build_ablation(frame, self.theory, self.stage2)

        self.assertEqual(
            int(output.loc[0, "evolutionary_escape_risk_explicit_variable_count"]),
            0,
        )
        self.assertFalse(bool(output.loc[0, "supported_evolutionary_dimension_applied"]))
        self.assertTrue(pd.isna(output.loc[0, "evolutionary_escape_supported_score"]))

    def test_gene_summary_collapses_duplicate_accessions(self) -> None:
        frame = self._base_frame()
        duplicate = frame.iloc[[0]].copy()
        duplicate["protein_id"] = "LOW_ESCAPE_2"
        frame = pd.concat([frame, duplicate], ignore_index=True)
        frame["evolutionary_escape_risk_status"] = "unknown_missing_evidence"
        frame["evolutionary_escape_risk_explicit_variable_count"] = 0
        frame["functional_node_theory_score"] = MODULE.compute_theory_score(
            frame,
            self.theory,
        )

        output, _ = MODULE.build_ablation(frame, self.theory, self.stage2)
        gene = MODULE.build_gene_summary(output).set_index("gene")

        self.assertEqual(int(gene.loc["low", "accession_count"]), 2)
        self.assertEqual(gene.loc["low", "evolutionary_evidence_mode"], "proxy_hypothesis_only")

    def test_missing_inputs_use_declared_zero_defaults(self) -> None:
        frame = pd.DataFrame({"protein_id": ["P1"], "functional_node_score": [1.0]})
        score = MODULE.compute_theory_score(frame, self.theory)
        self.assertGreaterEqual(float(score.iloc[0]), 0.0)
        self.assertLessEqual(float(score.iloc[0]), 1.0)

    def test_sensitivity_does_not_modify_input_configuration(self) -> None:
        original = self.theory["weights"]["w_evolutionary_constraint"]
        changed = MODULE.apply_sensitivity(
            self.theory,
            1.2,
            ["w_evolutionary_constraint"],
            ["p_escape"],
        )
        self.assertEqual(
            self.theory["weights"]["w_evolutionary_constraint"],
            original,
        )
        self.assertNotEqual(
            changed["weights"]["w_evolutionary_constraint"],
            original,
        )


if __name__ == "__main__":
    unittest.main()
