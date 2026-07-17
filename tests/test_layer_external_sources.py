from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.online_sources import fetch_layer_external_source
from tests.test_string_api import FakeResponse as StringFakeResponse
from tests.test_uniprot_api import FakeResponse as UniProtFakeResponse
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.online


class LayerExternalSourceTests(unittest.TestCase):
    def make_workspace(self, name: str) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "data_raw").mkdir(parents=True, exist_ok=True)
        (root / "results").mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", root / "config" / "params.yaml")
        for filename in ["essentiality.csv", "virulence.csv", "human_homologs.csv", "localization.csv"]:
            shutil.copy2(PROJECT_ROOT / "data_raw" / filename, root / "data_raw" / filename)
        (root / "results" / "organism_profile.json").write_text(
            json.dumps(
                {
                    "organism_canonical_name": "Pseudomonas aeruginosa",
                    "taxon_id": "287",
                }
            ),
            encoding="utf-8",
        )
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def _uniprot_payload(self, gene: str) -> dict:
        return {
            "results": [
                {
                    "primaryAccession": f"ACC_{gene}",
                    "uniProtkbId": f"ID_{gene}",
                    "entryType": "UniProtKB reviewed (Swiss-Prot)",
                    "annotationScore": 5.0,
                    "organism": {"scientificName": "Pseudomonas aeruginosa"},
                    "genes": [{"geneName": {"value": gene}}],
                    "comments": [
                        {
                            "commentType": "SUBCELLULAR LOCATION",
                            "subcellularLocations": [{"location": {"value": "Outer membrane"}}],
                        }
                    ],
                    "proteinDescription": {"recommendedName": {"fullName": {"value": f"Protein {gene}"}}},
                }
            ]
        }

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

    def _empty_human_lookup_payload(self) -> dict:
        return {"results": []}

    def _parse_controlled_inputs(self, value: str) -> dict[str, float]:
        parsed = {}
        for item in value.split(";"):
            key, _, raw = item.strip().partition("=")
            if key:
                parsed[key] = float(raw)
        return parsed

    def test_localization_layer_uses_uniprot_provider(self) -> None:
        workspace = self.make_workspace("layer_uniprot")
        config = load_config(workspace / "config" / "params.yaml")
        genes = ["gyrB", "rpoB", "ftsZ", "murA", "fabI", "acpP", "oprD", "lasB", "algD", "pvdA"]
        with patch("src.nodos_funcionales.uniprot_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [UniProtFakeResponse(self._uniprot_payload(gene)) for gene in genes]
            result = fetch_layer_external_source(
                layer_key="localization",
                workspace=workspace,
                filename="localization.csv",
                config=config,
                provider_name="uniprot_real",
            )
        self.assertEqual(result["source_name"], "uniprot_rest")
        self.assertEqual(result["status"], "api_real")
        self.assertGreaterEqual(float(result["confidence"]), 0.8)
        df = pd.read_csv(result["path"])
        self.assertIn("localization", df.columns)
        self.assertTrue(df["localization"].eq("outer_membrane").all())

    def test_literature_support_uses_curated_online_examples_catalog(self) -> None:
        workspace = self.make_workspace("layer_literature_catalog")
        (workspace / "results" / "organism_profile.json").write_text(
            json.dumps(
                {
                    "organism_canonical_name": "Pseudomonas aeruginosa",
                    "strain_canonical": "PAO1",
                    "taxon_id": "",
                }
            ),
            encoding="utf-8",
        )
        config = load_config(workspace / "config" / "params.yaml")
        result = fetch_layer_external_source(
            layer_key="literature_support",
            workspace=workspace,
            filename="literature_support.csv",
            config=config,
            provider_name="curated_online_examples",
        )
        self.assertEqual(result["source_name"], "curated_online_literature_catalog")
        self.assertEqual(result["status"], "curated_literature_catalog_materialized")
        self.assertGreaterEqual(float(result["confidence"]), 0.9)
        df = pd.read_csv(result["path"])
        self.assertIn("pubmed_id", df.columns)
        self.assertIn("curated_online_match_status", df.columns)
        self.assertIn("PA0008", set(df["protein_id"]))
        lasb = df.loc[df["gene"].str.lower().eq("lasb")].iloc[0]
        self.assertEqual(str(lasb["catalog_protein_id"]), "PA3724")
        self.assertEqual(str(lasb["evidence_source_type"]), "literature_curated")

    def test_required_layers_can_use_curated_online_examples_catalog(self) -> None:
        workspace = self.make_workspace("layer_required_catalog")
        (workspace / "results" / "organism_profile.json").write_text(
            json.dumps(
                {
                    "organism_canonical_name": "Pseudomonas aeruginosa",
                    "strain_canonical": "PAO1",
                    "taxon_id": "",
                }
            ),
            encoding="utf-8",
        )
        config = load_config(workspace / "config" / "params.yaml")
        result = fetch_layer_external_source(
            layer_key="virulence",
            workspace=workspace,
            filename="virulence.csv",
            config=config,
            provider_name="curated_online_examples",
        )
        self.assertEqual(result["source_name"], "curated_online_virulence_catalog")
        self.assertEqual(result["status"], "curated_virulence_catalog_materialized")
        df = pd.read_csv(result["path"])
        self.assertIn("curated_online_match_status", df.columns)
        self.assertIn("PA0008", set(df["protein_id"]))
        self.assertEqual(str(df.loc[df["protein_id"].eq("PA0008"), "database"].iloc[0]), "curated_online_pubmed_ncbi_v1")

    def test_functional_network_layer_uses_string_provider(self) -> None:
        workspace = self.make_workspace("layer_string")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.string_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [
                StringFakeResponse(
                    [
                        {"queryItem": "PA0001", "stringId": "287.PA0001", "preferredName": "gyrB"},
                        {"queryItem": "PA0002", "stringId": "287.PA0002", "preferredName": "rpoB"},
                    ]
                    + [
                        {"queryItem": f"PA000{i}", "stringId": f"287.PA000{i}", "preferredName": f"gene{i}"}
                        for i in range(3, 10)
                    ]
                    + [{"queryItem": "PA0010", "stringId": "287.PA0010", "preferredName": "pvdA"}]
                ),
                StringFakeResponse(
                    [
                        {"stringId_A": "287.PA0001", "stringId_B": "287.PA0002", "score": 0.91},
                        {"stringId_A": "287.PA0002", "stringId_B": "287.PA0003", "score": 0.88},
                    ]
                ),
            ]
            result = fetch_layer_external_source(
                layer_key="functional_network",
                workspace=workspace,
                filename="functional_network.csv",
                config=config,
                provider_name="string_real",
            )
        self.assertEqual(result["source_name"], "string_db")
        self.assertEqual(result["status"], "api_real")
        df = pd.read_csv(result["path"])
        self.assertIn("network_centrality", df.columns)
        self.assertEqual(len(df), 10)

    def test_functional_network_404_is_unresolved_provider_not_found(self) -> None:
        workspace = self.make_workspace("layer_string_404")
        config = load_config(workspace / "config" / "params.yaml")
        error = HTTPError("https://string-db.test", 404, "not found", {}, None)
        with patch("src.nodos_funcionales.online_sources.fetch_string_functional_network", side_effect=error):
            result = fetch_layer_external_source(
                layer_key="functional_network",
                workspace=workspace,
                filename="functional_network.csv",
                config=config,
                provider_name="string_real",
            )

        self.assertIsNone(result["path"])
        self.assertEqual(result["status"], "not_found")
        self.assertEqual(result["source_name"], "provider_not_found")
        self.assertEqual(result["source_database"], "provider_not_found")
        self.assertEqual(result["evidence"], "unresolved")
        self.assertEqual(float(result["confidence"]), 0.0)

    def test_essentiality_layer_uses_deg_provider(self) -> None:
        workspace = self.make_workspace("layer_deg")
        config = load_config(workspace / "config" / "params.yaml")
        payload = {"results": [{"protein_id": "PA0001", "gene": "gyrB", "evidence": "TnSeq"}]}
        with patch("src.nodos_funcionales.deg_api.urlopen", return_value=StringFakeResponse(payload)):
            result = fetch_layer_external_source(
                layer_key="essentiality",
                workspace=workspace,
                filename="essentiality.csv",
                config=config,
                provider_name="deg_real",
            )
        self.assertEqual(result["source_name"], "deg_database")
        self.assertEqual(result["status"], "api_real")
        df = pd.read_csv(result["path"])
        self.assertEqual(list(df.columns), ["protein_id", "gene", "essential", "evidence", "database"])
        self.assertTrue(df["essential"].isin([0, 1]).all())

    def test_virulence_layer_uses_vfdb_provider(self) -> None:
        workspace = self.make_workspace("layer_vfdb")
        config = load_config(workspace / "config" / "params.yaml")
        payload = {"results": [{"protein_id": "PA0008", "gene": "lasB", "category": "toxin"}]}
        with patch("src.nodos_funcionales.vfdb_api.urlopen", return_value=StringFakeResponse(payload)):
            result = fetch_layer_external_source(
                layer_key="virulence",
                workspace=workspace,
                filename="virulence.csv",
                config=config,
                provider_name="vfdb_real",
            )
        self.assertEqual(result["source_name"], "vfdb_database")
        self.assertEqual(result["status"], "api_real")
        df = pd.read_csv(result["path"])
        self.assertEqual(list(df.columns), ["protein_id", "gene", "virulence_score", "virulence_factor", "database"])
        self.assertTrue(df["virulence_score"].between(0, 1).all())

    def test_strain_conservation_layer_uses_bvbrc_provider(self) -> None:
        workspace = self.make_workspace("layer_bvbrc")
        config = load_config(workspace / "config" / "params.yaml")
        payload = {
            "results": [
                {"patric_id": "PA0001", "gene": "gyrB", "pgfam_id": "PGF_1", "figfam_id": "FIG_1", "genome_id": "g1"},
                {"patric_id": "PA0001", "gene": "gyrB", "pgfam_id": "PGF_1", "figfam_id": "FIG_1", "genome_id": "g2"},
                {"patric_id": "PA0002", "gene": "rpoB", "pgfam_id": "PGF_2", "figfam_id": "FIG_2", "genome_id": "g1"},
            ]
        }
        with patch("src.nodos_funcionales.bvbrc_api.urlopen", return_value=StringFakeResponse(payload)):
            result = fetch_layer_external_source(
                layer_key="strain_conservation",
                workspace=workspace,
                filename="strain_conservation.csv",
                config=config,
                provider_name="bvbrc_real",
            )
        self.assertEqual(result["source_name"], "bvbrc_api")
        self.assertEqual(result["status"], "api_real")
        df = pd.read_csv(result["path"])
        self.assertEqual(
            list(df.columns),
            ["protein_id", "gene", "core_genome_presence", "strain_coverage_score", "allelic_conservation", "variant_burden", "database"],
        )
        self.assertTrue(df["core_genome_presence"].between(0, 1).all())

    def test_human_homologs_layer_uses_real_provider_with_stub_backfill(self) -> None:
        workspace = self.make_workspace("layer_homologs_real")
        config = load_config(workspace / "config" / "params.yaml")
        side_effect = []
        for gene in ["gyrB", "rpoB", "ftsZ", "murA", "fabI", "acpP", "oprD", "lasB", "algD", "pvdA"]:
            if gene == "gyrB":
                side_effect.append(UniProtFakeResponse(self._human_gene_payload(gene)))
            elif gene == "acpP":
                side_effect.append(UniProtFakeResponse(self._empty_human_lookup_payload()))
                side_effect.append(UniProtFakeResponse(self._empty_human_lookup_payload()))
            else:
                side_effect.append(UniProtFakeResponse(self._empty_human_lookup_payload()))
        with patch("src.nodos_funcionales.online_sources.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = side_effect
            result = fetch_layer_external_source(
                layer_key="human_homologs",
                workspace=workspace,
                filename="human_homologs.csv",
                config=config,
                provider_name="uniprot_human_gene_lookup",
            )
        self.assertEqual(result["source_name"], "uniprot_human_gene_lookup+configurable_stub")
        self.assertEqual(result["status"], "api_real_partial_with_stub_backfill")
        self.assertAlmostEqual(float(result["confidence"]), 0.55, places=2)
        df = pd.read_csv(result["path"])
        self.assertIn("human_homolog", df.columns)
        self.assertTrue(pd.isna(df.loc[df["protein_id"] == "PA0001", "human_homolog"].iloc[0]))
        self.assertIn("homology_lookup_status", df.columns)
        self.assertIn("homology_query_strategy", df.columns)
        self.assertIn("homology_evidence_tier", df.columns)
        self.assertIn("homology_confidence_score", df.columns)
        self.assertIn("homology_missing_flags", df.columns)
        self.assertEqual(
            df.loc[df["protein_id"] == "PA0001", "homology_query_strategy"].iloc[0],
            "human_gene_exact",
        )
        self.assertEqual(
            df.loc[df["protein_id"] == "PA0001", "homology_evidence_tier"].iloc[0],
            "name_match_unverified",
        )
        self.assertLess(
            float(df.loc[df["protein_id"] == "PA0001", "homology_confidence_score"].iloc[0]),
            float(df.loc[df["protein_id"] == "PA0002", "homology_confidence_score"].iloc[0]),
        )
        self.assertIn("human_uniprot_accession", df.columns)
        self.assertEqual(df.loc[df["protein_id"] == "PA0001", "human_uniprot_accession"].iloc[0], "HUMAN_gyrB")

    def test_human_homologs_layer_uses_protein_name_fallback_when_gene_lookup_is_empty(self) -> None:
        workspace = self.make_workspace("layer_homologs_protein_name")
        (workspace / "data_raw" / "uniprot_annotations.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,uniprot_protein_name",
                    "PA0002,rpoB,RNA polymerase beta subunit",
                ]
            ),
            encoding="utf-8",
        )
        config = load_config(workspace / "config" / "params.yaml")
        side_effect = []
        genes = ["gyrB", "rpoB", "ftsZ", "murA", "fabI", "acpP", "oprD", "lasB", "algD", "pvdA"]
        for gene in genes:
            side_effect.append(UniProtFakeResponse(self._empty_human_lookup_payload()))
            if gene == "rpoB":
                side_effect.append(
                    UniProtFakeResponse(
                        {
                            "results": [
                                {
                                    "primaryAccession": "HUMAN_POLR2B",
                                    "uniProtkbId": "RPB2_HUMAN",
                                    "entryType": "UniProtKB reviewed (Swiss-Prot)",
                                    "organism": {"scientificName": "Homo sapiens"},
                                    "genes": [{"geneName": {"value": "POLR2B"}}],
                                }
                            ]
                        }
                    )
                )
        with patch("src.nodos_funcionales.online_sources.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = side_effect
            result = fetch_layer_external_source(
                layer_key="human_homologs",
                workspace=workspace,
                filename="human_homologs.csv",
                config=config,
                provider_name="uniprot_human_gene_lookup",
            )
        self.assertEqual(result["source_name"], "uniprot_human_gene_lookup+configurable_stub")
        self.assertEqual(result["status"], "api_real_partial_with_stub_backfill")
        df = pd.read_csv(result["path"])
        row = df.loc[df["protein_id"] == "PA0002"].iloc[0]
        self.assertTrue(pd.isna(row["human_homolog"]))
        self.assertEqual(row["human_gene"], "POLR2B")
        self.assertEqual(row["homology_lookup_status"], "name_match_unverified")
        self.assertEqual(row["homology_query_strategy"], "human_protein_name")
        self.assertEqual(row["homology_evidence_tier"], "name_match_unverified")

    def test_human_homologs_layer_uses_curated_human_gene_to_fill_accession(self) -> None:
        workspace = self.make_workspace("layer_homologs_curated_gene")
        for filename in ["essentiality.csv", "virulence.csv", "localization.csv"]:
            (workspace / "data_raw" / filename).unlink(missing_ok=True)
        (workspace / "data_raw" / "human_homologs.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,human_homolog,evalue,human_gene,database",
                    "PA0001,gyrB,1,1.0e-40,TOP2A,curated_homology",
                    "PA0002,rpoB,0,1.0,none,curated_homology",
                ]
            ),
            encoding="utf-8",
        )
        config = load_config(workspace / "config" / "params.yaml")
        side_effect = [
            UniProtFakeResponse(self._empty_human_lookup_payload()),
            UniProtFakeResponse(
                {
                    "results": [
                        {
                            "primaryAccession": "HUMAN_TOP2A",
                            "uniProtkbId": "TOP2A_HUMAN",
                            "entryType": "UniProtKB reviewed (Swiss-Prot)",
                            "organism": {"scientificName": "Homo sapiens"},
                            "genes": [{"geneName": {"value": "TOP2A"}}],
                        }
                    ]
                }
            ),
            UniProtFakeResponse(self._empty_human_lookup_payload()),
        ]
        with patch("src.nodos_funcionales.online_sources.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = side_effect
            result = fetch_layer_external_source(
                layer_key="human_homologs",
                workspace=workspace,
                filename="human_homologs.csv",
                config=config,
                provider_name="uniprot_human_gene_lookup",
            )
        self.assertEqual(result["status"], "api_real_partial_with_stub_backfill")
        df = pd.read_csv(result["path"])
        row = df.loc[df["protein_id"] == "PA0001"].iloc[0]
        self.assertEqual(row["homology_query_strategy"], "human_curated_gene")
        self.assertEqual(row["human_gene"], "TOP2A")
        self.assertEqual(row["human_uniprot_accession"], "HUMAN_TOP2A")

    def test_human_homologs_layer_falls_back_to_stub_when_real_lookup_unavailable(self) -> None:
        workspace = self.make_workspace("layer_homologs_stub")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.online_sources.urlopen", side_effect=URLError("offline")):
            result = fetch_layer_external_source(
                layer_key="human_homologs",
                workspace=workspace,
                filename="human_homologs.csv",
                config=config,
                provider_name="uniprot_human_gene_lookup",
            )
        self.assertEqual(result["source_name"], "configurable_stub_human_homologs_v1")
        self.assertEqual(result["status"], "external_real_unavailable_fallback_stub")
        self.assertAlmostEqual(float(result["confidence"]), 0.40, places=2)
        df = pd.read_csv(result["path"])
        self.assertIn("human_homolog", df.columns)

    def test_human_homologs_layer_uses_local_orthology_before_uniprot_lookup(self) -> None:
        workspace = self.make_workspace("layer_homologs_local_orthology")
        (workspace / "data_external").mkdir(exist_ok=True)
        (workspace / "data_external" / "human_homologs_orthology.csv").write_text(
            "\n".join(
                [
                    (
                        "protein_id,gene,human_homolog,evalue,human_gene,orthology_method,"
                        "orthology_tool,orthology_version,orthology_reference,"
                        "orthology_query_coverage,orthology_subject_coverage,"
                        "orthology_percent_identity,orthology_bitscore,"
                        "orthology_confidence_score,orthology_evidence_note"
                    ),
                    (
                        "PA0001,gyrB,1,1.0e-45,TOP2A,reciprocal_best_hit,"
                        "DIAMOND,2.1.0,local_run_2026_05_02,"
                        "0.82,0.79,46.0,240.0,0.88,curated local orthology"
                    ),
                ]
            ),
            encoding="utf-8",
        )
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.online_sources.urlopen") as urlopen_mock:
            result = fetch_layer_external_source(
                layer_key="human_homologs",
                workspace=workspace,
                filename="human_homologs.csv",
                config=config,
                provider_name="uniprot_human_gene_lookup",
            )
        urlopen_mock.assert_not_called()
        self.assertEqual(result["source_name"], "local_reproducible_orthology")
        self.assertEqual(result["status"], "local_orthology_file_materialized")
        self.assertAlmostEqual(float(result["confidence"]), 0.82, places=2)
        df = pd.read_csv(result["path"])
        row = df.loc[df["protein_id"] == "PA0001"].iloc[0]
        self.assertEqual(int(row["human_homolog"]), 1)
        self.assertEqual(row["human_gene"], "TOP2A")
        self.assertEqual(row["homology_lookup_status"], "local_orthology_match")
        self.assertEqual(row["homology_evidence_tier"], "local_reproducible_orthology")
        self.assertAlmostEqual(float(row["homology_confidence_score"]), 0.88, places=2)

    def test_host_annotation_layer_uses_controlled_homology_provider(self) -> None:
        workspace = self.make_workspace("layer_host_annotation")
        (workspace / "data_raw" / "human_homologs.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,human_homolog,evalue,human_gene,database,homology_lookup_status",
                    "PA0001,gyrB,1,1.0e-40,GYRB_HUMAN,computed_uniprot_human_gene_lookup_v1,real_match",
                    "PA0002,rpoB,0,,none,computed_uniprot_human_gene_lookup_v1,no_real_match",
                ]
            ),
            encoding="utf-8",
        )
        config = load_config(workspace / "config" / "params.yaml")
        result = fetch_layer_external_source(
            layer_key="host_annotation",
            workspace=workspace,
            filename="host_annotation.csv",
            config=config,
            provider_name="controlled_host_annotation_v1",
        )
        self.assertEqual(result["source_name"], "controlled_host_annotation_v1")
        self.assertEqual(result["status"], "controlled_provider_materialized")
        self.assertAlmostEqual(float(result["confidence"]), 0.58, places=2)
        df = pd.read_csv(result["path"])
        self.assertIn("domain_overlap_score", df.columns)
        self.assertIn("host_criticality_penalty", df.columns)
        self.assertIn("host_annotation_rule", df.columns)
        self.assertTrue(df["domain_overlap_score"].between(0, 1).all())
        self.assertTrue(df["host_criticality_penalty"].between(0, 1).all())
        by_protein = df.set_index("protein_id")
        self.assertGreater(
            float(by_protein.loc["PA0001", "domain_overlap_score"]),
            float(by_protein.loc["PA0002", "domain_overlap_score"]),
        )
        self.assertEqual(by_protein.loc["PA0001", "host_annotation_missing_flags"], "none")

    def test_host_annotation_layer_uses_interpro_provider_when_accessions_are_available(self) -> None:
        workspace = self.make_workspace("layer_host_annotation_interpro")
        (workspace / "data_raw" / "uniprot_annotations.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,uniprot_accession",
                    "PA0001,gyrB,BACT_GYRB",
                    "PA0002,rpoB,BACT_RPOB",
                ]
            ),
            encoding="utf-8",
        )
        (workspace / "data_raw" / "human_homologs.csv").write_text(
            "\n".join(
                [
                    "protein_id,gene,human_homolog,evalue,human_gene,database,human_uniprot_accession",
                    "PA0001,gyrB,1,1.0e-40,GYRB_HUMAN,computed_uniprot_human_gene_lookup_v1,HUMAN_GYRB",
                    "PA0002,rpoB,0,,none,computed_uniprot_human_gene_lookup_v1,",
                ]
            ),
            encoding="utf-8",
        )
        (workspace / "data_external").mkdir(exist_ok=True)
        (workspace / "data_external" / "human_essentiality.csv").write_text(
            "\n".join(
                [
                    "human_gene,human_essential,human_essentiality_score,database",
                    "GYRB_HUMAN,1,1.0,biosnap_test",
                ]
            ),
            encoding="utf-8",
        )
        config = load_config(workspace / "config" / "params.yaml")
        payloads = [
            {"results": [{"metadata": {"accession": "IPR000001"}}, {"metadata": {"accession": "IPR000002"}}]},
            {"results": []},
            {"results": [{"metadata": {"accession": "IPR000001"}}, {"metadata": {"accession": "IPR000003"}}]},
        ]
        with patch("src.nodos_funcionales.interpro_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [StringFakeResponse(payload) for payload in payloads]
            result = fetch_layer_external_source(
                layer_key="host_annotation",
                workspace=workspace,
                filename="host_annotation.csv",
                config=config,
                provider_name="interpro_domain_overlap",
            )
        self.assertEqual(result["source_name"], "interpro_api")
        self.assertEqual(result["status"], "api_real")
        self.assertAlmostEqual(float(result["confidence"]), 0.72, places=2)
        df = pd.read_csv(result["path"])
        by_protein = df.set_index("protein_id")
        self.assertEqual(by_protein.loc["PA0001", "interpro_rule"], "interpro_shared_domain_overlap_v1")
        self.assertAlmostEqual(float(by_protein.loc["PA0001", "domain_overlap_score"]), 1 / 3, places=4)
        self.assertAlmostEqual(float(by_protein.loc["PA0001", "host_criticality_penalty"]), 0.6, places=4)
        self.assertEqual(float(by_protein.loc["PA0001", "human_essentiality_score"]), 1.0)
        self.assertEqual(by_protein.loc["PA0001", "human_essentiality_status"], "matched")
        self.assertIn("IPR000001", by_protein.loc["PA0001", "interpro_shared_entries"])

    def test_controlled_therapeutic_provider_materializes_clinical_impact(self) -> None:
        workspace = self.make_workspace("layer_controlled_clinical")
        config = load_config(workspace / "config" / "params.yaml")
        result = fetch_layer_external_source(
            layer_key="clinical_impact",
            workspace=workspace,
            filename="clinical_impact.csv",
            config=config,
            provider_name="controlled_therapeutic_context_v1",
        )
        self.assertEqual(result["source_name"], "controlled_therapeutic_context_v1")
        self.assertEqual(result["status"], "controlled_provider_materialized")
        self.assertAlmostEqual(float(result["confidence"]), 0.62, places=2)
        df = pd.read_csv(result["path"])
        self.assertIn("host_damage_reduction_potential", df.columns)
        self.assertIn("disease_severity_association", df.columns)
        self.assertIn("clinical_impact_score", df.columns)
        self.assertIn("host_damage_score", df.columns)
        self.assertIn("controlled_context_rule", df.columns)
        self.assertIn("controlled_context_inputs", df.columns)
        self.assertIn("controlled_context_confidence_reason", df.columns)
        self.assertIn("controlled_context_missing_flags", df.columns)
        self.assertTrue(df["host_damage_score"].between(0, 1).all())
        self.assertTrue(df["database"].eq("computed_controlled_therapeutic_context_v1").all())
        row = df.loc[df["protein_id"] == "PA0008"].iloc[0]
        inputs = self._parse_controlled_inputs(row["controlled_context_inputs"])
        expected_damage = round(
            min(
                1.0,
                max(
                    0.0,
                    0.45 * (0.60 * inputs["virulence_score"] + 0.25 * inputs["virulence_factor"] + 0.15 * inputs["localization_access"])
                    + 0.35 * (0.75 * inputs["virulence_score"] + 0.25 * inputs["virulence_factor"])
                    + 0.20 * inputs["virulence_score"],
                ),
            ),
            4,
        )
        self.assertEqual(row["controlled_context_rule"], "clinical_impact_weighted_virulence_access_v1")
        self.assertAlmostEqual(float(row["host_damage_score"]), expected_damage, places=4)
        self.assertIn("confidence=0.62", row["controlled_context_confidence_reason"])
        self.assertEqual(row["controlled_context_missing_flags"], "none")

    def test_clinical_impact_uses_curated_organism_catalog_before_controlled_provider(self) -> None:
        workspace = self.make_workspace("layer_curated_clinical_catalog")
        catalog_dir = workspace / "data_external" / "curated_catalogs" / "clinical_impact"
        catalog_dir.mkdir(parents=True, exist_ok=True)
        (catalog_dir / "taxon_287.csv").write_text(
            "\n".join(
                [
                    (
                        "protein_id,gene,host_damage_reduction_potential,disease_severity_association,"
                        "clinical_impact_score,host_damage_score,host_direct_damage_score,"
                        "virulence_associated_severity_score,clinical_impact_evidence_type,"
                        "clinical_impact_evidence_reference,database"
                    ),
                    "PA0008,lasB,0.70,0.80,0.76,0.72,0.71,0.79,curated_literature,doi:10.example/impact,curated_clinical_impact_catalog_v1",
                ]
            ),
            encoding="utf-8",
        )
        config = load_config(workspace / "config" / "params.yaml")
        result = fetch_layer_external_source(
            layer_key="clinical_impact",
            workspace=workspace,
            filename="clinical_impact.csv",
            config=config,
            provider_name="controlled_therapeutic_context_v2",
        )
        self.assertEqual(result["source_name"], "curated_clinical_impact_catalog")
        self.assertEqual(result["status"], "curated_organism_catalog_materialized")
        self.assertAlmostEqual(float(result["confidence"]), 0.86, places=2)
        df = pd.read_csv(result["path"])
        self.assertIn("clinical_impact_catalog_source", df.columns)
        self.assertEqual(df.loc[0, "clinical_impact_evidence_reference"], "doi:10.example/impact")
        self.assertEqual(float(df.loc[0, "host_direct_damage_score"]), 0.71)

    def test_therapy_site_context_uses_curated_disease_site_catalog_before_controlled_provider(self) -> None:
        workspace = self.make_workspace("layer_curated_site_catalog")
        catalog_dir = workspace / "data_external" / "curated_catalogs" / "therapy_site_context"
        catalog_dir.mkdir(parents=True, exist_ok=True)
        (catalog_dir / "taxon_287.csv").write_text(
            "\n".join(
                [
                    (
                        "protein_id,gene,infection_site_access,infection_site,access_evidence_type,"
                        "access_evidence_reference,access_evidence_note,disease_context,syndrome,database"
                    ),
                    "PA0008,lasB,0.83,lung,curated_literature,doi:10.example/site,note,pneumonia,pneumonia,curated_disease_site_context_v1",
                ]
            ),
            encoding="utf-8",
        )
        config = load_config(workspace / "config" / "params.yaml")
        result = fetch_layer_external_source(
            layer_key="therapy_site_context",
            workspace=workspace,
            filename="therapy_site_context.csv",
            config=config,
            provider_name="controlled_therapeutic_context_v2",
        )
        self.assertEqual(result["source_name"], "curated_disease_site_context")
        self.assertEqual(result["status"], "curated_disease_site_context_materialized")
        self.assertAlmostEqual(float(result["confidence"]), 0.84, places=2)
        df = pd.read_csv(result["path"])
        self.assertIn("disease_site_context_source", df.columns)
        self.assertEqual(df.loc[0, "infection_site"], "lung")
        self.assertEqual(df.loc[0, "disease_context"], "pneumonia")

    def test_controlled_therapeutic_provider_materializes_disease_context(self) -> None:
        workspace = self.make_workspace("layer_controlled_disease")
        config = load_config(workspace / "config" / "params.yaml")
        result = fetch_layer_external_source(
            layer_key="curated_disease_context",
            workspace=workspace,
            filename="curated_disease_context.csv",
            config=config,
            provider_name="controlled_therapeutic_context_v1",
        )
        self.assertEqual(result["status"], "controlled_provider_materialized")
        df = pd.read_csv(result["path"])
        self.assertIn("infection_context_score", df.columns)
        self.assertIn("controlled_context_rule", df.columns)
        self.assertIn("controlled_context_inputs", df.columns)
        self.assertIn("controlled_context_confidence_reason", df.columns)
        self.assertIn("controlled_context_missing_flags", df.columns)
        self.assertTrue(df["infection_context_score"].between(0, 1).all())
        row = df.loc[df["protein_id"] == "PA0008"].iloc[0]
        inputs = self._parse_controlled_inputs(row["controlled_context_inputs"])
        expected_context = round(
            min(
                1.0,
                max(
                    0.0,
                    0.35 * inputs["host_damage_score"]
                    + 0.25 * inputs["infection_site_access"]
                    + 0.20 * inputs["functional_impact"]
                    + 0.20 * inputs["conservation"],
                ),
            ),
            4,
        )
        self.assertEqual(row["controlled_context_rule"], "disease_context_damage_access_function_conservation_v1")
        self.assertAlmostEqual(float(row["infection_context_score"]), expected_context, places=4)
        self.assertIn("default_network_network_centrality", row["controlled_context_missing_flags"])

    def test_controlled_therapeutic_provider_materializes_therapy_site_context(self) -> None:
        workspace = self.make_workspace("layer_controlled_site")
        config = load_config(workspace / "config" / "params.yaml")
        result = fetch_layer_external_source(
            layer_key="therapy_site_context",
            workspace=workspace,
            filename="therapy_site_context.csv",
            config=config,
            provider_name="controlled_therapeutic_context_v1",
        )
        self.assertEqual(result["status"], "controlled_provider_materialized")
        df = pd.read_csv(result["path"])
        self.assertIn("infection_site_access", df.columns)
        self.assertIn("controlled_context_rule", df.columns)
        self.assertIn("controlled_context_inputs", df.columns)
        self.assertIn("controlled_context_confidence_reason", df.columns)
        self.assertIn("controlled_context_missing_flags", df.columns)
        self.assertTrue(df["infection_site_access"].between(0, 1).all())
        row = df.loc[df["protein_id"] == "PA0008"].iloc[0]
        inputs = self._parse_controlled_inputs(row["controlled_context_inputs"])
        expected_access = round(0.85 * inputs["localization_access"] + 0.15 * inputs["virulence_score"], 4)
        self.assertEqual(row["controlled_context_rule"], "therapy_site_access_localization_weighted_v1")
        self.assertAlmostEqual(float(row["infection_site_access"]), expected_access, places=4)
        self.assertIn("confidence=0.62", row["controlled_context_confidence_reason"])

    def test_controlled_therapeutic_provider_v2_materializes_distinct_layer_rules(self) -> None:
        workspace = self.make_workspace("layer_controlled_v2")
        config = load_config(workspace / "config" / "params.yaml")
        expected_rules = {
            "clinical_impact": "clinical_impact_host_damage_virulence_v2",
            "curated_disease_context": "disease_context_function_conservation_infection_v2",
            "therapy_site_context": "therapy_site_access_localization_barrier_v2",
        }
        expected_score_columns = {
            "clinical_impact": "host_damage_score",
            "curated_disease_context": "infection_context_score",
            "therapy_site_context": "infection_site_access",
        }
        for layer_key, expected_rule in expected_rules.items():
            result = fetch_layer_external_source(
                layer_key=layer_key,
                workspace=workspace,
                filename={
                    "clinical_impact": "clinical_impact.csv",
                    "curated_disease_context": "curated_disease_context.csv",
                    "therapy_site_context": "therapy_site_context.csv",
                }[layer_key],
                config=config,
                provider_name="controlled_therapeutic_context_v2",
            )
            self.assertEqual(result["source_name"], "controlled_therapeutic_context_v2")
            self.assertEqual(result["status"], "controlled_provider_materialized")
            self.assertAlmostEqual(float(result["confidence"]), 0.66, places=2)
            df = pd.read_csv(result["path"])
            self.assertTrue(df["database"].eq("computed_controlled_therapeutic_context_v2").all())
            self.assertTrue(df["controlled_context_rule"].eq(expected_rule).all())
            self.assertTrue(df[expected_score_columns[layer_key]].between(0, 1).all())
            self.assertTrue(df["controlled_context_confidence_reason"].str.contains("semantic_v2").all())

    def test_controlled_therapeutic_provider_v2_differs_from_v1_for_site_access(self) -> None:
        workspace = self.make_workspace("layer_controlled_compare")
        config = load_config(workspace / "config" / "params.yaml")
        v1 = fetch_layer_external_source(
            layer_key="therapy_site_context",
            workspace=workspace,
            filename="therapy_site_context_v1.csv",
            config=config,
            provider_name="controlled_therapeutic_context_v1",
        )
        v2 = fetch_layer_external_source(
            layer_key="therapy_site_context",
            workspace=workspace,
            filename="therapy_site_context_v2.csv",
            config=config,
            provider_name="controlled_therapeutic_context_v2",
        )
        v1_df = pd.read_csv(v1["path"]).set_index("protein_id")
        v2_df = pd.read_csv(v2["path"]).set_index("protein_id")
        self.assertNotEqual(
            float(v1_df.loc["PA0008", "infection_site_access"]),
            float(v2_df.loc["PA0008", "infection_site_access"]),
        )
        self.assertEqual(
            v2_df.loc["PA0008", "controlled_context_rule"],
            "therapy_site_access_localization_barrier_v2",
        )


if __name__ == "__main__":
    unittest.main()
