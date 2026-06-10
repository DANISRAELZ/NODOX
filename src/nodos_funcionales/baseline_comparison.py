from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_baseline_comparison(scored_candidates: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    baselines = {
        "baseline_rank_by_antibiotic_target_score": "antibiotic_target_score",
        "baseline_rank_by_functional_node_score": "functional_node_score",
    }
    working = scored_candidates.copy()
    if "baseline_score_unweighted_mean" not in working.columns:
        score_columns = [
            column
            for column in ["antibiotic_target_score", "antivirulence_target_score", "functional_node_score"]
            if column in working.columns
        ]
        working["baseline_score_unweighted_mean"] = working[score_columns].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    baselines["baseline_rank_by_unweighted_mean"] = "baseline_score_unweighted_mean"

    nodos = working.sort_values("final_priority_rank").copy()
    nodos["nodos_rank"] = nodos["final_priority_rank"]
    for baseline_name, score_column in baselines.items():
        baseline = working.sort_values([score_column, "protein_id"], ascending=[False, True], kind="mergesort").copy()
        baseline["baseline_rank"] = range(1, len(baseline) + 1)
        merged = nodos.merge(
            baseline[["protein_id", "baseline_rank", score_column]],
            on="protein_id",
            how="left",
            suffixes=("", "_baseline"),
        )
        rows.append(
            pd.DataFrame(
                {
                    "baseline_name": baseline_name,
                    "gene": merged.get("gene", "not_reported"),
                    "protein_id": merged["protein_id"],
                    "nodos_rank": merged["nodos_rank"],
                    "baseline_rank": merged["baseline_rank"],
                    "rank_delta": merged["baseline_rank"] - merged["nodos_rank"],
                    "nodos_meta_priority_score": merged["meta_priority_score"],
                    "baseline_score": merged[score_column],
                    "therapeutic_role": merged.get("therapeutic_role", "not_reported"),
                    "evidence_confidence_score": merged.get("evidence_confidence_score", 0.0),
                    "interpretation_note": "baseline comparison only; candidate functional node remains a prioritized hypothesis",
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def write_baseline_comparison(
    scored_candidates: pd.DataFrame,
    output_dir: Path,
) -> pd.DataFrame:
    comparison = build_baseline_comparison(scored_candidates)
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(output_dir / "publication_table_6_baseline_comparison.csv", index=False)
    lines = [
        "# Baseline Comparison",
        "",
        "This comparison contrasts Nodos ranking with simple baseline rankings. It is a computational demonstration and not clinical recommendation.",
        "",
        _markdown_table(comparison.head(30)),
    ]
    (output_dir / "publication_baseline_comparison.md").write_text("\n".join(lines), encoding="utf-8")
    return comparison


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows available._"
    display = df.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].round(4)
    lines = [
        "| " + " | ".join(display.columns.astype(str)) + " |",
        "| " + " | ".join(["---"] * len(display.columns)) + " |",
    ]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in display.columns) + " |")
    return "\n".join(lines)
