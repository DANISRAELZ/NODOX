"""Paso 3: integrar tablas normalizadas en una tabla maestra auditable."""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.nodos_funcionales.integration import integrate_tables


def main() -> None:
    integrated = integrate_tables(BASE_DIR)
    print(f"[OK] Tabla integrada: data_processed/integrated_nodes.csv ({len(integrated)} filas)")


if __name__ == "__main__":
    main()
