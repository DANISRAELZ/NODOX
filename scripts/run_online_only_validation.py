from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.online_only_validation import run_online_only_validation


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

    for key in ("organism", "organism_slug", "taxon_id", "strain", "strain_slug"):
        value = getattr(args, key)
        if value is not None:
            configured[key] = value
    if not configured.get("organism"):
        raise ValueError("provide --organism or --organism-key")
    return configured


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run isolated online-only validation for a configured organism.")
    parser.add_argument("--organism", help="Scientific organism name.")
    parser.add_argument("--organism-slug", help="Stable lowercase slug used in output paths.")
    parser.add_argument("--taxon-id", type=int, help="NCBI taxonomy identifier used by online providers.")
    parser.add_argument("--strain", help="Optional strain or isolate name.")
    parser.add_argument("--strain-slug", help="Optional stable lowercase strain slug.")
    parser.add_argument("--organism-key", help="Key from config/online_only_organisms.json.")
    parser.add_argument("--run-dir", help="Optional isolated output directory.")
    parser.add_argument("--max-candidates", type=int, default=25, help="Bounded UniProt candidate seed size.")
    parser.add_argument("--disable-string", action="store_true", help="Record STRING as disabled and unresolved.")
    parser.add_argument("--disable-interpro", action="store_true", help="Record InterPro as disabled and unresolved.")
    parser.add_argument("--disable-literature", action="store_true", help="Record literature lookup as disabled and unresolved.")
    parser.add_argument(
        "--online-source-mode",
        default="online_optional",
        choices=["online_optional", "cache_first", "offline_only", "local", "api_stub", "auto"],
    )
    parser.add_argument(
        "--taxon-resolution-mode",
        default="online_optional",
        choices=["online_optional", "cache_first", "offline_only", "local", "api_stub", "auto"],
    )
    parser.add_argument("--refresh-taxon-cache", action="store_true")
    parser.add_argument("--write-taxon-cache", action="store_true")
    parser.add_argument("--materialize-unresolved-required-fallback", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        organism_options = resolve_organism_options(args)
    except ValueError as exc:
        parser.error(str(exc))

    result = run_online_only_validation(
        project_root=PROJECT_ROOT,
        **organism_options,
        run_dir=Path(args.run_dir) if args.run_dir else None,
        max_candidates=args.max_candidates,
        enable_string=not args.disable_string,
        enable_interpro=not args.disable_interpro,
        enable_literature=not args.disable_literature,
        online_source_mode=args.online_source_mode,
        taxon_resolution_mode=args.taxon_resolution_mode,
        refresh_taxon_cache=args.refresh_taxon_cache,
        no_write_taxon_cache=not args.write_taxon_cache,
        materialize_unresolved_required_fallback=args.materialize_unresolved_required_fallback,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result["pipeline_status"] in {"completed", "completed_after_unresolved_fallback"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
