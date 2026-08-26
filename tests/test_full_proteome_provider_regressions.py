from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import pandas as pd
import pytest

from src.nodos_funcionales.bvbrc_api import (
    _candidate_gene_batches,
    _candidate_genes,
    fetch_bvbrc_strain_conservation,
)
from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.interpro_api import fetch_interpro_host_annotation
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.online


class FakeResponse:
    def __init__(self, payload, content_type: str = "application/json", content_range: str = ""):
        self._payload = payload
        self._content_type = content_type
        self.headers = {"Content-Type": content_type}
        if content_range:
            self.headers["Content-Range"] = content_range
        self.status = 200

    def read(self) -> bytes:
        if isinstance(self._payload, str):
            return self._payload.encode("utf-8")
        return json.dumps(self._payload).encode("utf-8")

    def getheader(self, name: str, default: str = "") -> str:
        return self.headers.get(name, self.headers.get(name.title(), default))

    def geturl(self) -> str:
        return "https://example.test/provider"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None


def _workspace(name: str) -> Path:
    root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "data_raw").mkdir(parents=True, exist_ok=True)
    (root / "data_external").mkdir(parents=True, exist_ok=True)
    (root / "results").mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", root / "config" / "params.yaml")
    return root


def test_bvbrc_candidate_gene_limit_is_batch_size_not_coverage_limit() -> None:
    config = load_config(PROJECT_ROOT / "config" / "params.yaml")
    cfg = config["online_sources"]["bvbrc"]
    proteins = pd.DataFrame(
        [{"protein_id": f"P{i:04d}", "gene": f"gene{i:04d}"} for i in range(123)]
    )

    genes = _candidate_genes(proteins, cfg)
    batches = _candidate_gene_batches(proteins, cfg)

    assert len(genes) == 123
    assert len(batches) == 3
    assert [len(batch) for batch in batches] == [50, 50, 23]
    assert [gene for batch in batches for gene in batch] == genes


def test_bvbrc_manifest_reports_complete_multi_batch_coverage() -> None:
    workspace = _workspace("bvbrc_full_coverage")
    try:
        candidate_rows = [
            {"protein_id": f"P{i:04d}", "gene": f"gene{i:04d}"}
            for i in range(60)
        ]
        pd.DataFrame(candidate_rows).to_csv(workspace / "data_raw" / "essentiality.csv", index=False)
        config = load_config(workspace / "config" / "params.yaml")
        genome_payload = [{"genome_id": "g1"}, {"genome_id": "g2"}]
        first_batch = [
            {"gene": row["gene"], "pgfam_id": "PGF", "genome_id": "g1"}
            for row in candidate_rows[:50]
        ]
        second_batch = [
            {"gene": row["gene"], "pgfam_id": "PGF", "genome_id": "g1"}
            for row in candidate_rows[50:]
        ]
        with patch(
            "src.nodos_funcionales.bvbrc_api.urlopen",
            side_effect=[
                FakeResponse(genome_payload),
                FakeResponse(first_batch),
                FakeResponse(second_batch),
            ],
        ):
            result = fetch_bvbrc_strain_conservation(
                workspace,
                "Escherichia coli K-12 MG1655",
                "511145",
                config,
                "online_optional",
                no_write_cache=True,
            )

        manifest = result["manifest"]
        assert manifest["query_complete"] is True
        assert manifest["candidate_gene_count"] == 60
        assert manifest["feature_batches_total"] == 2
        assert manifest["feature_batches_completed"] == 2
        assert manifest["protein_count_mapped"] == 60
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_interpro_partial_success_is_not_reclassified_as_total_failure() -> None:
    workspace = _workspace("interpro_partial")
    try:
        (workspace / "data_raw" / "uniprot_annotations.csv").write_text(
            "protein_id,gene,uniprot_accession\n"
            "P1,gyrA,BACT1\n",
            encoding="utf-8",
        )
        (workspace / "data_raw" / "human_homologs.csv").write_text(
            "protein_id,gene,human_homolog,evalue,human_gene,database,human_uniprot_accession\n"
            "P1,gyrA,1,1e-20,HGENE,test,HUMAN1\n",
            encoding="utf-8",
        )
        (workspace / "data_external" / "human_essentiality.csv").write_text(
            "human_gene,human_essential,human_essentiality_score,database\n"
            "HGENE,1,1.0,test\n",
            encoding="utf-8",
        )
        config = load_config(workspace / "config" / "params.yaml")
        success_payload = {"results": [{"metadata": {"accession": "IPR000001"}}]}

        with patch(
            "src.nodos_funcionales.interpro_api.urlopen",
            side_effect=[FakeResponse(success_payload), URLError("temporary outage")],
        ):
            result = fetch_interpro_host_annotation(
                workspace,
                "Escherichia coli K-12 MG1655",
                "511145",
                config,
                "online_optional",
                no_write_cache=True,
            )

        manifest = result["manifest"]
        assert manifest["api_success"] is True
        assert manifest["api_complete"] is False
        assert manifest["provider_success"] is True
        assert manifest["accessions_succeeded"] == 1
        assert manifest["accessions_failed"] == 1
        assert manifest["retrieval_status"] == "connected_structured_payload_partial"
        assert manifest["source_used"] == "api_real_partial"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
