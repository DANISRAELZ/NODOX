"""Paso 2: normalizar identificadores y metadatos canonicos."""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.normalization import normalize_all


def main() -> None:
    config = load_config(BASE_DIR / "config" / "params.yaml")
    normalize_all(BASE_DIR, config)
    print("[OK] Archivos normalizados en data_processed/")


if __name__ == "__main__":
    main()
