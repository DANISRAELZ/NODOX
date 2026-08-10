#!/usr/bin/env python3
"""Run the read-only Stage 4H proxy-versus-supported ablation comparison."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for import_path in (PROJECT_ROOT, SCRIPT_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from run_evolutionary_ablation import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="NODOX run containing phase3_features and Stage 4G coverage outputs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Destination for existing ablation and new Stage 4H audit outputs.",
    )
    parser.add_argument(
        "--stage2-config",
        type=Path,
        default=Path("config/integrated_validation_stage2.json"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    run_dir = args.run_dir if args.run_dir.is_absolute() else repo_root / args.run_dir
    output_dir = (
        args.output_dir if args.output_dir.is_absolute() else repo_root / args.output_dir
    )
    config_path = (
        args.stage2_config
        if args.stage2_config.is_absolute()
        else repo_root / args.stage2_config
    )
    summary = run(
        repo_root=repo_root,
        run_dir=run_dir,
        output_dir=output_dir,
        stage2_config_path=config_path,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
