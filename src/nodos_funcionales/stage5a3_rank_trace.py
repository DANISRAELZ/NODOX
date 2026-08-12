from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STAGE = "5A.3"
STAGE_NAME = "Stage 5A.3 — Ranking traceability and score semantics audit"

RANKING_SORT_PRIORITY = [
    "included_in_therapeutic_ranking",
    "meta_priority_score_v3",
    "evidence_quality_score",
    "functional_node_theory_score",
    "confidence_ceiling",
    "meta_priority_score_v2",
]

PRIMARY_SCORE_PRIORITY = [
    "meta_priority_score_v3",
    "meta_priority_score_v2",
    "meta_priority_score",
    "therapeutic_priority_score",
    "nodo_score",
    "functional_node_theory_score",
    "score",
]

IDENTIFIER_COLUMNS = (
    "candidate_seed_accession",
    "protein_id",
    "accession",
    "gene",
)

TRACE_COLUMNS = [
    "benchmark_token",
    "benchmark_match_type",
    "benchmark_alias_used",
    "candidate_seed_accession",
    "protein_id",
    "gene",
    "discovered_naturally",
    "benchmark_forced_candidate",
    "seed_initial_rank",
    "seed_selected_rank",
    "selected_for_scoring",
    "stage5a2_final_rank_legacy",
    "stage5a2_reported_score_legacy",
    "stage5a2_reported_score_column_legacy",
    "ranking_match",
    "phase3_match",
    "final_rank",
    "final_rank_definition",
    "ranking_rank_column",
    "ranking_rank_column_value",
    "included_in_therapeutic_ranking",
    "therapeutic_primary_score",
    "therapeutic_primary_score_column",
    "therapeutic_sort_columns",
    "therapeutic_sort_values",
    "functional_node_theory_score",
    "functional_node_theory_rank",
    "functional_node_theory_confidence",
    "functional_node_theory_label",
    "evidence_quality_score",
    "confidence_ceiling",
    "meta_priority_score_v2",
    "meta_priority_score_v3",
    "rank_phase3_real_candidates",
    "rank_phase3_all_records",
    "phase3_evidence_confidence_label",
    "phase3_recommendation",
    "evolutionary_escape_risk_score",
    "redundancy_penalty",
    "host_similarity_risk",
    "host_similarity_penalty",
    "seed_to_fnt_rank_delta",
    "fnt_to_final_rank_delta",
    "seed_to_final_rank_delta",
    "legacy_score_matches_primary_semantics",
    "audit_status",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().casefold()


def _jsonable(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (bool, str, int, float)):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return str(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _workspace_from_run_dir(run_dir: Path) -> tuple[Path, Path]:
    base = Path(run_dir).resolve()
    if base.name == "workspace":
        workspace = base
        run_base = base.parent
    else:
        run_base = base
        workspace = base / "workspace"
    if not workspace.is_dir():
        raise ValueError(f"Stage 5A.3 workspace not found: {workspace}")
    return run_base, workspace


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise ValueError(f"Stage 5A.3 required input missing: {path}")
    return pd.read_csv(path, low_memory=False)


def _identifier_lookup(df: pd.DataFrame) -> dict[str, int]:
    lookup: dict[str, int] = {}
    for idx, row in df.iterrows():
        for column in IDENTIFIER_COLUMNS:
            if column not in df.columns:
                continue
            key = _norm(row.get(column))
            if key and key not in lookup:
                lookup[key] = idx
    return lookup


def _match_index(row: pd.Series, lookup: dict[str, int]) -> int | None:
    for column in IDENTIFIER_COLUMNS:
        key = _norm(row.get(column))
        if key and key in lookup:
            return lookup[key]
    return None


def _rank_column(ranking: pd.DataFrame) -> str | None:
    return next(
        (
            column
            for column in ("final_rank", "rank", "nodo_rank", "ranking_position")
            if column in ranking.columns
        ),
        None,
    )


def _primary_score_column(ranking: pd.DataFrame) -> str | None:
    return next((column for column in PRIMARY_SCORE_PRIORITY if column in ranking.columns), None)


def _sort_columns(ranking: pd.DataFrame) -> list[str]:
    return [column for column in RANKING_SORT_PRIORITY if column in ranking.columns]


def _first_value(
    ranking_row: pd.Series | None,
    phase3_row: pd.Series | None,
    column: str,
) -> Any:
    for row in (ranking_row, phase3_row):
        if row is not None and column in row.index:
            value = row.get(column)
            if not pd.isna(value):
                return value
    return pd.NA


def _fnt_ranks(ranking: pd.DataFrame) -> pd.Series | None:
    if "functional_node_theory_score" not in ranking.columns:
        return None
    return pd.to_numeric(
        ranking["functional_node_theory_score"], errors="coerce"
    ).rank(method="min", ascending=False, na_option="bottom")


def _numeric_delta(left: Any, right: Any) -> Any:
    try:
        if pd.isna(left) or pd.isna(right):
            return pd.NA
        return int(right) - int(left)
    except (TypeError, ValueError):
        return pd.NA


def build_stage5a3_rank_trace(
    stage5a2_audit: pd.DataFrame,
    ranking: pd.DataFrame,
    phase3: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build a benchmark-only trace of seed, FNT, Phase 3, and final ranking semantics.

    Stage 5A.3 is deliberately read-only with respect to scoring. It does not
    recalculate or reorder candidates. The final rank is defined as the 1-based
    row order already present in ``ranking_nodos.csv``.
    """
    if ranking.empty:
        raise ValueError("Stage 5A.3 cannot audit an empty ranking_nodos.csv")
    if "protein_id" not in ranking.columns:
        raise ValueError("Stage 5A.3 requires protein_id in ranking_nodos.csv")
    if "protein_id" not in phase3.columns:
        raise ValueError("Stage 5A.3 requires protein_id in phase3_features.csv")

    benchmarks = stage5a2_audit.copy()
    if "benchmark_requested" in benchmarks.columns:
        requested = benchmarks["benchmark_requested"].fillna(False).astype(bool)
        benchmarks = benchmarks.loc[requested].copy()
    elif "benchmark_token" in benchmarks.columns:
        benchmarks = benchmarks.loc[
            benchmarks["benchmark_token"].fillna("").astype(str).str.strip().ne("")
        ].copy()
    else:
        raise ValueError("Stage 5A.3 requires benchmark_token or benchmark_requested in the Stage 5A.2 audit")

    ranking_lookup = _identifier_lookup(ranking)
    phase3_lookup = _identifier_lookup(phase3)
    fnt_ranks = _fnt_ranks(ranking)
    rank_col = _rank_column(ranking)
    primary_col = _primary_score_column(ranking)
    sort_cols = _sort_columns(ranking)

    rows: list[dict[str, Any]] = []
    for _, benchmark in benchmarks.iterrows():
        ranking_idx = _match_index(benchmark, ranking_lookup)
        phase3_idx = _match_index(benchmark, phase3_lookup)

        ranking_row = ranking.loc[ranking_idx] if ranking_idx is not None else None
        phase3_row = phase3.loc[phase3_idx] if phase3_idx is not None else None

        final_rank = int(ranking.index.get_loc(ranking_idx)) + 1 if ranking_idx is not None else pd.NA
        fnt_rank = (
            int(fnt_ranks.loc[ranking_idx])
            if ranking_idx is not None
            and fnt_ranks is not None
            and pd.notna(fnt_ranks.loc[ranking_idx])
            else pd.NA
        )

        legacy_score = benchmark.get("final_score", pd.NA)
        legacy_score_col = str(benchmark.get("final_score_column", "") or "")
        legacy_semantics_match = bool(primary_col and legacy_score_col == primary_col)

        sort_values = {
            column: _jsonable(ranking_row.get(column))
            for column in sort_cols
        } if ranking_row is not None else {}

        trace = {
            "benchmark_token": benchmark.get("benchmark_token", ""),
            "benchmark_match_type": benchmark.get("benchmark_match_type", ""),
            "benchmark_alias_used": benchmark.get("benchmark_alias_used", ""),
            "candidate_seed_accession": benchmark.get("candidate_seed_accession", ""),
            "protein_id": benchmark.get("protein_id", ""),
            "gene": benchmark.get("gene", ""),
            "discovered_naturally": benchmark.get("discovered_naturally", False),
            "benchmark_forced_candidate": benchmark.get("benchmark_forced_candidate", False),
            "seed_initial_rank": benchmark.get("seed_initial_rank", pd.NA),
            "seed_selected_rank": benchmark.get("seed_selected_rank", pd.NA),
            "selected_for_scoring": benchmark.get("selected_for_scoring", False),
            "stage5a2_final_rank_legacy": benchmark.get("final_rank", pd.NA),
            "stage5a2_reported_score_legacy": legacy_score,
            "stage5a2_reported_score_column_legacy": legacy_score_col,
            "ranking_match": ranking_idx is not None,
            "phase3_match": phase3_idx is not None,
            "final_rank": final_rank,
            "final_rank_definition": "1_based_row_order_in_ranking_nodos.csv",
            "ranking_rank_column": rank_col or "",
            "ranking_rank_column_value": ranking_row.get(rank_col, pd.NA) if ranking_row is not None and rank_col else pd.NA,
            "included_in_therapeutic_ranking": _first_value(ranking_row, phase3_row, "included_in_therapeutic_ranking"),
            "therapeutic_primary_score": ranking_row.get(primary_col, pd.NA) if ranking_row is not None and primary_col else pd.NA,
            "therapeutic_primary_score_column": primary_col or "",
            "therapeutic_sort_columns": json.dumps(sort_cols, ensure_ascii=False),
            "therapeutic_sort_values": json.dumps(sort_values, ensure_ascii=False),
            "functional_node_theory_score": _first_value(ranking_row, phase3_row, "functional_node_theory_score"),
            "functional_node_theory_rank": fnt_rank,
            "functional_node_theory_confidence": _first_value(ranking_row, phase3_row, "functional_node_theory_confidence"),
            "functional_node_theory_label": _first_value(ranking_row, phase3_row, "functional_node_theory_label"),
            "evidence_quality_score": _first_value(ranking_row, phase3_row, "evidence_quality_score"),
            "confidence_ceiling": _first_value(ranking_row, phase3_row, "confidence_ceiling"),
            "meta_priority_score_v2": _first_value(ranking_row, phase3_row, "meta_priority_score_v2"),
            "meta_priority_score_v3": _first_value(ranking_row, phase3_row, "meta_priority_score_v3"),
            "rank_phase3_real_candidates": _first_value(ranking_row, phase3_row, "rank_phase3_real_candidates"),
            "rank_phase3_all_records": _first_value(ranking_row, phase3_row, "rank_phase3_all_records"),
            "phase3_evidence_confidence_label": _first_value(ranking_row, phase3_row, "phase3_evidence_confidence_label"),
            "phase3_recommendation": _first_value(ranking_row, phase3_row, "phase3_recommendation"),
            "evolutionary_escape_risk_score": _first_value(ranking_row, phase3_row, "evolutionary_escape_risk_score"),
            "redundancy_penalty": _first_value(ranking_row, phase3_row, "redundancy_penalty"),
            "host_similarity_risk": _first_value(ranking_row, phase3_row, "host_similarity_risk"),
            "host_similarity_penalty": _first_value(ranking_row, phase3_row, "host_similarity_penalty"),
            "seed_to_fnt_rank_delta": _numeric_delta(benchmark.get("seed_initial_rank", pd.NA), fnt_rank),
            "fnt_to_final_rank_delta": _numeric_delta(fnt_rank, final_rank),
            "seed_to_final_rank_delta": _numeric_delta(benchmark.get("seed_initial_rank", pd.NA), final_rank),
            "legacy_score_matches_primary_semantics": legacy_semantics_match,
            "audit_status": (
                "matched_ranking_and_phase3"
                if ranking_idx is not None and phase3_idx is not None
                else "missing_ranking_match"
                if ranking_idx is None
                else "missing_phase3_match"
            ),
        }
        rows.append(trace)

    trace_df = pd.DataFrame(rows)
    for column in TRACE_COLUMNS:
        if column not in trace_df.columns:
            trace_df[column] = pd.NA
    trace_df = trace_df[TRACE_COLUMNS]

    summary = {
        "benchmark_count": int(len(trace_df)),
        "ranking_row_count": int(len(ranking)),
        "phase3_row_count": int(len(phase3)),
        "ranking_match_count": int(trace_df["ranking_match"].fillna(False).sum()),
        "phase3_match_count": int(trace_df["phase3_match"].fillna(False).sum()),
        "primary_score_column": primary_col,
        "ranking_rank_column": rank_col,
        "ranking_sort_columns": sort_cols,
        "final_rank_definition": "1_based_row_order_in_ranking_nodos.csv",
        "legacy_score_semantics_mismatch_count": int(
            (~trace_df["legacy_score_matches_primary_semantics"].fillna(False)).sum()
        ),
    }
    return trace_df, summary


def run_stage5a3_rank_trace(run_dir: Path) -> dict[str, Any]:
    """Audit an already-completed Stage 5A.2 run without rerunning providers or scoring."""
    run_base, workspace = _workspace_from_run_dir(Path(run_dir))
    results = workspace / "results"
    processed = workspace / "data_processed"

    stage5a2_audit_path = results / "stage5a2_candidate_seed_audit.csv"
    ranking_path = results / "ranking_nodos.csv"
    phase3_path = processed / "phase3_features.csv"
    stage5a2_manifest_path = results / "stage5a2_manifest.json"

    source_paths = [stage5a2_audit_path, ranking_path, phase3_path]
    source_hashes = {str(path): _sha256(path) for path in source_paths if path.exists()}

    stage5a2_audit = _load_csv(stage5a2_audit_path)
    ranking = _load_csv(ranking_path)
    phase3 = _load_csv(phase3_path)

    trace, summary = build_stage5a3_rank_trace(stage5a2_audit, ranking, phase3)

    output_path = results / "stage5a3_rank_trace.csv"
    trace.to_csv(output_path, index=False)

    stage5a2_manifest: dict[str, Any] = {}
    if stage5a2_manifest_path.exists():
        stage5a2_manifest = json.loads(stage5a2_manifest_path.read_text(encoding="utf-8"))

    benchmark_trace = [
        {
            "benchmark_token": _jsonable(row.get("benchmark_token")),
            "protein_id": _jsonable(row.get("protein_id")),
            "gene": _jsonable(row.get("gene")),
            "seed_initial_rank": _jsonable(row.get("seed_initial_rank")),
            "functional_node_theory_rank": _jsonable(row.get("functional_node_theory_rank")),
            "final_rank": _jsonable(row.get("final_rank")),
            "therapeutic_primary_score": _jsonable(row.get("therapeutic_primary_score")),
            "therapeutic_primary_score_column": _jsonable(row.get("therapeutic_primary_score_column")),
            "functional_node_theory_score": _jsonable(row.get("functional_node_theory_score")),
            "evidence_quality_score": _jsonable(row.get("evidence_quality_score")),
            "audit_status": _jsonable(row.get("audit_status")),
        }
        for _, row in trace.iterrows()
    ]

    manifest = {
        "schema_version": "1.0",
        "stage": STAGE,
        "stage_name": STAGE_NAME,
        "source_stage": "5A.2",
        "run_dir": str(run_base),
        "workspace": str(workspace),
        "organism": stage5a2_manifest.get("organism"),
        "strain": stage5a2_manifest.get("strain"),
        "taxon_id": stage5a2_manifest.get("taxon_id"),
        "proteome_id": stage5a2_manifest.get("proteome_id"),
        "audit_status": "completed",
        **summary,
        "source_files": {
            "stage5a2_candidate_seed_audit": str(stage5a2_audit_path),
            "ranking_nodos": str(ranking_path),
            "phase3_features": str(phase3_path),
        },
        "source_sha256": source_hashes,
        "output": str(output_path),
        "benchmark_trace": benchmark_trace,
        "providers_rerun": False,
        "scoring_recomputed": False,
        "ranking_order_changed": False,
        "scoring_model_changed": False,
        "functional_node_theory_weights_changed": False,
        "interpretation": (
            "Stage 5A.3 separates the primary therapeutic ranking score and sort semantics "
            "from legacy Stage 5A.2 score labels. It is an audit-only stage."
        ),
        "generated_at_utc": _now(),
    }

    manifest_path = results / "stage5a3_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    review_package = run_base / "review_package"
    if review_package.is_dir():
        trace.to_csv(review_package / "stage5a3_rank_trace.csv", index=False)
        (review_package / "stage5a3_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return {
        "stage": STAGE,
        "audit_status": "completed",
        "run_dir": str(run_base),
        "workspace": str(workspace),
        "stage5a3_rank_trace": str(output_path),
        "stage5a3_manifest": str(manifest_path),
        "summary": summary,
        "benchmark_trace": benchmark_trace,
    }
