from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.discovery import resolve_taxon
from src.nodos_funcionales.io_errors import explain_cli_error
from src.nodos_funcionales.online_history import append_online_history, write_online_source_comparison
from src.nodos_funcionales.online_reporting import (
    build_before_after_ranking_audit,
    snapshot_pre_enrichment_state,
)
from src.nodos_funcionales.online_sources import SUPPORTED_ONLINE_SOURCES, fetch_online_source
from src.nodos_funcionales.online_organism_enrichment import run_organism_online_enrichment
from src.nodos_funcionales.pipeline import run_pipeline
from src.nodos_funcionales.string_api import STRING_SOURCE_MODES


def _load_existing_profile(workspace: Path) -> dict:
    profile_path = workspace / "results" / "organism_profile.json"
    if not profile_path.exists():
        return {}
    return json.loads(profile_path.read_text(encoding="utf-8"))


def _local_alias_taxon_id(organism: str) -> str | None:
    aliases_path = PROJECT_ROOT / "config" / "taxon_aliases.json"
    if not aliases_path.exists():
        return None
    payload = json.loads(aliases_path.read_text(encoding="utf-8"))
    organism_cf = organism.strip().casefold()
    for entry in payload.get("entries", []):
        names = [entry.get("canonical_name", ""), *(entry.get("aliases", []) or [])]
        if organism_cf in {str(name).strip().casefold() for name in names}:
            return str(entry.get("taxon_id") or "").strip() or None
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recupera una fuente online opcional y la transforma al esquema interno.")
    parser.add_argument("--organism", required=True, help="Nombre del microorganismo.")
    parser.add_argument("--strain", help="Cepa opcional.")
    parser.add_argument("--workspace", required=True, help="Workspace a enriquecer.")
    parser.add_argument("--source", choices=sorted(SUPPORTED_ONLINE_SOURCES), default="string", help="Proveedor online a usar.")
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=sorted(SUPPORTED_ONLINE_SOURCES),
        help="Proveedores online a usar en modo organism-first. Ejemplo: --sources uniprot string.",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(STRING_SOURCE_MODES),
        default="cache_first",
        help="Modo de la fuente online: offline_only, cache_first u online_optional.",
    )
    parser.add_argument("--refresh-online-cache", action="store_true", help="Fuerza refresco ignorando cache existente.")
    parser.add_argument("--force-refresh", action="store_true", help="Alias de --refresh-online-cache para el modo organism-first.")
    parser.add_argument("--no-write-online-cache", action="store_true", help="No escribe el resultado en cache local.")
    parser.add_argument("--invalidate-cache-key", help="Invalida selectivamente una entrada de cache conocida antes del fetch.")
    parser.add_argument("--invalidate-cache-protein-id", help="Invalida entradas de cache asociadas a una proteina concreta.")
    parser.add_argument("--replace-existing-functional-network", action="store_true", help="Reemplaza functional_network.csv aunque exista.")
    parser.add_argument(
        "--pipeline-mode",
        choices=["legacy", "phase2", "compare"],
        default="compare",
        help="Modo del pipeline a reejecutar tras el enriquecimiento online.",
    )
    parser.add_argument(
        "--skip-pipeline-rerun",
        action="store_true",
        help="Evita la reejecucion del pipeline tras el enriquecimiento online.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except (FileNotFoundError, PermissionError, OSError, ValueError) as exc:
        print(explain_cli_error(exc, "fetch_online_data.py"), file=sys.stderr)
        return 1


def _main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    workspace = Path(args.workspace)
    if args.sources:
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "config").mkdir(parents=True, exist_ok=True)
        config_target = workspace / "config" / "params.yaml"
        if not config_target.exists():
            shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", config_target)
        (workspace / "data_raw").mkdir(parents=True, exist_ok=True)
        (workspace / "results").mkdir(parents=True, exist_ok=True)
    elif not workspace.exists():
        raise FileNotFoundError(f"Workspace no encontrado: {workspace}")

    config_path = workspace / "config" / "params.yaml"
    config = load_config(config_path if config_path.exists() else PROJECT_ROOT / "config" / "params.yaml")

    existing_profile = _load_existing_profile(workspace)
    taxon_id = existing_profile.get("taxon_id")
    if not taxon_id:
        taxon_profile = resolve_taxon(
            PROJECT_ROOT,
            args.organism,
            args.strain,
            resolution_mode="cache_first",
            config=config,
        )
        taxon_id = taxon_profile.get("taxon_id")
    if not taxon_id:
        taxon_id = _local_alias_taxon_id(args.organism)
    if args.sources and not taxon_id and args.mode != "offline_only":
        taxon_profile = resolve_taxon(
            PROJECT_ROOT,
            args.organism,
            args.strain,
            resolution_mode=args.mode,
            config=config,
            refresh_cache=bool(args.force_refresh or args.refresh_online_cache),
        )
        taxon_id = taxon_profile.get("taxon_id")

    if args.sources:
        result = run_organism_online_enrichment(
            workspace=workspace,
            organism_name=args.organism,
            strain=args.strain,
            taxon_id=taxon_id,
            config=config,
            sources=args.sources,
            mode=args.mode,
            force_refresh=bool(args.force_refresh or args.refresh_online_cache),
        )
        print("[OK] Organism-first online enrichment complete")
        print(f"[OK] Organism: {args.organism}")
        print(f"[OK] Taxon id: {taxon_id or 'unknown'}")
        print(f"[OK] Report: {result['report_path']}")
        print(f"[OK] Audit: {result['audit_path']}")
        for summary in result["summaries"]:
            print(f"[OK] {summary.layer}: {summary.rows} rows ({summary.status}) -> {summary.path}")
            for note in summary.notes:
                if note:
                    print(f"[WARN] {summary.layer}: {note}")
        return 0
    if not taxon_id:
        taxon_profile = resolve_taxon(
            PROJECT_ROOT,
            args.organism,
            args.strain,
            resolution_mode="offline_only",
            config=config,
            refresh_cache=True,
            no_write_cache=True,
        )
        taxon_id = taxon_profile.get("taxon_id")

    if args.invalidate_cache_key:
        if args.source == "string":
            from src.nodos_funcionales.string_api import invalidate_string_cache_entry

            invalidate_string_cache_entry(workspace, config, args.invalidate_cache_key)
        elif args.source == "uniprot":
            from src.nodos_funcionales.uniprot_api import invalidate_uniprot_cache_entry

            invalidate_uniprot_cache_entry(workspace, config, args.invalidate_cache_key)

    if args.invalidate_cache_protein_id:
        if args.source == "string":
            from src.nodos_funcionales.string_api import invalidate_string_cache_entries_for_protein

            removed_count = invalidate_string_cache_entries_for_protein(workspace, config, args.invalidate_cache_protein_id)
        elif args.source == "uniprot":
            from src.nodos_funcionales.uniprot_api import invalidate_uniprot_cache_entries_for_protein

            removed_count = invalidate_uniprot_cache_entries_for_protein(workspace, config, args.invalidate_cache_protein_id)
        else:
            removed_count = 0
        print(f"[OK] Cache entries invalidated for protein: {removed_count}")

    snapshot_pre_enrichment_state(workspace, args.source)

    result = fetch_online_source(
        source=args.source,
        workspace=workspace,
        organism_name=args.organism,
        taxon_id=taxon_id,
        config=config,
        mode=args.mode,
        refresh_cache=args.refresh_online_cache,
        no_write_cache=args.no_write_online_cache,
        replace_existing=args.replace_existing_functional_network,
    )

    pipeline_rerun_status = "skipped"
    if not args.skip_pipeline_rerun:
        try:
            summary = run_pipeline(
                workspace,
                config_path if config_path.exists() else PROJECT_ROOT / "config" / "params.yaml",
                mode=args.pipeline_mode,
            )
            pipeline_rerun_status = f"ok ({summary['score_rows']} scored rows)"
        except Exception as exc:  # pragma: no cover
            pipeline_rerun_status = f"failed: {exc}"

    manifest = result["manifest"]
    print(f"[OK] Source: {manifest['source']}")
    print(f"[OK] Source used: {manifest['source_used']}")
    print(f"[OK] Cache hit: {manifest['cache_hit']}")
    print(f"[OK] API success: {manifest['api_success']}")
    print(f"[OK] Manifest: {result['manifest_path']}")
    print(f"[OK] Report: {result['report_path']}")
    if manifest.get("output_path"):
        print(f"[OK] functional_network.csv: {manifest['output_path']}")
    else:
        print("[INFO] Esta fuente no escribio functional_network.csv o se mantuvo el archivo existente.")
    print(f"[OK] Pipeline rerun: {pipeline_rerun_status}")
    impact_paths = build_before_after_ranking_audit(workspace)
    if impact_paths is not None:
        print(f"[OK] Online impact CSV: {impact_paths[0]}")
        print(f"[OK] Online impact Markdown: {impact_paths[1]}")
    history_path = append_online_history(workspace, manifest)
    comparison_paths = write_online_source_comparison(workspace)
    print(f"[OK] Online history: {history_path}")
    print(f"[OK] Online source comparison CSV: {comparison_paths[0]}")
    print(f"[OK] Online source comparison Markdown: {comparison_paths[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
