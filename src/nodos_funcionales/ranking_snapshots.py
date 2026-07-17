from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


SNAPSHOT_SCORE_COLUMNS = [
    "legacy_score_final",
    "antibiotic_target_score",
    "antivirulence_target_score",
    "functional_node_score",
    "meta_priority_score",
    "therapeutic_priority_score",
    "meta_priority_score_v3",
]

SNAPSHOT_TEXT_COLUMNS = [
    "therapeutic_role",
    "therapeutic_role_rule",
    "preferred_strategy",
    "ranking_inclusion_status",
]


def build_ranking_snapshot(ranking: pd.DataFrame, score_columns: Iterable[str] | None = None) -> pd.DataFrame:
    """Create a compact, deterministic ranking snapshot for regression checks."""
    if ranking.empty:
        return pd.DataFrame(columns=["rank", "protein_id", "gene"])
    snapshot = ranking.copy()
    if "rank" not in snapshot.columns:
        snapshot = snapshot.reset_index()
        if "rank" not in snapshot.columns:
            snapshot["rank"] = range(1, len(snapshot) + 1)
    columns = ["rank", "protein_id", "gene"]
    for column in ["organism", "strain", "taxon_id"]:
        if column in snapshot.columns:
            columns.append(column)
    for column in score_columns or SNAPSHOT_SCORE_COLUMNS:
        if column in snapshot.columns:
            columns.append(column)
    for column in SNAPSHOT_TEXT_COLUMNS:
        if column in snapshot.columns:
            columns.append(column)
    result = snapshot[[column for column in columns if column in snapshot.columns]].copy()
    for column in result.columns:
        if column in {"rank"}:
            result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0).astype(int)
        elif pd.api.types.is_numeric_dtype(result[column]) or column in SNAPSHOT_SCORE_COLUMNS:
            result[column] = pd.to_numeric(result[column], errors="coerce").round(6)
    return result.sort_values(["rank", "protein_id"], kind="stable").reset_index(drop=True)


def compare_ranking_snapshots(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    score_tolerance: float = 1.0e-6,
) -> pd.DataFrame:
    """Compare two snapshots and flag rank, score and label drift."""
    if reference.empty and current.empty:
        return pd.DataFrame(columns=["protein_id", "change_type", "rank_delta", "max_score_delta", "changed_fields"])
    ref = _prepare_for_compare(reference, "reference")
    cur = _prepare_for_compare(current, "current")
    merged = ref.merge(cur, on="protein_id", how="outer", suffixes=("_reference", "_current"), indicator=True)
    rows = []
    score_columns = sorted(
        {
            column.rsplit("_", 1)[0]
            for column in merged.columns
            if column.endswith("_reference") and column.rsplit("_", 1)[0] in SNAPSHOT_SCORE_COLUMNS
        }
    )
    text_columns = sorted(
        {
            column.rsplit("_", 1)[0]
            for column in merged.columns
            if column.endswith("_reference") and column.rsplit("_", 1)[0] in SNAPSHOT_TEXT_COLUMNS
        }
    )
    for _, row in merged.iterrows():
        if row["_merge"] == "left_only":
            rows.append(_comparison_row(row, "removed", 0, 0.0, "record_removed"))
            continue
        if row["_merge"] == "right_only":
            rows.append(_comparison_row(row, "added", 0, 0.0, "record_added"))
            continue
        rank_delta = int(row.get("rank_current", 0) or 0) - int(row.get("rank_reference", 0) or 0)
        changed_fields = []
        score_deltas = []
        for column in score_columns:
            delta = abs(_num(row.get(f"{column}_current")) - _num(row.get(f"{column}_reference")))
            score_deltas.append(delta)
            if delta > score_tolerance:
                changed_fields.append(column)
        for column in text_columns:
            if str(row.get(f"{column}_current", "")) != str(row.get(f"{column}_reference", "")):
                changed_fields.append(column)
        change_type = "unchanged"
        if rank_delta:
            change_type = "rank_changed"
        if changed_fields:
            change_type = "score_or_label_changed" if change_type == "unchanged" else "rank_and_score_changed"
        rows.append(
            _comparison_row(
                row,
                change_type,
                rank_delta,
                max(score_deltas) if score_deltas else 0.0,
                "; ".join(changed_fields) if changed_fields else "none",
            )
        )
    return pd.DataFrame(rows).sort_values(["change_type", "protein_id"], kind="stable").reset_index(drop=True)


def write_ranking_snapshot_outputs(results_dir: Path, ranking: pd.DataFrame) -> tuple[Path, Path | None]:
    results_dir.mkdir(parents=True, exist_ok=True)
    snapshot = build_ranking_snapshot(ranking)
    snapshot_path = results_dir / "ranking_snapshot.csv"
    snapshot.to_csv(snapshot_path, index=False)
    reference_path = results_dir / "ranking_snapshot_reference.csv"
    if not reference_path.exists():
        return snapshot_path, None
    reference = pd.read_csv(reference_path)
    comparison = compare_ranking_snapshots(reference, snapshot)
    comparison_path = results_dir / "ranking_snapshot_comparison.csv"
    comparison.to_csv(comparison_path, index=False)
    return snapshot_path, comparison_path


def _prepare_for_compare(df: pd.DataFrame, label: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["protein_id", "rank"])
    prepared = df.copy()
    if "protein_id" not in prepared.columns:
        raise ValueError(f"Snapshot {label} no tiene columna `protein_id`.")
    prepared["protein_id"] = prepared["protein_id"].fillna("").astype(str)
    return prepared


def _comparison_row(row: pd.Series, change_type: str, rank_delta: int, score_delta: float, fields: str) -> dict[str, object]:
    return {
        "protein_id": row.get("protein_id", ""),
        "gene_reference": row.get("gene_reference", ""),
        "gene_current": row.get("gene_current", ""),
        "change_type": change_type,
        "rank_reference": row.get("rank_reference", ""),
        "rank_current": row.get("rank_current", ""),
        "rank_delta": rank_delta,
        "max_score_delta": round(float(score_delta), 8),
        "changed_fields": fields,
    }


def _num(value: object) -> float:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").fillna(0.0).iloc[0]
    return float(numeric)
