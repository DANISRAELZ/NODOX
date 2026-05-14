from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.discovery import ACQUISITION_MODES, STRATEGY_CHOICES, TAXON_RESOLUTION_MODES, prepare_discovery_workspace
from src.nodos_funcionales.online.provider_modes import accepted_provider_modes
from src.nodos_funcionales.pipeline import run_pipeline
from src.nodos_funcionales.runtime import VALID_PIPELINE_MODES, resolve_pipeline_mode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Entrada multiorganismo para priorizacion explicable de blancos terapeuticos bacterianos.")
    parser.add_argument("--organism", required=True, help="Nombre del organismo bacteriano.")
    parser.add_argument("--strain", help="Cepa opcional.")
    parser.add_argument("--strategy", choices=sorted(STRATEGY_CHOICES), help="Estrategia preferida opcional.")
    parser.add_argument(
        "--acquisition-mode",
        choices=sorted(ACQUISITION_MODES),
        default="semi_auto",
        help="Modo de adquisicion: manual, semi_auto o auto.",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(VALID_PIPELINE_MODES),
        default="compare",
        help="Modo del pipeline existente: default, legacy, phase2, compare o phase3.",
    )
    parser.add_argument("--workspace", help="Ruta opcional del workspace independiente del organismo/cepa.")
    parser.add_argument(
        "--analysis-mode",
        default="user_data_plus_external",
        help="Etiqueta opcional de analisis para documentar el enfoque del workspace; no cambia la logica actual.",
    )
    parser.add_argument(
        "--allow-demo-data",
        action="store_true",
        help=(
            "Permite usar demos empaquetados solo si coinciden con el organismo/cepa; "
            "no define un organismo por defecto."
        ),
    )
    parser.add_argument(
        "--taxon-resolution-mode",
        choices=sorted(TAXON_RESOLUTION_MODES),
        help="Modo de resolucion taxonomica: offline_only, cache_first, online_optional, api_stub o auto.",
    )
    parser.add_argument("--refresh-taxon-cache", action="store_true", help="Ignora una entrada existente y vuelve a resolver taxonomia.")
    parser.add_argument("--no-write-taxon-cache", action="store_true", help="No escribe la resolucion obtenida en el cache local.")
    parser.add_argument("--offline-only", action="store_true", help="Alias rapido para forzar taxonomia sin llamadas de red.")
    parser.add_argument(
        "--online-source-mode",
        choices=sorted(accepted_provider_modes({})),
        help="Modo para fuentes externas de capas: offline_only, local, api_stub, cache_first, online_optional o auto.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Solo prepara discovery y no corre el motor.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    resolution_mode = "offline_only" if args.offline_only else args.taxon_resolution_mode
    if args.offline_only or resolution_mode in {"offline_only", "local", "api_stub"}:
        online_source_mode = "offline_only"
    else:
        online_source_mode = args.online_source_mode

    discovery = prepare_discovery_workspace(
        project_root=PROJECT_ROOT,
        organism_name=args.organism,
        strain=args.strain,
        strategy=args.strategy,
        acquisition_mode=args.acquisition_mode,
        workspace=args.workspace,
        allow_demo_data=args.allow_demo_data,
        dry_run=args.dry_run,
        taxon_resolution_mode=resolution_mode,
        refresh_taxon_cache=args.refresh_taxon_cache,
        no_write_taxon_cache=args.no_write_taxon_cache,
    )
    manifest = discovery["manifest"]
    profile = discovery["profile"]
    workspace = discovery["workspace"]

    print(f"[OK] Organismo: {profile['organism_canonical_name']}")
    print(f"[OK] Workspace: {workspace}")
    print(f"[OK] Resolution status: {profile['taxon_resolution_status']}")
    print(f"[OK] Online source mode: {online_source_mode or 'config_default'}")
    print(f"[OK] Discovery report: {discovery['report_path']}")
    print(f"[OK] Acquisition manifest: {discovery['manifest_path']}")

    if args.dry_run:
        print("[INFO] Dry-run activo: no se ejecuta el pipeline.")
        return 0

    if not manifest["can_run_pipeline"]:
        print("[INFO] El pipeline no se ejecuto porque faltan datos obligatorios o hay restricciones de procedencia.")
        if manifest["missing_required_datasets"]:
            print("[INFO] Faltan datasets obligatorios: " + ", ".join(manifest["missing_required_datasets"]))
            print(
                "[INFO] No se encontraron candidatos terapeuticos de entrada. "
                "Proporcione una lista de genes/proteinas en las capas obligatorias o habilite datos demo/fuentes compatibles."
            )
        if manifest["warnings"]:
            print("[INFO] Advertencias: " + " | ".join(manifest["warnings"]))
        return 0

    normalized_mode = resolve_pipeline_mode({"runtime": {"pipeline_mode": "compare"}}, args.mode)
    phase3_requested = normalized_mode == "phase3"
    demo_data_used = _demo_data_used(manifest)
    if phase3_requested:
        print("[OK] Phase 3 enabled")
        if demo_data_used:
            print("[WARN] Demo data used; confidence capped")

    results = run_pipeline(
        base_dir=workspace,
        config_path=workspace / "config" / "params.yaml",
        mode=normalized_mode,
        online_source_mode=online_source_mode,
    )
    print(
        "[OK] Pipeline ejecutado: "
        f"validation_rows={results['validation_rows']}, integrated_rows={results['integrated_rows']}, "
        f"feature_rows={results['feature_rows']}, score_rows={results['score_rows']}"
    )
    print(f"[OK] Ranking principal: {workspace / 'results' / 'ranking_nodos.csv'}")
    if results.get("phase3_enabled"):
        print(f"[OK] Evolutionary escape features computed: {workspace / 'results' / 'evolutionary_escape_audit.csv'}")
        print(f"[OK] Functional Node Theory score computed: {workspace / 'data_processed' / 'phase3_features.csv'}")
        print(f"[OK] Phase 3 ranking written: {workspace / 'results' / 'ranking_nodos_phase3.csv'}")
        print(f"[OK] Phase 3 reports written: {workspace / 'results' / 'theory_of_nodes_report.md'}")
    return 0


def _demo_data_used(manifest: dict) -> bool:
    if manifest.get("demo_files_copied"):
        return True
    for dataset in manifest.get("datasets", []):
        if dataset.get("generated_by") == "packaged_demo" or dataset.get("source_type") == "demo":
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
