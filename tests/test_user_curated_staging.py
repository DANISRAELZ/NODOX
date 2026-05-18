from __future__ import annotations

import importlib.util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "create_user_curated_staging.py"


def _load_staging_module():
    spec = importlib.util.spec_from_file_location("create_user_curated_staging", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _versioned_output_files() -> set[Path]:
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


def test_create_user_curated_staging_structure_in_tmp_path(tmp_path: Path) -> None:
    module = _load_staging_module()
    before_outputs = _versioned_output_files()
    root = tmp_path / "user_curated_staging"

    result = module.main(["project_alpha", "--root", str(root)])

    target = root / "project_alpha"
    assert result == 0
    assert target.exists()
    assert (target / "raw_inputs").is_dir()
    assert (target / "notes").is_dir()
    assert (target / "provenance").is_dir()
    assert (target / "manifest.csv").read_text(encoding="utf-8") == (
        PROJECT_ROOT / "data_templates" / "user_curated_dataset_manifest_template.csv"
    ).read_text(encoding="utf-8")
    assert (target / "README.md").read_text(encoding="utf-8") == (
        PROJECT_ROOT / "docs" / "templates" / "user_curated_staging_README_template.md"
    ).read_text(encoding="utf-8")
    assert _versioned_output_files() == before_outputs


def test_create_user_curated_staging_rejects_empty_or_dangerous_project_id(tmp_path: Path) -> None:
    module = _load_staging_module()
    root = tmp_path / "user_curated_staging"

    invalid_project_ids = ["", " ", "..", "../project", "nested/project", r"nested\project", "C:project"]
    for project_id in invalid_project_ids:
        assert module.main([project_id, "--root", str(root)]) == 1

    assert not root.exists()


def test_create_user_curated_staging_does_not_overwrite_existing_folder(tmp_path: Path) -> None:
    module = _load_staging_module()
    root = tmp_path / "user_curated_staging"
    target = root / "project_alpha"
    target.mkdir(parents=True)
    marker = target / "marker.txt"
    marker.write_text("keep me", encoding="utf-8")

    result = module.main(["project_alpha", "--root", str(root)])

    assert result == 1
    assert marker.read_text(encoding="utf-8") == "keep me"
    assert not (target / "manifest.csv").exists()
    assert not (target / "README.md").exists()
