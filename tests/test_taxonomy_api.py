from __future__ import annotations

import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.taxonomy_api import query_ncbi_taxonomy
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.online


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class TaxonomyApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(PROJECT_ROOT / "config" / "params.yaml")

    @patch("src.nodos_funcionales.taxonomy_api.urlopen")
    def test_query_ncbi_taxonomy_success(self, urlopen_mock) -> None:
        urlopen_mock.side_effect = [
            FakeResponse({"esearchresult": {"idlist": ["287"]}}),
            FakeResponse(
                {
                    "result": {
                        "uids": ["287"],
                        "287": {
                            "uid": "287",
                            "scientificname": "Pseudomonas aeruginosa",
                            "rank": "species",
                        },
                    }
                }
            ),
        ]
        result = query_ncbi_taxonomy("Pseudomonas aeruginosa", "PAO1", self.config)
        self.assertEqual(result["status"], "online_exact_name_match")
        self.assertEqual(result["taxon_id"], "287")
        self.assertEqual(result["rank"], "species")

    @patch("src.nodos_funcionales.taxonomy_api.urlopen")
    def test_query_ncbi_taxonomy_network_error(self, urlopen_mock) -> None:
        urlopen_mock.side_effect = URLError("network unreachable")
        result = query_ncbi_taxonomy("Corynebacterium pseudotuberculosis", None, self.config)
        self.assertEqual(result["status"], "online_no_match")
        self.assertIn("Network error", " ".join(result["api_error_notes"]))


if __name__ == "__main__":
    unittest.main()
