from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.evolutionary_fitness_cost_screening import (
    audit_screened_fitness_cost_literature,
)
from src.nodos_funcionales.online.provider_modes import normalize_provider_mode, provider_mode_choices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit screened evolutionary fitness-cost literature without changing NODOX scoring. "
            "Qualitative records remain screening-only until a supported numeric measurement is "
            "explicitly curated into the Stage 4E production catalog."
        )
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="NODOX workspace containing organism_profile.json in a supported location.",
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "config" / "params.yaml"),
        help="NODOX YAML configuration file.",
    )
    parser.add_argument(
        "--online-source-mode",
        choices=provider_mode_choices(),
        help="Optional source-mode override used only for policy evaluation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        parser.error(f"workspace does not exist: {workspace}")

    config = load_config(Path(args.config))
    if args.online_source_mode:
        config.setdefault("online_sources", {})["source_mode_effective"] = normalize_provider_mode(
            args.online_source_mode
        )

    summary = audit_screened_fitness_cost_literature(workspace, config)
    manifest_path = workspace / "results" / "evolutionary_fitness_cost_literature_screening_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    payload = {
        "workspace": str(workspace),
        "manifest": str(manifest_path),
        "status": manifest.get("status", "not_reported"),
        "scoring_effect": bool(manifest.get("scoring_effect", False)),
        "screened_record_count": int(manifest.get("screened_record_count", len(summary))),
        "quantitative_candidate_count": int(manifest.get("quantitative_candidate_count", 0)),
        "promoted_record_count": int(manifest.get("promoted_record_count", 0)),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
