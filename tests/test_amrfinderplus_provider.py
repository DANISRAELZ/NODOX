from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.nodos_funcionales.amrfinderplus_provider import (
    fetch_amrfinderplus_point_mutation_evidence,
)
from tests.helpers import PROJECT_ROOT


class FakeResponse:
    def __init__(self, payload: str, content_type: str = "text/plain") -> None:
        self._payload = payload
        self.headers = {"Content-Type": content_type}
        self.status = 200

    def read(self) -> bytes:
        return self._payload.encode("utf-8")

    def getheader(self, name: str, default: str = "") -> str:
        return self.headers.get(name, self.headers.get(name.title(), default))

    def geturl(self) -> str:
        return "https://example.test/amrfinderplus"

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


CATALOG_HEADER = "\t".join(
    [
        "allele",
        "gene_family",
        "whitelisted_taxa",
        "scope",
        "type",
        "subtype",
        "class",
        "subclass",
        "PubMed_reference",
        "db_version",
        "RefSeq_protein_accession",
    ]
)


def catalog_text(*rows: list[str]) -> str:
    return "\n".join([CATALOG_HEADER, *("\t".join(row) for row in rows)]) + "\n"


POINT_GYRA = [
    "gyrA_S84L",
    "gyrA",
    "Staphylococcus_aureus",
    "core",
    "AMR",
    "POINT",
    "QUINOLONE",
    "FLUOROQUINOLONE",
    "12345678",
    "2026-01-15.1",
    "WP_000000001.1",
]

POINT_GRLA = [
    "grlA_S80F",
    "grlA",
    "Staphylococcus_aureus",
    "core",
    "AMR",
    "POINT",
    "QUINOLONE",
    "FLUOROQUINOLONE",
    "23456789",
    "2026-01-15.1",
    "WP_000000002.1",
]

NON_POINT = [
    "blaZ",
    "blaZ",
    "",
    "core",
    "AMR",
    "ALLELE",
    "BETA-LACTAM",
    "PENICILLIN",
    "34567890",
    "2026-01-15.1",
    "WP_000000003.1",
]

OTHER_ORGANISM = [
    "gyrA_S83L",
    "gyrA",
    "Escherichia",
    "core",
    "AMR",
    "POINT",
    "QUINOLONE",
    "FLUOROQUINOLONE",
    "45678901",
    "2026-01-15.1",
    "WP_000000004.1",
]


class AmrFinderPlusProviderTests(unittest.TestCase):
    def make_workspace(self, genes: list[str]) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"amrfinder_stage4d_{uuid.uuid4().hex[:8]}"
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "data_raw").mkdir(parents=True, exist_ok=True)
        (root / "results").mkdir(parents=True, exist_ok=True)
        rows = ["protein_id,gene,essential,evidence,database"]
        for idx, gene in enumerate(genes, start=1):
            rows.append(f"P{idx:04d},{gene},1,test,test")
        (root / "data_raw" / "essentiality.csv").write_text(
            "\n".join(rows) + "\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def config(self) -> dict:
        return {"online_sources": {"amrfinderplus": {}}}

    def test_positive_point_mutation_match_produces_one_explicit_candidate_signal(self) -> None:
        workspace = self.make_workspace(["gyrA", "murA"])
        catalog = catalog_text(POINT_GYRA, NON_POINT, OTHER_ORGANISM)
        with patch(
            "src.nodos_funcionales.amrfinderplus_provider.urlopen",
            side_effect=[
                FakeResponse("2026-01-15.1\n"),
                FakeResponse(catalog, "text/tab-separated-values"),
            ],
        ):
            result = fetch_amrfinderplus_point_mutation_evidence(
                workspace,
                "Staphylococcus aureus",
                "1280",
                self.config(),
                "online_optional",
            )

        data = result["evolutionary_escape_risk_data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data.iloc[0]["gene"], "gyrA")
        self.assertEqual(float(data.iloc[0]["resistance_emergence_risk"]), 1.0)
        self.assertEqual(data.iloc[0]["amrfinder_mapping_status"], "exact_gene_and_taxon")
        self.assertEqual(data.iloc[0]["amrfinder_evidence_status"], "observed")
        self.assertEqual(
            data.iloc[0]["amrfinder_independence_group"],
            "ncbi_amrfinderplus_curated_point_mutations",
        )
        self.assertEqual(data.iloc[0]["amrfinder_mutation_symbols"], "gyrA_S84L")
        self.assertEqual(int(data.iloc[0]["amrfinder_mutation_count"]), 1)
        self.assertEqual(len(data.iloc[0]["amrfinder_catalog_sha256"]), 64)
        self.assertEqual(result["manifest"]["retrieval_status"], "api_real")
        self.assertTrue(result["manifest"]["affects_score"])

    def test_unmatched_candidate_is_omitted_never_encoded_as_zero(self) -> None:
        workspace = self.make_workspace(["murA"])
        with patch(
            "src.nodos_funcionales.amrfinderplus_provider.urlopen",
            side_effect=[
                FakeResponse("2026-01-15.1\n"),
                FakeResponse(catalog_text(POINT_GYRA), "text/tab-separated-values"),
            ],
        ):
            result = fetch_amrfinderplus_point_mutation_evidence(
                workspace,
                "Staphylococcus aureus",
                "1280",
                self.config(),
                "online_optional",
            )

        self.assertTrue(result["evolutionary_escape_risk_data"].empty)
        self.assertEqual(result["manifest"]["retrieval_status"], "no_candidate_gene_matches")
        self.assertFalse(result["manifest"]["affects_score"])

    def test_other_organism_point_mutation_is_not_reused(self) -> None:
        workspace = self.make_workspace(["gyrA"])
        with patch(
            "src.nodos_funcionales.amrfinderplus_provider.urlopen",
            side_effect=[
                FakeResponse("2026-01-15.1\n"),
                FakeResponse(catalog_text(OTHER_ORGANISM), "text/tab-separated-values"),
            ],
        ):
            result = fetch_amrfinderplus_point_mutation_evidence(
                workspace,
                "Staphylococcus aureus",
                "1280",
                self.config(),
                "online_optional",
            )

        self.assertTrue(result["evolutionary_escape_risk_data"].empty)
        self.assertEqual(result["manifest"]["retrieval_status"], "organism_not_covered")

    def test_non_point_amr_rows_do_not_create_evolutionary_evidence(self) -> None:
        workspace = self.make_workspace(["blaZ"])
        with patch(
            "src.nodos_funcionales.amrfinderplus_provider.urlopen",
            side_effect=[
                FakeResponse("2026-01-15.1\n"),
                FakeResponse(catalog_text(NON_POINT), "text/tab-separated-values"),
            ],
        ):
            result = fetch_amrfinderplus_point_mutation_evidence(
                workspace,
                "Staphylococcus aureus",
                "1280",
                self.config(),
                "online_optional",
            )

        self.assertTrue(result["evolutionary_escape_risk_data"].empty)
        self.assertEqual(result["manifest"]["point_mutation_catalog_rows"], 0)

    def test_cache_reuse_preserves_original_evidence_provenance_without_network(self) -> None:
        workspace = self.make_workspace(["gyrA"])
        with patch(
            "src.nodos_funcionales.amrfinderplus_provider.urlopen",
            side_effect=[
                FakeResponse("2026-01-15.1\n"),
                FakeResponse(catalog_text(POINT_GYRA), "text/tab-separated-values"),
            ],
        ):
            first = fetch_amrfinderplus_point_mutation_evidence(
                workspace,
                "Staphylococcus aureus",
                "1280",
                self.config(),
                "cache_first",
            )

        original = first["evolutionary_escape_risk_data"].iloc[0]
        with patch("src.nodos_funcionales.amrfinderplus_provider.urlopen") as urlopen_mock:
            second = fetch_amrfinderplus_point_mutation_evidence(
                workspace,
                "Staphylococcus aureus",
                "1280",
                self.config(),
                "cache_first",
            )

        urlopen_mock.assert_not_called()
        cached = second["evolutionary_escape_risk_data"].iloc[0]
        self.assertEqual(second["manifest"]["source_used"], "cache")
        self.assertEqual(cached["amrfinder_retrieved_at"], original["amrfinder_retrieved_at"])
        self.assertEqual(cached["amrfinder_source_version"], original["amrfinder_source_version"])
        self.assertEqual(cached["amrfinder_catalog_sha256"], original["amrfinder_catalog_sha256"])
        self.assertEqual(cached["amrfinder_provider_source_used"], "api_real")

    def test_invalid_catalog_schema_fails_closed(self) -> None:
        workspace = self.make_workspace(["gyrA"])
        bad_catalog = "allele\tgene_family\nfoo\tgyrA\n"
        with patch(
            "src.nodos_funcionales.amrfinderplus_provider.urlopen",
            side_effect=[
                FakeResponse("2026-01-15.1\n"),
                FakeResponse(bad_catalog, "text/tab-separated-values"),
            ],
        ):
            result = fetch_amrfinderplus_point_mutation_evidence(
                workspace,
                "Staphylococcus aureus",
                "1280",
                self.config(),
                "online_optional",
            )

        self.assertTrue(result["evolutionary_escape_risk_data"].empty)
        self.assertEqual(result["manifest"]["retrieval_status"], "catalog_schema_invalid")
        self.assertFalse(result["manifest"]["affects_score"])

    def test_disabled_provider_does_not_call_network(self) -> None:
        workspace = self.make_workspace(["gyrA"])
        config = {"online_sources": {"amrfinderplus": {"enabled": False}}}
        with patch("src.nodos_funcionales.amrfinderplus_provider.urlopen") as urlopen_mock:
            result = fetch_amrfinderplus_point_mutation_evidence(
                workspace,
                "Staphylococcus aureus",
                "1280",
                config,
                "online_optional",
            )

        urlopen_mock.assert_not_called()
        self.assertTrue(result["evolutionary_escape_risk_data"].empty)
        self.assertEqual(result["manifest"]["retrieval_status"], "provider_disabled")


if __name__ == "__main__":
    unittest.main()
