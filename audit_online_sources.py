from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.online_audit import run_experimental_online_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ejecuta una auditoria experimental fresh vs cache por fuentes online.")
    parser.add_argument("--organism", required=True, help="Nombre del microorganismo.")
    parser.add_argument("--strain", help="Cepa opcional.")
    parser.add_argument("--workspace", required=True, help="Workspace base a auditar.")
    parser.add_argument("--sources", nargs="+", default=["string", "uniprot"], help="Fuentes online a comparar.")
    parser.add_argument("--mode", choices=["offline_only", "cache_first", "online_optional"], default="online_optional")
    parser.add_argument("--pipeline-mode", choices=["legacy", "phase2", "compare"], default="compare")
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Fuerza refresh API y evita lectura de cache en escenarios online; incompatible con --compare-fresh-vs-cache.",
    )
    parser.add_argument("--disable-cache-read", action="store_true", help="Impide lectura de cache en escenarios fresh.")
    parser.add_argument("--disable-cache-write", action="store_true", help="Impide escritura de cache durante la auditoria.")
    parser.add_argument("--reset-history", action="store_true", help="Limpia artefactos online en los clones antes de correr.")
    parser.add_argument("--run-pipeline", action="store_true", help="Compat flag; el pipeline se ejecuta por defecto salvo dry-run.")
    parser.add_argument("--compare-fresh-vs-cache", action="store_true", help="Agrega escenarios cache para contrastar con escenarios fresh.")
    parser.add_argument("--dry-run", action="store_true", help="Construye escenarios sin ejecutar fetches ni pipeline.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = Path(args.workspace)
    if not workspace.exists():
        raise FileNotFoundError(f"Workspace no encontrado: {workspace}")

    audit_df, fresh_vs_cache_df, candidate_shifts_df, paths = run_experimental_online_audit(
        project_root=PROJECT_ROOT,
        workspace=workspace,
        organism_name=args.organism,
        strain=args.strain,
        sources=args.sources,
        mode=args.mode,
        pipeline_mode=args.pipeline_mode,
        force_refresh=args.force_refresh,
        disable_cache_read=args.disable_cache_read,
        disable_cache_write=args.disable_cache_write,
        reset_history=args.reset_history,
        run_pipeline_flag=not args.dry_run,
        compare_fresh_vs_cache=args.compare_fresh_vs_cache,
        dry_run=args.dry_run,
    )
    print(f"[OK] Scenarios audited: {len(audit_df)}")
    print(f"[OK] Fresh audit CSV: {paths['fresh_csv']}")
    print(f"[OK] Fresh audit Markdown: {paths['fresh_md']}")
    print(f"[OK] Fresh vs cache CSV: {paths['compare_csv']}")
    print(f"[OK] Fresh vs cache Markdown: {paths['compare_md']}")
    print(f"[OK] Candidate shifts CSV: {paths['candidate_shifts_csv']}")
    print(f"[OK] Fresh vs cache rows: {len(fresh_vs_cache_df)}")
    print(f"[OK] Candidate shifts rows: {len(candidate_shifts_df)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
