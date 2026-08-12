from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.stage5a4_evidence_recovery import run_stage5a4_evidence_recovery


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit and optionally recover score-relevant evidence for a completed NODOX Stage 5A.2/5A.3 run "
            "while reusing the frozen candidate snapshot and preserving model weights."
        )
    )
    parser.add_argument("--source-run-dir", required=True, help="Completed Stage 5A.2 run directory.")
    parser.add_argument("--recovery-run-dir", help="Separate output directory for Stage 5A.4 recovery.")
    parser.add_argument(
        "--execute-recovery",
        action="store_true",
        help="Retry provider enrichment and Phase 3 scoring on the frozen Stage 5A.2 candidate snapshot.",
    )
    parser.add_argument(
        "--vfdb-dataset",
        help="Optional VFDB dataset path. If omitted, Stage 5A.4 checks the project-root configured data_external path.",
    )
    parser.add_argument(
        "--deg-dataset",
        help="Optional DEG dataset path. If omitted, Stage 5A.4 checks the project-root configured data_external path.",
    )
    parser.add_argument("--disable-string", action="store_true")
    parser.add_argument("--disable-bvbrc", action="store_true")
    parser.add_argument("--online-source-mode", default="online_strict")
    parser.add_argument("--enable-diamond", action="store_true")
    parser.add_argument("--diamond-execution-mode", default="execute", choices=["execute", "cache_only"])
    parser.add_argument("--diamond-reference-fasta")
    parser.add_argument("--diamond-database-prefix")
    parser.add_argument("--diamond-cached-tsv")
    parser.add_argument("--diamond-executable", default="diamond")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_stage5a4_evidence_recovery(
            project_root=PROJECT_ROOT,
            source_run_dir=Path(args.source_run_dir),
            recovery_run_dir=Path(args.recovery_run_dir) if args.recovery_run_dir else None,
            execute_recovery=args.execute_recovery,
            vfdb_dataset=args.vfdb_dataset,
            deg_dataset=args.deg_dataset,
            enable_string=not args.disable_string,
            enable_bvbrc=not args.disable_bvbrc,
            enable_diamond=args.enable_diamond,
            diamond_execution_mode=args.diamond_execution_mode,
            diamond_reference_fasta=args.diamond_reference_fasta,
            diamond_database_prefix=args.diamond_database_prefix,
            diamond_cached_tsv=args.diamond_cached_tsv,
            diamond_executable=args.diamond_executable,
            online_source_mode=args.online_source_mode,
        )
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=True, default=str))
    status = str(result.get("pipeline_status") or result.get("status") or "")
    return 0 if status in {"preflight_completed", "completed", "completed_after_unresolved_fallback"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
