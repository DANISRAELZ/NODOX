"""Paso 4: derivar features y calcular scores legacy y Fase 2."""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.runtime import build_argument_parser, resolve_pipeline_mode
from src.nodos_funcionales.scoring import build_features_and_scores, compute_sensitivity


def main() -> None:
    parser = build_argument_parser("Derivar features y calcular scores legacy y Fase 2.")
    args = parser.parse_args()
    config = load_config(BASE_DIR / "config" / "params.yaml")
    mode = resolve_pipeline_mode(config, args.mode)
    features, scored = build_features_and_scores(BASE_DIR, config)
    if mode == "legacy":
        sensitivity = compute_sensitivity(features, {"sensitivity": {"enabled": False, "top_n": 0, "scenarios": {}}})
    else:
        sensitivity = compute_sensitivity(features, config)
    sensitivity.to_csv(BASE_DIR / "results" / "sensitivity_analysis.csv", index=False)
    print(f"[OK] Modo de pipeline: {mode}")
    print(f"[OK] Features Fase 2: data_processed/phase2_features.csv ({len(features)} filas)")
    print(f"[OK] Scores: data_processed/scored_nodes.csv ({len(scored)} filas)")
    print(f"[OK] Sensibilidad: results/sensitivity_analysis.csv ({len(sensitivity)} filas)")


if __name__ == "__main__":
    main()
