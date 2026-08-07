from __future__ import annotations

import math
import unittest
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.evolutionary_escape_risk import (
    compute_evolutionary_escape_risk_features,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def add_explicit_provenance(
    data: dict[str, list[object]],
    variable: str,
    *,
    independence_group: str,
    source_type: str = "computed_from_real_data",
    mapping_status: str = "exact_accession",
) -> None:
    data[f"{variable}_is_explicit"] = [True]
    data[f"{variable}_source_type"] = [source_type]
    data[f"{variable}_source_database"] = ["stage4b_test_db"]
    data[f"{variable}_source_record"] = [f"record:{variable}"]
    data[f"{variable}_source_version"] = ["2026-08-07"]
    data[f"{variable}_retrieved_at"] = ["2026-08-07T12:00:00+00:00"]
    data[f"{variable}_mapping_method"] = ["accession"]
    data[f"{variable}_mapping_status"] = [mapping_status]
    data[f"{variable}_evidence_status"] = ["observed"]
    data[f"{variable}_evidence_confidence"] = ["high"]
    data[f"{variable}_independence_group"] = [independence_group]


class EvolutionaryEvidenceModeTests(unittest.TestCase):
    def test_proxy_only_inputs_do_not_create_supported_penalty(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["p1"],
                "gene": ["g1"],
                "meta_priority_score": [0.8],
                "essentiality_support": [1.0],
                "conservation_score": [0.8],
            }
        )
        result = compute_evolutionary_escape_risk_features(df, {})
        self.assertEqual(
            result.loc[0, "evolutionary_escape_evidence_mode"],
            "proxy_hypothesis_only",
        )
        self.assertFalse(
            bool(result.loc[0, "evolutionary_evidence_contract_supported"])
        )
        self.assertTrue(
            math.isnan(float(result.loc[0, "evolutionary_escape_supported_score"]))
        )
        self.assertGreater(
            float(result.loc[0, "evolutionary_escape_proxy_penalty_applied"]),
            0.0,
        )
        self.assertEqual(
            float(result.loc[0, "evolutionary_escape_supported_penalty_applied"]),
            0.0,
        )
        self.assertEqual(
            float(result.loc[0, "evolutionary_supported_adjusted_meta_priority_score"]),
            0.8,
        )

    def test_numeric_value_marked_derived_is_not_explicit(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["p1"],
                "gene": ["g1"],
                "meta_priority_score": [0.8],
                "functional_redundancy_escape_score": [0.0],
                "functional_redundancy_escape_score_is_explicit": [False],
                "functional_redundancy_escape_score_source_type": ["missing"],
            }
        )
        result = compute_evolutionary_escape_risk_features(df, {})
        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_explicit_variable_count"]),
            0,
        )
        self.assertEqual(
            result.loc[0, "evolutionary_escape_supported_status"],
            "unknown_missing_evidence",
        )
        self.assertEqual(
            float(result.loc[0, "evolutionary_escape_supported_penalty_applied"]),
            0.0,
        )

    def test_three_flags_without_provenance_do_not_enable_supported_score(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["p1"],
                "gene": ["g1"],
                "meta_priority_score": [0.8],
                "mutation_tolerance_score": [0.9],
                "functional_redundancy_escape_score": [0.7],
                "fitness_cost_of_escape": [0.2],
                "mutation_tolerance_score_is_explicit": [True],
                "functional_redundancy_escape_score_is_explicit": [True],
                "fitness_cost_of_escape_is_explicit": [True],
            }
        )
        result = compute_evolutionary_escape_risk_features(df, {})
        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_explicit_variable_count"]),
            0,
        )
        self.assertFalse(
            bool(result.loc[0, "evolutionary_evidence_contract_supported"])
        )
        self.assertTrue(
            math.isnan(float(result.loc[0, "evolutionary_escape_supported_score"]))
        )
        self.assertGreater(
            int(
                result.loc[
                    0,
                    "evolutionary_evidence_contract_rejected_explicit_record_count",
                ]
            ),
            0,
        )
        self.assertEqual(
            result.loc[0, "evolutionary_escape_contract_failure_reason"],
            "explicit_records_rejected_by_contract",
        )

    def test_three_contract_variables_from_two_groups_enable_supported_score(self) -> None:
        data: dict[str, list[object]] = {
            "protein_id": ["p1"],
            "gene": ["g1"],
            "meta_priority_score": [0.8],
            "mutation_tolerance_score": [0.9],
            "functional_redundancy_escape_score": [0.7],
            "fitness_cost_of_escape": [0.2],
        }
        add_explicit_provenance(
            data,
            "mutation_tolerance_score",
            independence_group="strain_variation",
        )
        add_explicit_provenance(
            data,
            "functional_redundancy_escape_score",
            independence_group="strain_variation",
        )
        add_explicit_provenance(
            data,
            "fitness_cost_of_escape",
            independence_group="experimental_fitness",
        )
        result = compute_evolutionary_escape_risk_features(
            pd.DataFrame(data),
            {"evolutionary_escape_risk": {"minimum_explicit_variables": 3}},
        )
        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_explicit_variable_count"]),
            3,
        )
        self.assertEqual(
            int(
                result.loc[
                    0,
                    "evolutionary_escape_risk_independent_evidence_group_count",
                ]
            ),
            2,
        )
        self.assertTrue(
            bool(result.loc[0, "evolutionary_evidence_contract_supported"])
        )
        self.assertEqual(
            result.loc[0, "evolutionary_escape_evidence_mode"],
            "supported",
        )
        self.assertEqual(
            result.loc[0, "evolutionary_escape_supported_status"],
            "sufficient_explicit_evidence",
        )
        self.assertEqual(
            result.loc[0, "evolutionary_escape_contract_failure_reason"],
            "none",
        )
        self.assertFalse(
            math.isnan(float(result.loc[0, "evolutionary_escape_supported_score"]))
        )
        self.assertGreater(
            float(result.loc[0, "evolutionary_escape_supported_penalty_applied"]),
            0.0,
        )
        self.assertLess(
            float(result.loc[0, "evolutionary_supported_adjusted_meta_priority_score"]),
            0.8,
        )

    def test_three_contract_variables_from_one_group_are_not_supported(self) -> None:
        data: dict[str, list[object]] = {
            "protein_id": ["p1"],
            "gene": ["g1"],
            "meta_priority_score": [0.8],
            "mutation_tolerance_score": [0.9],
            "functional_redundancy_escape_score": [0.7],
            "fitness_cost_of_escape": [0.2],
        }
        for variable in [
            "mutation_tolerance_score",
            "functional_redundancy_escape_score",
            "fitness_cost_of_escape",
        ]:
            add_explicit_provenance(
                data,
                variable,
                independence_group="same_dataset",
            )
        result = compute_evolutionary_escape_risk_features(pd.DataFrame(data), {})
        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_explicit_variable_count"]),
            3,
        )
        self.assertEqual(
            int(
                result.loc[
                    0,
                    "evolutionary_escape_risk_independent_evidence_group_count",
                ]
            ),
            1,
        )
        self.assertFalse(
            bool(result.loc[0, "evolutionary_evidence_contract_supported"])
        )
        self.assertEqual(
            result.loc[0, "evolutionary_escape_risk_status"],
            "insufficient_evidence",
        )
        self.assertEqual(
            result.loc[0, "evolutionary_escape_contract_failure_reason"],
            "insufficient_independent_evidence",
        )
        self.assertTrue(
            math.isnan(float(result.loc[0, "evolutionary_escape_supported_score"]))
        )

    def test_unknown_source_type_is_rejected_as_explicit(self) -> None:
        data: dict[str, list[object]] = {
            "protein_id": ["p1"],
            "gene": ["g1"],
            "mutation_tolerance_score": [0.9],
        }
        add_explicit_provenance(
            data,
            "mutation_tolerance_score",
            independence_group="dataset_a",
            source_type="mystery_source",
        )
        result = compute_evolutionary_escape_risk_features(pd.DataFrame(data), {})
        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_explicit_variable_count"]),
            0,
        )
        self.assertIn(
            "unrecognized_source_type_not_explicit",
            str(result.loc[0, "evolutionary_evidence_contract_warnings"]),
        )

    def test_ambiguous_mapping_is_rejected_as_explicit(self) -> None:
        data: dict[str, list[object]] = {
            "protein_id": ["p1"],
            "gene": ["g1"],
            "mutation_tolerance_score": [0.9],
        }
        add_explicit_provenance(
            data,
            "mutation_tolerance_score",
            independence_group="dataset_a",
            mapping_status="ambiguous",
        )
        result = compute_evolutionary_escape_risk_features(pd.DataFrame(data), {})
        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_explicit_variable_count"]),
            0,
        )
        self.assertFalse(
            bool(result.loc[0, "evolutionary_evidence_contract_supported"])
        )

    def test_legacy_score_is_preserved_as_proxy_alias(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["p1"],
                "gene": ["g1"],
                "meta_priority_score": [0.8],
                "mutation_tolerance_score": [0.7],
                "functional_redundancy_escape_score": [0.6],
                "compensatory_pathway_score": [0.5],
                "fitness_cost_of_escape": [0.4],
                "evolutionary_constraint_score": [0.3],
                "resistance_emergence_risk": [0.6],
                "multi_node_dependency_score": [0.2],
            }
        )
        result = compute_evolutionary_escape_risk_features(df, {})
        self.assertAlmostEqual(
            float(result.loc[0, "evolutionary_escape_risk_score"]),
            float(result.loc[0, "evolutionary_escape_proxy_score"]),
            places=12,
        )
        self.assertAlmostEqual(
            float(result.loc[0, "evolutionary_escape_penalty_applied"]),
            float(result.loc[0, "evolutionary_escape_proxy_penalty_applied"]),
            places=12,
        )
        self.assertTrue(
            math.isnan(float(result.loc[0, "evolutionary_escape_supported_score"]))
        )

    def test_scoring_exports_evidence_mode_columns(self) -> None:
        scoring_text = (
            PROJECT_ROOT / "src" / "nodos_funcionales" / "scoring.py"
        ).read_text(encoding="utf-8")
        for column in [
            "evolutionary_escape_proxy_score",
            "evolutionary_escape_supported_score",
            "evolutionary_escape_evidence_mode",
            "evolutionary_escape_supported_penalty_applied",
            "evolutionary_supported_adjusted_meta_priority_score",
        ]:
            with self.subTest(column=column):
                self.assertIn(f'"{column}"', scoring_text)


if __name__ == "__main__":
    unittest.main()
