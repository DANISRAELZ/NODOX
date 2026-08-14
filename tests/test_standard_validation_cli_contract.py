from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_online_only_validation import validate_complete_snapshot_cli_contract


def _write_manifest(snapshot_dir: Path, payload: dict) -> None:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "snapshot_manifest.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_complete_mode_rejects_legacy_bounded_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / "legacy_snapshot"
    _write_manifest(snapshot, {"candidate_count": 25})

    with pytest.raises(ValueError, match="legacy or bounded"):
        validate_complete_snapshot_cli_contract(
            max_candidates=0,
            candidate_seed_snapshot=str(snapshot),
            expected_proteome_id="UP000000625",
        )


def test_complete_mode_accepts_explicit_complete_exact_proteome_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / "complete_snapshot"
    _write_manifest(
        snapshot,
        {
            "proteome_id": "UP000000625",
            "candidate_count": 4000,
            "requested_max_candidates": 0,
            "candidate_scope": "complete_exact_proteome",
            "query_semantics": "proteome_id_exact_no_species_broadening",
        },
    )

    validate_complete_snapshot_cli_contract(
        max_candidates=0,
        candidate_seed_snapshot=str(snapshot),
        expected_proteome_id="UP000000625",
    )


def test_complete_mode_rejects_proteome_mismatch(tmp_path: Path) -> None:
    snapshot = tmp_path / "wrong_proteome"
    _write_manifest(
        snapshot,
        {
            "proteome_id": "UP000002438",
            "candidate_count": 5000,
            "requested_max_candidates": 0,
            "candidate_scope": "complete_exact_proteome",
            "query_semantics": "proteome_id_exact_no_species_broadening",
        },
    )

    with pytest.raises(ValueError, match="proteome mismatch"):
        validate_complete_snapshot_cli_contract(
            max_candidates=0,
            candidate_seed_snapshot=str(snapshot),
            expected_proteome_id="UP000000625",
        )


def test_positive_candidate_limit_does_not_require_complete_snapshot_metadata(tmp_path: Path) -> None:
    snapshot = tmp_path / "bounded_snapshot"
    _write_manifest(snapshot, {"candidate_count": 25})

    validate_complete_snapshot_cli_contract(
        max_candidates=25,
        candidate_seed_snapshot=str(snapshot),
        expected_proteome_id="UP000000625",
    )
