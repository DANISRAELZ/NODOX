from __future__ import annotations

import unittest

import pandas as pd

from src.nodos_funcionales.evolutionary_evidence_integration import (
    summarize_feature_frame_evidence,
)


def add_record(
    data: dict[str, list[object]],
    variable: str,
    *,
    value: float,
    independence_group: str,
    mapping_status: str = "exact_accession",
    prefix: str | None = None,
) -> None:
    prefix = prefix or variable
    data[prefix] = [value]
    data[f"{prefix}_is_explicit"] = [True]
    data[f"{prefix}_source_type"] = ["computed_from_real_data"]
    data[f"{prefix}_source_database"] = ["stage4b_test_db"]
    data[f"{prefix}_source_record"] = [f"record:{variable}"]
    data[f"{prefix}_source_version"] = ["2026-08-07"]
    data[f"{prefix}_retrieved_at"] = ["2026-08-07T12:00:00+00:00"]
    data[f"{prefix}_mapping_method"] = ["accession"]
    data[f"{prefix}_mapping_status"] = [mapping_status]
    data[f"{prefix}_evidence_status"] = ["observed"]
    data[f"{prefix}_evidence_confidence"] = ["high"]
    data[f"{prefix}_independence_group"] = [independence_group]


class EvolutionaryEvidenceIntegrationTests(unittest.TestCase):
    def test_three_valid_variables_across_two_groups_are_supported(self) -> None:
        data: dict[str, list[object]] = {
            "protein_id": ["P1"],
            "gene": ["g1"],
        }
        add_record(
            data,
            "mutation_tolerance_score",
            value=0.7,
            independence_group="variation",
        )
        add_record(
            data,
            "functional_redundancy_escape_score",
            value=0.4,
            independence_group="variation",
        )
        add_record(
            data,
            "fitness_cost_of_escape",
            value=0.8,
            independence_group="fitness",
        )

        summary, matrix = summarize_feature_frame_evidence(pd.DataFrame(data))

        self.assertEqual(int(summary.loc[0, "explicit_variable_count"]), 3)
        self.assertEqual(
            int(summary.loc[0, "independent_evidence_group_count"]),
            2,
        )
        self.assertTrue(bool(summary.loc[0, "supported_by_contract"]))
        self.assertTrue(bool(matrix.loc[0, "mutation_tolerance_score"]))
        self.assertTrue(bool(matrix.loc[0, "fitness_cost_of_escape"]))

    def test_requested_explicit_without_provenance_is_rejected(self) -> None:
        frame = pd.DataFrame(
            {
                "protein_id": ["P1"],
                "gene": ["g1"],
                "mutation_tolerance_score": [0.7],
                "mutation_tolerance_score_is_explicit": [True],
            }
        )

        summary, matrix = summarize_feature_frame_evidence(frame)

        self.assertEqual(int(summary.loc[0, "explicit_variable_count"]), 0)
        self.assertEqual(
            int(summary.loc[0, "contract_rejected_explicit_record_count"]),
            1,
        )
        self.assertIn(
            "missing_source_database",
            str(summary.loc[0, "contract_errors"]),
        )
        self.assertFalse(bool(matrix.loc[0, "mutation_tolerance_score"]))

    def test_mutational_tolerance_alias_maps_to_canonical_variable(self) -> None:
        data: dict[str, list[object]] = {
            "protein_id": ["P1"],
            "gene": ["g1"],
        }
        add_record(
            data,
            "mutation_tolerance_score",
            prefix="mutational_tolerance_score",
            value=0.6,
            independence_group="variation",
        )

        summary, matrix = summarize_feature_frame_evidence(
            pd.DataFrame(data),
            minimum_explicit_variables=1,
            minimum_independent_groups=1,
        )

        self.assertEqual(int(summary.loc[0, "explicit_variable_count"]), 1)
        self.assertTrue(bool(summary.loc[0, "supported_by_contract"]))
        self.assertTrue(bool(matrix.loc[0, "mutation_tolerance_score"]))

    def test_ortholog_mapping_is_supporting_only_by_default(self) -> None:
        data: dict[str, list[object]] = {
            "protein_id": ["P1"],
            "gene": ["g1"],
        }
        add_record(
            data,
            "mutation_tolerance_score",
            value=0.6,
            independence_group="orthology",
            mapping_status="ortholog_match",
        )
        frame = pd.DataFrame(data)

        strict_summary, strict_matrix = summarize_feature_frame_evidence(
            frame,
            minimum_explicit_variables=1,
            minimum_independent_groups=1,
        )
        permissive_summary, permissive_matrix = summarize_feature_frame_evidence(
            frame,
            minimum_explicit_variables=1,
            minimum_independent_groups=1,
            allow_supporting_mapping_as_explicit=True,
        )

        self.assertFalse(bool(strict_summary.loc[0, "supported_by_contract"]))
        self.assertFalse(bool(strict_matrix.loc[0, "mutation_tolerance_score"]))
        self.assertTrue(bool(permissive_summary.loc[0, "supported_by_contract"]))
        self.assertTrue(bool(permissive_matrix.loc[0, "mutation_tolerance_score"]))

    def test_missing_candidate_identifier_fails_closed(self) -> None:
        data: dict[str, list[object]] = {"gene": ["g1"]}
        add_record(
            data,
            "mutation_tolerance_score",
            value=0.6,
            independence_group="variation",
        )

        summary, _ = summarize_feature_frame_evidence(
            pd.DataFrame(data),
            minimum_explicit_variables=1,
            minimum_independent_groups=1,
        )

        self.assertFalse(bool(summary.loc[0, "supported_by_contract"]))
        self.assertIn(
            "missing_candidate_id",
            str(summary.loc[0, "contract_errors"]),
        )


if __name__ == "__main__":
    unittest.main()
