from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.run_online_only_multiorganism_batch import build_parser, run_online_only_multiorganism_batch
from src.nodos_funcionales.external_provider_capture import normalize_sanitized_capture, validate_real_provider_captures
from tests.helpers import PROJECT_ROOT
from tests.test_online_only_multiorganism_batch import _fake_runner, _project


CAPTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "external_providers" / "real_captures_sanitized"


def _captures() -> list[Path]:
    return sorted(CAPTURE_DIR.glob("*.json"))


def _score_hashes(root: Path) -> dict[str, str]:
    return {
        name: hashlib.sha256((root / "src" / "nodos_funcionales" / name).read_bytes()).hexdigest()
        for name in ("scoring.py", "scoring_components.py")
    }


def test_sanitized_real_captures_pass_through_phase_7e_adapters() -> None:
    rows = []
    for path in _captures():
        rows.extend(normalize_sanitized_capture(json.loads(path.read_text(encoding="utf-8"))))

    assert {row["provider_name"] for row in rows} == {"VFDB", "DEG", "BV-BRC"}
    assert all(row["evidence_status"] in {"supported", "not_found", "unresolved", "provider_failed"} for row in rows)
    assert any(row["provider_name"] == "BV-BRC" and row["evidence_status"] == "supported" for row in rows)
    assert all(row["affects_score"] is False for row in rows)
    assert all("not be interpreted as absence" in row["interpretation_warning"] for row in rows)


def test_real_capture_validation_package_is_complete_and_conservative(tmp_path) -> None:
    before = _score_hashes(PROJECT_ROOT)
    result = validate_real_provider_captures(_captures(), tmp_path)

    for filename in (
        "vfdb_real_capture_validation.csv", "deg_real_capture_validation.csv",
        "bvbrc_real_capture_validation.csv", "real_capture_normalized_records.csv",
        "real_capture_normalized_records.json", "real_capture_validation_manifest.json",
        "EXTERNAL_PROVIDER_REAL_CAPTURE_VALIDATION_REVIEW.md",
    ):
        assert (tmp_path / filename).exists()
    review = (tmp_path / "EXTERNAL_PROVIDER_REAL_CAPTURE_VALIDATION_REVIEW.md").read_text(encoding="utf-8")
    assert "must not be interpreted as biological absence" in review
    assert result["manifest"]["network_queries_performed"] is False
    assert result["manifest"]["affects_score"] is False
    assert _score_hashes(PROJECT_ROOT) == before


def test_runner_flag_uses_existing_captures_without_network(tmp_path) -> None:
    args = build_parser().parse_args([
        "--organism-keys", "escherichia_coli", "--run-label", "phase7f",
        "--validate-real-provider-captures",
    ])
    assert args.validate_real_provider_captures is True
    project = _project(tmp_path)
    before = _score_hashes(project)
    result = run_online_only_multiorganism_batch(
        project, ["escherichia_coli"], "phase7f", output_dir=project / "batch",
        organism_runner=_fake_runner, validate_real_provider_captures_enabled=True,
        provider_capture_paths=_captures(),
    )

    output = project / "results" / "online_only_external_evidence" / "phase7f" / "real_capture_validation"
    assert result["manifest"]["phase_7f_enabled"] is True
    assert (output / "real_capture_validation_manifest.json").exists()
    assert _score_hashes(project) == before
