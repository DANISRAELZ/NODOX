"""Paso 5: exportar rankings y reporte interpretativo."""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.runtime import build_argument_parser, resolve_pipeline_mode
from src.nodos_funcionales.reporting import export_results


def main() -> None:
    parser = build_argument_parser("Exportar ranking y reporte interpretativo.")
    args = parser.parse_args()
    config = load_config(BASE_DIR / "config" / "params.yaml")
    mode = resolve_pipeline_mode(config, args.mode)
    export_results(BASE_DIR, config, mode=mode)
    print(f"[OK] Modo de pipeline: {mode}")
    print("[OK] Ranking principal: results/ranking_nodos.csv")
    print("[OK] Ranking legacy: results/ranking_nodos_legacy.csv")
    print("[OK] Reporte: results/report_phase2.md")


if __name__ == "__main__":
    main()
