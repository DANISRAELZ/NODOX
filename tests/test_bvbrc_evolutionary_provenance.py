from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.normalization import (
    _annotate_bvbrc_conservation_provenance,
)
from tests.helpers import PROJECT_ROOT


class BvbrcEvolutionaryProvenanceTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        (root / "results").mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def conservation_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "protein_id": "PTEST1",
                    "gene": "gyrB",
                    "core_genome_presence": 0.80,
                    "strain_coverage_score": 0.80,
                    "allelic_conservation": 0.60,
                    "variant_burden": 0.40,
                    "database": "BV-BRC",
                }
            ]
        )

    def write_manifest(
        self,
        workspace: Path,
        *,
        source_used: str,
        generated_at: str = "2026-08-07T12:34:56+00:00",
    ) -> None:
        payload = {
            "source": "bvbrc",
            "provider": "BV-BRC",
            "provider_name": "BV-BRC",
            "taxon_id": "287",
            "query_cache_key": "bvbrc::287::snapshot123",
            "query_complete": True,
            "provider_success": True,
            "retrieval_status": "api_real",
            "source_used": source_used,
            "genomes_retrieved": 125,
            "generated_at_utc": generated_at,
        }
        (workspace / "results" / "bvbrc_conservation_manifest.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def test_live_manifest_materializes_stable_candidate_provenance(self) -> None:
        workspace = self.make_workspace("bvbrc_stage4c_live")
        self.write_manifest(workspace, source_used="api_real")

        result = _annotate_bvbrc_conservation_provenance(
            workspace,
            self.conservation_frame(),
        )

        self.assertEqual(
            result.loc[0, "conservation_retrieved_at"],
            "2026-08-07T12:34:56+00:00",
        )
        self.assertEqual(
            result.loc[0, "conservation_provider_query_cache_key"],
            "bvbrc::287::snapshot123",
        )
        self.assertEqual(
            result.loc[0, "conservation_mapping_status"],
            "exact_gene_and_taxon",
        )
        self.assertEqual(
            result.loc[0, "conservation_independence_group"],
            "bvbrc_strain_conservation_taxon_287",
        )
        self.assertIn(
            "candidate=PTEST1;gene=gyrB",
            str(result.loc[0, "conservation_source_record"]),
        )
        self.assertIn(
            "2026-08-07T12:34:56+00:00",
            str(result.loc[0, "conservation_source_version"]),
        )

    def test_cache_manifest_preserves_original_retrieval_timestamp(self) -> None:
        workspace = self.make_workspace("bvbrc_stage4c_cache")
        original_timestamp = "2026-08-01T01:02:03+00:00"
        self.write_manifest(
            workspace,
            source_used="cache",
            generated_at=original_timestamp,
        )

        result = _annotate_bvbrc_conservation_provenance(
            workspace,
            self.conservation_frame(),
        )

        self.assertEqual(
            result.loc[0, "conservation_retrieved_at"],
            original_timestamp,
        )
        self.assertEqual(
            result.loc[0, "conservation_provider_source_used"],
            "cache",
        )
        self.assertEqual(
            result.loc[0, "conservation_provider_retrieval_status"],
            "api_real",
        )

    def test_incomplete_or_failed_manifest_does_not_create_provenance(self) -> None:
        workspace = self.make_workspace("bvbrc_stage4c_incomplete")
        payload = {
            "taxon_id": "287",
            "query_cache_key": "bvbrc::287::incomplete",
            "query_complete": False,
            "provider_success": False,
            "retrieval_status": "paginated_response_incomplete",
            "source_used": "api_failed",
            "generated_at_utc": "2026-08-07T12:34:56+00:00",
        }
        (workspace / "results" / "bvbrc_conservation_manifest.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

        result = _annotate_bvbrc_conservation_provenance(
            workspace,
            self.conservation_frame(),
        )

        self.assertNotIn("conservation_source_record", result.columns)
        self.assertNotIn("conservation_retrieved_at", result.columns)

    def test_non_bvbrc_database_is_not_annotated_from_stale_manifest(self) -> None:
        workspace = self.make_workspace("bvbrc_stage4c_wrong_database")
        self.write_manifest(workspace, source_used="api_real")
        frame = self.conservation_frame()
        frame["database"] = "user_curated_conservation"

        result = _annotate_bvbrc_conservation_provenance(workspace, frame)

        self.assertNotIn("conservation_source_record", result.columns)


if __name__ == "__main__":
    unittest.main()
