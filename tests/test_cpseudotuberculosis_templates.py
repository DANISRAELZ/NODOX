from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from tests.helpers import PROJECT_ROOT


BASE_DIR = PROJECT_ROOT / "data_user" / "cpseudotuberculosis_biovar_ovis"
TEMPLATE_DIR = BASE_DIR / "templates"

EXPECTED_COLUMNS = {
    "essentiality.csv": ["protein_id", "gene", "essential", "evidence", "database"],
    "virulence.csv": ["protein_id", "gene", "virulence_score", "virulence_factor", "database"],
    "human_homologs.csv": ["protein_id", "gene", "human_homolog", "evalue", "human_gene", "database"],
    "localization.csv": ["protein_id", "gene", "localization", "database"],
    "strain_conservation.csv": [
        "protein_id",
        "gene",
        "core_genome_presence",
        "strain_coverage_score",
        "allelic_conservation",
        "variant_burden",
        "database",
    ],
    "functional_network.csv": [
        "protein_id",
        "gene",
        "network_centrality",
        "pathway_bottleneck_score",
        "redundancy_penalty",
        "functional_dependency_score",
        "database",
    ],
    "clinical_impact.csv": [
        "protein_id",
        "gene",
        "host_damage_reduction_potential",
        "disease_severity_association",
        "clinical_impact_score",
        "host_damage_score",
        "host_direct_damage_score",
        "virulence_associated_severity_score",
        "clinical_impact_catalog_source",
        "clinical_impact_evidence_type",
        "clinical_impact_evidence_reference",
        "clinical_impact_evidence_note",
        "database",
    ],
    "curated_disease_context.csv": [
        "protein_id",
        "gene",
        "infection_context_score",
        "disease_context",
        "infection_stage",
        "context_evidence_type",
        "context_evidence_reference",
        "context_evidence_note",
        "database",
    ],
    "therapy_site_context.csv": [
        "protein_id",
        "gene",
        "infection_site_access",
        "infection_site",
        "access_evidence_type",
        "access_evidence_reference",
        "access_evidence_note",
        "disease_context",
        "syndrome",
        "disease_site_context_source",
        "database",
    ],
    "literature_support.csv": [
        "protein_id",
        "gene_id",
        "gene",
        "literature_support_score",
        "evidence_type",
        "reference",
        "doi_or_url",
        "notes",
        "source_quality",
        "database",
    ],
    "host_annotation.csv": ["protein_id", "gene", "domain_overlap_score", "host_criticality_penalty", "database"],
}


class CpseudotuberculosisTemplateTests(unittest.TestCase):
    def test_workspace_structure_exists(self) -> None:
        self.assertTrue(BASE_DIR.exists())
        self.assertTrue((BASE_DIR / "README.md").exists())
        self.assertTrue(TEMPLATE_DIR.exists())
        self.assertTrue((BASE_DIR / "metadata").exists())

    def test_templates_have_expected_columns(self) -> None:
        for filename, expected in EXPECTED_COLUMNS.items():
            with self.subTest(filename=filename):
                path = TEMPLATE_DIR / filename
                self.assertTrue(path.exists())
                self.assertEqual(list(pd.read_csv(path).columns), expected)

    def test_metadata_and_plan_exist(self) -> None:
        self.assertTrue((BASE_DIR / "metadata" / "README.md").exists())
        self.assertTrue((BASE_DIR / "metadata" / "isolates.csv").exists())
        self.assertTrue((PROJECT_ROOT / "docs" / "cpseudotuberculosis_data_integration_plan.md").exists())

    def test_plan_documents_dry_run_and_no_invented_data(self) -> None:
        text = (PROJECT_ROOT / "docs" / "cpseudotuberculosis_data_integration_plan.md").read_text(encoding="utf-8")
        self.assertIn("Corynebacterium pseudotuberculosis", text)
        self.assertIn("--dry-run", text)
        self.assertIn("No contiene datos biologicos inventados", text)


if __name__ == "__main__":
    unittest.main()
