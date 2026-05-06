from __future__ import annotations

import unittest

from src.nodos_funcionales.workspace_compare import compare_workspaces
from tests.helpers import PROJECT_ROOT


class WorkspaceCompareTests(unittest.TestCase):
    def test_compare_workspaces_returns_known_sessions(self) -> None:
        comparison = compare_workspaces(PROJECT_ROOT)
        self.assertIn("workspace_name", comparison.columns)
        self.assertIn("organism_canonical_name", comparison.columns)
        self.assertIn("online_source", comparison.columns)
        self.assertIn("online_source_used", comparison.columns)
        self.assertIn("online_impact_status", comparison.columns)
        self.assertIn("online_changed_candidate_count", comparison.columns)
        self.assertIn("online_history_count", comparison.columns)
        self.assertIn("online_sources_seen", comparison.columns)
        self.assertTrue(comparison["workspace_name"].isin(["cpseudo_demo", "pao1_demo"]).any())


if __name__ == "__main__":
    unittest.main()
