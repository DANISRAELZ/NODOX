from __future__ import annotations

import unittest

import pandas as pd

from tests.helpers import PROJECT_ROOT


TEMPLATE_DIR = PROJECT_ROOT / "data_templates"

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
        "gene",
        "organism",
        "disease_context",
        "evidence_type",
        "therapeutic_relevance",
        "virulence_relevance",
        "essentiality_relevance",
        "resistance_relevance",
        "host_safety_relevance",
        "evolutionary_escape_relevance",
        "citation",
        "doi",
        "pubmed_id",
        "year",
        "evidence_strength",
        "evidence_source_type",
        "curator_notes",
        "literature_support_score",
        "source_quality",
        "database",
    ],
    "host_annotation_template.csv": ["protein_id", "gene", "domain_overlap_score", "host_criticality_penalty", "database"],
    "evolutionary_escape_risk_template.csv": [
        "candidate_id",
        "gene",
        "protein_id",
        "organism",
        "strain",
        "mutation_tolerance_score",
        "functional_redundancy_escape_score",
        "compensatory_pathway_score",
        "fitness_cost_of_escape",
        "evolutionary_constraint_score",
        "resistance_emergence_risk",
        "multi_node_dependency_score",
        "evidence_source",
        "source_type",
        "confidence",
        "notes",
    ],
    "organism_profile_template.csv": [
        "organism",
        "strain",
        "taxonomy_id",
        "genome_accession",
        "proteome_source",
        "annotation_source",
        "essentiality_available",
        "virulence_available",
        "conservation_available",
        "functional_network_available",
        "localization_available",
        "human_homologs_available",
        "evolutionary_escape_available",
        "literature_support_available",
        "clinical_context_available",
        "disease_context_available",
        "host_context",
        "curator",
        "date",
        "notes",
    ],
}

FORBIDDEN_TERMS = [
    "cpseudo" + "_mexico",
    "Mexican " + "isolates",
    "aislados " + "mexicanos",
    "17 " + "isolates",
    "pangenome " + "mexicano",
    "cpseudotuberculosis" + "_biovar_ovis",
]

ORGANISM_SPECIFIC_DEFAULT_TERMS = [
    "Pseudomonas aeruginosa",
    "Pseudomonas aeruginosa PAO1",
    "PAO1",
]


class GenericOrganismTemplateTests(unittest.TestCase):
    def test_generic_template_directory_exists(self) -> None:
        self.assertTrue(TEMPLATE_DIR.exists())

    def test_generic_templates_have_expected_columns(self) -> None:
        for filename, expected in EXPECTED_COLUMNS.items():
            with self.subTest(filename=filename):
                path = TEMPLATE_DIR / filename
                self.assertTrue(path.exists())
                self.assertEqual(list(pd.read_csv(path).columns), expected)

    def test_generic_workflow_documentation_exists(self) -> None:
        for relative_path in [
            "docs/generic_annotation_import.md",
            "docs/online_organism_enrichment.md",
            "docs/project_boundaries.md",
        ]:
            with self.subTest(path=relative_path):
                self.assertTrue((PROJECT_ROOT / relative_path).exists())

    def test_this_test_has_no_project_specific_terms(self) -> None:
        text = (PROJECT_ROOT / "tests" / "test_generic_organism_templates.py").read_text(encoding="utf-8")
        for term in FORBIDDEN_TERMS:
            with self.subTest(term=term):
                self.assertNotIn(term, text)

    def test_multi_organism_templates_do_not_default_to_pao1(self) -> None:
        for filename in ["evolutionary_escape_risk_template.csv", "organism_profile_template.csv"]:
            text = (TEMPLATE_DIR / filename).read_text(encoding="utf-8")
            for term in ORGANISM_SPECIFIC_DEFAULT_TERMS:
                with self.subTest(filename=filename, term=term):
                    self.assertNotIn(term, text)

    def test_corynebacterium_is_only_generic_online_example_in_docs(self) -> None:
        text = (PROJECT_ROOT / "docs" / "online_organism_enrichment.md").read_text(encoding="utf-8")
        self.assertIn("Corynebacterium pseudotuberculosis", text)
        self.assertIn("ejemplo generico", text)
        for term in ["coleccion particular", "proyecto genomico independiente"]:
            self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()
