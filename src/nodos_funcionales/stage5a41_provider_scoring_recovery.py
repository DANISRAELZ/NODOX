from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .online_only_validation import build_online_only_provider_audit
from .pipeline import run_pipeline
from .stage5a4_evidence_recovery import (
    build_benchmark_comparison,
    build_coverage_table,
    load_source_provider_audit,
    resolve_provider_dataset,
    run_stage5a4_evidence_recovery,
)

STAGE = "5A.4.1"
STAGE_NAME = "Stage 5A.4.1 — Versioned DEG/VFDB scoring contract recovery"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _resolve_run_dir(project_root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _workspace_from_source(source_run_dir: Path) -> tuple[Path, Path]:
    base = Path(source_run_dir).resolve()
    workspace = base if base.name == "workspace" else base / "workspace"
    run_base = base.parent if base.name == "workspace" else base
    if not workspace.is_dir():
        raise ValueError(f"Stage 5A.4.1 source workspace not found: {workspace}")
    return run_base, workspace


def _parse_vfdb_snapshot_fields(record_id: object, description: object) -> dict[str, str]:
    """Derive provider identifiers from the versioned VFDB SetA FASTA snapshot.

    The normalization is deliberately syntactic: it only exposes identifiers
    already present in VFDB. It never invents benchmark aliases or target labels.
    """
    record = str(record_id or "").strip()
    text = str(description or "").strip()

    vf_match = re.match(r"\s*(VFG\d+)", record, flags=re.IGNORECASE)
    vf_id = vf_match.group(1) if vf_match else ""

    accession_match = re.search(r"(?:gb|ref|emb|dbj)\|([^()|\s]+)", record, flags=re.IGNORECASE)
    protein = accession_match.group(1).strip() if accession_match else ""

    remainder = text
    if record and remainder.startswith(record):
        remainder = remainder[len(record) :].lstrip()
    gene_match = re.match(r"\(([^()]+)\)", remainder)
    gene = gene_match.group(1).strip() if gene_match else ""

    organism_match = re.search(r"\[([^\[\]]+)\]\s*$", text)
    organism = organism_match.group(1).strip() if organism_match else ""

    return {
        "vf_id": vf_id,
        "protein": protein,
        "gene": gene,
        "organism": organism,
        "function": text,
    }


def normalize_vfdb_snapshot(source_path: Path, output_path: Path) -> dict[str, Any]:
    """Normalize the local VFDB SetA snapshot into fields understood by vfdb_api."""
    source = Path(source_path).resolve()
    output = Path(output_path).resolve()
    if not source.is_file():
        raise ValueError(f"VFDB source snapshot not found: {source}")

    frame = pd.read_csv(source, low_memory=False)
    required = {"record_id", "description"}
    if not required.issubset(frame.columns):
        raise ValueError(
            "Stage 5A.4.1 VFDB normalization requires record_id and description; "
            f"found {sorted(frame.columns)}"
        )

    parsed = pd.DataFrame(
        [
            _parse_vfdb_snapshot_fields(row.get("record_id"), row.get("description"))
            for _, row in frame.iterrows()
        ],
        index=frame.index,
    )
    normalized = frame.copy()
    for column in ["vf_id", "protein", "gene", "organism", "function"]:
        normalized[column] = parsed[column]

    output.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(output, index=False)

    source_version = source.with_suffix(".version.txt")
    version_path = output.with_suffix(".version.txt")
    version_lines = [
        "dataset=VFDB_setA_pro",
        f"source_path={source}",
        f"source_sha256={_sha256(source)}",
        f"normalized_sha256={_sha256(output)}",
        f"record_count={len(normalized)}",
        "normalization=stage5a41_vfdb_schema_adapter_v1",
        "normalization_semantics=syntactic_identifiers_from_record_id_and_description_no_alias_inference",
    ]
    if source_version.is_file():
        version_lines.append(f"source_version_sha256={_sha256(source_version)}")
    version_path.write_text("\n".join(version_lines) + "\n", encoding="utf-8")

    return {
        "source_path": str(source),
        "source_sha256": _sha256(source),
        "output_path": str(output),
        "output_sha256": _sha256(output),
        "version_path": str(version_path),
        "record_count": int(len(normalized)),
        "gene_parsed_count": int(normalized["gene"].fillna("").astype(str).str.strip().ne("").sum()),
        "organism_parsed_count": int(normalized["organism"].fillna("").astype(str).str.strip().ne("").sum()),
        "protein_identifier_parsed_count": int(normalized["protein"].fillna("").astype(str).str.strip().ne("").sum()),
    }


def overlay_deg_essentiality(
    candidate_layer: pd.DataFrame,
    deg_matches: pd.DataFrame,
    *,
    database_label: str = "deg_real_v1",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Overlay positive DEG evidence onto the complete candidate essentiality layer.

    Unmatched candidates remain unresolved. Absence from DEG is never converted
    into essential=0, because missing positive evidence is not negative evidence.
    """
    if "protein_id" not in candidate_layer.columns:
        raise ValueError("candidate essentiality layer lacks protein_id")
    if "protein_id" not in deg_matches.columns:
        raise ValueError("DEG matches lack protein_id")

    result = candidate_layer.copy()
    if "gene" not in result.columns:
        result["gene"] = result["protein_id"]
    for column in ["essential", "evidence", "database"]:
        if column not in result.columns:
            result[column] = pd.NA

    match_frame = deg_matches.copy()
    match_frame["_protein_key"] = match_frame["protein_id"].fillna("").astype(str).str.strip().str.upper()
    match_frame = match_frame.loc[match_frame["_protein_key"].ne("")].drop_duplicates("_protein_key", keep="first")
    match_lookup = match_frame.set_index("_protein_key")

    candidate_keys = result["protein_id"].fillna("").astype(str).str.strip().str.upper()
    mask = candidate_keys.isin(match_lookup.index)
    matched_keys = candidate_keys.loc[mask]

    result.loc[mask, "essential"] = 1
    evidence_by_key = match_lookup.get("evidence", pd.Series(index=match_lookup.index, dtype=object))
    result.loc[mask, "evidence"] = matched_keys.map(evidence_by_key).fillna("DEG essential gene annotation").values
    result.loc[mask, "database"] = database_label
    result["essentiality_status"] = result.get(
        "essentiality_status", pd.Series(pd.NA, index=result.index, dtype=object)
    )
    result.loc[mask, "essentiality_status"] = "essential_supported_by_deg"
    result["deg_support"] = False
    result.loc[mask, "deg_support"] = True
    result["deg_evidence_source_type"] = pd.NA
    result.loc[mask, "deg_evidence_source_type"] = "versioned_external_deg"

    unmatched = ~mask
    existing_numeric = pd.to_numeric(result.loc[unmatched, "essential"], errors="coerce")
    unresolved_unmatched = int(existing_numeric.isna().sum())

    audit = {
        "candidate_count": int(len(result)),
        "deg_match_count": int(mask.sum()),
        "unmatched_candidate_count": int(unmatched.sum()),
        "unmatched_still_unresolved_count": unresolved_unmatched,
        "negative_evidence_inferred_count": 0,
        "database_label": database_label,
    }
    return result, audit


def _mark_provider_manifest_score_effect(
    path: Path,
    *,
    layer_key: str,
    provider_name: str,
    matched_count: int,
    evidence_level: str,
    scoring_columns: list[str],
    interpretation: str,
) -> dict[str, Any]:
    manifest = _json_load(path)
    usable = int(matched_count) > 0
    manifest.update(
        {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "provider": provider_name,
            "retrieval_success": usable,
            "mapping_success": usable,
            "usable_evidence": usable,
            "affects_score": usable,
            "matched_candidate_count": int(matched_count),
            "protein_count_mapped": int(matched_count),
            "evidence_level": evidence_level if usable else "unresolved",
            "scoring_columns_used": ";".join(scoring_columns) if usable else "none",
            "experimental_validation_supported": False,
            "stage5a41_score_contract": interpretation,
            "generated_at_utc": _now(),
        }
    )
    _json_dump(path, manifest)
    return manifest


def _source_trace(source_workspace: Path) -> pd.DataFrame:
    trace = source_workspace / "results" / "stage5a3_rank_trace.csv"
    if not trace.exists():
        raise ValueError("Stage 5A.4.1 requires stage5a3_rank_trace.csv in the source workspace")
    return pd.read_csv(trace, low_memory=False)


def run_stage5a41_provider_scoring_recovery(
    *,
    project_root: Path,
    source_run_dir: Path,
    recovery_run_dir: Path,
    execute_recovery: bool = False,
    enable_string: bool = True,
    enable_bvbrc: bool = True,
    online_source_mode: str = "online_strict",
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    source_base, source_workspace = _workspace_from_source(_resolve_run_dir(root, source_run_dir))
    recovery_base = _resolve_run_dir(root, recovery_run_dir)
    recovery_base.mkdir(parents=True, exist_ok=True)

    source_manifest_path = source_workspace / "results" / "stage5a2_manifest.json"
    source_manifest = _json_load(source_manifest_path)
    if not source_manifest:
        raise ValueError("Stage 5A.4.1 requires a completed Stage 5A.2 manifest")
    candidate_count = int(source_manifest.get("candidate_count_selected", 0) or 0)
    if candidate_count <= 0:
        raise ValueError("Stage 5A.4.1 source candidate count is zero")

    vfdb_source = resolve_provider_dataset(root, "vfdb")
    deg_source = resolve_provider_dataset(root, "deg")
    if not vfdb_source["ready"]:
        raise ValueError("Stage 5A.4.1 requires a versioned VFDB dataset")
    if not deg_source["ready"]:
        raise ValueError("Stage 5A.4.1 requires a versioned DEG dataset")

    normalized_vfdb = recovery_base / "stage5a41_vfdb_normalized.csv"
    vfdb_normalization = normalize_vfdb_snapshot(Path(vfdb_source["path"]), normalized_vfdb)

    preflight = {
        "schema_version": "1.0",
        "stage": STAGE,
        "stage_name": STAGE_NAME,
        "source_run_dir": str(source_base),
        "source_workspace": str(source_workspace),
        "recovery_run_dir": str(recovery_base),
        "candidate_count": candidate_count,
        "organism": source_manifest.get("organism"),
        "strain": source_manifest.get("strain"),
        "taxon_id": source_manifest.get("taxon_id"),
        "proteome_id": source_manifest.get("proteome_id"),
        "vfdb_source": vfdb_source,
        "vfdb_normalization": vfdb_normalization,
        "deg_source": deg_source,
        "deg_scoring_semantics": "positive_DEG_matches_overlay_basal_essentiality_unmatched_remain_unresolved",
        "vfdb_scoring_semantics": "exact_provider_mapping_after_syntactic_schema_normalization_no_benchmark_alias_inference",
        "online_source_mode": online_source_mode,
        "scoring_model_changed": False,
        "functional_node_theory_weights_changed": False,
        "therapeutic_weights_changed": False,
        "generated_at_utc": _now(),
    }
    preflight_path = recovery_base / "stage5a41_preflight_manifest.json"
    _json_dump(preflight_path, preflight)

    if not execute_recovery:
        return {
            "stage": STAGE,
            "status": "preflight_completed",
            "preflight": str(preflight_path),
            "vfdb_normalized": str(normalized_vfdb),
            "vfdb_gene_parsed_count": vfdb_normalization["gene_parsed_count"],
            "deg_ready": bool(deg_source["ready"]),
            "providers_rerun": False,
            "scoring_recomputed": False,
        }

    workspace_candidate = recovery_base / "workspace"
    if workspace_candidate.exists():
        raise ValueError(
            "Stage 5A.4.1 execute mode requires a fresh recovery directory without an existing workspace; "
            "use a new --recovery-run-dir to avoid stale provider caches."
        )

    core = run_stage5a4_evidence_recovery(
        project_root=root,
        source_run_dir=source_base,
        recovery_run_dir=recovery_base,
        execute_recovery=True,
        vfdb_dataset=normalized_vfdb,
        deg_dataset=Path(deg_source["path"]),
        enable_string=enable_string,
        enable_bvbrc=enable_bvbrc,
        enable_diamond=False,
        online_source_mode=online_source_mode,
    )

    recovery_workspace = Path(core["workspace"])
    external_dir = recovery_workspace / "data_external"
    results_dir = recovery_workspace / "results"

    candidate_layer_path = external_dir / "essentiality.csv"
    deg_matches_path = results_dir / "deg_essentiality_matches.csv"
    if not candidate_layer_path.exists():
        raise ValueError("Stage 5A.4.1 recovery candidate essentiality layer is missing")
    if not deg_matches_path.exists():
        raise ValueError("Stage 5A.4.1 DEG produced no match table")

    candidate_layer = pd.read_csv(candidate_layer_path, low_memory=False)
    deg_matches = pd.read_csv(deg_matches_path, low_memory=False)
    combined, deg_overlay = overlay_deg_essentiality(candidate_layer, deg_matches)
    if len(combined) != candidate_count:
        raise ValueError(
            f"Stage 5A.4.1 DEG overlay changed candidate count: expected {candidate_count}, found {len(combined)}"
        )
    combined.to_csv(candidate_layer_path, index=False)

    essentiality_manifest_path = results_dir / "online_only_essentiality_manifest.json"
    essentiality_manifest = _mark_provider_manifest_score_effect(
        essentiality_manifest_path,
        layer_key="essentiality",
        provider_name="deg",
        matched_count=deg_overlay["deg_match_count"],
        evidence_level="versioned_external_essentiality_dataset",
        scoring_columns=["essential"],
        interpretation=(
            "DEG positive matches were overlaid onto the frozen UniProt candidate universe as basal essentiality. "
            "Unmatched candidates remain unresolved; DEG was not converted into contextual_essentiality_score."
        ),
    )
    essentiality_manifest.update(
        {
            "provider_mode": "local_dataset",
            "source_used": "versioned_local_dataset_overlay",
            "retrieval_status": "versioned_local_dataset_integrated",
            "local_dataset_path": str(deg_source["path"]),
            "local_dataset_sha256": str(deg_source["sha256"]),
            "candidate_count": candidate_count,
            "negative_evidence_inferred_count": 0,
        }
    )
    _json_dump(essentiality_manifest_path, essentiality_manifest)

    vfdb_provider_manifest_path = results_dir / "vfdb_virulence_manifest.json"
    vfdb_provider_manifest = _json_load(vfdb_provider_manifest_path)
    vfdb_mapped = int(vfdb_provider_manifest.get("protein_count_mapped", 0) or 0)
    _mark_provider_manifest_score_effect(
        vfdb_provider_manifest_path,
        layer_key="virulence",
        provider_name="vfdb",
        matched_count=vfdb_mapped,
        evidence_level="versioned_external_virulence_dataset",
        scoring_columns=["virulence_score", "virulence_factor"],
        interpretation=(
            "VFDB SetA records were mapped only after syntactic extraction of identifiers already present in "
            "record_id/description. No benchmark target was injected or aliased."
        ),
    )
    online_vfdb_manifest_path = results_dir / "online_only_virulence_manifest.json"
    if online_vfdb_manifest_path.exists():
        _mark_provider_manifest_score_effect(
            online_vfdb_manifest_path,
            layer_key="virulence",
            provider_name="vfdb",
            matched_count=vfdb_mapped,
            evidence_level="versioned_external_virulence_dataset",
            scoring_columns=["virulence_score", "virulence_factor"],
            interpretation="VFDB score effect follows exact mapped records in the normalized versioned snapshot.",
        )

    second_pass = run_pipeline(
        base_dir=recovery_workspace,
        config_path=recovery_workspace / "config" / "params.yaml",
        mode="phase3",
        online_source_mode=online_source_mode,
    )

    source_audit = load_source_provider_audit(source_base, source_workspace)
    after_audit = build_online_only_provider_audit(recovery_workspace, core.get("seed_result", {}))
    coverage = build_coverage_table(source_audit, after_audit, candidate_count=candidate_count)
    coverage_path = results_dir / "stage5a41_evidence_coverage.csv"
    coverage.to_csv(coverage_path, index=False)

    source_trace = _source_trace(source_workspace)
    ranking_path = results_dir / "ranking_nodos.csv"
    if not ranking_path.exists():
        raise ValueError("Stage 5A.4.1 second-pass ranking was not generated")
    ranking = pd.read_csv(ranking_path, low_memory=False)
    benchmark = build_benchmark_comparison(source_trace, ranking)
    benchmark_path = results_dir / "stage5a41_benchmark_comparison.csv"
    benchmark.to_csv(benchmark_path, index=False)

    manifest = {
        **preflight,
        "audit_status": "completed",
        "first_pass_pipeline_status": core.get("pipeline_status"),
        "first_pass_pipeline_error": core.get("pipeline_error", ""),
        "second_pass_pipeline_result": second_pass,
        "providers_rerun": True,
        "scoring_recomputed": True,
        "candidate_discovery_rerun": False,
        "candidate_count_after_overlay": int(len(combined)),
        "deg_overlay": deg_overlay,
        "vfdb_mapped_candidate_count": vfdb_mapped,
        "usable_scoring_layers_before": int(coverage["before_usable_evidence"].fillna(False).astype(bool).sum()),
        "usable_scoring_layers_after": int(coverage["after_usable_evidence"].fillna(False).astype(bool).sum()),
        "score_affecting_layers_before": int(coverage["before_affects_score"].fillna(False).astype(bool).sum()),
        "score_affecting_layers_after": int(coverage["after_affects_score"].fillna(False).astype(bool).sum()),
        "new_usable_evidence_layers": coverage.loc[
            coverage["usable_evidence_recovered"].fillna(False).astype(bool), "layer_key"
        ].astype(str).tolist(),
        "new_score_affecting_layers": coverage.loc[
            coverage["score_affecting_evidence_recovered"].fillna(False).astype(bool), "layer_key"
        ].astype(str).tolist(),
        "benchmark_match_count": int(benchmark["recovery_match"].fillna(False).astype(bool).sum()),
        "coverage_output": str(coverage_path),
        "benchmark_comparison_output": str(benchmark_path),
        "scoring_model_changed": False,
        "functional_node_theory_weights_changed": False,
        "therapeutic_weights_changed": False,
        "experimental_validation_supported": False,
        "interpretation": (
            "Stage 5A.4.1 repairs provider-to-scoring contracts for versioned DEG and VFDB evidence. "
            "It does not calibrate target weights and does not infer negative evidence from absent provider records."
        ),
        "generated_at_utc": _now(),
    }
    manifest_path = results_dir / "stage5a41_manifest.json"
    _json_dump(manifest_path, manifest)

    return {
        "stage": STAGE,
        "status": "completed",
        "workspace": str(recovery_workspace),
        "stage5a41_manifest": str(manifest_path),
        "stage5a41_coverage": str(coverage_path),
        "stage5a41_benchmark_comparison": str(benchmark_path),
        "deg_match_count": deg_overlay["deg_match_count"],
        "vfdb_mapped_candidate_count": vfdb_mapped,
        "new_score_affecting_layers": manifest["new_score_affecting_layers"],
        "scoring_model_changed": False,
    }
