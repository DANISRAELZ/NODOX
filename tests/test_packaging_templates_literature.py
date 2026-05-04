from __future__ import annotations

import importlib
import shutil
import unittest
import uuid
from pathlib import Path

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.reporting import export_results
from src.nodos_funcionales.scoring import build_features_and_scores, compute_sensitivity
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import PROJECT_ROOT

pytestmark = [pytest.mark.integration, pytest.mark.slow]


EXPECTED_TEMPLATE_COLUMNS = {
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
}


class PackagingTemplatesLiteratureTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        workspace = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        (workspace / "config").mkdir(parents=True, exist_ok=True)
        (workspace / "data_raw").mkdir(parents=True, exist_ok=True)
        (workspace / "results").mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", workspace / "config" / "params.yaml")
        for source in (PROJECT_ROOT / "data_demo").glob("*.csv"):
            if source.name == "literature_support.csv":
                continue
            shutil.copy2(source, workspace / "data_raw" / source.name)
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))
        return workspace

    def test_package_imports_from_src_layout(self) -> None:
        module = importlib.import_module("src.nodos_funcionales")
        self.assertIsNotNone(module)

    def test_csv_templates_have_expected_columns(self) -> None:
        for filename, expected_columns in EXPECTED_TEMPLATE_COLUMNS.items():
            with self.subTest(filename=filename):
                df = pd.read_csv(PROJECT_ROOT / "data_templates" / filename)
                self.assertEqual(list(df.columns), expected_columns)
                self.assertGreaterEqual(len(df), 1)

    def test_pipeline_runs_without_literature_support_layer(self) -> None:
        workspace = self.make_workspace("literature_absent")
        config = load_config(workspace / "config" / "params.yaml")
        load_and_validate_all(workspace, config)
        normalize_all(workspace, config)
        integrate_tables(workspace)
        _, scored = build_features_and_scores(workspace, config)

        self.assertFalse((workspace / "data_processed" / "normalized_literature_support.csv").exists())
        self.assertIn("meta_priority_score", scored.columns)
        self.assertIn("therapeutic_priority_score", scored.columns)

    def test_literature_support_is_normalized_without_changing_scores(self) -> None:
        workspace = self.make_workspace("literature_present")
        shutil.copy2(PROJECT_ROOT / "data_demo" / "literature_support.csv", workspace / "data_raw" / "literature_support.csv")
        config = load_config(workspace / "config" / "params.yaml")
        load_and_validate_all(workspace, config)
        normalize_all(workspace, config)
        integrate_tables(workspace)
        _, scored = build_features_and_scores(workspace, config)

        literature = pd.read_csv(workspace / "data_processed" / "normalized_literature_support.csv")
        self.assertIn("literature_support_score", literature.columns)
        self.assertIn("meta_priority_score", scored.columns)
        self.assertNotIn("literature_support_score", scored.columns)

    def test_literature_support_is_reported_as_interpretive_evidence(self) -> None:
        workspace = self.make_workspace("literature_report")
        shutil.copy2(PROJECT_ROOT / "data_demo" / "literature_support.csv", workspace / "data_raw" / "literature_support.csv")
        config = load_config(workspace / "config" / "params.yaml")
        load_and_validate_all(workspace, config)
        normalize_all(workspace, config)
        integrate_tables(workspace)
        features, scored = build_features_and_scores(workspace, config)
        before_scores = scored[["protein_id", "meta_priority_score", "therapeutic_priority_score"]].copy()
        compute_sensitivity(features, config).to_csv(workspace / "results" / "sensitivity_analysis.csv", index=False)
        export_results(workspace, config)

        after_scores = pd.read_csv(workspace / "data_processed" / "scored_nodes.csv")[
            ["protein_id", "meta_priority_score", "therapeutic_priority_score"]
        ]
        pd.testing.assert_frame_equal(before_scores.reset_index(drop=True), after_scores.reset_index(drop=True))
        literature_summary = pd.read_csv(workspace / "results" / "literature_support_summary.csv")
        self.assertIn("interpretive_note", literature_summary.columns)
        self.assertTrue(literature_summary["interpretive_note"].str.contains("no afecta el ranking").all())
        executive = (workspace / "results" / "resumen_ejecutivo.md").read_text(encoding="utf-8")
        self.assertIn("Soporte bibliografico", executive)

    def test_export_generates_executive_summary(self) -> None:
        workspace = self.make_workspace("executive_summary")
        config = load_config(workspace / "config" / "params.yaml")
        load_and_validate_all(workspace, config)
        normalize_all(workspace, config)
        integrate_tables(workspace)
        features, _ = build_features_and_scores(workspace, config)
        compute_sensitivity(features, config).to_csv(workspace / "results" / "sensitivity_analysis.csv", index=False)
        export_results(workspace, config)

        summary_path = workspace / "results" / "resumen_ejecutivo.md"
        self.assertTrue(summary_path.exists())
        text = summary_path.read_text(encoding="utf-8")
        self.assertIn("priorizacion computacional exploratoria", text)
        self.assertIn("Top 10 blancos priorizados", text)


if __name__ == "__main__":
    unittest.main()
