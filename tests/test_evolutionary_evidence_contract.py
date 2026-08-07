from __future__ import annotations

import unittest

from src.nodos_funcionales.evolutionary_evidence_contract import (
    EvolutionaryEvidenceRecord,
    evidence_validations_to_frame,
    summarize_candidate_evidence,
    validate_evidence_record,
    validate_evidence_records,
)


def valid_record(**overrides):
    data = {
        "candidate_id": "P0A123",
        "gene": "geneA",
        "variable": "mutation_tolerance_score",
        "value": 0.4,
        "source_type": "real_external_online",
        "source_database": "example_db",
        "source_record": "record-1",
        "source_version": "2026-08",
        "retrieved_at": "2026-08-06T20:00:00+00:00",
        "mapping_method": "accession",
        "mapping_status": "exact_accession",
        "evidence_status": "observed",
        "is_explicit": True,
        "evidence_confidence": "moderate",
        "independence_group": "strain_variation_dataset_v1",
        "method_scope": "all eligible genomes",
        "taxon_id": "210",
    }
    data.update(overrides)
    return EvolutionaryEvidenceRecord.from_mapping(data)


class EvolutionaryEvidenceContractTests(unittest.TestCase):
    def test_valid_direct_record_is_explicit(self) -> None:
        validation = validate_evidence_record(valid_record())
        self.assertTrue(validation.valid)
        self.assertTrue(validation.eligible_as_explicit)
        self.assertTrue(validation.record.is_explicit)

    def test_missing_source_zero_is_not_explicit(self) -> None:
        validation = validate_evidence_record(
            valid_record(value=0.0, source_type="missing")
        )
        self.assertTrue(validation.valid)
        self.assertFalse(validation.eligible_as_explicit)
        self.assertFalse(validation.record.is_explicit)
        self.assertIn(
            "explicit_flag_rejected_by_source_type",
            validation.warnings,
        )

    def test_proxy_and_derived_sources_are_not_explicit(self) -> None:
        for source_type in ["proxy", "derived", "synthetic_fixture"]:
            with self.subTest(source_type=source_type):
                validation = validate_evidence_record(
                    valid_record(source_type=source_type)
                )
                self.assertFalse(validation.eligible_as_explicit)

    def test_unresolved_mapping_is_not_explicit(self) -> None:
        validation = validate_evidence_record(
            valid_record(
                mapping_status="unmapped",
                evidence_status="mapping_failed",
            )
        )
        self.assertTrue(validation.valid)
        self.assertFalse(validation.eligible_as_explicit)

    def test_not_detected_requires_method_scope(self) -> None:
        invalid = validate_evidence_record(
            valid_record(
                value=0.0,
                evidence_status="not_detected_with_method",
                method_scope="",
            )
        )
        self.assertFalse(invalid.valid)
        self.assertIn(
            "not_detected_requires_method_scope",
            invalid.errors,
        )

        valid = validate_evidence_record(
            valid_record(
                value=0.0,
                evidence_status="not_detected_with_method",
                method_scope="searched 250 complete genomes",
            )
        )
        self.assertTrue(valid.valid)
        self.assertTrue(valid.eligible_as_explicit)

    def test_supporting_family_mapping_is_not_direct_by_default(self) -> None:
        record = valid_record(mapping_status="family_match")
        conservative = validate_evidence_record(record)
        permissive = validate_evidence_record(
            record,
            allow_supporting_mapping_as_explicit=True,
        )
        self.assertFalse(conservative.eligible_as_explicit)
        self.assertTrue(permissive.eligible_as_explicit)

    def test_summary_requires_variables_and_independent_groups(self) -> None:
        records = [
            valid_record(
                variable="mutation_tolerance_score",
                source_record="r1",
                independence_group="same_dataset",
            ),
            valid_record(
                variable="evolutionary_constraint_score",
                source_record="r2",
                independence_group="same_dataset",
            ),
            valid_record(
                variable="resistance_emergence_risk",
                source_record="r3",
                independence_group="same_dataset",
            ),
        ]
        summary = summarize_candidate_evidence(
            validate_evidence_records(records),
            minimum_explicit_variables=3,
            minimum_independent_groups=2,
        )
        self.assertEqual(int(summary.loc[0, "explicit_variable_count"]), 3)
        self.assertEqual(
            int(summary.loc[0, "independent_evidence_group_count"]),
            1,
        )
        self.assertFalse(bool(summary.loc[0, "supported_by_contract"]))

        records.append(
            valid_record(
                variable="fitness_cost_of_escape",
                source_record="r4",
                independence_group="independent_literature_dataset",
            )
        )
        summary = summarize_candidate_evidence(
            validate_evidence_records(records),
            minimum_explicit_variables=3,
            minimum_independent_groups=2,
        )
        self.assertTrue(bool(summary.loc[0, "supported_by_contract"]))

    def test_validation_frame_is_auditable(self) -> None:
        frame = evidence_validations_to_frame(
            validate_evidence_records([valid_record()])
        )
        for column in [
            "candidate_id",
            "variable",
            "source_database",
            "source_record",
            "mapping_status",
            "contract_valid",
            "contract_explicit_eligible",
            "contract_errors",
            "contract_warnings",
        ]:
            with self.subTest(column=column):
                self.assertIn(column, frame.columns)


if __name__ == "__main__":
    unittest.main()
