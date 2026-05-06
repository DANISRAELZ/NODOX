from __future__ import annotations

from pathlib import Path

from .config import load_config
from .integration import integrate_tables
from .normalization import normalize_all
from .reporting import export_results
from .runtime import resolve_pipeline_mode
from .scoring import build_features_and_scores, build_phase3_scores, compute_sensitivity
from .validation import load_and_validate_all


def run_pipeline(
    base_dir: Path,
    config_path: Path,
    mode: str = "compare",
    online_source_mode: str | None = None,
) -> dict[str, object]:
    config = load_config(config_path)
    if online_source_mode:
        config.setdefault("online_sources", {})["source_mode_effective"] = online_source_mode
    mode = resolve_pipeline_mode(config, mode)
    validation_summary = load_and_validate_all(base_dir, config)
    normalize_all(base_dir, config)
    integrated = integrate_tables(base_dir)
    features, scored = build_features_and_scores(base_dir, config)
    phase3_enabled = mode == "phase3" or bool(config.get("phase3", {}).get("enabled", False))
    phase3_feature_rows = 0
    phase3_score_rows = 0
    if phase3_enabled:
        phase3_features, phase3_scored = build_phase3_scores(base_dir, config, features)
        phase3_feature_rows = len(phase3_features)
        phase3_score_rows = len(phase3_scored)
    sensitivity = compute_sensitivity(features, config)
    sensitivity.to_csv(base_dir / "results" / "sensitivity_analysis.csv", index=False)
    export_results(base_dir, config, mode=mode)
    return {
        "mode": mode,
        "phase3_enabled": phase3_enabled,
        "validation_rows": len(validation_summary),
        "integrated_rows": len(integrated),
        "feature_rows": len(features),
        "score_rows": len(scored),
        "phase3_feature_rows": phase3_feature_rows,
        "phase3_score_rows": phase3_score_rows,
    }
