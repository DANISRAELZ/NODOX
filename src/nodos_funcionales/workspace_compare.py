from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_workspace(workspace: Path) -> dict[str, Any]:
    results_dir = workspace / "results"
    profile_path = results_dir / "organism_profile.json"
    manifest_path = results_dir / "acquisition_manifest.json"
    ranking_path = results_dir / "ranking_nodos.csv"
    online_manifest_path = results_dir / "online_source_manifest.json"
    online_impact_path = results_dir / "online_enrichment_impact.csv"
    online_history_path = results_dir / "online_source_history.jsonl"
    online_source_comparison_path = results_dir / "online_source_comparison.csv"
    summary = {
        "workspace": str(workspace),
        "workspace_name": workspace.name,
        "organism_canonical_name": "",
        "strain_canonical": "",
        "completeness_status": "missing",
        "can_run_pipeline": False,
        "present_dataset_count": 0,
        "missing_required_count": 0,
        "top_candidate_protein_id": "",
        "top_candidate_gene": "",
        "top_meta_priority_score": None,
        "online_source": "",
        "online_source_used": "",
        "online_cache_hit": None,
        "online_api_success": None,
        "online_data_realism_flag": "",
        "online_fallback_reason": "",
        "online_impact_status": "",
        "online_changed_candidate_count": 0,
        "online_top10_changed_count": 0,
        "online_history_count": 0,
        "online_sources_seen": "",
    }
    if profile_path.exists():
        profile = _load_json(profile_path)
        summary["organism_canonical_name"] = profile.get("organism_canonical_name", "")
        summary["strain_canonical"] = profile.get("strain_canonical") or ""
        summary["completeness_status"] = profile.get("completeness_status", "missing")
    if manifest_path.exists():
        manifest = _load_json(manifest_path)
        summary["can_run_pipeline"] = bool(manifest.get("can_run_pipeline", False))
        summary["present_dataset_count"] = int(manifest.get("present_dataset_count", 0))
        summary["missing_required_count"] = len(manifest.get("missing_required_datasets", []))
    if ranking_path.exists():
        ranking = pd.read_csv(ranking_path)
        if not ranking.empty:
            top = ranking.iloc[0]
            summary["top_candidate_protein_id"] = top.get("protein_id", "")
            summary["top_candidate_gene"] = top.get("gene", "")
            summary["top_meta_priority_score"] = top.get("meta_priority_score")
    if online_manifest_path.exists():
        online_manifest = _load_json(online_manifest_path)
        summary["online_source"] = online_manifest.get("source", "")
        summary["online_source_used"] = online_manifest.get("source_used", "")
        summary["online_cache_hit"] = online_manifest.get("cache_hit")
        summary["online_api_success"] = online_manifest.get("api_success")
        summary["online_data_realism_flag"] = online_manifest.get("data_realism_flag", "")
        summary["online_fallback_reason"] = online_manifest.get("fallback_reason") or ""
    if online_impact_path.exists():
        impact = pd.read_csv(online_impact_path)
        if not impact.empty and "impact_scope" in impact.columns:
            changed_mask = impact["impact_scope"].astype(str).eq("ranking_changed")
            changed_count = int(changed_mask.sum())
            top10_changed_count = int(changed_mask.head(10).sum())
            summary["online_changed_candidate_count"] = changed_count
            summary["online_top10_changed_count"] = top10_changed_count
            summary["online_impact_status"] = (
                "ranking_changed" if changed_count > 0 else "annotation_or_provenance_only"
            )
    if online_history_path.exists():
        lines = [line.strip() for line in online_history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        summary["online_history_count"] = len(lines)
    if online_source_comparison_path.exists():
        comparison = pd.read_csv(online_source_comparison_path)
        if not comparison.empty and "source" in comparison.columns:
            summary["online_sources_seen"] = ";".join(comparison["source"].astype(str).tolist())
    return summary


def compare_workspaces(base_dir: Path) -> pd.DataFrame:
    session_dir = base_dir / "data_sessions"
    if not session_dir.exists():
        return pd.DataFrame(columns=["workspace_name", "organism_canonical_name"])
    rows = [summarize_workspace(path) for path in sorted(session_dir.iterdir()) if path.is_dir()]
    return pd.DataFrame(rows)


def write_workspace_comparison(base_dir: Path) -> tuple[Path, Path, pd.DataFrame]:
    results_dir = base_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    comparison = compare_workspaces(base_dir)
    csv_path = results_dir / "workspace_comparison.csv"
    md_path = results_dir / "workspace_comparison.md"
    comparison.to_csv(csv_path, index=False)
    if comparison.empty:
        markdown = "# Workspace Comparison\n\n_No workspaces found._\n"
    else:
        display = comparison.copy()
        float_columns = display.select_dtypes(include=["float", "float64"]).columns
        if len(float_columns):
            display[float_columns] = display[float_columns].round(4)
        lines = [
            "# Workspace Comparison",
            "",
            "| " + " | ".join(display.columns) + " |",
            "| " + " | ".join(["---"] * len(display.columns)) + " |",
        ]
        for _, row in display.iterrows():
            lines.append("| " + " | ".join(str(row[column]) for column in display.columns) + " |")
        markdown = "\n".join(lines)
    md_path.write_text(markdown, encoding="utf-8")
    return csv_path, md_path, comparison
