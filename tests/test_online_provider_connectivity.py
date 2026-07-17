from __future__ import annotations

import json
from urllib.error import HTTPError

from src.nodos_funcionales.online_provider_connectivity import (
    CONSERVATIVE_WARNING,
    check_provider_connectivity,
    run_provider_connectivity_audit,
)


def test_success_empty_timeout_schema_http_and_skipped_are_normalized(tmp_path) -> None:
    success = check_provider_connectivity("UniProt", "Escherichia coli", 562, requester=lambda *a, **k: {"results": [{}]})
    empty = check_provider_connectivity("Europe PMC", "Escherichia coli", 562, requester=lambda *a, **k: {"resultList": {"result": []}})
    timeout = check_provider_connectivity("STRING", "Escherichia coli", 562, requester=lambda *a, **k: (_ for _ in ()).throw(TimeoutError("late")))
    schema = check_provider_connectivity("InterPro", "Escherichia coli", 562, requester=lambda *a, **k: "unexpected")
    http = check_provider_connectivity("VFDB", "Escherichia coli", 562, requester=lambda *a, **k: (_ for _ in ()).throw(HTTPError("u", 503, "down", {}, None)))
    skipped = check_provider_connectivity("DEG", "Escherichia coli", 562, enabled=False)

    assert [success["status"], empty["status"], timeout["status"], schema["status"], http["status"], skipped["status"]] == [
        "success", "no_results", "timeout", "schema_error", "http_error", "skipped"
    ]
    assert all(row["blocking"] is False for row in (success, empty, timeout, schema, http, skipped))
    assert len(http["error_message"]) <= 300

    result = run_provider_connectivity_audit(
        [{"organism_label": "Escherichia coli", "taxon_id": 562}], tmp_path,
        requester=lambda *a, **k: {"results": []}, provider_names=["UniProt"],
    )
    assert result["manifest"]["phase"].startswith("7C")
    assert CONSERVATIVE_WARNING in (tmp_path / "ONLINE_ONLY_PROVIDER_CONNECTIVITY_REVIEW.md").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "provider_connectivity_matrix.json").read_text(encoding="utf-8"))[0]["status"] == "no_results"
