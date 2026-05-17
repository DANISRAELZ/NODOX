from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.user_curated_validation import validate_user_curated_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prevalidar un manifest user_curated sin ejecutar importacion, pipeline ni scoring."
    )
    parser.add_argument("manifest", help="Ruta al CSV user_curated_dataset_manifest.csv.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    errors = validate_user_curated_manifest(args.manifest)
    if errors:
        print("[ERROR] Manifest user_curated invalido:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("[OK] Manifest user_curated valido para revision/importacion.")
    print("[OK] Esta prevalidacion no ejecuta pipeline, importacion ni scoring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
