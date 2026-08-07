from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.layer_registry import get_layer_definition
from src.nodos_funcionales.layer_resolver import _resolve_single_layer
from tests.helpers import make_temp_project


def provider_row(
    *,
    protein_id: str,
    gene: str,
    taxon_id: str,
    organism_group: str,
    source_used: str = "api_real",
) -> dict[str, object]:
    return {
        "protein_id": protein_id,
        "gene": gene,
        "resistance_emergence_risk": 1.0,
        "evidence_source": "NCBI AMRFinderPlus Reference Gene Catalog point mutations",
        "source_type": "literature_curated",
        "confidence": "high",
        "notes": "positive-only target-level evidence",
        "database": "ncbi_amrfinderplus_reference_gene_catalog:2026-05-15.1",
        "amrfinder_source_record": f"AMRFinderPlus:2026-05-15.1;gene={gene};organism={organism_group};mutations=test_mutation",
        "amrfinder_source_version": "2026-05-15.1",
        "amrfinder_retrieved_at": "2026-08-07T18:30:00+00:00",
        "amrfinder_catalog_sha256": "c" * 64,
        "amrfinder_mapping_method": "exact_gene_family_and_whitelisted_organism",
        "amrfinder_mapping_status": "exact_gene_and_taxon",
        "amrfinder_evidence_status": "observed",
        "amrfinder_evidence_confidence": "high",
        "amrfinder_independence_group": "ncbi_amrfinderplus_curated_point_mutations",
        "amrfinder_method_scope": "exact gene and organism positive AMR POINT evidence",
        "amrfinder_taxon_id": taxon_id,
        "amrfinder_organism_group": organism_group,
        "amrfinder_pubmed_references": "12345678",
        "amrfinder_mutation_symbols": "test_mutation",
        "amrfinder_drug_classes": "TEST_CLASS",
        "amrfinder_drug_subclasses": "TEST_SUBCLASS",
        "amrfinder_mutation_count": 1,
        "amrfinder_provider_retrieval_status": "api_real",
        "amrfinder_provider_source_used": "api_real",
        "amrfinder_provider_url": "https://example.test/ReferenceGeneCatalog.txt",
    }


def provider_result(row: dict[str, object], *, source_used: str) -> dict[str, object]:
    return {
        "evolutionary_escape_risk_data": pd.DataFrame([row]),
        "manifest": {
            "source_used": source_used,
            "retrieval_status": "cache_reused" if source_used == "cache" else "api_real",
            "query_complete": True,
        },
        "manifest_path": None,
    }


class AmrFinderPlusLayerResolutionTests(unittest.TestCase):
    def write_profile(self, project_dir, name: str, taxon_id: str) -> None:
        path = project_dir / "results" / "organism_profile.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "organism_input_name": name,
                    "organism_canonical_name": name,
                    "taxon_id": taxon_id,
                }
            ),
            encoding="utf-8",
        )

    def test_stale_provider_raw_from_previous_organism_is_replaced(self) -> None:
        project_dir = make_temp_project()
        definition = get_layer_definition("evolutionary_escape_risk")
        stale = provider_row(
            protein_id="PA0001",
            gene="gyrB",
            taxon_id="287",
            organism_group="Pseudomonas_aeruginosa",
        )
        raw_path = project_dir / "data_raw" / definition.filename
        pd.DataFrame([stale]).to_csv(raw_path, index=False)
        self.write_profile(project_dir, "Helicobacter pylori", "210")

        config = load_config(project_dir / "config" / "params.yaml")
        config["online_sources"]["source_mode_default"] = "online_optional"
        current = provider_row(
            protein_id="PA0001",
            gene="gyrB",
            taxon_id="210",
            organism_group="Helicobacter_pylori",
        )

        with patch(
            "src.nodos_funcionales.layer_resolver._amrfinder_exact_query_cached",
            return_value=False,
        ), patch(
            "src.nodos_funcionales.layer_resolver.fetch_amrfinderplus_point_mutation_evidence",
            return_value=provider_result(current, source_used="api_real"),
        ) as provider_mock:
            resolution = _resolve_single_layer(project_dir, config, definition)

        provider_mock.assert_called_once()
        refreshed = pd.read_csv(raw_path)
        self.assertEqual(str(refreshed.iloc[0]["amrfinder_taxon_id"]), "210")
        self.assertEqual(refreshed.iloc[0]["amrfinder_organism_group"], "Helicobacter_pylori")
        self.assertEqual(resolution.source_type, "external")
        self.assertTrue(resolution.is_external)
        self.assertFalse(resolution.is_cached)

    def test_offline_only_without_exact_query_cache_never_calls_provider(self) -> None:
        project_dir = make_temp_project()
        definition = get_layer_definition("evolutionary_escape_risk")
        stale = provider_row(
            protein_id="PA0001",
            gene="gyrB",
            taxon_id="287",
            organism_group="Pseudomonas_aeruginosa",
        )
        raw_path = project_dir / "data_raw" / definition.filename
        external_path = project_dir / "data_external" / definition.filename
        pd.DataFrame([stale]).to_csv(raw_path, index=False)
        pd.DataFrame([stale]).to_csv(external_path, index=False)
        self.write_profile(project_dir, "Helicobacter pylori", "210")

        config = load_config(project_dir / "config" / "params.yaml")
        config["online_sources"]["source_mode_default"] = "offline_only"

        with patch(
            "src.nodos_funcionales.layer_resolver._amrfinder_exact_query_cached",
            return_value=False,
        ), patch(
            "src.nodos_funcionales.layer_resolver.fetch_amrfinderplus_point_mutation_evidence"
        ) as provider_mock:
            resolution = _resolve_single_layer(project_dir, config, definition)

        provider_mock.assert_not_called()
        self.assertEqual(resolution.source_type, "missing")
        self.assertEqual(
            resolution.retrieval_status,
            "offline_only_without_matching_query_cache",
        )
        self.assertFalse(raw_path.exists())
        self.assertFalse(external_path.exists())

    def test_offline_only_with_exact_query_cache_uses_provider_cache_delivery(self) -> None:
        project_dir = make_temp_project()
        definition = get_layer_definition("evolutionary_escape_risk")
        self.write_profile(project_dir, "Helicobacter pylori", "210")
        config = load_config(project_dir / "config" / "params.yaml")
        config["online_sources"]["source_mode_default"] = "offline_only"
        cached = provider_row(
            protein_id="PA0001",
            gene="gyrB",
            taxon_id="210",
            organism_group="Helicobacter_pylori",
        )

        with patch(
            "src.nodos_funcionales.layer_resolver._amrfinder_exact_query_cached",
            return_value=True,
        ), patch(
            "src.nodos_funcionales.layer_resolver.fetch_amrfinderplus_point_mutation_evidence",
            return_value=provider_result(cached, source_used="cache"),
        ) as provider_mock:
            resolution = _resolve_single_layer(project_dir, config, definition)

        provider_mock.assert_called_once()
        self.assertEqual(resolution.source_type, "cache")
        self.assertTrue(resolution.is_cached)
        self.assertFalse(resolution.is_external)
        self.assertEqual(resolution.retrieval_status, "cache_reused")
        raw = pd.read_csv(project_dir / "data_raw" / definition.filename)
        self.assertEqual(str(raw.iloc[0]["amrfinder_taxon_id"]), "210")


if __name__ == "__main__":
    unittest.main()
