from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError

from src.nodos_funcionales.full_provider_integration import (
    NON_BLOCKING_NOTE,
    PROVIDER_STATUSES,
    normalize_online_provider_response,
    resolve_human_essentiality_provider,
    resolve_local_dataset_provider,
    resolve_online_provider,
    run_full_provider_integration_audit,
)
from src.nodos_funcionales.provider_response_audit import ProviderResponse


class FakeHTTPResponse:
    def __init__(self, raw: bytes, content_type: str = "application/json", status: int = 200) -> None:
        self._raw = raw
        self.headers = {"Content-Type": content_type}
        self.status = status
        self.url = "https://provider.example/test"

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._raw


def _opener(raw: bytes, content_type: str = "application/json"):
    def open_response(*args: object, **kwargs: object) -> FakeHTTPResponse:
        return FakeHTTPResponse(raw, content_type)

    return open_response


def test_online_json_structured_payload_becomes_connected_structured() -> None:
    row = resolve_online_provider("uniprot", opener=_opener(b'{"results":[{"id":"P0A"}]}'))

    assert row["provider_status"] == "connected_structured"
    assert row["payload_type"] == "json"
    assert row["structured"] is True
    assert row["evidence_items_count"] == 1
    assert row["affects_score"] is False


def test_online_valid_empty_payload_becomes_connected_empty() -> None:
    row = resolve_online_provider("uniprot", opener=_opener(b'{"results":[]}'))

    assert row["provider_status"] == "connected_empty"
    assert row["structured"] is True
    assert row["evidence_items_count"] == 0
    assert row["affects_score"] is False


def test_online_html_payload_becomes_unsupported_payload() -> None:
    row = resolve_online_provider("uniprot", opener=_opener(b"<html><body>portal</body></html>", "text/html"))

    assert row["provider_status"] == "unsupported_payload"
    assert row["payload_type"] == "html"
    assert row["error_category"] == "html_instead_of_structured_payload"
    assert row["affects_score"] is False


def test_online_network_failure_becomes_unavailable() -> None:
    def failing_opener(*args: object, **kwargs: object) -> FakeHTTPResponse:
        raise URLError("temporary DNS failure")

    row = resolve_online_provider("uniprot", opener=failing_opener)

    assert row["provider_status"] == "unavailable"
    assert row["error_category"] == "unresolved"
    assert "temporary DNS failure" in row["error_message_sanitized"]
    assert row["affects_score"] is False


def test_online_404_can_be_recorded_as_deprecated_or_changed() -> None:
    response = ProviderResponse(
        payload=None,
        url="https://provider.example/old",
        http_status=404,
        content_type="text/plain",
        payload_type="empty",
        rejection_reason="HTTP 404",
        error_status="not_found",
    )
    row = normalize_online_provider_response("interpro", response)

    assert row["provider_status"] == "deprecated_or_changed"
    assert row["affects_score"] is False


def test_vfdb_and_deg_missing_local_datasets_are_non_blocking(tmp_path: Path) -> None:
    vfdb = resolve_local_dataset_provider("vfdb", tmp_path)
    deg = resolve_local_dataset_provider("deg", tmp_path)

    assert vfdb["provider_status"] == "local_dataset_missing"
    assert deg["provider_status"] == "local_dataset_missing"
    assert vfdb["affects_score"] is False
    assert deg["affects_score"] is False


def test_vfdb_and_deg_available_local_datasets_include_checksum_and_version(tmp_path: Path) -> None:
    data_dir = tmp_path / "data_external"
    data_dir.mkdir()
    vfdb_path = data_dir / "vfdb.csv"
    deg_path = data_dir / "deg.csv"
    vfdb_path.write_text("gene,virulence_factor\nlasB,1\n", encoding="utf-8")
    deg_path.write_text("gene,essentiality_status\nftsZ,essential\n", encoding="utf-8")
    (data_dir / "vfdb.version.txt").write_text("VFDB local test fixture", encoding="utf-8")
    (data_dir / "deg.version.txt").write_text("DEG local test fixture", encoding="utf-8")

    vfdb = resolve_local_dataset_provider("vfdb", tmp_path)
    deg = resolve_local_dataset_provider("deg", tmp_path)

    assert vfdb["provider_status"] == "local_dataset_available"
    assert deg["provider_status"] == "local_dataset_available"
    assert vfdb["checksum_sha256"]
    assert deg["checksum_sha256"]
    assert vfdb["dataset_version"] == "VFDB local test fixture"
    assert deg["dataset_version"] == "DEG local test fixture"
    assert vfdb["evidence_items_count"] == 1
    assert deg["evidence_items_count"] == 1


def test_human_essentiality_is_skipped_for_bacteria() -> None:
    row = resolve_human_essentiality_provider(organism_domain="bacteria")

    assert row["provider_status"] == "skipped_not_applicable"
    assert row["provider_mode"] == "optional"
    assert row["affects_score"] is False


def test_full_provider_audit_runner_writes_manifest_and_never_blocks(tmp_path: Path) -> None:
    result = run_full_provider_integration_audit(
        tmp_path,
        tmp_path / "review",
        opener=_opener(b'{"results":[]}'),
        organism_domain="bacteria",
    )
    manifest_path = tmp_path / "review" / "full_provider_integration_manifest.json"
    review_path = tmp_path / "review" / "FULL_PROVIDER_INTEGRATION_REVIEW.md"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["blocking_failures"] == 0
    assert manifest["affects_score"] is False
    assert manifest["note"] == NON_BLOCKING_NOTE
    assert NON_BLOCKING_NOTE in review_path.read_text(encoding="utf-8")
    assert all(row["affects_score"] is False for row in result["rows"])
    assert {row["provider_key"] for row in result["rows"]} == {
        "uniprot",
        "string",
        "interpro",
        "bvbrc",
        "europe_pmc",
        "taxonomy",
        "vfdb",
        "deg",
        "human_essentiality",
    }
    assert {row["provider_status"] for row in result["rows"]} <= PROVIDER_STATUSES
