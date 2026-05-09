from __future__ import annotations

import json
import shutil

import pytest

from src.nodos_funcionales.curated_snapshots import (
    assert_curated_snapshot_valid,
    list_available_snapshots,
    load_curated_snapshot,
    load_curated_snapshot_by_id,
    validate_snapshot,
    validate_curated_snapshot,
    validate_curated_snapshots,
)
from tests.helpers import PROJECT_ROOT


PAO1_SNAPSHOT_DIR = PROJECT_ROOT / "data_external" / "curated_snapshots" / "pseudomonas_aeruginosa_pao1"
CORY_SNAPSHOT_DIR = PROJECT_ROOT / "data_external" / "curated_snapshots" / "corynebacterium_pseudotuberculosis_biovar_ovis"
SNAPSHOTS_ROOT = PROJECT_ROOT / "data_external" / "curated_snapshots"


@pytest.mark.unit
def test_pao1_curated_snapshot_is_valid() -> None:
    errors = validate_snapshot(PAO1_SNAPSHOT_DIR)

    assert errors == []
    snapshot = load_curated_snapshot(PAO1_SNAPSHOT_DIR)
    assert snapshot["metadata"]["snapshot_id"] == "pseudomonas_aeruginosa_pao1_demo_controlled_v1"


@pytest.mark.unit
def test_corynebacterium_curated_snapshot_is_valid() -> None:
    errors = validate_snapshot(CORY_SNAPSHOT_DIR)

    assert errors == []
    snapshot = load_curated_snapshot(CORY_SNAPSHOT_DIR)
    assert snapshot["metadata"]["organism"] == "Corynebacterium pseudotuberculosis"
    assert snapshot["metadata"]["biovar"] == "ovis"
    assert snapshot["taxonomy"]["taxon_id"] == "1719"


@pytest.mark.unit
def test_multiple_curated_snapshots_validate_together() -> None:
    results = validate_curated_snapshots([PAO1_SNAPSHOT_DIR, CORY_SNAPSHOT_DIR])

    assert results == {
        "pseudomonas_aeruginosa_pao1": [],
        "corynebacterium_pseudotuberculosis_biovar_ovis": [],
    }


@pytest.mark.unit
def test_snapshots_can_be_listed_and_loaded_by_id_without_organism_specific_function() -> None:
    snapshot_dirs = list_available_snapshots(SNAPSHOTS_ROOT)

    assert PAO1_SNAPSHOT_DIR in snapshot_dirs
    assert CORY_SNAPSHOT_DIR in snapshot_dirs
    snapshot = load_curated_snapshot_by_id(SNAPSHOTS_ROOT, "corynebacterium_pseudotuberculosis_biovar_ovis_controlled_v1")
    assert snapshot["metadata"]["organism"] == "Corynebacterium pseudotuberculosis"


@pytest.mark.unit
def test_cross_validation_organism_snapshot_can_be_added_without_validator_change(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path, CORY_SNAPSHOT_DIR)
    _rewrite_snapshot_identity(
        snapshot_dir,
        organism="Mycobacterium tuberculosis",
        strain="H37Rv",
        snapshot_id="mycobacterium_tuberculosis_h37rv_cross_validation_v1",
        taxon_id="83332",
    )

    errors = validate_snapshot(snapshot_dir)

    assert errors == []


@pytest.mark.unit
def test_unknown_partial_organism_snapshot_can_pass_with_explicit_limitations(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path, CORY_SNAPSHOT_DIR)
    _rewrite_snapshot_identity(
        snapshot_dir,
        organism="Unresolved bacterium",
        strain=None,
        snapshot_id="unresolved_bacterium_partial_controlled_v1",
        taxon_id=None,
    )
    metadata_path = snapshot_dir / "snapshot_metadata.json"
    metadata = _read_json(metadata_path)
    metadata["limitations"] = ["Taxon id and strain are not resolved yet; user data may still be validated by contract."]
    _write_json(metadata_path, metadata)
    taxonomy_path = snapshot_dir / "taxonomy.json"
    taxonomy = _read_json(taxonomy_path)
    taxonomy["limitations"] = ["Taxon id unresolved; snapshot is partial and controlled."]
    _write_json(taxonomy_path, taxonomy)

    errors = validate_snapshot(snapshot_dir)

    assert errors == []


@pytest.mark.unit
def test_missing_required_metadata_field_is_reported(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path, PAO1_SNAPSHOT_DIR)
    metadata_path = snapshot_dir / "snapshot_metadata.json"
    metadata = _read_json(metadata_path)
    metadata.pop("taxon_id")
    _write_json(metadata_path, metadata)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("taxon_id" in error and "obligatorio" in error for error in errors)


@pytest.mark.unit
def test_source_cannot_be_stub_and_real_external(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path, PAO1_SNAPSHOT_DIR)
    manifest_path = snapshot_dir / "sources_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["sources"][0]["is_stub"] = True
    manifest["sources"][0]["is_real_external"] = True
    _write_json(manifest_path, manifest)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("categorias incompatibles" in error for error in errors)


@pytest.mark.unit
def test_controlled_source_cannot_claim_fresh_api_run(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path, PAO1_SNAPSHOT_DIR)
    manifest_path = snapshot_dir / "sources_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["sources"][0]["retrieval_status"] = "fresh_api_run"
    _write_json(manifest_path, manifest)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("controlada" in error and "fresh_api_run" in error for error in errors)


@pytest.mark.unit
def test_fallback_requires_provenance_notes(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path, PAO1_SNAPSHOT_DIR)
    manifest_path = snapshot_dir / "sources_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["sources"][-1]["notes"] = ""
    _write_json(manifest_path, manifest)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("fallback" in error and "notas" in error for error in errors)


@pytest.mark.unit
def test_cache_reuse_run_is_not_controlled_fixture(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path, PAO1_SNAPSHOT_DIR)
    manifest_path = snapshot_dir / "sources_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["sources"][1]["evidence_kind"] = "controlled_fixture"
    _write_json(manifest_path, manifest)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("cache_reuse_run" in error and "controlled_fixture" in error for error in errors)


@pytest.mark.unit
def test_no_network_snapshot_rejects_string_fresh_api_run(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path, CORY_SNAPSHOT_DIR)
    manifest_path = snapshot_dir / "sources_manifest.json"
    manifest = _read_json(manifest_path)
    string_source = next(source for source in manifest["sources"] if source["source_name"] == "STRING")
    string_source["retrieval_status"] = "fresh_api_run"
    string_source["is_real_external"] = True
    _write_json(manifest_path, manifest)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("STRING" in error and "fresh_api_run" in error for error in errors)
    assert any("prohibe llamadas frescas" in error for error in errors)


@pytest.mark.unit
def test_controlled_functional_annotation_requires_reference_and_notes(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path, CORY_SNAPSHOT_DIR)
    annotations_path = snapshot_dir / "functional_annotations.json"
    annotations = _read_json(annotations_path)
    annotations["annotations"][0]["source_reference"] = ""
    annotations["annotations"][0]["notes"] = ""
    _write_json(annotations_path, annotations)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("source_reference" in error for error in errors)
    assert any("notes" in error for error in errors)


@pytest.mark.unit
def test_taxonomy_without_taxon_id_is_allowed_with_explicit_limitation(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path, CORY_SNAPSHOT_DIR)
    taxonomy_path = snapshot_dir / "taxonomy.json"
    taxonomy = _read_json(taxonomy_path)
    taxonomy["taxon_id"] = None
    taxonomy["limitations"] = ["Taxon id pending controlled offline curation."]
    _write_json(taxonomy_path, taxonomy)

    errors = validate_curated_snapshot(snapshot_dir)

    assert not any("taxon_id" in error and "limitacion" in error for error in errors)


@pytest.mark.unit
def test_taxonomy_without_taxon_id_requires_explicit_limitation(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path, CORY_SNAPSHOT_DIR)
    taxonomy_path = snapshot_dir / "taxonomy.json"
    taxonomy = _read_json(taxonomy_path)
    taxonomy["taxon_id"] = None
    taxonomy["limitations"] = []
    _write_json(taxonomy_path, taxonomy)

    errors = validate_curated_snapshot(snapshot_dir)

    assert any("taxon_id" in error and "limitacion explicita" in error for error in errors)


@pytest.mark.unit
def test_assertion_error_is_clear_for_nontechnical_reader(tmp_path) -> None:
    snapshot_dir = _copy_snapshot(tmp_path, PAO1_SNAPSHOT_DIR)
    metadata_path = snapshot_dir / "snapshot_metadata.json"
    metadata = _read_json(metadata_path)
    metadata.pop("organism")
    _write_json(metadata_path, metadata)

    with pytest.raises(ValueError) as exc_info:
        assert_curated_snapshot_valid(snapshot_dir)

    assert "El snapshot curado no es valido" in str(exc_info.value)
    assert "organism" in str(exc_info.value)


def _copy_snapshot(tmp_path, source_dir):
    target = tmp_path / "snapshot"
    shutil.copytree(source_dir, target)
    return target


def _rewrite_snapshot_identity(snapshot_dir, organism: str, strain: str | None, snapshot_id: str, taxon_id: str | None) -> None:
    metadata_path = snapshot_dir / "snapshot_metadata.json"
    metadata = _read_json(metadata_path)
    metadata["organism"] = organism
    metadata["canonical_organism_name"] = organism
    metadata["strain"] = strain
    metadata["biovar"] = None
    metadata["strain_scope"] = strain or "unresolved strain scope"
    metadata["taxon_id"] = taxon_id
    metadata["snapshot_id"] = snapshot_id
    metadata["snapshot_label"] = f"{organism} controlled snapshot"
    _write_json(metadata_path, metadata)

    taxonomy_path = snapshot_dir / "taxonomy.json"
    taxonomy = _read_json(taxonomy_path)
    taxonomy["organism"] = organism
    taxonomy["canonical_organism_name"] = organism
    taxonomy["strain_scope"] = strain or "unresolved strain scope"
    taxonomy["biovar"] = None
    taxonomy["taxon_id"] = taxon_id
    taxonomy["taxonomy_source"] = "temporary_test_fixture"
    taxonomy["cache_key"] = None
    _write_json(taxonomy_path, taxonomy)

    manifest_path = snapshot_dir / "sources_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["snapshot_id"] = snapshot_id
    _write_json(manifest_path, manifest)


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
