from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.online_only_validation import run_pseudomonas_online_only_validation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run isolated online-only validation for Pseudomonas aeruginosa.")
    parser.add_argument("--run-dir", help="Optional isolated run directory under results/online_only_runs.")
    parser.add_argument("--max-seed-candidates", type=int, default=25, help="Bounded UniProt candidate seed size.")
    parser.add_argument(
        "--online-source-mode",
        default="online_optional",
        choices=["online_optional", "cache_first", "offline_only", "local", "api_stub", "auto"],
        help="External provider mode for this isolated run.",
    )
    parser.add_argument(
        "--taxon-resolution-mode",
        default="online_optional",
        choices=["online_optional", "cache_first", "offline_only", "local", "api_stub", "auto"],
        help="Taxonomy resolution mode for this isolated run.",
    )
    parser.add_argument("--refresh-taxon-cache", action="store_true")
    parser.add_argument("--write-taxon-cache", action="store_true", help="Allow writing taxonomy cache for this run.")
    parser.add_argument(
        "--materialize-unresolved-required-fallback",
        action="store_true",
        help="Create explicit unresolved external required layers if live providers cannot be used.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_pseudomonas_online_only_validation(
        project_root=PROJECT_ROOT,
        run_dir=Path(args.run_dir) if args.run_dir else None,
        max_seed_candidates=args.max_seed_candidates,
        online_source_mode=args.online_source_mode,
        taxon_resolution_mode=args.taxon_resolution_mode,
        refresh_taxon_cache=args.refresh_taxon_cache,
        no_write_taxon_cache=not args.write_taxon_cache,
        materialize_unresolved_required_fallback=args.materialize_unresolved_required_fallback,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    if result["pipeline_status"] in {"completed", "completed_after_unresolved_fallback"}:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
