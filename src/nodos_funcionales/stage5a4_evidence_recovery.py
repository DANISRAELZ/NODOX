from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .config import load_config
from .online_only_validation import (
    build_online_only_provider_audit,
    run_online_only_validation,
)

STAGE = "5A.4"
STAGE_NAME = "Stage 5A.4 — Evidence coverage recovery and audit"

SCORING_LAYERS = [
    "essentiality",
    "virulence",
    "human_homologs",
    "localization",
    "functional_network",
    "host_annotation",
    "strain_conservation",
    "contextual_essentiality",
]

IDENTIFIER_COLUMNS = (
    "candidate_seed_accession",
    "protein_id",
    "accession",
    "gene",
)


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


def _workspace_from_run_dir(run_dir: Path) -> tuple[Path, Path]:
    base = Path(run_dir).expanduser().resolve()
    if base.name == "workspace":
        workspace = base
        base = base.parent
    else:
        workspace = base / "workspace"
    if not workspace.is_dir():
        raise ValueError(f"Stage 5A.4 source workspace not found: {workspace}")
    return base, workspace


def _required_source_files(base: Path, workspace: Path) -> dict[str, Path]:
    files = {
        "stage5a2_manifest": workspace / "results" / "stage5a2_manifest.json",
        "stage5a2_audit": workspace / "results" / "stage5a2_candidate_seed_audit.csv",
        "ranking_nodos": workspace / "results" / "ranking_nodos.csv",
        "phase3_features": workspace / "data_processed" / "phase3_features.csv",
        "candidate_snapshot": base / "stage5a2_candidate_seed_snapshot",
    }
    missing = [name for name, path in files.items() if not path.exists()]
    if missing:
        raise ValueError(
            "Stage 5A.4 requires a completed Stage 5A.2 run; missing: "
            + ", ".join(missing)
        )
    return files


def _provider_audit_path(base: Path, workspace: Path) -> Path | None:
    candidates = [
        workspace / "results" / "online_only_provider_audit.csv",
        base / "review_package" / "online_only_provider_audit.csv",
    ]
    return next((path for path in candidates if path.exists()), None)


def load_source_provider_audit(base: Path, workspace: Path) -> pd.DataFrame:
    path = _provider_audit_path(base, workspace)
    if path is None:
        return build_online_only_provider_audit(workspace, {})
    return pd.read_csv(path, low_memory=False)


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes"}


def build_coverage_table(
    before: pd.DataFrame,
    after: pd.DataFrame | None = None,
    candidate_count: int | None = None,
) -> pd.DataFrame:
    """Summarize score-relevant evidence coverage before and after recovery."""
    after = after if after is not None else pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for layer in SCORING_LAYERS:
        row: dict[str, Any] = {"layer_key": layer}
        for prefix, frame in (("before", before), ("after", after)):
            selected = frame.loc[frame.get("layer_key", pd.Series(dtype=str)).astype(str).eq(layer)] if not frame.empty else pd.DataFrame()
            item = selected.iloc[-1] if not selected.empty else pd.Series(dtype=object)
            matched = int(pd.to_numeric(pd.Series([item.get("matched_candidate_count", 0)]), errors="coerce").fillna(0).iloc[0])
            row.update(
                {
                    f"{prefix}_provider_name": str(item.get("provider_name", "not_reported") or "not_reported"),
                    f"{prefix}_retrieval_status": str(item.get("retrieval_status", "not_reported") or "not_reported"),
                    f"{prefix}_usable_evidence": _safe_bool(item.get("usable_evidence", False)),
                    f"{prefix}_affects_score": _safe_bool(item.get("affects_score", False)),
                    f"{prefix}_matched_candidate_count": matched,
                    f"{prefix}_evidence_level": str(item.get("evidence_level", "unresolved") or "unresolved"),
                    f"{prefix}_fallback_reason": str(item.get("fallback_reason", "") or ""),
                }
            )
            if candidate_count and candidate_count > 0:
                row[f"{prefix}_coverage_fraction"] = matched / candidate_count
            else:
                row[f"{prefix}_coverage_fraction"] = None
        row["usable_evidence_recovered"] = (
            bool(row.get("after_usable_evidence"))
            and not bool(row.get("before_usable_evidence"))
        )
        row["score_affecting_evidence_recovered"] = (
            bool(row.get("after_affects_score"))
            and not bool(row.get("before_affects_score"))
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _configured_dataset(project_root: Path, provider: str) -> tuple[Path, Path]:
    cfg = load_config(project_root / "config" / "params.yaml")["online_sources"][provider]
    dataset = Path(str(cfg["local_dataset_path"]))
    version = Path(str(cfg["local_dataset_version_path"]))
    if not dataset.is_absolute():
        dataset = project_root / dataset
    if not version.is_absolute():
        version = project_root / version
    return dataset.resolve(), version.resolve()


def resolve_provider_dataset(
    project_root: Path,
    provider: str,
    override: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve a versioned local provider dataset from an explicit or project-root path."""
    configured, version_path = _configured_dataset(project_root, provider)
    if override is not None and str(override).strip():
        path = Path(override).expanduser()
        if not path.is_absolute():
            path = project_root / path
        path = path.resolve()
        source = "explicit_override"
    else:
        path = configured
        source = "project_root_config_path"
    exists = path.is_file()
    version = (
        version_path.read_text(encoding="utf-8", errors="replace").strip()[:300]
        if version_path.is_file()
        else "not_recorded"
    )
    return {
        "provider": provider,
        "path": str(path),
        "exists": exists,
        "source": source,
        "size_bytes": path.stat().st_size if exists else 0,
        "sha256": _sha256(path) if exists else "",
        "version_path": str(version_path),
        "version_recorded": version_path.is_file(),
        "version": version or "not_recorded",
        "ready": bool(exists and version_path.is_file()),
    }


def _diamond_preflight(
    project_root: Path,
    *,
    enabled: bool,
    execution_mode: str,
    reference_fasta: str | Path | None,
    database_prefix: str | Path | None,
    cached_tsv: str | Path | None,
) -> dict[str, Any]:
    def resolve(value: str | Path | None) -> Path | None:
        if value is None or not str(value).strip():
            return None
        path = Path(value).expanduser()
        return (path if path.is_absolute() else project_root / path).resolve()

    reference = resolve(reference_fasta)
    database = resolve(database_prefix)
    cached = resolve(cached_tsv)
    if database is not None and database.suffix.lower() == ".dmnd":
        database = database.with_suffix("")
    database_file = Path(str(database) + ".dmnd") if database is not None else None
    mode = str(execution_mode).strip().casefold()
    ready = False
    reason = "disabled"
    if enabled and mode == "execute":
        ready = bool(reference and reference.is_file())
        reason = "ready" if ready else "execute_requires_reference_fasta"
    elif enabled and mode == "cache_only":
        ready = bool(cached and cached.is_file())
        reason = "ready" if ready else "cache_only_requires_cached_tsv"
    return {
        "enabled": bool(enabled),
        "execution_mode": mode,
        "reference_fasta": str(reference) if reference else "",
        "reference_exists": bool(reference and reference.is_file()),
        "database_prefix": str(database) if database else "",
        "database_exists": bool(database_file and database_file.is_file()),
        "cached_tsv": str(cached) if cached else "",
        "cached_tsv_exists": bool(cached and cached.is_file()),
        "ready": ready,
        "reason": reason,
    }


def _norm(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().casefold()


def _identifier_lookup(df: pd.DataFrame) -> dict[str, int]:
    lookup: dict[str, int] = {}
    for idx, row in df.iterrows():
        for column in IDENTIFIER_COLUMNS:
            if column not in df.columns:
                continue
            key = _norm(row.get(column))
            if key:
                lookup.setdefault(key, idx)
    return lookup


def _match_index(row: pd.Series, lookup: dict[str, int]) -> int | None:
    for column in IDENTIFIER_COLUMNS:
        key = _norm(row.get(column))
        if key and key in lookup:
            return lookup[key]
    return None


def build_benchmark_comparison(
    source_trace: pd.DataFrame,
    recovery_ranking: pd.DataFrame,
) -> pd.DataFrame:
    """Compare benchmark ranks/scores before and after evidence recovery."""
    if recovery_ranking.empty or "protein_id" not in recovery_ranking.columns:
        raise ValueError("Stage 5A.4 recovery ranking is empty or lacks protein_id")
    lookup = _identifier_lookup(recovery_ranking)
    rows: list[dict[str, Any]] = []
    for _, source in source_trace.iterrows():
        idx = _match_index(source, lookup)
        recovered = recovery_ranking.loc[idx] if idx is not None else None
        recovery_rank = int(recovery_ranking.index.get_loc(idx)) + 1 if idx is not None else pd.NA
        before_rank = source.get("final_rank", pd.NA)
        before_score = source.get("therapeutic_primary_score", pd.NA)
        after_score = recovered.get("meta_priority_score_v3", pd.NA) if recovered is not None else pd.NA
        before_fnt = source.get("functional_node_theory_score", pd.NA)
        after_fnt = recovered.get("functional_node_theory_score", pd.NA) if recovered is not None else pd.NA
        before_quality = source.get("evidence_quality_score", pd.NA)
        after_quality = recovered.get("evidence_quality_score", pd.NA) if recovered is not None else pd.NA
        rows.append(
            {
                "benchmark_token": source.get("benchmark_token", ""),
                "protein_id": source.get("protein_id", ""),
                "gene": source.get("gene", ""),
                "recovery_match": idx is not None,
                "before_final_rank": before_rank,
                "after_final_rank": recovery_rank,
                "final_rank_delta": (
                    int(recovery_rank) - int(before_rank)
                    if pd.notna(recovery_rank) and pd.notna(before_rank)
                    else pd.NA
                ),
                "before_meta_priority_score_v3": before_score,
                "after_meta_priority_score_v3": after_score,
                "meta_priority_score_v3_delta": (
                    float(after_score) - float(before_score)
                    if pd.notna(after_score) and pd.notna(before_score)
                    else pd.NA
                ),
                "before_functional_node_theory_score": before_fnt,
                "after_functional_node_theory_score": after_fnt,
                "functional_node_theory_score_delta": (
                    float(after_fnt) - float(before_fnt)
                    if pd.notna(after_fnt) and pd.notna(before_fnt)
                    else pd.NA
                ),
                "before_evidence_quality_score": before_quality,
                "after_evidence_quality_score": after_quality,
                "evidence_quality_score_delta": (
                    float(after_quality) - float(before_quality)
                    if pd.notna(after_quality) and pd.notna(before_quality)
                    else pd.NA
                ),
                "after_phase3_evidence_confidence_label": (
                    recovered.get("phase3_evidence_confidence_label", pd.NA)
                    if recovered is not None
                    else pd.NA
                ),
                "after_phase3_recommendation": (
                    recovered.get("phase3_recommendation", pd.NA)
                    if recovered is not None
                    else pd.NA
                ),
            }
        )
    return pd.DataFrame(rows)


def _source_trace(workspace: Path) -> pd.DataFrame:
    trace = workspace / "results" / "stage5a3_rank_trace.csv"
    if trace.exists():
        return pd.read_csv(trace, low_memory=False)
    audit = pd.read_csv(workspace / "results" / "stage5a2_candidate_seed_audit.csv", low_memory=False)
    requested = audit.get("benchmark_token", pd.Series(index=audit.index, dtype=str)).fillna("").astype(str).str.strip().ne("")
    subset = audit.loc[requested].copy()
    subset["therapeutic_primary_score"] = pd.NA
    return subset


def _recovered_usable_count(coverage: pd.DataFrame, column: str) -> int:
    if column not in coverage.columns:
        return 0
    return int(coverage[column].fillna(False).astype(bool).sum())


def run_stage5a4_evidence_recovery(
    *,
    project_root: Path,
    source_run_dir: Path,
    recovery_run_dir: Path | None = None,
    execute_recovery: bool = False,
    vfdb_dataset: str | Path | None = None,
    deg_dataset: str | Path | None = None,
    enable_string: bool = True,
    enable_bvbrc: bool = True,
    enable_diamond: bool = False,
    diamond_execution_mode: str = "execute",
    diamond_reference_fasta: str | Path | None = None,
    diamond_database_prefix: str | Path | None = None,
    diamond_cached_tsv: str | Path | None = None,
    diamond_executable: str = "diamond",
    online_source_mode: str = "online_strict",
) -> dict[str, Any]:
    """Audit a completed 5A.2 run and optionally rerun scoring on its frozen candidate snapshot."""
    root = Path(project_root).resolve()
    source_base, source_workspace = _workspace_from_run_dir(source_run_dir)
    source_files = _required_source_files(source_base, source_workspace)
    source_manifest = _json_load(source_files["stage5a2_manifest"])
    source_audit = load_source_provider_audit(source_base, source_workspace)
    candidate_count = int(source_manifest.get("candidate_count_selected", 0) or 0)

    vfdb = resolve_provider_dataset(root, "vfdb", vfdb_dataset)
    deg = resolve_provider_dataset(root, "deg", deg_dataset)
    diamond = _diamond_preflight(
        root,
        enabled=enable_diamond,
        execution_mode=diamond_execution_mode,
        reference_fasta=diamond_reference_fasta,
        database_prefix=diamond_database_prefix,
        cached_tsv=diamond_cached_tsv,
    )

    if recovery_run_dir is None:
        recovery_base = source_base.parent / f"{source_base.name}_stage5a4_recovery"
    else:
        recovery_base = Path(recovery_run_dir)
        if not recovery_base.is_absolute():
            recovery_base = root / recovery_base
    recovery_base = recovery_base.resolve()
    recovery_base.mkdir(parents=True, exist_ok=True)

    before_coverage = build_coverage_table(source_audit, candidate_count=candidate_count)
    before_path = recovery_base / "stage5a4_evidence_coverage_before.csv"
    before_coverage.to_csv(before_path, index=False)

    preflight = {
        "schema_version": "1.0",
        "stage": STAGE,
        "stage_name": STAGE_NAME,
        "source_stage": "5A.2/5A.3",
        "source_run_dir": str(source_base),
        "source_workspace": str(source_workspace),
        "recovery_run_dir": str(recovery_base),
        "organism": source_manifest.get("organism"),
        "strain": source_manifest.get("strain"),
        "taxon_id": source_manifest.get("taxon_id"),
        "proteome_id": source_manifest.get("proteome_id"),
        "candidate_count": candidate_count,
        "candidate_snapshot": str(source_files["candidate_snapshot"]),
        "vfdb": vfdb,
        "deg": deg,
        "string_enabled": bool(enable_string),
        "bvbrc_enabled": bool(enable_bvbrc),
        "diamond": diamond,
        "interpro_enabled": False,
        "literature_enabled": False,
        "dataset_policy": "explicit_override_then_project_root_config_path",
        "candidate_policy": "reuse_frozen_stage5a2_snapshot_no_uniprot_discovery",
        "scoring_model_changed": False,
        "functional_node_theory_weights_changed": False,
        "generated_at_utc": _now(),
    }
    preflight_path = recovery_base / "stage5a4_preflight_manifest.json"
    _json_dump(preflight_path, preflight)

    if not execute_recovery:
        return {
            "stage": STAGE,
            "status": "preflight_completed",
            "preflight": str(preflight_path),
            "coverage_before": str(before_path),
            "vfdb_ready": vfdb["ready"],
            "deg_ready": deg["ready"],
            "diamond_ready": diamond["ready"],
            "providers_rerun": False,
            "scoring_recomputed": False,
        }

    if enable_diamond and not diamond["ready"]:
        raise ValueError(f"Stage 5A.4 DIAMOND preflight failed: {diamond['reason']}")

    core = run_online_only_validation(
        project_root=root,
        organism=str(source_manifest.get("organism") or "").strip(),
        taxon_id=str(source_manifest.get("taxon_id") or "").strip(),
        strain=str(source_manifest.get("strain") or "").strip() or None,
        run_dir=recovery_base,
        max_candidates=candidate_count,
        candidate_seed_snapshot=source_files["candidate_snapshot"],
        enable_string=enable_string,
        enable_interpro=False,
        enable_literature=False,
        enable_vfdb=True,
        enable_deg=True,
        enable_bvbrc=enable_bvbrc,
        vfdb_dataset=vfdb["path"] if vfdb["exists"] else None,
        deg_dataset=deg["path"] if deg["exists"] else None,
        online_source_mode=online_source_mode,
        enable_diamond=enable_diamond,
        diamond_execution_mode=diamond_execution_mode,
        diamond_reference_fasta=diamond_reference_fasta,
        diamond_database_prefix=diamond_database_prefix,
        diamond_cached_tsv=diamond_cached_tsv,
        diamond_executable=diamond_executable,
    )

    recovery_workspace = Path(core["workspace"])
    after_audit = build_online_only_provider_audit(recovery_workspace, core.get("seed_result", {}))
    coverage = build_coverage_table(source_audit, after_audit, candidate_count=candidate_count)
    coverage_path = recovery_workspace / "results" / "stage5a4_evidence_coverage.csv"
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(coverage_path, index=False)

    source_trace = _source_trace(source_workspace)
    recovery_ranking_path = recovery_workspace / "results" / "ranking_nodos.csv"
    benchmark_comparison = pd.DataFrame()
    benchmark_path = recovery_workspace / "results" / "stage5a4_benchmark_comparison.csv"
    if recovery_ranking_path.exists():
        recovery_ranking = pd.read_csv(recovery_ranking_path, low_memory=False)
        benchmark_comparison = build_benchmark_comparison(source_trace, recovery_ranking)
        benchmark_comparison.to_csv(benchmark_path, index=False)

    manifest = {
        **preflight,
        "audit_status": "completed",
        "pipeline_status": core.get("pipeline_status"),
        "pipeline_error": core.get("pipeline_error", ""),
        "providers_rerun": True,
        "scoring_recomputed": True,
        "candidate_discovery_rerun": False,
        "ranking_order_changed_by_stage5a4_code": False,
        "source_files_sha256": {
            name: _sha256(path)
            for name, path in source_files.items()
            if path.is_file()
        },
        "coverage_output": str(coverage_path),
        "benchmark_comparison_output": str(benchmark_path) if benchmark_path.exists() else "",
        "usable_scoring_layers_before": _recovered_usable_count(coverage, "before_usable_evidence"),
        "usable_scoring_layers_after": _recovered_usable_count(coverage, "after_usable_evidence"),
        "score_affecting_layers_before": _recovered_usable_count(coverage, "before_affects_score"),
        "score_affecting_layers_after": _recovered_usable_count(coverage, "after_affects_score"),
        "new_usable_evidence_layers": coverage.loc[
            coverage["usable_evidence_recovered"].fillna(False).astype(bool), "layer_key"
        ].astype(str).tolist(),
        "new_score_affecting_layers": coverage.loc[
            coverage["score_affecting_evidence_recovered"].fillna(False).astype(bool), "layer_key"
        ].astype(str).tolist(),
        "benchmark_match_count": int(benchmark_comparison.get("recovery_match", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if not benchmark_comparison.empty else 0,
        "scoring_model_changed": False,
        "functional_node_theory_weights_changed": False,
        "experimental_validation_supported": False,
        "interpretation": (
            "Stage 5A.4 reuses the frozen Stage 5A.2 candidate snapshot, retries score-relevant evidence providers, "
            "and measures evidence/ranking changes without changing model weights."
        ),
        "generated_at_utc": _now(),
    }
    manifest_path = recovery_workspace / "results" / "stage5a4_manifest.json"
    _json_dump(manifest_path, manifest)

    review = recovery_base / "review_package"
    if review.is_dir():
        coverage.to_csv(review / "stage5a4_evidence_coverage.csv", index=False)
        if not benchmark_comparison.empty:
            benchmark_comparison.to_csv(review / "stage5a4_benchmark_comparison.csv", index=False)
        _json_dump(review / "stage5a4_manifest.json", manifest)

    return {
        **core,
        "stage5a4_manifest": str(manifest_path),
        "stage5a4_coverage": str(coverage_path),
        "stage5a4_benchmark_comparison": str(benchmark_path) if benchmark_path.exists() else "",
        "stage5a4_summary": manifest,
    }
