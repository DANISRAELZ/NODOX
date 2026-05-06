from __future__ import annotations

import shutil
import uuid
import unittest
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.acquisition import import_user_dataset
from src.nodos_funcionales.discovery import prepare_discovery_workspace
from tests.helpers import PROJECT_ROOT


class AcquisitionTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_import_user_dataset_maps_alias_columns(self) -> None:
        workspace = self.make_workspace("import_case")
        prepare_discovery_workspace(
            project_root=PROJECT_ROOT,
            organism_name="Corynebacterium pseudotuberculosis",
            acquisition_mode="semi_auto",
            workspace=workspace,
        )
        source = workspace / "virulence_export.csv"
        pd.DataFrame(
            {
                "locus_tag": ["CP001"],
                "gene_name": ["pld"],
                "score": [0.82],
                "vf_flag": [1],
                "source": ["lit_demo_source"],
            }
        ).to_csv(source, index=False)

        result = import_user_dataset(
            workspace=workspace,
            dataset_key="virulence",
            input_path=source,
            project_root=PROJECT_ROOT,
        )
        imported = pd.read_csv(result["target_path"])
        self.assertEqual(list(imported.columns), ["protein_id", "gene", "virulence_score", "virulence_factor", "database"])
        self.assertEqual(imported.iloc[0]["protein_id"], "CP001")
        self.assertEqual(imported.iloc[0]["database"], "lit_demo_source")


if __name__ == "__main__":
    unittest.main()
