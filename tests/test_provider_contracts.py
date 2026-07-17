from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from src.nodos_funcionales.provider_contracts import PROVIDER_CONTRACTS, contract_matrix_records
from tests.helpers import PROJECT_ROOT


EXPECTED_PROVIDERS = {
    "candidate_seed",
    "uniprot",
    "string",
    "interpro",
    "bvbrc",
    "vfdb",
    "deg",
    "europe_pmc",
    "taxonomy",
    "human_essentiality",
}


def _degraded_statuses(provider_key: str) -> set[str]:
    return {item.final_status for item in PROVIDER_CONTRACTS[provider_key].degraded_statuses}


def test_all_expected_providers_have_contracts() -> None:
    assert set(PROVIDER_CONTRACTS) == EXPECTED_PROVIDERS


def test_contracts_define_required_payload_and_degradation_fields() -> None:
    for contract in PROVIDER_CONTRACTS.values():
        assert contract.required_fields
        assert contract.accepted_payload_types
        assert contract.degraded_statuses
        assert contract.accepted_statuses
        assert contract.parser_name
        assert contract.provenance_required is True


def test_only_candidate_seed_blocks_ranking() -> None:
    blocking = {key for key, contract in PROVIDER_CONTRACTS.items() if contract.blocks_ranking}
    assert blocking == {"candidate_seed"}


def test_degradations_do_not_infer_evidence_or_affect_score() -> None:
    for key, contract in PROVIDER_CONTRACTS.items():
        for degraded in contract.degraded_statuses:
            assert degraded.affects_score is False
            assert degraded.evidence_inferred is False
            if key != "candidate_seed":
                assert degraded.blocks_ranking is False


def test_vfdb_and_deg_do_not_accept_html_payloads() -> None:
    for provider_key in ("vfdb", "deg"):
        contract = PROVIDER_CONTRACTS[provider_key]
        assert "html" not in contract.accepted_payload_types
        assert "html_instead_of_structured_payload" in _degraded_statuses(provider_key)


def test_deg_zip_requires_formal_adapter_before_acceptance() -> None:
    deg = PROVIDER_CONTRACTS["deg"]
    assert "zip" not in deg.accepted_payload_types
    assert "unsupported_structured_archive" in _degraded_statuses("deg")
    assert "zip" in next(row for row in contract_matrix_records() if row["provider_key"] == "deg")["rejected_payloads"]


def test_string_and_interpro_accept_json_and_degrade_ssl_network() -> None:
    for provider_key in ("string", "interpro"):
        contract = PROVIDER_CONTRACTS[provider_key]
        statuses = _degraded_statuses(provider_key)
        assert contract.accepted_payload_types == ("json",)
        assert "ssl_error" in statuses
        assert "network_error" in statuses
        assert contract.blocks_ranking is False
        assert contract.affects_score_on_degradation is False


def test_bvbrc_accepts_json_and_empty_payload_is_not_negative_evidence() -> None:
    contract = PROVIDER_CONTRACTS["bvbrc"]
    empty_contract = next(item for item in contract.degraded_statuses if item.final_status == "empty_payload")
    assert "json" in contract.accepted_payload_types
    assert empty_contract.affects_score is False
    assert empty_contract.blocks_ranking is False
    assert empty_contract.evidence_inferred is False
    assert "not negative evidence" in empty_contract.conservative_reason


def test_matrix_csv_and_json_match_contract_providers() -> None:
    csv_path = PROJECT_ROOT / "docs" / "audit_artifacts" / "online_provider_contract_matrix_7J.csv"
    json_path = PROJECT_ROOT / "docs" / "audit_artifacts" / "online_provider_contract_matrix_7J.json"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    json_rows = payload["providers"]
    assert {row["provider_key"] for row in csv_rows} == set(PROVIDER_CONTRACTS)
    assert {row["provider_key"] for row in json_rows} == set(PROVIDER_CONTRACTS)
    assert csv_rows == contract_matrix_records()
    assert json_rows == contract_matrix_records()


def test_contract_phase_does_not_touch_scoring_config_or_gui() -> None:
    paths = [
        "src/nodos_funcionales/scoring_components.py",
        "gui",
        "apps",
    ]
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", *paths],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == ""


def test_publication_docs_do_not_mix_with_unrequested_organisms() -> None:
    docs = [
        PROJECT_ROOT / "docs" / "online_provider_contract_matrix_7J.md",
        PROJECT_ROOT / "docs" / "online_only_provider_publication_readiness_7J.md",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in docs).casefold()
    forbidden_organism = "coryne" + "bacterium"
    assert forbidden_organism not in text
