from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.online.provider_modes import provider_mode_choices
from src.nodos_funcionales.stage5a2_candidate_discovery import (
    PROVIDER_PROFILES,
    parse_benchmark_alias_specs,
    run_stage5a2_validation,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run NODOX Stage 5A.2 with strain/proteome-scoped discovery, explicit exact "
            "benchmark aliases and a resilient full-proteome scoring profile."
        )
    )
    parser.add_argument("--organism", required=True, help="Scientific organism name.")
    parser.add_argument("--taxon-id", required=True, type=int, help="NCBI taxonomy identifier, preferably strain-specific.")
    parser.add_argument("--proteome-id", help="Optional UniProt proteome identifier, for example UP000000429.")
    parser.add_argument("--organism-slug", help="Optional stable output slug.")
    parser.add_argument("--strain", help="Optional strain or isolate name.")
    parser.add_argument("--strain-slug", help="Optional stable strain slug.")
    parser.add_argument("--run-dir", help="Optional isolated output directory.")
    parser.add_argument("--max-candidates", type=int, default=0, help="Use 0 (default) to retrieve the complete result set within the selected scope.")
    parser.add_argument("--page-size", type=int, default=500, help="UniProt page size (1-500; default 500).")
    parser.add_argument("--benchmark-mode", choices=["blind", "conditional"], default="blind")
    parser.add_argument(
        "--benchmark-candidate",
        action="append",
        default=[],
        help="Canonical benchmark label. Repeat for multiple targets.",
    )
    parser.add_argument(
        "--benchmark-alias",
        action="append",
        default=[],
        help=(
            "Exact benchmark identity alias using CANONICAL=ALIAS or CANONICAL=ALIAS1,ALIAS2. "
            "In blind mode aliases label already-discovered records only; they never trigger retrieval or injection."
        ),
    )
    parser.add_argument(
        "--provider-profile",
        choices=sorted(PROVIDER_PROFILES),
        default="benchmark_resilient",
        help=(
            "benchmark_resilient skips InterPro and literature metadata because they are non-scoring in the current "
            "pipeline and can block full-proteome throughput; full preserves existing orchestration."
        ),
    )
    parser.add_argument("--online-source-mode", default="online_strict", choices=provider_mode_choices())
    parser.add_argument("--disable-string", action="store_true")
    parser.add_argument("--disable-interpro", action="store_true")
    parser.add_argument("--disable-literature", action="store_true")
    parser.add_argument("--disable-vfdb", action="store_true")
    parser.add_argument("--disable-deg", action="store_true")
    parser.add_argument("--disable-bvbrc", action="store_true")
    parser.add_argument("--vfdb-dataset")
    parser.add_argument("--deg-dataset")
    parser.add_argument(
        "--taxon-resolution-mode",
        default="online_optional",
        choices=["online_optional", "cache_first", "offline_only", "local", "api_stub", "auto"],
    )
    parser.add_argument("--refresh-taxon-cache", action="store_true")
    parser.add_argument("--write-taxon-cache", action="store_true")
    parser.add_argument("--materialize-unresolved-required-fallback", action="store_true")
    parser.add_argument("--enable-diamond", action="store_true")
    parser.add_argument("--diamond-execution-mode", default="execute", choices=["execute", "cache_only"])
    parser.add_argument("--diamond-reference-fasta")
    parser.add_argument("--diamond-database-prefix")
    parser.add_argument("--diamond-cached-tsv")
    parser.add_argument("--diamond-candidate-fasta")
    parser.add_argument("--diamond-executable", default="diamond")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_candidates < 0:
        parser.error("--max-candidates must be zero or positive")
    if not 1 <= args.page_size <= 500:
        parser.error("--page-size must be between 1 and 500")
    try:
        aliases = parse_benchmark_alias_specs(args.benchmark_alias)
        result = run_stage5a2_validation(
            project_root=PROJECT_ROOT,
            organism=args.organism,
            taxon_id=args.taxon_id,
            proteome_id=args.proteome_id,
            organism_slug=args.organism_slug,
            strain=args.strain,
            strain_slug=args.strain_slug,
            run_dir=Path(args.run_dir) if args.run_dir else None,
            max_candidates=args.max_candidates,
            page_size=args.page_size,
            benchmark_mode=args.benchmark_mode,
            benchmark_candidates=args.benchmark_candidate,
            benchmark_aliases=aliases,
            provider_profile=args.provider_profile,
            online_source_mode=args.online_source_mode,
            enable_string=not args.disable_string,
            enable_interpro=not args.disable_interpro,
            enable_literature=not args.disable_literature,
            enable_vfdb=not args.disable_vfdb,
            enable_deg=not args.disable_deg,
            enable_bvbrc=not args.disable_bvbrc,
            vfdb_dataset=args.vfdb_dataset,
            deg_dataset=args.deg_dataset,
            taxon_resolution_mode=args.taxon_resolution_mode,
            refresh_taxon_cache=args.refresh_taxon_cache,
            no_write_taxon_cache=not args.write_taxon_cache,
            materialize_unresolved_required_fallback=args.materialize_unresolved_required_fallback,
            enable_diamond=args.enable_diamond,
            diamond_execution_mode=args.diamond_execution_mode,
            diamond_reference_fasta=args.diamond_reference_fasta,
            diamond_database_prefix=args.diamond_database_prefix,
            diamond_cached_tsv=args.diamond_cached_tsv,
            diamond_candidate_fasta=args.diamond_candidate_fasta,
            diamond_executable=args.diamond_executable,
        )
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result.get("pipeline_status") in {"completed", "completed_after_unresolved_fallback"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
