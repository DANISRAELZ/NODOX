from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.online.provider_modes import normalize_provider_mode, provider_mode_choices
from src.nodos_funcionales.standard_validation import run_standard_validation


def load_organism_registry(path: Path | None = None) -> dict[str, dict[str, Any]]:
    registry_path = path or PROJECT_ROOT / "config" / "online_only_organisms.json"
    with registry_path.open(encoding="utf-8") as handle:
        registry = json.load(handle)
    if not isinstance(registry, dict):
        raise ValueError("online-only organism registry must be a JSON object")
    return registry


def resolve_organism_options(args: argparse.Namespace, registry_path: Path | None = None) -> dict[str, Any]:
    configured: dict[str, Any] = {}
    if args.organism_key:
        registry = load_organism_registry(registry_path)
        if args.organism_key not in registry:
            choices = ", ".join(sorted(registry))
            raise ValueError(f"unknown organism key {args.organism_key!r}; available keys: {choices}")
        configured.update(registry[args.organism_key])

    for key in ("organism", "organism_slug", "taxon_id", "strain", "strain_slug", "proteome_id"):
        value = getattr(args, key)
        if value is not None:
            configured[key] = value
    if not configured.get("organism"):
        raise ValueError("provide --organism or --organism-key")
    return configured


def validate_complete_snapshot_cli_contract(
    *,
    max_candidates: int,
    candidate_seed_snapshot: str | None,
    expected_proteome_id: str | None,
) -> None:
    """Prevent a legacy bounded snapshot from being reported as a complete proteome run."""
    if int(max_candidates) != 0 or not candidate_seed_snapshot:
        return

    snapshot_dir = Path(candidate_seed_snapshot).expanduser().resolve()
    manifest_path = snapshot_dir / "snapshot_manifest.json"
    if not manifest_path.is_file():
        raise ValueError(
            "complete-proteome mode requires candidate snapshot metadata at snapshot_manifest.json"
        )
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    snapshot_proteome = str(manifest.get("proteome_id") or "").strip().upper()
    candidate_scope = str(manifest.get("candidate_scope") or "").strip()
    query_semantics = str(manifest.get("query_semantics") or "").strip()
    snapshot_requested_max = manifest.get("requested_max_candidates")

    if (
        not snapshot_proteome
        or candidate_scope != "complete_exact_proteome"
        or query_semantics != "proteome_id_exact_no_species_broadening"
        or snapshot_requested_max != 0
    ):
        raise ValueError(
            "--max-candidates=0 cannot reuse a legacy or bounded candidate snapshot; "
            "the snapshot must explicitly declare a complete exact proteome"
        )

    expected = str(expected_proteome_id or "").strip().upper()
    if expected and snapshot_proteome != expected:
        raise ValueError(
            f"candidate snapshot proteome mismatch: expected {expected}, found {snapshot_proteome}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the standard NODOX validation flow. Publication benchmarks should use an exact "
            "strain/proteome identity and the complete candidate universe."
        )
    )
    parser.add_argument("--organism", help="Scientific organism name.")
    parser.add_argument("--organism-slug", help="Stable lowercase slug used in output paths.")
    parser.add_argument("--taxon-id", type=int, help="NCBI taxonomy identifier for the requested strain/proteome.")
    parser.add_argument("--strain", help="Optional strain or isolate name.")
    parser.add_argument("--strain-slug", help="Optional stable lowercase strain slug.")
    parser.add_argument(
        "--proteome-id",
        help=(
            "Exact UniProt proteome identifier (for example UP000000625). Required when "
            "--max-candidates=0 unless an exact candidate snapshot is supplied."
        ),
    )
    parser.add_argument("--organism-key", help="Key from config/online_only_organisms.json.")
    parser.add_argument("--run-dir", help="Optional isolated output directory.")
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=0,
        help=(
            "Candidate limit inside the exact proteome. 0 means the complete exact proteome; "
            "positive values are intended only for bounded smoke tests."
        ),
    )
    parser.add_argument(
        "--candidate-seed-snapshot",
        help=(
            "Validated versioned UniProt candidate-seed snapshot directory. "
            "Reuse is reported as snapshot_reused, not as live API success."
        ),
    )
    parser.add_argument("--disable-string", action="store_true", help="Record STRING as disabled and unresolved.")
    parser.add_argument("--disable-interpro", action="store_true", help="Record InterPro as disabled and unresolved.")
    parser.add_argument("--disable-literature", action="store_true", help="Record literature lookup as disabled and unresolved.")
    parser.add_argument("--disable-vfdb", action="store_true", help="Do not inspect or use the configured local VFDB dataset.")
    parser.add_argument("--disable-deg", action="store_true", help="Do not inspect or use the configured local DEG dataset.")
    parser.add_argument("--disable-bvbrc", action="store_true", help="Do not query the BV-BRC API.")
    parser.add_argument("--vfdb-dataset", help="Versioned local VFDB CSV/TSV used by this isolated run.")
    parser.add_argument("--deg-dataset", help="Versioned local DEG CSV/TSV used by this isolated run.")
    parser.add_argument(
        "--online-source-mode",
        default="online_strict",
        choices=provider_mode_choices(),
    )
    parser.add_argument(
        "--taxon-resolution-mode",
        default="online_optional",
        choices=["online_optional", "cache_first", "offline_only", "local", "api_stub", "auto"],
    )
    parser.add_argument("--refresh-taxon-cache", action="store_true")
    parser.add_argument("--write-taxon-cache", action="store_true")
    parser.add_argument("--materialize-unresolved-required-fallback", action="store_true")
    parser.add_argument(
        "--enable-diamond",
        action="store_true",
        help="Explicitly enable the DIAMOND human-homology provider for this run only.",
    )
    parser.add_argument(
        "--diamond-execution-mode",
        default="execute",
        choices=["execute", "cache_only"],
        help="Execute DIAMOND or reuse an explicitly supplied cached TSV.",
    )
    parser.add_argument("--diamond-reference-fasta", help="Real human reference FASTA (.faa or .faa.gz).")
    parser.add_argument("--diamond-database-prefix", help="Local DIAMOND database prefix, without .dmnd.")
    parser.add_argument("--diamond-cached-tsv", help="Validated cached DIAMOND TSV for cache_only mode.")
    parser.add_argument("--diamond-candidate-fasta", help="Optional existing candidate FASTA.")
    parser.add_argument("--diamond-executable", default="diamond", help="DIAMOND command or executable path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        organism_options = resolve_organism_options(args)
        validate_complete_snapshot_cli_contract(
            max_candidates=args.max_candidates,
            candidate_seed_snapshot=args.candidate_seed_snapshot,
            expected_proteome_id=organism_options.get("proteome_id"),
        )
    except (ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    try:
        result = run_standard_validation(
            project_root=PROJECT_ROOT,
            **organism_options,
            run_dir=Path(args.run_dir) if args.run_dir else None,
            max_candidates=args.max_candidates,
            candidate_seed_snapshot=args.candidate_seed_snapshot,
            enable_string=not args.disable_string,
            enable_interpro=not args.disable_interpro,
            enable_literature=not args.disable_literature,
            enable_vfdb=not args.disable_vfdb,
            enable_deg=not args.disable_deg,
            enable_bvbrc=not args.disable_bvbrc,
            vfdb_dataset=args.vfdb_dataset,
            deg_dataset=args.deg_dataset,
            online_source_mode=normalize_provider_mode(args.online_source_mode),
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
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=True, default=str))
    return 0 if result["pipeline_status"] in {"completed", "completed_after_unresolved_fallback"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
