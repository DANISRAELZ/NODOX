from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _json_dump(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def snapshot_pre_enrichment_state(workspace: Path, source: str) -> tuple[Path, Path]:
    workspace = Path(workspace)
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    ranking_path = results_dir / "ranking_nodos.csv"
    manifest_path = results_dir / "online_source_manifest.json"
    snapshot_ranking_path = results_dir / "online_enrichment_before.csv"
    snapshot_meta_path = results_dir / "online_enrichment_before.json"

    if ranking_path.exists():
        ranking = pd.read_csv(ranking_path)
        ranking.to_csv(snapshot_ranking_path, index=False)
    else:
        pd.DataFrame().to_csv(snapshot_ranking_path, index=False)

    payload = {
        "planned_source": source,
        "has_prior_ranking": ranking_path.exists(),
        "has_prior_online_manifest": manifest_path.exists(),
        "prior_online_manifest_path": str(manifest_path) if manifest_path.exists() else "",
    }
    if manifest_path.exists():
        payload["prior_online_manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
    _json_dump(snapshot_meta_path, payload)
    return snapshot_ranking_path, snapshot_meta_path


def build_before_after_ranking_audit(workspace: Path) -> tuple[Path, Path] | None:
    workspace = Path(workspace)
    results_dir = workspace / "results"
    audit_path = results_dir / "online_enrichment_impact.csv"
    summary_path = results_dir / "online_enrichment_impact.md"
    ranking_path = results_dir / "ranking_nodos.csv"
    manifest_path = results_dir / "online_source_manifest.json"
    before_ranking_path = results_dir / "online_enrichment_before.csv"
    before_meta_path = results_dir / "online_enrichment_before.json"
    if not ranking_path.exists() or not manifest_path.exists():
        return None

    ranking_after = pd.read_csv(ranking_path)
    if ranking_after.empty:
        return None

    required_columns = {"protein_id", "gene", "meta_priority_score"}
    if not required_columns.issubset(ranking_after.columns):
        return None

    ranking_after = ranking_after[["protein_id", "gene", "meta_priority_score"]].copy()
    ranking_after["rank_after_online"] = range(1, len(ranking_after) + 1)
    ranking_after = ranking_after.rename(columns={"meta_priority_score": "meta_priority_score_after"})

    if before_ranking_path.exists():
        ranking_before = pd.read_csv(before_ranking_path)
    else:
        ranking_before = pd.DataFrame()

    if not ranking_before.empty and required_columns.issubset(ranking_before.columns):
        ranking_before = ranking_before[["protein_id", "gene", "meta_priority_score"]].copy()
        ranking_before["rank_before_online"] = range(1, len(ranking_before) + 1)
        ranking_before = ranking_before.rename(columns={"meta_priority_score": "meta_priority_score_before"})
    else:
        ranking_before = pd.DataFrame(columns=["protein_id", "gene", "meta_priority_score_before", "rank_before_online"])

    comparison = ranking_after.merge(
        ranking_before[["protein_id", "rank_before_online", "meta_priority_score_before"]],
        on="protein_id",
        how="left",
    )
    comparison["rank_shift"] = comparison["rank_before_online"] - comparison["rank_after_online"]
    comparison["score_delta"] = comparison["meta_priority_score_after"] - comparison["meta_priority_score_before"]
    comparison["changed_after_online"] = (
        comparison["rank_before_online"].fillna(-1) != comparison["rank_after_online"].fillna(-1)
    ) | (
        comparison["score_delta"].fillna(0).abs() > 1e-12
    )

    comparison["impact_scope"] = comparison["changed_after_online"].map(
        lambda changed: "ranking_changed" if changed else "annotation_or_provenance_only"
    )
    comparison.to_csv(audit_path, index=False)

    before_meta = {}
    if before_meta_path.exists():
        before_meta = json.loads(before_meta_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed_count = int(comparison["changed_after_online"].sum())
    unchanged_count = int((~comparison["changed_after_online"]).sum())
    top10_changed = int(comparison.head(10)["changed_after_online"].sum())

    lines = [
        "# Online Enrichment Impact",
        "",
        f"- Current source: `{manifest.get('source', 'unknown')}`",
        f"- Source used: `{manifest.get('source_used', 'unknown')}`",
        f"- API success: `{manifest.get('api_success', False)}`",
        f"- Prior ranking available: `{before_meta.get('has_prior_ranking', False)}`",
        f"- Candidates with any detected change: `{changed_count}`",
        f"- Candidates unchanged after enrichment: `{unchanged_count}`",
        f"- Top 10 candidates changed: `{top10_changed}`",
        "",
        "| protein_id | gene | rank_before_online | rank_after_online | rank_shift | score_delta | impact_scope |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in comparison.head(10).iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["protein_id"]),
                    str(row["gene"]),
                    str("" if pd.isna(row["rank_before_online"]) else int(row["rank_before_online"])),
                    str(int(row["rank_after_online"])),
                    str("" if pd.isna(row["rank_shift"]) else int(row["rank_shift"])),
                    f"{0.0 if pd.isna(row['score_delta']) else float(row['score_delta']):.4f}",
                    str(row["impact_scope"]),
                ]
            )
            + " |"
        )
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return audit_path, summary_path
