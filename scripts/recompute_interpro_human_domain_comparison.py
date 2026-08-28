from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from nodos_funcionales.config import load_config
from nodos_funcionales.interpro_human_domain import (
    build_comparison_table,
    fetch_human_interpro_catalog,
    write_catalog_snapshot,
)


def _read_cached_catalog(path: Path) -> tuple[set[str], dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = {
        str(value).strip().upper()
        for value in payload.get("entries", [])
        if str(value).strip().upper().startswith("IPR")
    }
    if not entries:
        raise ValueError(f"cached human InterPro catalog contains no entries: {path}")
    manifest = {
        key: value
        for key, value in payload.items()
        if key not in {"entries", "sha256"}
    }
    manifest["cache_reused"] = True
    return entries, manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare frozen bacterial InterPro annotations against an auditable "
            "catalog of InterPro entries observed in human proteins. The output "
            "is audit-only and does not change Phase 3 scoring."
        )
    )
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument(
        "--provider-base-url",
        default="https://www.ebi.ac.uk/interpro/api",
    )
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--page-size", type=int, default=200)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--retry-backoff-seconds", type=float, default=2.0)
    parser.add_argument(
        "--reuse-catalog",
        action="store_true",
        help="Reuse results/interpro_human_domain_catalog.json instead of the network.",
    )
    args = parser.parse_args()

    workspace = args.workspace.expanduser().resolve()
    config_path = workspace / "config" / "params.yaml"
    config = load_config(config_path)
    external_dir = workspace / config["layer_resolution"]["external_data_dir"]
    host_annotation_path = external_dir / "host_annotation.csv"
    if not host_annotation_path.is_file():
        raise FileNotFoundError(f"host annotation not found: {host_annotation_path}")

    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = results_dir / "interpro_human_domain_catalog.json"

    if args.reuse_catalog:
        human_catalog, catalog_manifest = _read_cached_catalog(catalog_path)
    else:
        human_catalog, catalog_manifest = fetch_human_interpro_catalog(
            args.provider_base_url,
            timeout_seconds=args.timeout_seconds,
            page_size=args.page_size,
            max_attempts=args.max_attempts,
            retry_backoff_seconds=args.retry_backoff_seconds,
        )
        catalog_manifest["cache_reused"] = False
        catalog_manifest = write_catalog_snapshot(
            catalog_path,
            human_catalog,
            catalog_manifest,
        )

    host_annotation = pd.read_csv(host_annotation_path, low_memory=False)
    comparison = build_comparison_table(host_annotation, human_catalog)
    output_path = results_dir / "interpro_human_domain_comparison.csv"
    comparison.to_csv(output_path, index=False)

    completed = comparison[
        "interpro_human_comparison_status"
    ].eq("complete_taxon_catalog_comparison")
    empirical = pd.to_numeric(
        comparison["domain_overlap_score_empirical"], errors="coerce"
    )
    manifest = {
        "provider": "interpro_api",
        "human_taxon_id": "9606",
        "source_host_annotation": str(host_annotation_path),
        "human_catalog_snapshot": str(catalog_path),
        "comparison_output": str(output_path),
        "input_rows": int(len(host_annotation)),
        "complete_comparison_rows": int(completed.sum()),
        "missing_bacterial_annotation_rows": int((~completed).sum()),
        "empirical_score_rows": int(empirical.notna().sum()),
        "empirical_score_mean": (
            float(empirical.mean()) if empirical.notna().any() else None
        ),
        "domain_overlap_score_promoted_to_phase3": False,
        "scoring_effect": "none_pending_calibration",
        "interpretation": (
            "The empirical score is the fraction of bacterial InterPro entries "
            "also observed in the human taxonomy catalog. It is not a calibrated "
            "toxicity probability and is not promoted to Phase 3 by this script."
        ),
        "catalog": catalog_manifest,
    }
    manifest_path = results_dir / "interpro_human_domain_comparison_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(manifest, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
