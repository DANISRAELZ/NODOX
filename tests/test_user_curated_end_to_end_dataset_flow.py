from __future__ import annotations

import csv
import shutil
from pathlib import Path

from src.nodos_funcionales.acquisition import import_user_dataset
from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.layer_resolver import resolve_layer_inputs
from src.nodos_funcionales.user_curated_validation import validate_user_curated_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "user_curated_minimal_dataset"

FIXTURE_TO_TEMPLATE = {
    "manifest.csv": "user_curated_dataset_manifest_template.csv",
    "essentiality.csv": "essentiality_template.csv",
    "virulence.csv": "virulence_template.csv",
    "human_homologs.csv": "human_homologs_template.csv",
    "localization.csv": "localization_template.csv",
    "gene_list.csv": "gene_list_template.csv",
    "functional_annotations.csv": "functional_annotations_template.csv",
    "conservation.csv": "conservation_template.csv",
    "organism_profile.csv": "organism_profile_template.csv",
    "evolutionary_escape_risk.csv": "evolutionary_escape_risk_template.csv",
    "evolutionary_escape.csv": "evolutionary_escape_template.csv",
    "manual_curation.csv": "manual_curation_template.csv",
    "external_sources.csv": "external_sources_template.csv",
}

IMPORTABLE_LAYER_FILES = {
    "essentiality": "essentiality.csv",
    "virulence": "virulence.csv",
    "human_homologs": "human_homologs.csv",
    "localization": "localization.csv",
}

FORBIDDEN_EVIDENCE_VALUES = {"demo", "proxy", "cache", "controlled_reference", "online"}
FORBIDDEN_ORGANISM_TOKENS = {"corynebacterium", "pao1", "h37rv"}
EVOLUTIONARY_TERMS = {
    "evolutionary_escape_risk",
    "evolutionary_constraint",
    "mutation_tolerance",
    "pathway_redundancy",
    "paralog_count",
    "mobile_context",
    "hgt_context",
    "recombination_context",
    "resistance_association",
}


def _csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle))


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _protected_output_files() -> set[Path]:
    protected_dirs = [
        PROJECT_ROOT / "results",
        PROJECT_ROOT / "data_processed",
        PROJECT_ROOT / "data_sessions",
    ]
    files: set[Path] = set()
    for directory in protected_dirs:
        if directory.exists():
            files.update(path.relative_to(PROJECT_ROOT) for path in directory.rglob("*") if path.is_file())
    return files


def _write_workspace_config(workspace: Path) -> None:
    config_dir = workspace / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "params.yaml").write_text("", encoding="utf-8")


def test_minimal_user_curated_fixture_exists_and_matches_templates() -> None:
    assert FIXTURE_ROOT.exists()

    for fixture_name, template_name in FIXTURE_TO_TEMPLATE.items():
        fixture_path = FIXTURE_ROOT / fixture_name
        template_path = PROJECT_ROOT / "data_templates" / template_name

        assert fixture_path.exists(), fixture_name
        assert template_path.exists(), template_name
        assert _csv_header(fixture_path) == _csv_header(template_path)


def test_minimal_user_curated_fixture_manifest_and_source_boundaries() -> None:
    manifest_path = FIXTURE_ROOT / "manifest.csv"

    assert validate_user_curated_manifest(manifest_path) == []

    manifest_rows = _csv_rows(manifest_path)
    assert manifest_rows
    assert {row["source_type"] for row in manifest_rows} == {"user_curated"}
    assert {row["organism"] for row in manifest_rows} == {"Example organism"}
    assert {row["strain"] for row in manifest_rows} == {"Example strain"}
    assert {row["dataset_id"] for row in manifest_rows} == {"minimal_user_curated_end_to_end_test"}

    fixture_values: list[str] = []
    for fixture_name in FIXTURE_TO_TEMPLATE:
        for row in _csv_rows(FIXTURE_ROOT / fixture_name):
            fixture_values.extend(str(value).strip().casefold() for value in row.values())

    assert not (FORBIDDEN_EVIDENCE_VALUES & set(fixture_values))
    assert not any(token in " ".join(fixture_values) for token in FORBIDDEN_ORGANISM_TOKENS)
    assert "user_curated" in " ".join(fixture_values)


def test_minimal_user_curated_fixture_preserves_evolutionary_terms() -> None:
    evolutionary_text = " ".join(
        (FIXTURE_ROOT / name).read_text(encoding="utf-8").casefold()
        for name in ["evolutionary_escape_risk.csv", "evolutionary_escape.csv"]
    )

    for term in EVOLUTIONARY_TERMS:
        assert term in evolutionary_text


def test_minimal_user_curated_imports_to_data_user_and_resolves_as_user_layer(tmp_path: Path) -> None:
    before_outputs = _protected_output_files()
    workspace = tmp_path / "workspace"
    fixture_copy = tmp_path / "fixture"
    shutil.copytree(FIXTURE_ROOT, fixture_copy)
    _write_workspace_config(workspace)

    manifest_path = fixture_copy / "manifest.csv"
    assert validate_user_curated_manifest(manifest_path) == []

    for dataset_key, filename in IMPORTABLE_LAYER_FILES.items():
        result = import_user_dataset(
            workspace=workspace,
            dataset_key=dataset_key,
            input_path=fixture_copy / filename,
            project_root=PROJECT_ROOT,
            as_user_layer=True,
        )

        assert result["as_user_layer"] is True
        assert Path(result["target_path"]).is_relative_to(workspace / "data_user")
        assert Path(result["copied_source"]).is_relative_to(workspace / "data_user" / "source_exports")
        assert Path(result["target_path"]).exists()
        assert Path(result["copied_source"]).exists()
        assert not (workspace / "data_raw" / filename).exists()

        imported_rows = _csv_rows(Path(result["target_path"]))
        assert imported_rows
        imported_values = {str(value).strip().casefold() for row in imported_rows for value in row.values()}
        assert "user_curated_fixture" in imported_values
        assert not (FORBIDDEN_EVIDENCE_VALUES & imported_values)

    config = load_config(workspace / "config" / "params.yaml")
    config["online_sources"]["source_mode_effective"] = "offline_only"
    config["online_sources"]["therapeutic_context"]["enabled"] = False
    config["online_sources"]["therapeutic_context_v2"]["enabled"] = False

    layer_manifest = resolve_layer_inputs(workspace, config)
    for layer in IMPORTABLE_LAYER_FILES:
        resolved = layer_manifest[layer]
        assert resolved["resolved_from"] == "user"
        assert resolved["source_type"] == "user"
        assert resolved["is_user_supplied"] is True
        assert resolved["is_cached"] is False
        assert resolved["is_proxy"] is False
        assert resolved["is_external"] is False
        assert resolved["source_name"] not in FORBIDDEN_EVIDENCE_VALUES

    assert _protected_output_files() == before_outputs
