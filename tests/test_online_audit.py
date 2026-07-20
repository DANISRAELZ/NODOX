from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.nodos_funcionales.online_audit import (
    _scenario_definitions,
    build_fresh_vs_cache_comparison,
    run_experimental_online_audit,
    write_clean_online_audit,
)
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.online


class OnlineAuditTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        root = Path(tempfile.mkdtemp(prefix=f"nodox_{name}_"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_write_clean_online_audit_outputs(self) -> None:
        workspace = self.make_workspace("online_audit")
        with patch("src.nodos_funcionales.online_audit.run_experimental_online_audit") as audit_mock:
            audit_mock.return_value = (
                pd.DataFrame(
                    [
                        {
                            "scenario": "baseline_no_online",
                            "source_combination": "none",
                            "comparison_group": "baseline",
                        },
                        {
                            "scenario": "string_only_fresh",
                            "source_combination": "string",
                            "comparison_group": "fresh",
                        },
                        {
                            "scenario": "uniprot_only_fresh",
                            "source_combination": "uniprot",
                            "comparison_group": "fresh",
                        },
                    ]
                ),
                pd.DataFrame(),
                pd.DataFrame(),
                {},
            )
            csv_path, md_path, df = write_clean_online_audit(
                project_root=PROJECT_ROOT,
                workspace=workspace,
                organism_name="Test bacterium",
                strain="test_strain",
                sources=["string", "uniprot"],
            )
        self.assertTrue(csv_path.exists())
        self.assertTrue(md_path.exists())
        self.assertEqual(set(df["source_combination"]), {"string", "uniprot"})

    def test_scenario_definitions_include_fresh_and_cache(self) -> None:
        scenarios = _scenario_definitions(["string", "uniprot"], compare_fresh_vs_cache=True)
        names = {item["scenario"] for item in scenarios}
        self.assertIn("baseline_no_online", names)
        self.assertIn("uniprot_only_fresh", names)
        self.assertIn("string_only_fresh", names)
        self.assertIn("combined_online_fresh", names)
        self.assertIn("uniprot_only_cache", names)
        self.assertIn("string_only_cache", names)
        self.assertIn("combined_online_cache", names)

    def test_build_fresh_vs_cache_comparison(self) -> None:
        audit_df = pd.DataFrame(
            [
                {
                    "scenario": "string_only_fresh",
                    "source_combination": "string",
                    "run_kind": "fresh_api_run",
                    "impact_status": "score_level_effect",
                    "scores_changed_count": 2,
                    "ranking_changed": True,
                    "comparison_group": "fresh",
                },
                {
                    "scenario": "string_only_cache",
                    "source_combination": "string",
                    "run_kind": "cache_reuse_run",
                    "impact_status": "annotation_or_provenance_only",
                    "scores_changed_count": 0,
                    "ranking_changed": False,
                    "comparison_group": "cache",
                },
            ]
        )
        comparison = build_fresh_vs_cache_comparison(audit_df)
        self.assertEqual(len(comparison), 1)
        self.assertEqual(comparison.iloc[0]["comparison_label"], "fresh_effect_confirmed")

    def test_build_fresh_vs_cache_comparison_marks_fallback(self) -> None:
        audit_df = pd.DataFrame(
            [
                {
                    "scenario": "uniprot_only_fresh",
                    "source_combination": "uniprot",
                    "run_kind": "fallback_after_api_failure",
                    "impact_status": "annotation_or_provenance_only",
                    "scores_changed_count": 0,
                    "ranking_changed": False,
                    "comparison_group": "fresh",
                },
                {
                    "scenario": "uniprot_only_cache",
                    "source_combination": "uniprot",
                    "run_kind": "cache_reuse_run",
                    "impact_status": "annotation_or_provenance_only",
                    "scores_changed_count": 0,
                    "ranking_changed": False,
                    "comparison_group": "cache",
                },
            ]
        )
        comparison = build_fresh_vs_cache_comparison(audit_df)
        self.assertEqual(comparison.iloc[0]["comparison_label"], "api_failed_fallback_used")

    def test_force_refresh_conflicts_with_fresh_vs_cache_comparison(self) -> None:
        workspace = self.make_workspace("online_audit_conflict")
        with self.assertRaisesRegex(ValueError, "force_refresh"):
            run_experimental_online_audit(
                project_root=PROJECT_ROOT,
                workspace=workspace,
                organism_name="Test bacterium",
                strain="test_strain",
                sources=["string"],
                force_refresh=True,
                compare_fresh_vs_cache=True,
                dry_run=True,
            )


if __name__ == "__main__":
    unittest.main()
