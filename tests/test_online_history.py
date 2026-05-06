from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.online_history import append_online_history, classify_online_run, load_online_history, write_online_source_comparison
from tests.helpers import PROJECT_ROOT


class OnlineHistoryTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        (root / "results").mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_append_and_compare_online_history(self) -> None:
        workspace = self.make_workspace("online_history")
        impact = pd.DataFrame(
            [
                {
                    "protein_id": "PA0001",
                    "gene": "gyrB",
                    "impact_scope": "ranking_changed",
                }
            ]
        )
        impact.to_csv(workspace / "results" / "online_enrichment_impact.csv", index=False)
        append_online_history(
            workspace,
            {
                "source": "string",
                "provider": "string_api",
                "mode": "online_optional",
                "source_used": "api_real",
                "cache_hit": False,
                "api_attempted": True,
                "api_success": True,
                "data_realism_flag": "computed_online",
                "fallback_reason": None,
                "query_cache_key": "string::demo",
                "taxon_id": "287",
            },
        )
        impact["impact_scope"] = "annotation_or_provenance_only"
        impact.to_csv(workspace / "results" / "online_enrichment_impact.csv", index=False)
        append_online_history(
            workspace,
            {
                "source": "uniprot",
                "provider": "uniprot_rest",
                "mode": "cache_first",
                "source_used": "cache",
                "cache_hit": True,
                "api_attempted": False,
                "api_success": False,
                "data_realism_flag": "computed_cached",
                "fallback_reason": None,
                "query_cache_key": "uniprot::demo",
                "taxon_id": "287",
            },
        )
        history = load_online_history(workspace)
        self.assertEqual(len(history), 2)
        csv_path, md_path, comparison = write_online_source_comparison(workspace)
        self.assertTrue(csv_path.exists())
        self.assertTrue(md_path.exists())
        self.assertEqual(set(comparison["source"]), {"string", "uniprot"})
        self.assertIn("latest_run_kind", comparison.columns)

    def test_classify_online_run(self) -> None:
        self.assertEqual(
            classify_online_run({"source_used": "api_real", "api_attempted": True, "api_success": True, "cache_hit": False}),
            "fresh_api_run",
        )
        self.assertEqual(
            classify_online_run({"source_used": "cache", "api_attempted": False, "api_success": False, "cache_hit": True}),
            "cache_reuse_run",
        )


if __name__ == "__main__":
    unittest.main()
