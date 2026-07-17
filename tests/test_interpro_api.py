from __future__ import annotations

import json
import shutil
import ssl
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.interpro_api import fetch_interpro_host_annotation
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.online


class FakeResponse:
    def __init__(self, payload, content_type: str = "application/json"):
        self._payload = payload
        self._content_type = content_type
        self.status = 200

    def read(self) -> bytes:
        if isinstance(self._payload, str):
            return self._payload.encode("utf-8")
        return json.dumps(self._payload).encode("utf-8")

    def getheader(self, name: str, default: str = "") -> str:
        return self._content_type if name.lower() == "content-type" else default

    def geturl(self) -> str:
        return "https://www.ebi.ac.uk/interpro/api/mock"

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class InterProApiTests(unittest.TestCase):
    def make_workspace(self, name: str, with_accessions: bool = True) -> Path:
        root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "data_raw").mkdir(parents=True, exist_ok=True)
        (root / "data_external").mkdir(parents=True, exist_ok=True)
        (root / "results").mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", root / "config" / "params.yaml")
        bacterial_accession = "BACT_GYRB" if with_accessions else ""
        human_accession = "HUMAN_GYRB" if with_accessions else ""
        (root / "data_raw" / "uniprot_annotations.csv").write_text(
            "protein_id,gene,uniprot_accession\n"
            f"PA0001,gyrB,{bacterial_accession}\n",
            encoding="utf-8",
        )
        (root / "data_raw" / "human_homologs.csv").write_text(
            "protein_id,gene,human_homolog,evalue,human_gene,database,human_uniprot_accession\n"
            f"PA0001,gyrB,1,1.0e-40,GYRB_HUMAN,computed_uniprot_human_gene_lookup_v1,{human_accession}\n",
            encoding="utf-8",
        )
        (root / "data_external" / "human_essentiality.csv").write_text(
            "human_gene,human_essential,human_essentiality_score,database\n"
            "GYRB_HUMAN,1,1.0,biosnap_test\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def test_structured_json_payload_materializes_domain_overlap(self) -> None:
        workspace = self.make_workspace("interpro_success")
        config = load_config(workspace / "config" / "params.yaml")
        payloads = [
            {"results": [{"metadata": {"accession": "IPR000001"}}]},
            {"results": [{"metadata": {"accession": "IPR000001"}}, {"metadata": {"accession": "IPR000002"}}]},
        ]
        with patch("src.nodos_funcionales.interpro_api.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [FakeResponse(payload) for payload in payloads]
            result = fetch_interpro_host_annotation(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        self.assertEqual(result["manifest"]["retrieval_status"], "connected_structured_payload")
        self.assertTrue(result["manifest"]["api_success"])
        self.assertFalse(result["manifest"]["blocks_ranking"])
        self.assertFalse(result["manifest"]["affects_score"])
        self.assertGreater(result["manifest"]["paired_domain_rows"], 0)

    def test_ssl_error_is_conservative_non_blocking_status(self) -> None:
        workspace = self.make_workspace("interpro_ssl")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.interpro_api.urlopen", side_effect=ssl.SSLError("OPENSSL_Applink")):
            result = fetch_interpro_host_annotation(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        self.assertEqual(result["manifest"]["retrieval_status"], "ssl_error")
        self.assertFalse(result["manifest"]["api_success"])
        self.assertFalse(result["manifest"]["evidence_inferred"])
        self.assertFalse(result["manifest"]["blocks_ranking"])
        self.assertFalse(result["manifest"]["affects_score"])

    def test_network_error_is_conservative_non_blocking_status(self) -> None:
        workspace = self.make_workspace("interpro_network")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.interpro_api.urlopen", side_effect=URLError("offline")):
            result = fetch_interpro_host_annotation(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        self.assertEqual(result["manifest"]["retrieval_status"], "network_error")
        self.assertFalse(result["manifest"]["api_success"])
        self.assertFalse(result["manifest"]["evidence_inferred"])

    def test_unexpected_payload_is_not_domain_evidence(self) -> None:
        workspace = self.make_workspace("interpro_invalid")
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.interpro_api.urlopen", return_value=FakeResponse("free text", "text/plain")):
            result = fetch_interpro_host_annotation(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        self.assertEqual(result["manifest"]["retrieval_status"], "invalid_payload")
        self.assertFalse(result["manifest"]["api_success"])
        self.assertFalse(result["manifest"]["evidence_inferred"])

    def test_missing_accessions_do_not_call_network_or_block_ranking(self) -> None:
        workspace = self.make_workspace("interpro_no_accessions", with_accessions=False)
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.interpro_api.urlopen") as urlopen_mock:
            result = fetch_interpro_host_annotation(workspace, "Pseudomonas aeruginosa", "287", config, "online_optional")
        urlopen_mock.assert_not_called()
        self.assertEqual(result["manifest"]["retrieval_status"], "unresolved")
        self.assertFalse(result["manifest"]["api_attempted"])
        self.assertFalse(result["manifest"]["blocks_ranking"])


if __name__ == "__main__":
    unittest.main()
