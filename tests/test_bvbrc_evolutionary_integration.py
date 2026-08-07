from __future__ import annotations

import json
import unittest

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import make_temp_project


class BvbrcEvolutionaryIntegrationTests(unittest.TestCase):
    def test_bvbrc_provider_provenance_reaches_integrated_nodes(self) -> None:
        project_dir = make_temp_project()
        raw_path = project_dir / "data_raw" / "strain_conservation.csv"
        conservation = pd.read_csv(raw_path)
        conservation["database"] = "BV-BRC"
        conservation.to_csv(raw_path, index=False)

        manifest = {
            "source": "bvbrc",
            "provider": "BV-BRC",
            "provider_name": "BV-BRC",
            "taxon_id": "287",
            "query_cache_key": "bvbrc::287::integration-test",
            "query_complete": True,
            "provider_success": True,
            "retrieval_status": "api_real",
            "source_used": "api_real",
            "genomes_retrieved": 200,
            "generated_at_utc": "2026-08-07T13:00:00+00:00",
        }
        (project_dir / "results" / "bvbrc_conservation_manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrated = integrate_tables(project_dir)

        row = integrated.set_index("protein_id").loc["PA0001"]
        self.assertEqual(
            row["conservation_retrieved_at"],
            "2026-08-07T13:00:00+00:00",
        )
        self.assertEqual(
            row["conservation_provider_query_cache_key"],
            "bvbrc::287::integration-test",
        )
        self.assertEqual(
            row["conservation_mapping_status"],
            "exact_gene_and_taxon",
        )
        self.assertEqual(
            row["conservation_independence_group"],
            "bvbrc_strain_conservation_taxon_287",
        )
        self.assertIn(
            "candidate=PA0001;gene=gyrB",
            str(row["conservation_source_record"]),
        )

        saved = pd.read_csv(project_dir / "data_processed" / "integrated_nodes.csv")
        saved_row = saved.set_index("protein_id").loc["PA0001"]
        self.assertEqual(
            saved_row["conservation_source_record"],
            row["conservation_source_record"],
        )
        self.assertEqual(
            saved_row["conservation_source_version"],
            row["conservation_source_version"],
        )


if __name__ == "__main__":
    unittest.main()
