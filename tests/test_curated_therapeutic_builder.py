from __future__ import annotations

import importlib.util
import shutil
import unittest
import uuid
from pathlib import Path

import pandas as pd

from tests.helpers import PROJECT_ROOT


SCRIPT_PATH = PROJECT_ROOT / "scripts" / "build_curated_therapeutic_inputs.py"
spec = importlib.util.spec_from_file_location("build_curated_therapeutic_inputs", SCRIPT_PATH)
builder = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(builder)


class CuratedTherapeuticBuilderTests(unittest.TestCase):
    def make_workspace(self) -> Path:
        workspace = PROJECT_ROOT / ".tmp_tests" / f"curated_builder_{uuid.uuid4().hex[:8]}"
        (workspace / "results").mkdir(parents=True, exist_ok=True)
        (workspace / "data_user").mkdir(parents=True, exist_ok=True)
        (workspace / "data_external").mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))
        return workspace

    def write_queues(self, workspace: Path) -> None:
        pd.DataFrame(
            [
                {
                    "protein_id": "PA0008",
                    "gene": "lasB",
                    "curated_host_direct_damage_score": 0.81,
                    "curated_virulence_associated_severity_score": 0.77,
                    "curated_clinical_impact_score": 0.79,
                    "curated_clinical_impact_evidence_type": "curated_literature",
                    "curated_clinical_impact_evidence_reference": "doi:10.example/clinical",
                    "curated_clinical_impact_evidence_note": "manual note",
                    "curated_database": "curated_clinical_catalog_test",
                },
                {
                    "protein_id": "PA0001",
                    "gene": "gyrB",
                    "curated_host_direct_damage_score": "",
                    "curated_virulence_associated_severity_score": "",
                    "curated_clinical_impact_score": "",
                    "curated_clinical_impact_evidence_type": "",
                    "curated_clinical_impact_evidence_reference": "",
                    "curated_clinical_impact_evidence_note": "",
                    "curated_database": "",
                },
            ]
        ).to_csv(workspace / "results" / "clinical_impact_curation_queue.csv", index=False)
        pd.DataFrame(
            [
                {
                    "protein_id": "PA0008",
                    "gene": "lasB",
                    "curated_infection_context_score": 0.74,
                    "curated_disease_context": "pneumonia",
                    "curated_infection_stage": "acute_infection",
                    "curated_context_evidence_type": "curated_literature",
                    "curated_context_evidence_reference": "doi:10.example/context",
                    "curated_context_evidence_note": "manual context note",
                    "curated_database": "curated_context_catalog_test",
                }
            ]
        ).to_csv(workspace / "results" / "disease_context_curation_queue.csv", index=False)
        pd.DataFrame(
            [
                {
                    "protein_id": "PA0008",
                    "gene": "lasB",
                    "curated_infection_site_access": 0.83,
                    "curated_infection_site": "lung",
                    "curated_access_evidence_type": "curated_literature",
                    "curated_access_evidence_reference": "doi:10.example/site",
                    "curated_access_evidence_note": "manual site note",
                    "curated_database": "curated_site_catalog_test",
                }
            ]
        ).to_csv(workspace / "results" / "therapy_site_context_curation_queue.csv", index=False)

    def test_builder_writes_data_user_files_from_complete_curated_rows(self) -> None:
        workspace = self.make_workspace()
        self.write_queues(workspace)

        written = builder.build_curated_inputs(
            workspace=workspace,
            target="data_user",
            catalog_key="manual_test",
            overwrite=False,
        )

        self.assertEqual({item[0] for item in written}, {"clinical_impact", "curated_disease_context", "therapy_site_context"})
        clinical = pd.read_csv(workspace / "data_user" / "clinical_impact.csv")
        self.assertEqual(len(clinical), 1)
        self.assertEqual(clinical.loc[0, "protein_id"], "PA0008")
        self.assertAlmostEqual(float(clinical.loc[0, "host_direct_damage_score"]), 0.81)
        self.assertEqual(clinical.loc[0, "clinical_impact_evidence_reference"], "doi:10.example/clinical")
        disease = pd.read_csv(workspace / "data_user" / "curated_disease_context.csv")
        self.assertEqual(disease.loc[0, "disease_context"], "pneumonia")
        self.assertEqual(disease.loc[0, "context_evidence_reference"], "doi:10.example/context")
        site = pd.read_csv(workspace / "data_user" / "therapy_site_context.csv")
        self.assertEqual(site.loc[0, "infection_site"], "lung")
        self.assertEqual(site.loc[0, "access_evidence_reference"], "doi:10.example/site")

    def test_builder_writes_external_catalog_files_when_requested(self) -> None:
        workspace = self.make_workspace()
        self.write_queues(workspace)

        builder.build_curated_inputs(
            workspace=workspace,
            target="external_catalog",
            catalog_key="taxon 287",
            overwrite=False,
        )

        self.assertTrue((workspace / "data_external" / "curated_catalogs" / "clinical_impact" / "taxon_287.csv").exists())
        self.assertTrue((workspace / "data_external" / "curated_catalogs" / "curated_disease_context" / "taxon_287.csv").exists())
        self.assertTrue((workspace / "data_external" / "curated_catalogs" / "therapy_site_context" / "taxon_287.csv").exists())

    def test_builder_refuses_to_overwrite_without_flag(self) -> None:
        workspace = self.make_workspace()
        self.write_queues(workspace)
        builder.build_curated_inputs(workspace=workspace, target="data_user", catalog_key="manual", overwrite=False)

        with self.assertRaises(FileExistsError):
            builder.build_curated_inputs(workspace=workspace, target="data_user", catalog_key="manual", overwrite=False)


if __name__ == "__main__":
    unittest.main()
