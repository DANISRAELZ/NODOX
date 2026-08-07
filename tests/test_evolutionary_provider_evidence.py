from __future__ import annotations

import math
import unittest

import pandas as pd

from src.nodos_funcionales.evolutionary_escape_risk import (
    compute_evolutionary_escape_risk_features,
)
from src.nodos_funcionales.evolutionary_provider_evidence import (
    materialize_provider_evolutionary_evidence,
)


def bvbrc_frame(**overrides: object) -> pd.DataFrame:
    row: dict[str, object] = {
        "protein_id": "PTEST1",
        "gene": "gyrB",
        "taxon_id": "287",
        "meta_priority_score": 0.80,
        "core_genome_presence": 0.80,
        "strain_coverage_score": 0.80,
        "allelic_conservation": 0.60,
        "variant_burden": 0.40,
        "core_genome_presence_is_placeholder": False,
        "strain_coverage_score_is_placeholder": False,
        "allelic_conservation_is_placeholder": False,
        "variant_burden_is_placeholder": False,
        "conservation_database": "BV-BRC",
        "strain_conservation_source_type": "external",
        "strain_conservation_source_name": "bvbrc_real",
        "strain_conservation_is_external": True,
        "strain_conservation_is_cached": False,
        "strain_conservation_is_proxy": False,
        "strain_conservation_confidence": 0.82,
        "strain_conservation_retrieval_status": "api_real",
        "strain_conservation_generated_by": "external",
        "conservation_source_record": "bvbrc::287::query123;candidate=PTEST1;gene=gyrB",
        "conservation_source_version": "bvbrc_unversioned_snapshot@2026-08-07T12:00:00+00:00",
        "conservation_retrieved_at": "2026-08-07T12:00:00+00:00",
        "conservation_mapping_method": "bvbrc_gene_filter_with_taxon_scope",
        "conservation_mapping_status": "exact_gene_and_taxon",
        "conservation_evidence_status": "observed",
        "conservation_evidence_confidence": "moderate",
        "conservation_independence_group": "bvbrc_strain_conservation_taxon_287",
        "conservation_method_scope": "query_complete=true; genomes_retrieved=100",
        "conservation_taxon_id": "287",
        "conservation_provider_retrieval_status": "api_real",
        "conservation_provider_query_cache_key": "bvbrc::287::query123",
        "conservation_provider_source_used": "api_real",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def add_explicit_record(
    frame: pd.DataFrame,
    variable: str,
    value: float,
    *,
    group: str,
) -> None:
    frame[variable] = value
    frame[f"{variable}_is_explicit"] = True
    frame[f"{variable}_source_type"] = "experimental"
    frame[f"{variable}_source_database"] = "independent_stage4c_test"
    frame[f"{variable}_source_record"] = f"record:{variable}"
    frame[f"{variable}_source_version"] = "v1"
    frame[f"{variable}_retrieved_at"] = "2026-08-07T12:00:00+00:00"
    frame[f"{variable}_mapping_method"] = "accession"
    frame[f"{variable}_mapping_status"] = "exact_accession"
    frame[f"{variable}_evidence_status"] = "observed"
    frame[f"{variable}_evidence_confidence"] = "high"
    frame[f"{variable}_independence_group"] = group
    frame[f"{variable}_taxon_id"] = "287"
    frame[f"{variable}_notes"] = "independent Stage 4C regression evidence"


class EvolutionaryProviderEvidenceTests(unittest.TestCase):
    def test_bvbrc_materializes_one_constraint_variable(self) -> None:
        result = materialize_provider_evolutionary_evidence(bvbrc_frame())

        self.assertTrue(bool(result.loc[0, "bvbrc_evolutionary_evidence_eligible"]))
        self.assertAlmostEqual(
            float(result.loc[0, "bvbrc_evolutionary_constraint_score"]),
            0.70,
            places=12,
        )
        self.assertAlmostEqual(
            float(result.loc[0, "evolutionary_constraint_score"]),
            0.70,
            places=12,
        )
        self.assertTrue(bool(result.loc[0, "evolutionary_constraint_score_is_explicit"]))
        self.assertEqual(
            result.loc[0, "evolutionary_constraint_score_mapping_status"],
            "exact_gene_and_taxon",
        )
        self.assertEqual(
            result.loc[0, "evolutionary_constraint_score_independence_group"],
            "bvbrc_strain_conservation_taxon_287",
        )
        self.assertEqual(
            result.loc[0, "evolutionary_constraint_score_retrieved_at"],
            "2026-08-07T12:00:00+00:00",
        )
        self.assertEqual(
            result.loc[0, "evolutionary_constraint_score_source_record"],
            "bvbrc::287::query123;candidate=PTEST1;gene=gyrB",
        )
        self.assertIn(
            "unversioned",
            str(result.loc[0, "evolutionary_constraint_score_source_version"]),
        )

    def test_bvbrc_alone_is_explicit_but_not_contract_supported(self) -> None:
        result = compute_evolutionary_escape_risk_features(bvbrc_frame(), {})

        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_explicit_variable_count"]),
            1,
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
        self.assertIn(
            "evolutionary_constraint_score",
            str(result.loc[0, "evolutionary_escape_risk_explicit_variables"]),
        )
        self.assertFalse(
            bool(result.loc[0, "evolutionary_evidence_contract_supported"])
        )
        self.assertTrue(
            math.isnan(float(result.loc[0, "evolutionary_escape_supported_score"]))
        )
        self.assertEqual(
            result.loc[0, "evolutionary_escape_contract_failure_reason"],
            "insufficient_explicit_variables",
        )

    def test_correlated_bvbrc_metrics_do_not_create_four_independent_records(self) -> None:
        result = compute_evolutionary_escape_risk_features(bvbrc_frame(), {})

        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_explicit_variable_count"]),
            1,
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
        explicit_text = str(result.loc[0, "evolutionary_escape_risk_explicit_variables"])
        self.assertNotIn("strain_coverage_score", explicit_text)
        self.assertNotIn("variant_burden", explicit_text)

    def test_placeholder_or_missing_allelic_signal_fails_closed(self) -> None:
        placeholder = materialize_provider_evolutionary_evidence(
            bvbrc_frame(allelic_conservation_is_placeholder=True)
        )
        self.assertFalse(bool(placeholder.loc[0, "bvbrc_evolutionary_evidence_eligible"]))
        self.assertEqual(
            placeholder.loc[0, "bvbrc_evolutionary_evidence_reason"],
            "allelic_conservation_is_placeholder",
        )

        missing = materialize_provider_evolutionary_evidence(
            bvbrc_frame(allelic_conservation=float("nan"))
        )
        self.assertFalse(bool(missing.loc[0, "bvbrc_evolutionary_evidence_eligible"]))
        self.assertEqual(
            missing.loc[0, "bvbrc_evolutionary_evidence_reason"],
            "missing_or_invalid_allelic_conservation",
        )

    def test_user_or_demo_layer_is_not_promoted_to_bvbrc_explicit_evidence(self) -> None:
        user = materialize_provider_evolutionary_evidence(
            bvbrc_frame(
                strain_conservation_source_type="user",
                strain_conservation_is_external=False,
            )
        )
        self.assertFalse(bool(user.loc[0, "bvbrc_evolutionary_evidence_eligible"]))
        self.assertEqual(
            user.loc[0, "bvbrc_evolutionary_evidence_reason"],
            "strain_conservation_not_external_or_provider_cache",
        )

        demo = materialize_provider_evolutionary_evidence(
            bvbrc_frame(
                strain_conservation_generated_by="packaged_demo",
                strain_conservation_source_type="cache",
                strain_conservation_is_external=False,
                strain_conservation_is_cached=True,
                conservation_provider_source_used="cache",
            )
        )
        self.assertFalse(bool(demo.loc[0, "bvbrc_evolutionary_evidence_eligible"]))
        self.assertEqual(
            demo.loc[0, "bvbrc_evolutionary_evidence_reason"],
            "strain_conservation_layer_is_demo_or_mixed_demo",
        )

    def test_old_cache_without_original_provider_provenance_fails_closed(self) -> None:
        frame = bvbrc_frame(
            strain_conservation_source_type="cache",
            strain_conservation_is_external=False,
            strain_conservation_is_cached=True,
            conservation_provider_source_used="cache",
        )
        frame = frame.drop(
            columns=[
                "conservation_source_record",
                "conservation_source_version",
                "conservation_retrieved_at",
            ]
        )

        result = materialize_provider_evolutionary_evidence(frame)

        self.assertFalse(bool(result.loc[0, "bvbrc_evolutionary_evidence_eligible"]))
        self.assertIn(
            "missing_original_bvbrc_provenance",
            str(result.loc[0, "bvbrc_evolutionary_evidence_reason"]),
        )

    def test_provider_cache_preserves_original_retrieval_provenance(self) -> None:
        frame = bvbrc_frame(
            strain_conservation_source_type="cache",
            strain_conservation_is_external=False,
            strain_conservation_is_cached=True,
            strain_conservation_retrieval_status="resolved_from_cache",
            strain_conservation_generated_by="cache",
            conservation_provider_source_used="cache",
        )

        result = materialize_provider_evolutionary_evidence(frame)

        self.assertTrue(bool(result.loc[0, "bvbrc_evolutionary_evidence_eligible"]))
        self.assertEqual(
            result.loc[0, "evolutionary_constraint_score_retrieved_at"],
            "2026-08-07T12:00:00+00:00",
        )
        self.assertEqual(
            result.loc[0, "evolutionary_constraint_score_source_type"],
            "computed_from_real_data",
        )

    def test_existing_canonical_evidence_is_preserved(self) -> None:
        frame = bvbrc_frame(evolutionary_constraint_score=0.22)
        add_explicit_record(
            frame,
            "evolutionary_constraint_score",
            0.22,
            group="existing_constraint_study",
        )
        result = materialize_provider_evolutionary_evidence(frame)

        self.assertAlmostEqual(
            float(result.loc[0, "evolutionary_constraint_score"]),
            0.22,
            places=12,
        )
        self.assertEqual(
            result.loc[0, "evolutionary_constraint_score_independence_group"],
            "existing_constraint_study",
        )
        self.assertEqual(
            result.loc[0, "bvbrc_evolutionary_evidence_reason"],
            "eligible_but_existing_canonical_evidence_preserved",
        )

    def test_bvbrc_plus_independent_group_can_satisfy_full_contract(self) -> None:
        frame = bvbrc_frame()
        add_explicit_record(
            frame,
            "mutation_tolerance_score",
            0.80,
            group="independent_experimental_study",
        )
        add_explicit_record(
            frame,
            "fitness_cost_of_escape",
            0.70,
            group="independent_experimental_study",
        )

        result = compute_evolutionary_escape_risk_features(frame, {})

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
        self.assertTrue(
            bool(result.loc[0, "evolutionary_constraint_score_contract_explicit"])
        )
        self.assertAlmostEqual(
            float(result.loc[0, "evolutionary_constraint_score"]),
            0.70,
            places=12,
        )
        self.assertFalse(
            math.isnan(float(result.loc[0, "evolutionary_escape_supported_score"]))
        )
        self.assertGreater(
            float(result.loc[0, "evolutionary_escape_supported_penalty_applied"]),
            0.0,
        )
        self.assertEqual(
            result.loc[0, "evolutionary_escape_risk_status"],
            "sufficient_evidence",
        )


if __name__ == "__main__":
    unittest.main()
