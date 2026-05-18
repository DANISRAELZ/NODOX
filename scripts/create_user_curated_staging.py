from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGING_ROOT = PROJECT_ROOT / "user_curated_staging"
MANIFEST_TEMPLATE = PROJECT_ROOT / "data_templates" / "user_curated_dataset_manifest_template.csv"
README_TEMPLATE = PROJECT_ROOT / "docs" / "templates" / "user_curated_staging_README_template.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Crear una estructura local ignorada para preparar datos user_curated "
            "sin importar datos, ejecutar pipeline ni calcular scoring."
        )
    )
    parser.add_argument("project_id", help="Identificador local seguro para la carpeta de staging.")
    parser.add_argument(
        "--root",
        default=str(DEFAULT_STAGING_ROOT),
        help="Raiz local de staging. Por defecto usa user_curated_staging/ en el repositorio.",
    )
    return parser


def validate_project_id(project_id: str) -> str:
    cleaned = project_id.strip()
    if not cleaned:
        raise ValueError("project_id must not be empty.")
    if cleaned in {".", ".."} or ".." in cleaned:
        raise ValueError("project_id must not contain parent-directory references.")
    if any(separator in cleaned for separator in ("/", "\\")):
        raise ValueError("project_id must be a single folder name, not a path.")
    if Path(cleaned).is_absolute():
        raise ValueError("project_id must be relative, not absolute.")
    if ":" in cleaned:
        raise ValueError("project_id must not contain drive or scheme separators.")
    return cleaned


def create_staging(project_id: str, root: str | Path = DEFAULT_STAGING_ROOT) -> Path:
    safe_project_id = validate_project_id(project_id)
    staging_root = Path(root)
    target_dir = staging_root / safe_project_id

    if target_dir.exists():
        raise FileExistsError(f"Staging folder already exists and was not modified: {target_dir}")

    if not MANIFEST_TEMPLATE.exists():
        raise FileNotFoundError(f"Manifest template not found: {MANIFEST_TEMPLATE}")
    if not README_TEMPLATE.exists():
        raise FileNotFoundError(f"README template not found: {README_TEMPLATE}")

    target_dir.mkdir(parents=True)
    for child in ("raw_inputs", "notes", "provenance"):
        (target_dir / child).mkdir()

    shutil.copyfile(MANIFEST_TEMPLATE, target_dir / "manifest.csv")
    shutil.copyfile(README_TEMPLATE, target_dir / "README.md")
    return target_dir


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        target_dir = create_staging(args.project_id, args.root)
    except (FileExistsError, FileNotFoundError, OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[OK] Created local user_curated staging folder: {target_dir}")
    print("[WARN] This folder is local/ignored staging. Do not version real or sensitive data.")
    print("[WARN] This command did not download data, import datasets, run pipeline, or calculate scoring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
