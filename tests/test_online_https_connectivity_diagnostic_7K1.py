from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import scripts.diagnose_online_https_connectivity_7K1 as diagnostic
from tests.helpers import PROJECT_ROOT


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["python"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_classifies_success_ssl_and_network_errors() -> None:
    assert diagnostic.classify_probe_result(0, '{"ok": true}', "") == "success"
    assert diagnostic.classify_probe_result(1, "", "OPENSSL_Uplink: no OPENSSL_Applink") == "openssl_applink_error"
    assert diagnostic.classify_probe_result(1, "", "URLError: network unreachable") == "network_error"


def test_diagnostic_generates_json_csv_and_markdown_without_real_network(tmp_path: Path, monkeypatch) -> None:
    def fake_dns_rows():
        return [
            diagnostic._base_row("dns", "rest.uniprot.org", "", "success", "success", records=1),
        ]

    responses = iter(
        [
            _completed('{"ok": true, "http_status": 200, "content_type": "application/json", "bytes": 24}'),
            _completed("", "OPENSSL_Uplink: no OPENSSL_Applink", 1),
            _completed("", "URLError: network unreachable", 1),
        ]
        * 8
    )

    monkeypatch.setattr(diagnostic, "_dns_rows", fake_dns_rows)
    monkeypatch.setattr(diagnostic, "_run_python_probe", lambda code, url: next(responses))

    output_json = tmp_path / "diagnostic.json"
    output_csv = tmp_path / "diagnostic.csv"
    output_md = tmp_path / "diagnostic.md"
    payload = diagnostic.run_diagnostic(output_json, output_csv, output_md)

    assert output_json.exists()
    assert output_csv.exists()
    assert output_md.exists()
    assert payload["biological_evidence_generated"] is False
    assert payload["scoring_modified"] is False
    assert payload["ranking_modified"] is False
    rows = list(csv.DictReader(output_csv.open(encoding="utf-8")))
    assert rows
    assert {"success", "openssl_applink_error", "network_error"}.issubset(
        {row["cause_classification"] for row in rows}
    )
    assert "does not touch scoring" in output_md.read_text(encoding="utf-8")


def test_candidate_seed_probe_reports_contract_status(monkeypatch) -> None:
    monkeypatch.setattr(
        diagnostic,
        "_run_python_probe",
        lambda code, url: _completed(
            '{"ok": true, "http_status": 200, "content_type": "application/json", "payload_type": "json", "record_count": 1}'
        ),
    )
    row = diagnostic._probe_candidate_seed("candidate_seed_taxon_287", "https://example.test")

    assert row["passes_contract"] == "true"
    assert row["contract_provider"] == "candidate_seed/uniprot"
    assert row["payload_type"] == "json"
    assert row["evidence_inferred"] == "false"


def test_diagnostic_does_not_touch_scoring_or_gui() -> None:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--",
            "src/nodos_funcionales/scoring_components.py",
            "gui",
            "apps",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == ""


def test_diagnostic_artifacts_are_not_biological_evidence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(diagnostic, "_dns_rows", lambda: [])
    monkeypatch.setattr(
        diagnostic,
        "_run_python_probe",
        lambda code, url: _completed("", "certificate_verify_failed", 1),
    )
    payload = diagnostic.run_diagnostic(tmp_path / "d.json", tmp_path / "d.csv", tmp_path / "d.md")

    assert payload["probable_cause"] == "certificate_verify_failed"
    assert all(row["evidence_inferred"] == "false" for row in payload["rows"])
    assert all(row["affects_score"] == "false" for row in payload["rows"])
