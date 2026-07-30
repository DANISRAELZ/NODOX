from __future__ import annotations

import shutil
import json
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.layer_resolver import resolve_layer_inputs
from tests.test_uniprot_api import FakeResponse as UniProtFakeResponse
from tests.helpers import PROJECT_ROOT

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class LayerResolverTests(unittest.TestCase):
    def make_workspace(self) -> Path:
        workspace = PROJECT_ROOT / ".tmp_tests" / f"layer_resolver_{uuid.uuid4().hex[:8]}"
        for relative in ["config", "data_raw", "data_user", "data_cache", "data_external", "results"]:
            (workspace / relative).mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))

        params_source = PROJECT_ROOT / "config" / "params.yaml"
        (workspace / "config" / "params.yaml").write_text(params_source.read_text(encoding="utf-8"), encoding="utf-8")

        for filename in [
            "essentiality.csv",
            "virulence.csv",
            "human_homologs.csv",
            "localization.csv",
        ]:
            source = PROJECT_ROOT / "data_raw" / filename
            if source.exists():
                (workspace / "data_raw" / filename).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        for filename in ["functional_network.csv", "host_annotation.csv", "literature_support.csv"]:
            source = PROJECT_ROOT / "data_demo" / filename
            if source.exists():
                (workspace / "data_external" / filename).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return workspace

    def _human_gene_payload(self, gene: str) -> dict:
        return {
            "results": [
                {
                    "primaryAccession": f"HUMAN_{gene}",
                    "uniProtkbId": f"HUMAN_ID_{gene}",
                    "entryType": "UniProtKB reviewed (Swiss-Prot)",
                    "organism": {"scientificName": "Homo sapiens"},
                    "genes": [{"geneName": {"value": gene}}],
                }
            ]
        }

    def test_user_data_has_priority_over_cache_and_external(self) -> None:
        workspace = self.make_workspace()
        (workspace / "data_user" / "essentiality.csv").write_text(
            "\n".join(
                [
                    "protein,gene_name,essentiality_flag,evidence_note,source",
                    "PA0001,gyrB,0,user_supplied,user_layer",
                ]
            ),
            encoding="utf-8",
        )
        (workspace / "data_cache" / "essentiality.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,essential,evidence,database",
                    "PA0001,gyrB,1,cache_hit,cache_layer",
                ]
            ),
            encoding="utf-8",
        )
        (workspace / "data_external" / "essentiality.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,essential,evidence,database",
                    "PA0001,gyrB,1,external_hit,external_layer",
                ]
            ),
            encoding="utf-8",
        )

        config = load_config(workspace / "config" / "params.yaml")
        config["online_sources"]["source_mode_effective"] = "offline_only"
        manifest = resolve_layer_inputs(workspace, config)
        resolved = pd.read_csv(workspace / "data_raw" / "essentiality.csv")

        self.assertEqual(manifest["essentiality"]["resolved_from"], "user")
        self.assertEqual(int(resolved.loc[0, "essential"]), 0)
        self.assertEqual(resolved.loc[0, "database"], "user_layer")

    def test_packaged_demo_raw_keeps_demo_provenance(self) -> None:
        workspace = self.make_workspace()
        manifest = {
            "demo_files_copied": ["essentiality.csv"],
            "datasets": [
                {
                    "filename": "essentiality.csv",
                    "table_key": "essentiality",
                    "source_type": "demo",
                    "generated_by": "packaged_demo",
                }
            ],
        }
        (workspace / "results" / "acquisition_manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        config = load_config(workspace / "config" / "params.yaml")
        config["online_sources"]["source_mode_effective"] = "offline_only"
        config["online_sources"]["therapeutic_context"]["enabled"] = False
        config["online_sources"]["therapeutic_context_v2"]["enabled"] = False
        resolved_manifest = resolve_layer_inputs(workspace, config)

        essentiality = resolved_manifest["essentiality"]
        self.assertEqual(essentiality["resolved_from"], "raw")
        self.assertEqual(essentiality["source_type"], "packaged_demo")
        self.assertEqual(essentiality["generated_by"], "packaged_demo")
        self.assertFalse(bool(essentiality["is_user_supplied"]))
        self.assertIn("packaged_demo:essentiality.csv", essentiality["selected_inputs"])

    def test_cache_fallback_is_used_when_user_data_is_missing(self) -> None:
        workspace = self.make_workspace()
        (workspace / "data_cache" / "essentiality.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,essential,evidence,database",
                    "PA0002,rpoB,0,cache_hit,cache_layer",
                ]
            ),
            encoding="utf-8",
        )

        config = load_config(workspace / "config" / "params.yaml")
        config["online_sources"]["source_mode_effective"] = "offline_only"
        manifest = resolve_layer_inputs(workspace, config)
        resolved = pd.read_csv(workspace / "data_raw" / "essentiality.csv")

        self.assertEqual(manifest["essentiality"]["resolved_from"], "cache")
        self.assertEqual(int(resolved.loc[0, "essential"]), 0)

    def test_external_fallback_populates_cache_when_enabled(self) -> None:
        workspace = self.make_workspace()
        (workspace / "data_raw" / "essentiality.csv").unlink(missing_ok=True)
        (workspace / "data_external" / "essentiality.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,essential,evidence,database",
                    "PA0003,ftsZ,0,external_hit,external_layer",
                ]
            ),
            encoding="utf-8",
        )

        config = load_config(workspace / "config" / "params.yaml")
        config["online_sources"]["source_mode_effective"] = "offline_only"
        manifest = resolve_layer_inputs(workspace, config)
        resolved = pd.read_csv(workspace / "data_raw" / "essentiality.csv")
        cached = pd.read_csv(workspace / "data_cache" / "essentiality.csv")

        self.assertEqual(manifest["essentiality"]["resolved_from"], "external")
        self.assertEqual(int(resolved.loc[0, "essential"]), 0)
        self.assertEqual(int(cached.loc[0, "essential"]), 0)

    def test_proxy_fallback_is_recorded_for_optional_layer(self) -> None:
        workspace = self.make_workspace()
        config = load_config(workspace / "config" / "params.yaml")
        config["online_sources"]["therapeutic_context"]["enabled"] = False
        config["online_sources"]["therapeutic_context_v2"]["enabled"] = False
        manifest = resolve_layer_inputs(workspace, config)

        self.assertEqual(manifest["clinical_impact"]["resolved_from"], "proxy")
        self.assertTrue(manifest["clinical_impact"]["is_proxy"])
        self.assertEqual(manifest["clinical_impact"]["retrieval_status"], "proxy_default")
        self.assertFalse((workspace / "data_raw" / "clinical_impact.csv").exists())

    def test_therapeutic_user_data_has_priority_over_controlled_provider(self) -> None:
        workspace = self.make_workspace()
        (workspace / "data_user" / "clinical_impact.csv").write_text(
            "\n".join(
                [
                    "protein,gene_name,host_damage_reduction_potential,disease_severity_association,clinical_impact_score,host_damage_score,source",
                    "PA0001,gyrB,0.11,0.12,0.13,0.14,user_clinical_layer",
                ]
            ),
            encoding="utf-8",
        )

        config = load_config(workspace / "config" / "params.yaml")
        manifest = resolve_layer_inputs(workspace, config)

        resolved = pd.read_csv(workspace / "data_raw" / "clinical_impact.csv")
        self.assertEqual(manifest["clinical_impact"]["resolved_from"], "user")
        self.assertEqual(manifest["clinical_impact"]["source_type"], "user")
        self.assertTrue(bool(manifest["clinical_impact"]["is_user_supplied"]))
        self.assertEqual(float(resolved.loc[0, "host_damage_score"]), 0.14)
        self.assertEqual(resolved.loc[0, "database"], "user_clinical_layer")

    def test_therapeutic_cache_is_used_before_controlled_provider(self) -> None:
        workspace = self.make_workspace()
        (workspace / "data_cache" / "therapy_site_context.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,infection_site_access,database",
                    "PA0007,oprD,0.77,cache_therapy_site_layer",
                ]
            ),
            encoding="utf-8",
        )

        config = load_config(workspace / "config" / "params.yaml")
        manifest = resolve_layer_inputs(workspace, config)

        resolved = pd.read_csv(workspace / "data_raw" / "therapy_site_context.csv")
        self.assertEqual(manifest["therapy_site_context"]["resolved_from"], "cache")
        self.assertEqual(manifest["therapy_site_context"]["source_type"], "cache")
        self.assertTrue(bool(manifest["therapy_site_context"]["is_cached"]))
        self.assertEqual(float(resolved.loc[0, "infection_site_access"]), 0.77)
        self.assertEqual(resolved.loc[0, "database"], "cache_therapy_site_layer")

    def test_therapeutic_controlled_provider_is_used_when_no_user_cache_or_raw_exists(self) -> None:
        workspace = self.make_workspace()
        config = load_config(workspace / "config" / "params.yaml")
        manifest = resolve_layer_inputs(workspace, config)

        resolved = pd.read_csv(workspace / "data_raw" / "curated_disease_context.csv")
        cached = pd.read_csv(workspace / "data_cache" / "curated_disease_context.csv")
        self.assertEqual(manifest["curated_disease_context"]["resolved_from"], "external")
        self.assertEqual(manifest["curated_disease_context"]["source_type"], "external")
        self.assertEqual(
            manifest["curated_disease_context"]["source_name"],
            "controlled_therapeutic_context_v2",
        )
        self.assertEqual(
            manifest["curated_disease_context"]["retrieval_status"],
            "controlled_provider_materialized",
        )
        self.assertAlmostEqual(float(manifest["curated_disease_context"]["confidence"]), 0.66, places=2)
        self.assertTrue(bool(manifest["curated_disease_context"]["is_external"]))
        self.assertFalse(bool(manifest["curated_disease_context"]["is_proxy"]))
        self.assertIn("infection_context_score", resolved.columns)
        self.assertEqual(len(resolved), 10)
        self.assertEqual(len(cached), 10)

    def test_human_homologs_user_data_has_priority_over_external_provider(self) -> None:
        workspace = self.make_workspace()
        (workspace / "data_user" / "human_homologs.csv").write_text(
            "\n".join(
                [
                    "protein,gene_name,homolog_flag,best_evalue,human_symbol,source",
                    "PA0001,gyrB,1,1.0e-40,GYRB_HUMAN,user_layer",
                ]
            ),
            encoding="utf-8",
        )

        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.layer_resolver.fetch_layer_external_source") as external_mock:
            manifest = resolve_layer_inputs(workspace, config)

        resolved = pd.read_csv(workspace / "data_raw" / "human_homologs.csv")
        self.assertEqual(manifest["human_homologs"]["resolved_from"], "user")
        self.assertEqual(manifest["human_homologs"]["source_type"], "user")
        self.assertTrue(bool(manifest["human_homologs"]["is_user_supplied"]))
        self.assertEqual(int(resolved.loc[0, "human_homolog"]), 1)
        self.assertEqual(resolved.loc[0, "human_gene"], "GYRB_HUMAN")
        self.assertFalse(
            any(call.kwargs.get("layer_key") == "human_homologs" for call in external_mock.call_args_list)
        )

    def test_human_homologs_cache_fallback_is_used_before_external_provider(self) -> None:
        workspace = self.make_workspace()
        (workspace / "data_raw" / "human_homologs.csv").unlink(missing_ok=True)
        (workspace / "data_cache" / "human_homologs.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,human_homolog,evalue,human_gene,database",
                    "PA0002,rpoB,1,1.0e-30,RPOB_HUMAN,cache_layer",
                ]
            ),
            encoding="utf-8",
        )

        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.layer_resolver.fetch_layer_external_source") as external_mock:
            manifest = resolve_layer_inputs(workspace, config)

        resolved = pd.read_csv(workspace / "data_raw" / "human_homologs.csv")
        self.assertEqual(manifest["human_homologs"]["resolved_from"], "cache")
        self.assertEqual(manifest["human_homologs"]["source_type"], "cache")
        self.assertTrue(bool(manifest["human_homologs"]["is_cached"]))
        self.assertEqual(int(resolved.loc[0, "human_homolog"]), 1)
        self.assertEqual(resolved.loc[0, "database"], "cache_layer")
        self.assertFalse(
            any(call.kwargs.get("layer_key") == "human_homologs" for call in external_mock.call_args_list)
        )

    def test_therapy_site_context_user_evidence_has_priority_over_controlled_provider(self) -> None:
        workspace = self.make_workspace()
        (workspace / "data_user" / "therapy_site_context.csv").write_text(
            "\n".join(
                [
                    "protein,gene_name,site_access_score,site_of_infection,evidence_type,reference,comment,source",
                    "PA0008,lasB,0.88,lung_abscess,curated_literature,doi:10.example/site,note,user_site_layer",
                ]
            ),
            encoding="utf-8",
        )

        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.layer_resolver.fetch_layer_external_source") as external_mock:
            manifest = resolve_layer_inputs(workspace, config)

        resolved = pd.read_csv(workspace / "data_raw" / "therapy_site_context.csv")
        self.assertEqual(manifest["therapy_site_context"]["resolved_from"], "user")
        self.assertEqual(manifest["therapy_site_context"]["source_type"], "user")
        self.assertTrue(bool(manifest["therapy_site_context"]["is_user_supplied"]))
        self.assertEqual(float(resolved.loc[0, "infection_site_access"]), 0.88)
        self.assertEqual(resolved.loc[0, "infection_site"], "lung_abscess")
        self.assertEqual(resolved.loc[0, "access_evidence_reference"], "doi:10.example/site")
        self.assertFalse(
            any(call.kwargs.get("layer_key") == "therapy_site_context" for call in external_mock.call_args_list)
        )

    def test_human_homologs_real_provider_is_used_when_no_user_or_cache_exists(self) -> None:
        workspace = self.make_workspace()
        (workspace / "data_raw" / "human_homologs.csv").unlink(missing_ok=True)
        side_effect = []
        for gene in ["gyrB", "rpoB", "ftsZ", "murA", "fabI", "acpP", "oprD", "lasB", "algD", "pvdA"]:
            if gene == "gyrB":
                side_effect.append(UniProtFakeResponse(self._human_gene_payload(gene)))
            else:
                side_effect.append(UniProtFakeResponse({"results": []}))

        config = load_config(workspace / "config" / "params.yaml")
        config["online_sources"]["human_homology_diamond"]["enabled"] = True
        with patch("src.nodos_funcionales.online_sources.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = side_effect
            manifest = resolve_layer_inputs(workspace, config)

        resolved = pd.read_csv(workspace / "data_raw" / "human_homologs.csv")
        cached = pd.read_csv(workspace / "data_cache" / "human_homologs.csv")
        self.assertEqual(manifest["human_homologs"]["resolved_from"], "external")
        self.assertEqual(manifest["human_homologs"]["source_type"], "external")
        self.assertEqual(
            manifest["human_homologs"]["source_name"],
            "diamond_human_sequence_alignment",
        )
        self.assertEqual(
            manifest["human_homologs"]["retrieval_status"],
            "diamond_query_fasta_unavailable",
        )
        self.assertAlmostEqual(float(manifest["human_homologs"]["confidence"]), 0.0, places=2)
        self.assertTrue(bool(manifest["human_homologs"]["is_external"]))
        self.assertTrue(pd.isna(resolved.loc[resolved["protein_id"] == "PA0001", "human_homolog"].iloc[0]))
        self.assertTrue(pd.isna(cached.loc[cached["protein_id"] == "PA0001", "human_homolog"].iloc[0]))
        self.assertEqual(
            resolved.loc[resolved["protein_id"] == "PA0001", "homology_evidence_tier"].iloc[0],
            "diamond_unresolved",
        )

    def test_host_annotation_user_data_has_priority_over_controlled_provider(self) -> None:
        workspace = self.make_workspace()
        (workspace / "data_user" / "host_annotation.csv").write_text(
            "\n".join(
                [
                    "protein,gene_name,domain_overlap,host_criticality,source",
                    "PA0001,gyrB,0.12,0.13,user_host_layer",
                ]
            ),
            encoding="utf-8",
        )

        config = load_config(workspace / "config" / "params.yaml")
        manifest = resolve_layer_inputs(workspace, config)

        resolved = pd.read_csv(workspace / "data_raw" / "host_annotation.csv")
        self.assertEqual(manifest["host_annotation"]["resolved_from"], "user")
        self.assertEqual(manifest["host_annotation"]["source_type"], "user")
        self.assertTrue(bool(manifest["host_annotation"]["is_user_supplied"]))
        self.assertEqual(float(resolved.loc[0, "domain_overlap_score"]), 0.12)
        self.assertEqual(float(resolved.loc[0, "host_criticality_penalty"]), 0.13)
        self.assertEqual(resolved.loc[0, "database"], "user_host_layer")

    def test_host_annotation_controlled_provider_is_used_when_no_user_cache_or_raw_exists(self) -> None:
        workspace = self.make_workspace()
        external_path = workspace / "data_external" / "host_annotation.csv"
        external_path.write_text(
            "\n".join(
                [
                    "protein_id,gene,domain_overlap_score,host_criticality_penalty,database",
                    "PA0001,gyrB,0.0,0.0,computed_host_annotation_from_homology_v1",
                ]
            ),
            encoding="utf-8",
        )
        config = load_config(workspace / "config" / "params.yaml")
        manifest = resolve_layer_inputs(workspace, config)

        resolved = pd.read_csv(workspace / "data_raw" / "host_annotation.csv")
        cached = pd.read_csv(workspace / "data_cache" / "host_annotation.csv")
        self.assertEqual(manifest["host_annotation"]["resolved_from"], "external")
        self.assertEqual(manifest["host_annotation"]["source_type"], "external")
        self.assertEqual(manifest["host_annotation"]["source_name"], "interpro_domain_overlap")
        self.assertEqual(manifest["host_annotation"]["retrieval_status"], "external_not_requested")
        self.assertAlmostEqual(float(manifest["host_annotation"]["confidence"]), 0.70, places=2)
        self.assertTrue(bool(manifest["host_annotation"]["is_external"]))
        self.assertFalse(bool(manifest["host_annotation"]["is_proxy"]))
        self.assertIn("domain_overlap_score", resolved.columns)
        self.assertIn("host_criticality_penalty", resolved.columns)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(len(cached), 1)


if __name__ == "__main__":
    unittest.main()
