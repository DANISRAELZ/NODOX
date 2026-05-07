from __future__ import annotations

import json
import shutil

import pytest

from src.nodos_funcionales.curated_snapshots import assert_curated_snapshot_valid, load_curated_snapshot, validate_curated_snapshot
from tests.helpers import PROJECT_ROOT


SNAPSHOT_DIR = PROJECT_ROOT / "data_external" / "curated_snapshots" / "pseudomonas_aeruginosa_pao1"


@pytest.mark.unit
def test_pao1_curated_snapshot_is_valid() -> None:
    errors = validate_curated_snapshot(SNAPSHOT_DIR)

    assert errors == []
    snapshot = load_curated_snapshot(SNAPSHOT_DIR)
    assert snapshot["metadata"]["snapshot_id"] == "pseudomonas_aeruginosa_pao1_demo_controlled_v1"


@pytest.mark.unit
def test_missing_required_metadata_field_is_reported(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path)
    metadata_path = snapshot_dir / "snapshot_metadata.json"
    metadata = _read_json(metadata_path)
    metadata.pop("taxon_id")
    _write_json(metadata_path, metadata)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("taxon_id" in error and "obligatorio" in error for error in errors)


@pytest.mark.unit
def test_source_cannot_be_stub_and_real_external(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path)
    manifest_path = snapshot_dir / "sources_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["sources"][0]["is_stub"] = True
    manifest["sources"][0]["is_real_external"] = True
    _write_json(manifest_path, manifest)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("categorias incompatibles" in error for error in errors)


@pytest.mark.unit
def test_controlled_source_cannot_claim_fresh_api_run(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path)
    manifest_path = snapshot_dir / "sources_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["sources"][0]["retrieval_status"] = "fresh_api_run"
    _write_json(manifest_path, manifest)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("controlada" in error and "fresh_api_run" in error for error in errors)


@pytest.mark.unit
def test_fallback_requires_provenance_notes(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path)
    manifest_path = snapshot_dir / "sources_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["sources"][-1]["notes"] = ""
    _write_json(manifest_path, manifest)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("fallback" in error and "notas" in error for error in errors)


@pytest.mark.unit
def test_cache_reuse_run_is_not_controlled_fixture(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path)
    manifest_path = snapshot_dir / "sources_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["sources"][1]["evidence_kind"] = "controlled_fixture"
    _write_json(manifest_path, manifest)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("cache_reuse_run" in error and "controlled_fixture" in error for error in errors)


@pytest.mark.unit
def test_assertion_error_is_clear_for_nontechnical_reader(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path)
    metadata_path = snapshot_dir / "snapshot_metadata.json"
    metadata = _read_json(metadata_path)
    metadata.pop("organism")
    _write_json(metadata_path, metadata)

    with pytest.raises(ValueError) as exc_info:
        assert_curated_snapshot_valid(snapshot_dir)

    assert "El snapshot curado no es valido" in str(exc_info.value)
    assert "organism" in str(exc_info.value)


def _copy_snapshot(tmp_path):
    target = tmp_path / "snapshot"
    shutil.copytree(SNAPSHOT_DIR, target)
    return target


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
