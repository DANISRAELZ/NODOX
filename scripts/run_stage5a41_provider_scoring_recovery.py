from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.online.provider_modes import provider_mode_choices
from src.nodos_funcionales.stage5a41_provider_scoring_recovery import (
    run_stage5a41_provider_scoring_recovery,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run NODOX Stage 5A.4.1: normalize the versioned VFDB snapshot, "
            "overlay positive DEG matches onto basal essentiality, and optionally "
            "recompute Phase 3 without changing model weights."
        )
    )
    parser.add_argument(
        "--source-run-dir",
        required=True,
        help="Completed Stage 5A.2/5A.3 source run containing the frozen candidate snapshot.",
    )
    parser.add_argument(
        "--recovery-run-dir",
        required=True,
        help="Fresh isolated Stage 5A.4.1 recovery directory.",
    )
    parser.add_argument(
        "--execute-recovery",
        action="store_true",
        help="Run providers and the two-pass Phase 3 recovery. Without this flag only preflight/normalization runs.",
    )
    parser.add_argument("--disable-string", action="store_true")
    parser.add_argument("--disable-bvbrc", action="store_true")
    parser.add_argument(
        "--online-source-mode",
        default="online_strict",
        choices=provider_mode_choices(),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_stage5a41_provider_scoring_recovery(
            project_root=PROJECT_ROOT,
            source_run_dir=Path(args.source_run_dir),
            recovery_run_dir=Path(args.recovery_run_dir),
            execute_recovery=args.execute_recovery,
            enable_string=not args.disable_string,
            enable_bvbrc=not args.disable_bvbrc,
            online_source_mode=args.online_source_mode,
        )
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=True, default=str))
    return 0 if result.get("status") in {"preflight_completed", "completed"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
