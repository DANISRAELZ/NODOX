from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import PROJECT_ROOT, make_temp_project


class IntegrationTests(unittest.TestCase):
    def _make_workspace_with_host_audit_columns(self) -> Path:
        workspace = PROJECT_ROOT / ".tmp_tests" / f"integration_host_audit_{uuid.uuid4().hex[:8]}"
        for dirname in ["data_raw", "config", "data_processed", "results"]:
            (workspace / dirname).mkdir(parents=True, exist_ok=True)
        for path in (PROJECT_ROOT / "data_raw").glob("*.csv"):
            shutil.copyfile(path, workspace / "data_raw" / path.name)
        shutil.copyfile(PROJECT_ROOT / "config" / "params.yaml", workspace / "config" / "params.yaml")
        (workspace / "data_raw" / "host_annotation.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,domain_overlap_score,host_criticality_penalty,interpro_rule,interpro_shared_entries,human_essentiality_score,human_essentiality_status,database",
                    "PA0001,gyrB,0.33,0.44,interpro_shared_domain_overlap_v1,IPR000001,1.0,matched_essential,computed_interpro_domain_overlap_v1",
                ]
            ),
            encoding="utf-8",
        )
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))
        return workspace

    def test_integrated_table_contains_canonical_fields(self) -> None:
        project_dir = make_temp_project()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrated = integrate_tables(project_dir)

        self.assertIn("protein_id_canonical", integrated.columns)
        self.assertIn("mapping_confidence", integrated.columns)
        self.assertIn("source_database", integrated.columns)
        self.assertIn("essentiality_source_type", integrated.columns)
        self.assertIn("virulence_source_type", integrated.columns)
        self.assertIn("clinical_impact_source_type", integrated.columns)
        self.assertIn("clinical_impact_retrieval_status", integrated.columns)
        self.assertEqual(len(integrated), 10)
        for column in [
            "core_genome_presence",
            "strain_coverage_score",
            "allelic_conservation",
            "variant_burden",
            "network_centrality",
            "pathway_bottleneck_score",
            "redundancy_penalty",
            "functional_dependency_score",
            "domain_overlap_score",
            "host_criticality_penalty",
        ]:
            self.assertIn(column, integrated.columns)
        self.assertTrue(integrated["network_centrality"].notna().all())
        self.assertTrue(integrated["core_genome_presence"].notna().all())
        self.assertTrue(integrated["essentiality_source_type"].eq("raw").all())
        self.assertTrue(integrated["clinical_impact_source_type"].isin(["external", "cache", "raw"]).all())
        self.assertFalse(integrated["clinical_impact_source_type"].eq("proxy").any())
        self.assertIn("host_damage_score", integrated.columns)
        self.assertTrue(integrated["host_damage_score"].notna().all())

    def test_integrated_table_propagates_host_annotation_audit_columns(self) -> None:
        project_dir = self._make_workspace_with_host_audit_columns()
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrated = integrate_tables(project_dir)

        self.assertIn("interpro_rule", integrated.columns)
        self.assertIn("interpro_shared_entries", integrated.columns)
        self.assertIn("human_essentiality_score", integrated.columns)
        self.assertEqual(
            integrated.set_index("protein_id").loc["PA0001", "interpro_rule"],
            "interpro_shared_domain_overlap_v1",
        )

    def test_integrated_table_accepts_optional_phase3_inputs(self) -> None:
        project_dir = make_temp_project()
        raw_dir = project_dir / "data_raw"
        (raw_dir / "contextual_essentiality.csv").write_text(
            "\n".join(
                [
                    (
                        "protein_id,gene,contextual_essentiality_score,pleiotropy_score,"
                        "functional_node_theory_score,therapeutic_role_v3,phase3_notes"
                    ),
                    "PA0008,lasB,0.86,0.72,0.81,antivirulence_node,lung context signal",
                ]
            ),
            encoding="utf-8",
        )
        (raw_dir / "evolutionary_escape.csv").write_text(
            "\n".join(
                [
                    (
                        "protein_id,gene,known_escape_mutation_score,inferred_functional_tolerance_score,"
                        "module_participation_score,paralog_count_score,alternative_pathway_score,"
                        "mutational_tolerance_score,fitness_cost_score,"
                        "compensation_difficulty_score,biofilm_escape_penalty,"
                        "horizontal_transfer_penalty,evolutionary_escape_risk_score,"
                        "evolutionary_space_constraint_score"
                    ),
                    "PA0008,lasB,0.12,0.21,0.73,0.20,0.30,0.22,0.79,0.74,0.10,0.08,0.28,0.76",
                ]
            ),
            encoding="utf-8",
        )
        (raw_dir / "redundancy.csv").write_text(
            "\n".join(
                [
                    (
                        "protein_id,gene,paralog_count,pathway_alternative_count,"
                        "functional_backup_score,metabolic_bypass_score,regulatory_bypass_score,"
                        "paralog_evidence_reference,pathway_evidence_reference,redundancy_evidence_type"
                    ),
                    "PA0008,lasB,1,2,0.35,0.20,0.30,local_paralog_table,curated_pathway_map,curated_local",
                ]
            ),
            encoding="utf-8",
        )
        (raw_dir / "collateral_sensitivity.csv").write_text(
            "\n".join(
                [
                    (
                        "protein_id,gene,collateral_sensitivity_score,"
                        "combination_opportunity_score,recommended_combination_class,"
                        "combination_partner,combination_evidence_reference,combination_rationale"
                    ),
                    "PA0008,lasB,0.69,0.71,virulence_plus_conventional_antibiotic,beta_lactam,doi:10.example/combo,example rationale",
                ]
            ),
            encoding="utf-8",
        )
        (raw_dir / "evidence_quality.csv").write_text(
            "\n".join(
                [
                    (
                        "protein_id,gene,evidence_quality_score,confidence_ceiling,"
                        "evidence_source_type,evidence_notes,audit_flags,phase3_notes"
                    ),
                    "PA0008,lasB,0.66,0.70,curated_literature,example evidence,manual_review,evidence note",
                ]
            ),
            encoding="utf-8",
        )
        config = load_config(project_dir / "config" / "params.yaml")
        load_and_validate_all(project_dir, config)
        normalize_all(project_dir, config)
        integrated = integrate_tables(project_dir)

        row = integrated.set_index("protein_id").loc["PA0008"]
        self.assertEqual(float(row["contextual_essentiality_score"]), 0.86)
        self.assertEqual(float(row["known_escape_mutation_score"]), 0.12)
        self.assertEqual(float(row["evolutionary_escape_risk_score"]), 0.28)
        self.assertEqual(float(row["paralog_count"]), 1.0)
        self.assertEqual(float(row["pathway_alternative_count"]), 2.0)
        self.assertEqual(float(row["collateral_sensitivity_score"]), 0.69)
        self.assertEqual(float(row["combination_opportunity_score"]), 0.71)
        self.assertEqual(float(row["evidence_quality_score"]), 0.66)
        self.assertEqual(row["recommended_combination_class"], "virulence_plus_conventional_antibiotic")
        self.assertEqual(row["combination_partner"], "beta_lactam")
        self.assertEqual(row["evidence_source_type"], "curated_literature")


if __name__ == "__main__":
    unittest.main()
