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


CATALOG_SHA = "a" * 64


def amrfinder_frame(**overrides: object) -> pd.DataFrame:
    row: dict[str, object] = {
        "protein_id": "PTEST1",
        "gene": "gyrA",
        "taxon_id": "1280",
        "meta_priority_score": 0.80,
        "resistance_emergence_risk": 1.0,
        "evolutionary_escape_risk_database": "ncbi_amrfinderplus_reference_gene_catalog:2026-01-15.1",
        "evolutionary_escape_risk_evidence_source": "NCBI AMRFinderPlus Reference Gene Catalog point mutations",
        "evolutionary_escape_risk_input_source_type": "literature_curated",
        "evolutionary_escape_risk_input_confidence": "high",
        "evolutionary_escape_risk_notes": "positive-only target-level evidence",
        "evolutionary_escape_risk_source_type": "external",
        "evolutionary_escape_risk_source_name": "ncbi_amrfinderplus_point_mutations",
        "evolutionary_escape_risk_is_user_supplied": False,
        "evolutionary_escape_risk_is_external": True,
        "evolutionary_escape_risk_is_cached": False,
        "evolutionary_escape_risk_is_proxy": False,
        "evolutionary_escape_risk_confidence": 0.95,
        "evolutionary_escape_risk_retrieval_status": "api_real",
        "evolutionary_escape_risk_generated_by": "external",
        "amrfinder_source_record": "AMRFinderPlus:2026-01-15.1;gene=gyrA;organism=Staphylococcus_aureus;mutations=gyrA_S84L",
        "amrfinder_source_version": "2026-01-15.1",
        "amrfinder_retrieved_at": "2026-08-07T18:00:00+00:00",
        "amrfinder_catalog_sha256": CATALOG_SHA,
        "amrfinder_mapping_method": "exact_gene_family_and_whitelisted_organism",
        "amrfinder_mapping_status": "exact_gene_and_taxon",
        "amrfinder_evidence_status": "observed",
        "amrfinder_evidence_confidence": "high",
        "amrfinder_independence_group": "ncbi_amrfinderplus_curated_point_mutations",
        "amrfinder_method_scope": "positive curated AMR POINT mutation for exact gene and organism",
        "amrfinder_taxon_id": "1280",
        "amrfinder_organism_group": "Staphylococcus_aureus",
        "amrfinder_pubmed_references": "12345678",
        "amrfinder_mutation_symbols": "gyrA_S84L",
        "amrfinder_drug_classes": "QUINOLONE",
        "amrfinder_drug_subclasses": "FLUOROQUINOLONE",
        "amrfinder_mutation_count": 1,
        "amrfinder_provider_retrieval_status": "api_real",
        "amrfinder_provider_source_used": "api_real",
        "amrfinder_provider_url": "https://example.test/ReferenceGeneCatalog.txt",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def add_bvbrc_constraint_inputs(frame: pd.DataFrame) -> None:
    fields: dict[str, object] = {
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
        "strain_conservation_retrieval_status": "api_real",
        "strain_conservation_generated_by": "external",
        "conservation_source_record": "bvbrc::1280::query123;candidate=PTEST1;gene=gyrA",
        "conservation_source_version": "bvbrc_unversioned_snapshot@2026-08-07T18:00:00+00:00",
        "conservation_retrieved_at": "2026-08-07T18:00:00+00:00",
        "conservation_mapping_method": "bvbrc_gene_filter_with_taxon_scope",
        "conservation_mapping_status": "exact_gene_and_taxon",
        "conservation_evidence_status": "observed",
        "conservation_evidence_confidence": "moderate",
        "conservation_independence_group": "bvbrc_strain_conservation_taxon_1280",
        "conservation_method_scope": "query_complete=true; genomes_retrieved=100",
        "conservation_taxon_id": "1280",
        "conservation_provider_retrieval_status": "api_real",
        "conservation_provider_query_cache_key": "bvbrc::1280::query123",
        "conservation_provider_source_used": "api_real",
    }
    for key, value in fields.items():
        frame[key] = value


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
    frame[f"{variable}_source_database"] = "independent_stage4d_test"
    frame[f"{variable}_source_record"] = f"record:{variable}"
    frame[f"{variable}_source_version"] = "v1"
    frame[f"{variable}_retrieved_at"] = "2026-08-07T18:00:00+00:00"
    frame[f"{variable}_mapping_method"] = "accession"
    frame[f"{variable}_mapping_status"] = "exact_accession"
    frame[f"{variable}_evidence_status"] = "observed"
    frame[f"{variable}_evidence_confidence"] = "high"
    frame[f"{variable}_independence_group"] = group
    frame[f"{variable}_taxon_id"] = "1280"
    frame[f"{variable}_notes"] = "independent Stage 4D regression evidence"


class EvolutionaryAmrFinderEvidenceTests(unittest.TestCase):
    def test_amrfinder_materializes_resistance_variable_with_strict_provenance(self) -> None:
        result = materialize_provider_evolutionary_evidence(amrfinder_frame())

        self.assertTrue(bool(result.loc[0, "amrfinder_evolutionary_evidence_eligible"]))
        self.assertEqual(float(result.loc[0, "amrfinder_resistance_emergence_risk"]), 1.0)
        self.assertTrue(bool(result.loc[0, "resistance_emergence_risk_is_explicit"]))
        self.assertEqual(
            result.loc[0, "resistance_emergence_risk_source_type"],
            "literature_curated",
        )
        self.assertEqual(
            result.loc[0, "resistance_emergence_risk_mapping_status"],
            "exact_gene_and_taxon",
        )
        self.assertEqual(
            result.loc[0, "resistance_emergence_risk_independence_group"],
            "ncbi_amrfinderplus_curated_point_mutations",
        )
        self.assertEqual(
            result.loc[0, "resistance_emergence_risk_source_version"],
            "2026-01-15.1",
        )
        self.assertIn(
            "gyrA_S84L",
            str(result.loc[0, "resistance_emergence_risk_notes"]),
        )

    def test_amrfinder_alone_is_one_variable_one_group_and_not_supported(self) -> None:
        result = compute_evolutionary_escape_risk_features(amrfinder_frame(), {})

        self.assertEqual(int(result.loc[0, "evolutionary_escape_risk_explicit_variable_count"]), 1)
        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_independent_evidence_group_count"]),
            1,
        )
        self.assertIn(
            "resistance_emergence_risk",
            str(result.loc[0, "evolutionary_escape_risk_explicit_variables"]),
        )
        self.assertFalse(bool(result.loc[0, "evolutionary_evidence_contract_supported"]))
        self.assertTrue(math.isnan(float(result.loc[0, "evolutionary_escape_supported_score"])))
        self.assertEqual(
            result.loc[0, "evolutionary_escape_contract_failure_reason"],
            "insufficient_explicit_variables",
        )

    def test_amrfinder_plus_bvbrc_are_two_independent_groups_but_still_below_variable_gate(self) -> None:
        frame = amrfinder_frame()
        add_bvbrc_constraint_inputs(frame)

        result = compute_evolutionary_escape_risk_features(frame, {})

        self.assertEqual(int(result.loc[0, "evolutionary_escape_risk_explicit_variable_count"]), 2)
        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_independent_evidence_group_count"]),
            2,
        )
        self.assertFalse(bool(result.loc[0, "evolutionary_evidence_contract_supported"]))
        self.assertEqual(
            result.loc[0, "evolutionary_escape_contract_failure_reason"],
            "insufficient_explicit_variables",
        )
        groups = str(result.loc[0, "evolutionary_escape_risk_independence_groups"])
        self.assertIn("bvbrc_strain_conservation_taxon_1280", groups)
        self.assertIn("ncbi_amrfinderplus_curated_point_mutations", groups)

    def test_third_independent_explicit_variable_enables_supported_path(self) -> None:
        frame = amrfinder_frame()
        add_bvbrc_constraint_inputs(frame)
        add_explicit_record(
            frame,
            "fitness_cost_of_escape",
            0.70,
            group="independent_fitness_experiment",
        )

        result = compute_evolutionary_escape_risk_features(frame, {})

        self.assertEqual(int(result.loc[0, "evolutionary_escape_risk_explicit_variable_count"]), 3)
        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_independent_evidence_group_count"]),
            3,
        )
        self.assertTrue(bool(result.loc[0, "evolutionary_evidence_contract_supported"]))
        self.assertTrue(bool(result.loc[0, "resistance_emergence_risk_contract_explicit"]))
        self.assertFalse(math.isnan(float(result.loc[0, "evolutionary_escape_supported_score"])))
        self.assertGreater(
            float(result.loc[0, "evolutionary_escape_supported_penalty_applied"]),
            0.0,
        )

    def test_zero_or_missing_amrfinder_signal_is_not_negative_explicit_evidence(self) -> None:
        zero = compute_evolutionary_escape_risk_features(
            amrfinder_frame(resistance_emergence_risk=0.0),
            {},
        )
        self.assertFalse(bool(zero.loc[0, "amrfinder_evolutionary_evidence_eligible"]))
        self.assertEqual(
            int(zero.loc[0, "evolutionary_escape_risk_explicit_variable_count"]),
            0,
        )

        missing = compute_evolutionary_escape_risk_features(
            amrfinder_frame(resistance_emergence_risk=float("nan")),
            {},
        )
        self.assertFalse(bool(missing.loc[0, "amrfinder_evolutionary_evidence_eligible"]))
        self.assertEqual(
            int(missing.loc[0, "evolutionary_escape_risk_explicit_variable_count"]),
            0,
        )

    def test_cache_delivery_preserves_original_amrfinder_independence_group(self) -> None:
        frame = amrfinder_frame(
            evolutionary_escape_risk_source_type="cache",
            evolutionary_escape_risk_is_external=False,
            evolutionary_escape_risk_is_cached=True,
            evolutionary_escape_risk_retrieval_status="resolved_from_cache",
            evolutionary_escape_risk_generated_by="cache",
        )
        result = compute_evolutionary_escape_risk_features(frame, {})

        self.assertTrue(bool(result.loc[0, "amrfinder_evolutionary_evidence_eligible"]))
        self.assertEqual(
            result.loc[0, "resistance_emergence_risk_independence_group"],
            "ncbi_amrfinderplus_curated_point_mutations",
        )
        self.assertEqual(
            int(result.loc[0, "evolutionary_escape_risk_independent_evidence_group_count"]),
            1,
        )

    def test_taxon_mismatch_fails_closed(self) -> None:
        result = materialize_provider_evolutionary_evidence(
            amrfinder_frame(amrfinder_taxon_id="562")
        )
        self.assertFalse(bool(result.loc[0, "amrfinder_evolutionary_evidence_eligible"]))
        self.assertEqual(
            result.loc[0, "amrfinder_evolutionary_evidence_reason"],
            "amrfinder_provider_taxon_mismatch",
        )

    def test_existing_canonical_resistance_evidence_is_preserved(self) -> None:
        frame = amrfinder_frame()
        add_explicit_record(
            frame,
            "resistance_emergence_risk",
            0.65,
            group="existing_resistance_study",
        )
        result = materialize_provider_evolutionary_evidence(frame)

        self.assertAlmostEqual(float(result.loc[0, "resistance_emergence_risk"]), 0.65)
        self.assertEqual(
            result.loc[0, "resistance_emergence_risk_independence_group"],
            "existing_resistance_study",
        )
        self.assertEqual(
            result.loc[0, "amrfinder_evolutionary_evidence_reason"],
            "no_positive_amrfinder_point_mutation_evidence",
        )


if __name__ == "__main__":
    unittest.main()
