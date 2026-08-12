from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.stage5a3_rank_trace import run_stage5a3_rank_trace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run NODOX Stage 5A.3 as a read-only ranking traceability audit over "
            "an already-completed Stage 5A.2 run."
        )
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help=(
            "Existing Stage 5A.2 run directory, for example "
            "results/20260812_hpylori_26695_stage5a2_blind."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_stage5a3_rank_trace(Path(args.run_dir))
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
