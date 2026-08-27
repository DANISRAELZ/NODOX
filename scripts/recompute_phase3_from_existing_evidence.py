from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recompute NODOX scoring and Phase 3 from an existing workspace without "
            "rerunning external evidence providers. Intended for scoring-semantics fixes "
            "when the workspace already contains frozen DEG/VFDB/STRING/DIAMOND/BV-BRC evidence."
        )
    )
    parser.add_argument("--workspace", required=True, help="Existing NODOX workspace directory.")
    parser.add_argument("--online-source-mode", default="online_strict")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()
    config_path = workspace / "config" / "params.yaml"
    if not workspace.is_dir():
        raise SystemExit(f"workspace not found: {workspace}")
    if not config_path.is_file():
        raise SystemExit(f"workspace config not found: {config_path}")

    result = run_pipeline(
        base_dir=workspace,
        config_path=config_path,
        mode="phase3",
        online_source_mode=args.online_source_mode,
    )
    print(
        json.dumps(
            {
                "status": "completed",
                "workspace": str(workspace),
                "external_providers_rerun": False,
                "pipeline_result": result,
                "note": (
                    "Recomputed from evidence already materialized in the workspace; "
                    "this command does not invoke DIAMOND, STRING, BV-BRC, InterPro, literature, DEG or VFDB retrieval."
                ),
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
