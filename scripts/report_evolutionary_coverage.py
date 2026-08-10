from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.evolutionary_coverage_reporting import (
    write_evolutionary_coverage_outputs,
)
from src.nodos_funcionales.online.provider_modes import (
    normalize_provider_mode,
    provider_mode_choices,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the Stage 4G candidate-level evolutionary evidence coverage report "
            "without changing scoring formulas, weights, scores, or ranking."
        )
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="NODOX workspace containing data_processed/phase2_features.csv.",
    )
    parser.add_argument(
        "--features",
        help=(
            "Optional feature-table override. Relative paths are resolved from the workspace. "
            "The default is data_processed/phase2_features.csv."
        ),
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "config" / "params.yaml"),
        help="NODOX YAML configuration file.",
    )
    parser.add_argument(
        "--online-source-mode",
        choices=provider_mode_choices(),
        help="Optional source-mode override used for Stage 4E/4F policy evaluation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        parser.error(f"workspace does not exist: {workspace}")

    features_path = Path(args.features) if args.features else Path("data_processed/phase2_features.csv")
    if not features_path.is_absolute():
        features_path = workspace / features_path
    if not features_path.exists():
        parser.error(f"feature table does not exist: {features_path}")

    config = load_config(Path(args.config))
    if args.online_source_mode:
        config.setdefault("online_sources", {})["source_mode_effective"] = normalize_provider_mode(
            args.online_source_mode
        )

    features = pd.read_csv(features_path)
    manifest = write_evolutionary_coverage_outputs(workspace, features, config)
    print(json.dumps(manifest, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
