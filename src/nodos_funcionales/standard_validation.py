from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd

from .config import load_config
from .online_http import urlopen_json
from .online.provider_modes import normalize_provider_mode
from .online_only_validation import (
    build_online_only_provider_audit,
    build_online_only_review_package,
    default_online_only_run_dir,
    run_online_only_validation,
)
from .pipeline import run_pipeline
from .stage5a4_evidence_recovery import resolve_provider_dataset
from .stage5a41_provider_scoring_recovery import (
    _mark_provider_manifest_score_effect,
    normalize_vfdb_snapshot,
    overlay_deg_essentiality,
)


STANDARD_FLOW_SCHEMA_VERSION = "1.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _slugify(value: str | None) -> str:
    import re

    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or "organism"


def _first_gene_name(entry: dict[str, Any]) -> str:
    for gene in entry.get("genes", []) or []:
        primary = gene.get("geneName", {}) or {}
        if primary.get("value"):
            return str(primary["value"]).strip()
        for key in ("orderedLocusNames", "orfNames", "synonyms"):
            for item in gene.get(key, []) or []:
                if item.get("value"):
                    return str(item["value"]).strip()
    return ""


def _stream_uniprot_proteome(
    *,
    proteome_id: str,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Retrieve one exact UniProt proteome without a species-level candidate query."""
    proteome = str(proteome_id or "").strip().upper()
    if not proteome.startswith("UP"):
        raise ValueError("proteome_id must be a UniProt proteome identifier such as UP000000625")

    cfg = config["online_sources"]["uniprot"]
    search_base = str(cfg["provider_base_url"])
    stream_base = search_base.replace("/search", "/stream")
    fields = str(cfg["fields"])
    requested_fields = [item.strip() for item in fields.split(",") if item.strip()]
    if "sequence" not in requested_fields:
        requested_fields.append("sequence")
    params = {
        "query": f"(proteome:{proteome})",
        "format": "json",
        "fields": ",".join(requested_fields),
    }
    url = f"{stream_base}?{urlencode(params)}"
    payload = urlopen_json(
        url,
        timeout=max(float(cfg.get("provider_timeout_seconds", 15)), 60.0),
        headers={
            "User-Agent": str(cfg["provider_user_agent"]),
            "Accept": "application/json",
        },
    )
    records = payload.get("results", []) if isinstance(payload, dict) else []
    if not isinstance(records, list) or not records:
        raise ValueError(f"UniProt returned no candidate records for exact proteome {proteome}")
    return [record for record in records if isinstance(record, dict)]


def _candidate_rows_and_records(
    records: list[dict[str, Any]],
    *,
    max_candidates: int,
    database_label: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if int(max_candidates) < 0:
        raise ValueError("max_candidates cannot be negative; use 0 for the complete proteome")

    unique_records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in records:
        accession = str(entry.get("primaryAccession") or entry.get("uniProtkbId") or "").strip()
        sequence = str((entry.get("sequence") or {}).get("value") or "").strip()
        if not accession or not sequence:
            continue
        key = accession.upper()
        if key in seen:
            continue
        seen.add(key)
        unique_records.append(entry)

    if max_candidates > 0:
        unique_records = unique_records[: int(max_candidates)]
    if not unique_records:
        raise ValueError("exact-proteome candidate retrieval produced no records with protein sequences")

    rows: list[dict[str, Any]] = []
    for entry in unique_records:
        accession = str(entry.get("primaryAccession") or entry.get("uniProtkbId") or "").strip()
        protein_id = accession.upper()
        gene = _first_gene_name(entry) or protein_id
        rows.append(
            {
                "protein_id": protein_id,
                "gene": gene,
                "essential": pd.NA,
                "evidence": "",
                "database": f"{database_label}:exact_proteome_candidate_seed",
                "essentiality_status": "unresolved_online_seed",
                "evidence_source_type": "online_external_exact_proteome_candidate_discovery",
                "candidate_seed_provider": "uniprot_rest",
                "candidate_seed_accession": accession,
                "candidate_seed_note": (
                    "Exact UniProt proteome candidate seed; this row is not essentiality evidence."
                ),
            }
        )
    return rows, unique_records


def _write_fasta(path: Path, records: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    for entry in records:
        accession = str(entry.get("primaryAccession") or entry.get("uniProtkbId") or "").strip()
        entry_id = str(entry.get("uniProtkbId") or accession).strip()
        sequence = str((entry.get("sequence") or {}).get("value") or "").replace(" ", "").replace("\n", "")
        prefix = "sp" if "reviewed" in str(entry.get("entryType") or "").casefold() else "tr"
        lines.append(f">{prefix}|{accession}|{entry_id}")
        lines.extend(sequence[index : index + 60] for index in range(0, len(sequence), 60))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def materialize_exact_proteome_snapshot(
    *,
    project_root: Path,
    snapshot_dir: Path,
    organism: str,
    taxon_id: str,
    strain: str | None,
    proteome_id: str,
    max_candidates: int = 0,
) -> dict[str, Any]:
    """Create the reproducible candidate snapshot used by the standard validation flow.

    ``max_candidates=0`` means the complete exact UniProt proteome. A positive
    value intentionally truncates the exact-proteome record set for smoke tests.
    """
    root = Path(project_root).resolve()
    target = Path(snapshot_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    config = load_config(root / "config" / "params.yaml")
    records = _stream_uniprot_proteome(proteome_id=proteome_id, config=config)
    rows, selected_records = _candidate_rows_and_records(
        records,
        max_candidates=int(max_candidates),
        database_label=str(config["online_sources"]["uniprot"]["database_label"]),
    )

    records_path = target / "uniprot_seed_records.json"
    csv_path = target / "candidate_seed.csv"
    fasta_path = target / "candidate_proteins.faa"
    records_path.write_text(
        json.dumps({"results": selected_records}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    _write_fasta(fasta_path, selected_records)

    files = {}
    for path in (records_path, csv_path, fasta_path):
        files[path.name] = {
            "sha256": _sha256(path),
            "size_bytes": path.stat().st_size,
        }
    manifest = {
        "schema_version": STANDARD_FLOW_SCHEMA_VERSION,
        "snapshot_type": "versioned_uniprot_candidate_seed",
        "snapshot_id": f"standard_exact_proteome_{str(proteome_id).lower()}",
        "provider_name": "uniprot_rest",
        "organism_name": organism,
        "strain": strain,
        "taxon_id": str(taxon_id),
        "proteome_id": str(proteome_id).upper(),
        "candidate_count": len(rows),
        "requested_max_candidates": int(max_candidates),
        "candidate_scope": "complete_exact_proteome" if int(max_candidates) == 0 else "bounded_exact_proteome",
        "query_semantics": "proteome_id_exact_no_species_broadening",
        "files": files,
        "generated_at_utc": _now(),
    }
    _json_dump(target / "snapshot_manifest.json", manifest)
    _json_dump(
        target / "candidate_seed_manifest_original.json",
        {
            "provider_name": "uniprot_rest",
            "source_used": "api_real",
            "retrieval_status": "exact_proteome_api_real",
            "proteome_id": str(proteome_id).upper(),
            "taxon_id": str(taxon_id),
            "candidate_count": len(rows),
            "requested_max_candidates": int(max_candidates),
            "generated_at_utc": _now(),
        },
    )
    return manifest


def _resolve_snapshot_candidate_count(snapshot_dir: Path) -> int:
    manifest = _json_load(Path(snapshot_dir) / "snapshot_manifest.json")
    count = int(manifest.get("candidate_count", 0) or 0)
    if count <= 0:
        raise ValueError("candidate snapshot manifest must declare a positive candidate_count")
    return count


def _prepare_vfdb_dataset(
    *,
    project_root: Path,
    run_dir: Path,
    override: str | Path | None,
) -> tuple[str | None, dict[str, Any]]:
    resolved = resolve_provider_dataset(project_root, "vfdb", override=override)
    if not resolved.get("exists"):
        return None, {"status": "missing", "source": resolved}

    source = Path(str(resolved["path"]))
    try:
        columns = set(pd.read_csv(source, nrows=1, sep=None, engine="python").columns)
    except Exception as exc:  # noqa: BLE001
        return str(source), {"status": "unreadable", "source": resolved, "error": type(exc).__name__}

    supported = {"protein_id", "protein", "locus_tag", "gene", "gene_name", "vf_id"}
    if columns & supported:
        return str(source), {"status": "already_provider_compatible", "source": resolved}
    if {"record_id", "description"}.issubset(columns):
        normalized = run_dir / "standard_contracts" / "vfdb_normalized.csv"
        audit = normalize_vfdb_snapshot(source, normalized)
        return str(normalized), {
            "status": "normalized_for_standard_flow",
            "source": resolved,
            "normalization": audit,
        }
    return str(source), {"status": "unsupported_schema", "source": resolved, "columns": sorted(columns)}


def _prepare_deg_dataset(
    *,
    project_root: Path,
    override: str | Path | None,
) -> tuple[str | None, dict[str, Any]]:
    resolved = resolve_provider_dataset(project_root, "deg", override=override)
    return (str(resolved["path"]) if resolved.get("exists") else None), resolved


def apply_standard_provider_scoring_contracts(
    *,
    workspace: Path,
    online_source_mode: str,
    recompute_scoring: bool = True,
) -> dict[str, Any]:
    """Apply the validated Stage 5A.4.1 DEG/VFDB semantics in the standard run.

    DEG is basal positive-only essentiality: matched candidates receive
    ``essential=1`` and unmatched candidates remain unresolved. VFDB affects
    virulence scoring only for actually mapped records. No FNT or therapeutic
    weights are modified.
    """
    workspace = Path(workspace).resolve()
    results_dir = workspace / "results"
    external_dir = workspace / "data_external"
    candidate_layer_path = external_dir / "essentiality.csv"
    deg_matches_path = results_dir / "deg_essentiality_matches.csv"

    deg_overlay = {
        "candidate_count": 0,
        "deg_match_count": 0,
        "unmatched_candidate_count": 0,
        "unmatched_still_unresolved_count": 0,
        "negative_evidence_inferred_count": 0,
    }
    if candidate_layer_path.is_file() and deg_matches_path.is_file():
        candidates = pd.read_csv(candidate_layer_path, low_memory=False)
        deg_matches = pd.read_csv(deg_matches_path, low_memory=False)
        combined, deg_overlay = overlay_deg_essentiality(candidates, deg_matches)
        if len(combined) != len(candidates):
            raise ValueError("DEG standard-flow overlay changed the candidate universe")
        combined.to_csv(candidate_layer_path, index=False)
        _mark_provider_manifest_score_effect(
            results_dir / "online_only_essentiality_manifest.json",
            layer_key="essentiality",
            provider_name="deg",
            matched_count=int(deg_overlay["deg_match_count"]),
            evidence_level="versioned_external_essentiality_dataset",
            scoring_columns=["essential"],
            interpretation=(
                "Standard flow: positive DEG matches are basal essentiality; unmatched candidates remain unresolved."
            ),
        )
        contextual_path = results_dir / "online_only_contextual_essentiality_manifest.json"
        contextual = _json_load(contextual_path)
        if contextual:
            contextual.update(
                {
                    "usable_evidence": False,
                    "affects_score": False,
                    "scoring_columns_used": "none",
                    "retrieval_status": "reclassified_to_basal_essentiality",
                    "stage5a41_score_contract": (
                        "DEG is intentionally not contextual_essentiality_score and is not double-counted."
                    ),
                    "generated_at_utc": _now(),
                }
            )
            _json_dump(contextual_path, contextual)

    vfdb_manifest_path = results_dir / "vfdb_virulence_manifest.json"
    vfdb_manifest = _json_load(vfdb_manifest_path)
    vfdb_mapped = int(vfdb_manifest.get("protein_count_mapped", 0) or 0)
    if vfdb_manifest:
        _mark_provider_manifest_score_effect(
            vfdb_manifest_path,
            layer_key="virulence",
            provider_name="vfdb",
            matched_count=vfdb_mapped,
            evidence_level="versioned_external_virulence_dataset",
            scoring_columns=["virulence_score", "virulence_factor"],
            interpretation=(
                "Standard flow: VFDB affects scoring only for exact records mapped after provider schema normalization."
            ),
        )
        online_vfdb = results_dir / "online_only_virulence_manifest.json"
        if online_vfdb.is_file():
            _mark_provider_manifest_score_effect(
                online_vfdb,
                layer_key="virulence",
                provider_name="vfdb",
                matched_count=vfdb_mapped,
                evidence_level="versioned_external_virulence_dataset",
                scoring_columns=["virulence_score", "virulence_factor"],
                interpretation="Standard flow VFDB score effect follows mapped normalized records only.",
            )

    score_affecting_recovery = int(deg_overlay.get("deg_match_count", 0) or 0) > 0 or vfdb_mapped > 0
    second_pass: dict[str, Any] = {}
    if recompute_scoring and score_affecting_recovery:
        second_pass = run_pipeline(
            base_dir=workspace,
            config_path=workspace / "config" / "params.yaml",
            mode="phase3",
            online_source_mode=normalize_provider_mode(online_source_mode),
        )

    provider_audit = build_online_only_provider_audit(workspace, {})
    provider_audit.to_csv(results_dir / "online_only_provider_audit.csv", index=False)
    manifest = {
        "schema_version": STANDARD_FLOW_SCHEMA_VERSION,
        "status": "completed",
        "deg_overlay": deg_overlay,
        "vfdb_mapped_candidate_count": vfdb_mapped,
        "score_affecting_recovery": score_affecting_recovery,
        "scoring_recomputed": bool(second_pass),
        "second_pass_pipeline_result": second_pass,
        "negative_evidence_inferred_count": 0,
        "functional_node_theory_weights_changed": False,
        "therapeutic_weights_changed": False,
        "generated_at_utc": _now(),
    }
    _json_dump(results_dir / "standard_provider_scoring_contract_manifest.json", manifest)
    return manifest


def run_standard_validation(
    *,
    project_root: Path,
    organism: str,
    organism_slug: str | None = None,
    taxon_id: int | str | None = None,
    strain: str | None = None,
    strain_slug: str | None = None,
    proteome_id: str | None = None,
    run_dir: Path | None = None,
    max_candidates: int = 0,
    candidate_seed_snapshot: str | Path | None = None,
    enable_string: bool = True,
    enable_interpro: bool = True,
    enable_literature: bool = True,
    enable_vfdb: bool = True,
    enable_deg: bool = True,
    enable_bvbrc: bool = True,
    vfdb_dataset: str | Path | None = None,
    deg_dataset: str | Path | None = None,
    online_source_mode: str = "online_strict",
    taxon_resolution_mode: str = "online_optional",
    refresh_taxon_cache: bool = False,
    no_write_taxon_cache: bool = True,
    materialize_unresolved_required_fallback: bool = False,
    enable_diamond: bool = False,
    diamond_execution_mode: str = "execute",
    diamond_reference_fasta: str | Path | None = None,
    diamond_database_prefix: str | Path | None = None,
    diamond_cached_tsv: str | Path | None = None,
    diamond_candidate_fasta: str | Path | None = None,
    diamond_executable: str = "diamond",
) -> dict[str, Any]:
    """Run the standard validation contract used for publication benchmarks."""
    root = Path(project_root).resolve()
    requested_max = int(max_candidates)
    if requested_max < 0:
        raise ValueError("max_candidates cannot be negative; use 0 for the complete proteome")
    proteome = str(proteome_id or "").strip().upper()
    if requested_max == 0 and not proteome and candidate_seed_snapshot is None:
        raise ValueError(
            "max_candidates=0 requests a complete candidate universe and therefore requires proteome_id "
            "or an exact versioned candidate_seed_snapshot"
        )
    configured_taxon = str(taxon_id or "").strip()
    if proteome and not configured_taxon:
        raise ValueError("exact proteome runs require an explicit strain/proteome taxon_id for identity auditing")

    resolved_slug = organism_slug or _slugify(organism)
    if strain:
        resolved_strain_slug = strain_slug or _slugify(strain)
        output_slug = f"{resolved_slug}_{resolved_strain_slug}"
    else:
        output_slug = resolved_slug
    base_run_dir = Path(run_dir).resolve() if run_dir else default_online_only_run_dir(root, output_slug)
    base_run_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path: Path | None = Path(candidate_seed_snapshot).expanduser().resolve() if candidate_seed_snapshot else None
    snapshot_manifest: dict[str, Any] = {}
    if snapshot_path is not None:
        raw_manifest = _json_load(snapshot_path / "snapshot_manifest.json")
        snapshot_proteome = str(raw_manifest.get("proteome_id") or "").strip().upper()
        if proteome and snapshot_proteome and snapshot_proteome != proteome:
            raise ValueError(
                f"candidate snapshot proteome mismatch: expected {proteome}, found {snapshot_proteome}"
            )
        snapshot_manifest = raw_manifest
    elif proteome:
        snapshot_path = base_run_dir / "standard_candidate_seed_snapshot"
        if snapshot_path.exists():
            raise ValueError(
                "standard candidate snapshot already exists; use a fresh --run-dir or explicitly reuse it with "
                "--candidate-seed-snapshot"
            )
        snapshot_manifest = materialize_exact_proteome_snapshot(
            project_root=root,
            snapshot_dir=snapshot_path,
            organism=organism,
            taxon_id=configured_taxon,
            strain=strain,
            proteome_id=proteome,
            max_candidates=requested_max,
        )

    effective_max = _resolve_snapshot_candidate_count(snapshot_path) if snapshot_path is not None else requested_max
    resolved_vfdb, vfdb_contract = _prepare_vfdb_dataset(
        project_root=root,
        run_dir=base_run_dir,
        override=vfdb_dataset,
    ) if enable_vfdb else (None, {"status": "disabled"})
    resolved_deg, deg_contract = _prepare_deg_dataset(
        project_root=root,
        override=deg_dataset,
    ) if enable_deg else (None, {"status": "disabled"})

    result = run_online_only_validation(
        project_root=root,
        organism=organism,
        organism_slug=resolved_slug,
        taxon_id=taxon_id,
        strain=strain,
        strain_slug=strain_slug,
        run_dir=base_run_dir,
        max_candidates=effective_max,
        candidate_seed_snapshot=snapshot_path,
        enable_string=enable_string,
        enable_interpro=enable_interpro,
        enable_literature=enable_literature,
        enable_vfdb=enable_vfdb,
        enable_deg=enable_deg,
        enable_bvbrc=enable_bvbrc,
        vfdb_dataset=resolved_vfdb,
        deg_dataset=resolved_deg,
        online_source_mode=online_source_mode,
        taxon_resolution_mode=taxon_resolution_mode,
        refresh_taxon_cache=refresh_taxon_cache,
        no_write_taxon_cache=no_write_taxon_cache,
        materialize_unresolved_required_fallback=materialize_unresolved_required_fallback,
        enable_diamond=enable_diamond,
        diamond_execution_mode=diamond_execution_mode,
        diamond_reference_fasta=diamond_reference_fasta,
        diamond_database_prefix=diamond_database_prefix,
        diamond_cached_tsv=diamond_cached_tsv,
        diamond_candidate_fasta=diamond_candidate_fasta,
        diamond_executable=diamond_executable,
    )

    workspace = Path(result["workspace"])
    contracts = apply_standard_provider_scoring_contracts(
        workspace=workspace,
        online_source_mode=online_source_mode,
        recompute_scoring=True,
    )
    if contracts.get("second_pass_pipeline_result"):
        result["pipeline_result"] = contracts["second_pass_pipeline_result"]
        result["pipeline_status"] = "completed"
        result["pipeline_error"] = ""

    result["package"] = build_online_only_review_package(
        run_dir=base_run_dir,
        workspace=workspace,
        organism=organism,
        organism_slug=resolved_slug,
        taxon_id=str(taxon_id or "") or None,
        strain=strain,
        strain_slug=strain_slug,
        seed_result=result.get("seed_result", {}),
        pipeline_status=result["pipeline_status"],
        pipeline_error=result.get("pipeline_error", ""),
        pipeline_result=result.get("pipeline_result", {}),
        online_source_mode=online_source_mode,
    )

    standard_manifest = {
        "schema_version": STANDARD_FLOW_SCHEMA_VERSION,
        "status": result["pipeline_status"],
        "organism": organism,
        "strain": strain,
        "taxon_id": str(taxon_id or "") or None,
        "proteome_id": proteome or snapshot_manifest.get("proteome_id"),
        "candidate_scope": (
            "complete_exact_proteome" if requested_max == 0 else "bounded_exact_proteome" if proteome else "legacy_bounded_taxon_query"
        ),
        "requested_max_candidates": requested_max,
        "effective_candidate_count": effective_max,
        "candidate_seed_snapshot": str(snapshot_path) if snapshot_path else None,
        "vfdb_contract": vfdb_contract,
        "deg_contract": deg_contract,
        "provider_scoring_contracts": contracts,
        "species_broadening_allowed_for_candidate_seed": False if proteome else True,
        "negative_evidence_inferred_count": 0,
        "functional_node_theory_weights_changed": False,
        "therapeutic_weights_changed": False,
        "generated_at_utc": _now(),
    }
    _json_dump(workspace / "results" / "standard_validation_manifest.json", standard_manifest)
    result["standard_validation_manifest"] = str(workspace / "results" / "standard_validation_manifest.json")
    result["standard_validation"] = standard_manifest
    return result
