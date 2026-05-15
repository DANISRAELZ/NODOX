from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.acquisition import import_user_dataset
from src.nodos_funcionales.generic_annotation_import import write_layer_csvs
from src.nodos_funcionales.io_errors import explain_cli_error
from src.nodos_funcionales.validation import DATASET_SPECS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importar un export tabular del usuario al esquema interno del workspace.")
    parser.add_argument("--organism", help="Nombre del organismo bacteriano; se registra solo como contexto de ejecucion.")
    parser.add_argument("--strain", help="Cepa opcional; se registra solo como contexto de ejecucion.")
    parser.add_argument("--workspace", required=True, help="Workspace destino.")
    parser.add_argument("--dataset", choices=sorted(spec.table_key for spec in DATASET_SPECS), help="Dataset interno destino.")
    parser.add_argument("--input", help="CSV fuente exportado por el usuario.")
    parser.add_argument("--input-dir", help="Directorio con CSVs del usuario; si se usa, se busca <dataset>.csv.")
    parser.add_argument(
        "--input-format",
        choices=["generic_csv", "generic_annotations"],
        default="generic_csv",
        help="Formato de entrada. generic_annotations materializa varias capas desde anotaciones genomicas locales.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except (FileNotFoundError, PermissionError, OSError, ValueError) as exc:
        print(explain_cli_error(exc, "import_dataset.py"), file=sys.stderr)
        return 1


def _main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.input_format == "generic_annotations":
        if not args.input_dir:
            parser.error("--input-format generic_annotations requiere --input-dir")
        summaries = write_layer_csvs(
            workspace=Path(args.workspace),
            input_dir=Path(args.input_dir),
            organism=args.organism or "",
            strain=args.strain or "",
        )
        print("[OK] Importacion generica de anotaciones completada")
        if args.organism:
            print(f"[OK] Organismo: {args.organism}")
        if args.strain:
            print(f"[OK] Cepa: {args.strain}")
        for summary in summaries:
            print(
                f"[OK] {summary.layer}: {summary.rows} filas -> {summary.path} "
                f"({summary.provenance_status})"
            )
            for warning in summary.warnings:
                if warning:
                    print(f"[WARN] {summary.layer}: {warning}")
        return 0

    if not args.dataset:
        parser.error("--dataset es requerido cuando --input-format generic_csv")
    input_path = Path(args.input) if args.input else None
    if input_path is None and args.input_dir:
        input_path = Path(args.input_dir) / f"{args.dataset}.csv"
    if input_path is None:
        parser.error("debe proporcionar --input o --input-dir")
    result = import_user_dataset(
        workspace=Path(args.workspace),
        dataset_key=args.dataset,
        input_path=input_path,
        project_root=PROJECT_ROOT,
    )
    if args.organism:
        print(f"[OK] Organismo: {args.organism}")
    if args.strain:
        print(f"[OK] Cepa: {args.strain}")
    print(f"[OK] Dataset importado: {result['dataset_key']}")
    print(f"[OK] Destino: {result['target_path']}")
    print(f"[OK] Filas fuente: {result['source_rows']}; filas mapeadas: {result['mapped_rows']}")
    print(f"[OK] Columnas mapeadas: {result['renamed_columns']}")
    if result["copied_source"]:
        print(f"[OK] Copia del export original: {result['copied_source']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
