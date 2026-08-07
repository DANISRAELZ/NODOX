from __future__ import annotations

import json
import unittest

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import make_temp_project


class AmrFinderPlusProvenanceTransportTests(unittest.TestCase):
    def test_external_amrfinder_provenance_survives_validation_normalization_and_integration(self) -> None:
        project_dir = make_temp_project()
        external_dir = project_dir / "data_external"
        external_dir.mkdir(parents=True, exist_ok=True)

        row = {
            "protein_id": "PA0001",
            "gene": "gyrB",
            "resistance_emergence_risk": 1.0,
            "evidence_source": "NCBI AMRFinderPlus Reference Gene Catalog point mutations",
            "source_type": "literature_curated",
            "confidence": "high",
            "notes": "positive-only target-level evidence",
            "database": "ncbi_amrfinderplus_reference_gene_catalog:2026-01-15.1",
            "amrfinder_source_record": "AMRFinderPlus:2026-01-15.1;gene=gyrB;organism=Pseudomonas_aeruginosa;mutations=gyrB_E468D",
            "amrfinder_source_version": "2026-01-15.1",
            "amrfinder_retrieved_at": "2026-08-07T18:00:00+00:00",
            "amrfinder_catalog_sha256": "b" * 64,
            "amrfinder_mapping_method": "exact_gene_family_and_whitelisted_organism",
            "amrfinder_mapping_status": "exact_gene_and_taxon",
            "amrfinder_evidence_status": "observed",
            "amrfinder_evidence_confidence": "high",
            "amrfinder_independence_group": "ncbi_amrfinderplus_curated_point_mutations",
            "amrfinder_method_scope": "exact gene and organism positive AMR POINT evidence",
            "amrfinder_taxon_id": "287",
            "amrfinder_organism_group": "Pseudomonas_aeruginosa",
            "amrfinder_pubmed_references": "12345678",
            "amrfinder_mutation_symbols": "gyrB_E468D",
            "amrfinder_drug_classes": "QUINOLONE",
            "amrfinder_drug_subclasses": "FLUOROQUINOLONE",
            "amrfinder_mutation_count": 1,
            "amrfinder_provider_retrieval_status": "api_real",
            "amrfinder_provider_source_used": "api_real",
            "amrfinder_provider_url": "https://example.test/ReferenceGeneCatalog.txt",
        }
        pd.DataFrame([row]).to_csv(
            external_dir / "evolutionary_escape_risk.csv",
            index=False,
        )

        profile_path = project_dir / "results" / "organism_profile.json"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            json.dumps(
                {
                    "organism_input_name": "Pseudomonas aeruginosa",
                    "organism_canonical_name": "Pseudomonas aeruginosa",
                    "taxon_id": "287",
                }
            ),
            encoding="utf-8",
        )

        config = load_config(project_dir / "config" / "params.yaml")
        config["online_sources"]["source_mode_default"] = "offline_only"
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrated = integrate_tables(project_dir)

        candidate = integrated.set_index("protein_id").loc["PA0001"]
        self.assertEqual(float(candidate["resistance_emergence_risk"]), 1.0)
        self.assertEqual(
            candidate["evolutionary_escape_risk_database"],
            "ncbi_amrfinderplus_reference_gene_catalog:2026-01-15.1",
        )
        self.assertEqual(candidate["amrfinder_source_version"], "2026-01-15.1")
        self.assertEqual(candidate["amrfinder_catalog_sha256"], "b" * 64)
        self.assertEqual(candidate["amrfinder_mutation_symbols"], "gyrB_E468D")
        self.assertEqual(int(float(candidate["amrfinder_pubmed_references"])), 12345678)
        self.assertEqual(candidate["amrfinder_mapping_status"], "exact_gene_and_taxon")
        self.assertEqual(
            candidate["amrfinder_independence_group"],
            "ncbi_amrfinderplus_curated_point_mutations",
        )
        self.assertEqual(candidate["evolutionary_escape_risk_source_type"], "external")
        self.assertTrue(bool(candidate["evolutionary_escape_risk_is_external"]))


if __name__ == "__main__":
    unittest.main()
