from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.online.provider_modes import normalize_provider_mode
from src.nodos_funcionales.online_only_validation import build_online_only_provider_audit
from src.nodos_funcionales.pipeline import run_pipeline
from src.nodos_funcionales.standard_validation import run_standard_validation
from src.nodos_funcionales.string_local_dataset import materialize_string_local_network


def _load_registry() -> dict[str, dict]:
    path = PROJECT_ROOT / "config" / "online_only_organisms.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_organism(args: argparse.Namespace) -> dict:
    values: dict = {}
    if args.organism_key:
        registry = _load_registry()
        if args.organism_key not in registry:
            raise ValueError(f"unknown organism key: {args.organism_key}")
        values.update(registry[args.organism_key])
    for key in ("organism", "organism_slug", "taxon_id", "strain", "strain_slug", "proteome_id"):
        value = getattr(args, key)
        if value is not None:
            values[key] = value
    if not values.get("organism"):
        raise ValueError("provide --organism or --organism-key")
    return values


def _existing_file(value: str | None, label: str) -> Path:
    if not value:
        raise ValueError(f"missing required {label}")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"{label} not found: {path}")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a publication-grade NODOX complete-proteome validation with versioned local STRING, "
            "DEG and VFDB evidence plus explicit DIAMOND human homology."
        )
    )
    parser.add_argument("--organism-key")
    parser.add_argument("--organism")
    parser.add_argument("--organism-slug")
    parser.add_argument("--taxon-id", type=int)
    parser.add_argument("--strain")
    parser.add_argument("--strain-slug")
    parser.add_argument("--proteome-id")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--candidate-seed-snapshot")
    parser.add_argument("--deg-dataset", required=True)
    parser.add_argument("--vfdb-dataset", required=True)
    parser.add_argument("--string-links", required=True)
    parser.add_argument("--string-aliases", required=True)
    parser.add_argument("--string-required-score", type=int, default=400)
    parser.add_argument("--diamond-execution-mode", choices=["execute", "cache_only"], default="execute")
    parser.add_argument("--diamond-reference-fasta")
    parser.add_argument("--diamond-database-prefix")
    parser.add_argument("--diamond-cached-tsv")
    parser.add_argument("--diamond-candidate-fasta")
    parser.add_argument("--diamond-executable", default="diamond")
    parser.add_argument("--online-source-mode", default="online_strict")
    parser.add_argument("--disable-interpro", action="store_true")
    parser.add_argument("--disable-literature", action="store_true")
    parser.add_argument("--disable-bvbrc", action="store_true")
    return parser


def validate_inputs(args: argparse.Namespace, organism: dict) -> dict[str, Path]:
    if not organism.get("proteome_id"):
        raise ValueError("publication validation requires an exact proteome_id")
    if not organism.get("taxon_id"):
        raise ValueError("publication validation requires an exact taxon_id")

    paths = {
        "deg": _existing_file(args.deg_dataset, "DEG dataset"),
        "vfdb": _existing_file(args.vfdb_dataset, "VFDB dataset"),
        "string_links": _existing_file(args.string_links, "STRING protein.links dataset"),
        "string_aliases": _existing_file(args.string_aliases, "STRING protein.aliases dataset"),
    }
    if args.diamond_execution_mode == "cache_only":
        paths["diamond_cached_tsv"] = _existing_file(args.diamond_cached_tsv, "DIAMOND cached TSV")
    else:
        reference_exists = bool(args.diamond_reference_fasta and Path(args.diamond_reference_fasta).expanduser().exists())
        database_exists = False
        if args.diamond_database_prefix:
            prefix = Path(args.diamond_database_prefix).expanduser()
            database_exists = prefix.exists() or Path(str(prefix) + ".dmnd").exists()
        if not (reference_exists or database_exists):
            raise ValueError("DIAMOND execute mode requires an existing human reference FASTA or database prefix")
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        organism = _resolve_organism(args)
        paths = validate_inputs(args, organism)
    except ValueError as exc:
        parser.error(str(exc))

    result = run_standard_validation(
        project_root=PROJECT_ROOT,
        **organism,
        run_dir=Path(args.run_dir),
        max_candidates=0,
        candidate_seed_snapshot=args.candidate_seed_snapshot,
        enable_string=False,
        enable_interpro=not args.disable_interpro,
        enable_literature=not args.disable_literature,
        enable_vfdb=True,
        enable_deg=True,
        enable_bvbrc=not args.disable_bvbrc,
        vfdb_dataset=paths["vfdb"],
        deg_dataset=paths["deg"],
        online_source_mode=normalize_provider_mode(args.online_source_mode),
        enable_diamond=True,
        diamond_execution_mode=args.diamond_execution_mode,
        diamond_reference_fasta=args.diamond_reference_fasta,
        diamond_database_prefix=args.diamond_database_prefix,
        diamond_cached_tsv=args.diamond_cached_tsv,
        diamond_candidate_fasta=args.diamond_candidate_fasta,
        diamond_executable=args.diamond_executable,
    )

    workspace = Path(result["workspace"])
    string_result = materialize_string_local_network(
        workspace=workspace,
        links_path=paths["string_links"],
        aliases_path=paths["string_aliases"],
        taxon_id=str(organism["taxon_id"]),
        required_score=int(args.string_required_score),
    )

    provider_manifest = dict(string_result["manifest"])
    provider_manifest.update(
        {
            "source": "string",
            "provider_name": "string_db",
            "provider_mode": "versioned_local_dataset",
            "source_used": "local_dataset",
            "retrieval_status": "local_dataset_available",
            "provider_attempted": True,
            "provider_success": True,
            "api_attempted": False,
            "api_success": False,
            "usable_evidence": bool(provider_manifest.get("affects_score")),
            "scoring_columns_used": [
                "network_centrality",
                "pathway_bottleneck_score",
                "redundancy_penalty",
                "functional_dependency_score",
            ],
        }
    )
    manifest_path = workspace / "results" / "string_functional_network_manifest.json"
    manifest_path.write_text(json.dumps(provider_manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    second_pass = run_pipeline(
        base_dir=workspace,
        config_path=workspace / "config" / "params.yaml",
        mode="phase3",
        online_source_mode=normalize_provider_mode(args.online_source_mode),
    )
    audit = build_online_only_provider_audit(workspace, {})
    audit.to_csv(workspace / "results" / "online_only_provider_audit.csv", index=False)

    publication_manifest = {
        "schema_version": "1.0",
        "status": "completed",
        "organism": organism,
        "candidate_scope": "complete_exact_proteome",
        "string_local_manifest": str(manifest_path),
        "deg_dataset": str(paths["deg"]),
        "vfdb_dataset": str(paths["vfdb"]),
        "diamond_execution_mode": args.diamond_execution_mode,
        "phase3_second_pass": second_pass,
        "technical_completion_is_biological_completion": False,
        "required_evidence_backends": ["DEG", "VFDB", "STRING local dataset", "DIAMOND"],
    }
    publication_path = workspace / "results" / "publication_validation_manifest.json"
    publication_path.write_text(json.dumps(publication_manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print(
        json.dumps(
            {
                "pipeline_status": "completed",
                "workspace": str(workspace),
                "publication_validation_manifest": str(publication_path),
                "string_mapping_coverage_fraction": string_result["manifest"]["mapping_coverage_fraction"],
                "string_interaction_edge_count": string_result["manifest"]["interaction_edge_count"],
                "phase3_second_pass": second_pass,
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
