"""Paso 1: validar inputs crudos y generar un resumen de calidad."""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.validation import load_and_validate_all


def main() -> None:
    config = load_config(BASE_DIR / "config" / "params.yaml")
    summary = load_and_validate_all(BASE_DIR, config)
    validated_count = len(list((BASE_DIR / "data_processed").glob("validated_*.csv")))
    print(f"[OK] Archivos validados: {validated_count}")
    print(f"[OK] Resumen de validacion: data_processed/validation_summary.csv ({len(summary)} filas)")


if __name__ == "__main__":
    main()
