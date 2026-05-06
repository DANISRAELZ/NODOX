from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.acquisition import import_user_dataset
from src.nodos_funcionales.validation import DATASET_SPECS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importar un export tabular del usuario al esquema interno del workspace.")
    parser.add_argument("--organism", help="Nombre del organismo bacteriano; se registra solo como contexto de ejecucion.")
    parser.add_argument("--strain", help="Cepa opcional; se registra solo como contexto de ejecucion.")
    parser.add_argument("--workspace", required=True, help="Workspace destino.")
    parser.add_argument("--dataset", required=True, choices=sorted(spec.table_key for spec in DATASET_SPECS), help="Dataset interno destino.")
    parser.add_argument("--input", help="CSV fuente exportado por el usuario.")
    parser.add_argument("--input-dir", help="Directorio con CSVs del usuario; si se usa, se busca <dataset>.csv.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
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
