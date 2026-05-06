from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _impact_summary_from_csv(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "online_impact_status": "",
            "online_changed_candidate_count": 0,
            "online_top10_changed_count": 0,
        }
    impact = pd.read_csv(path)
    if impact.empty or "impact_scope" not in impact.columns:
        return {
            "online_impact_status": "",
            "online_changed_candidate_count": 0,
            "online_top10_changed_count": 0,
        }
    changed_mask = impact["impact_scope"].astype(str).eq("ranking_changed")
    changed_count = int(changed_mask.sum())
    return {
        "online_impact_status": "ranking_changed" if changed_count > 0 else "annotation_or_provenance_only",
        "online_changed_candidate_count": changed_count,
        "online_top10_changed_count": int(changed_mask.head(10).sum()),
    }


def classify_online_run(manifest: dict[str, Any]) -> str:
    source_used = str(manifest.get("source_used", ""))
    cache_hit = bool(manifest.get("cache_hit", False))
    api_attempted = bool(manifest.get("api_attempted", False))
    api_success = bool(manifest.get("api_success", False))
    if source_used == "api_real" and api_attempted and api_success:
        return "fresh_api_run"
    if source_used == "cache" and cache_hit and not api_attempted:
        return "cache_reuse_run"
    if source_used == "cache" and cache_hit and api_attempted and not api_success:
        return "fallback_after_api_failure"
    return "other_online_run"


def append_online_history(workspace: Path, manifest: dict[str, Any]) -> Path:
    workspace = Path(workspace)
    results_dir = workspace / "results"
    history_path = results_dir / "online_source_history.jsonl"
    impact_summary = _impact_summary_from_csv(results_dir / "online_enrichment_impact.csv")
    entry = {
        "recorded_at_utc": _utc_now(),
        "workspace": str(workspace),
        "source": manifest.get("source", ""),
        "provider": manifest.get("provider", ""),
        "mode": manifest.get("mode", ""),
        "source_used": manifest.get("source_used", ""),
        "cache_hit": manifest.get("cache_hit"),
        "api_attempted": manifest.get("api_attempted"),
        "api_success": manifest.get("api_success"),
        "data_realism_flag": manifest.get("data_realism_flag", ""),
        "fallback_reason": manifest.get("fallback_reason") or "",
        "query_cache_key": manifest.get("query_cache_key", ""),
        "taxon_id": manifest.get("taxon_id", ""),
        "run_kind": classify_online_run(manifest),
        **impact_summary,
    }
    _append_jsonl(history_path, entry)
    return history_path


def load_online_history(workspace: Path) -> pd.DataFrame:
    rows = _read_jsonl(Path(workspace) / "results" / "online_source_history.jsonl")
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def write_online_source_comparison(workspace: Path) -> tuple[Path, Path, pd.DataFrame]:
    workspace = Path(workspace)
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    history = load_online_history(workspace)
    csv_path = results_dir / "online_source_comparison.csv"
    md_path = results_dir / "online_source_comparison.md"
    if history.empty:
        pd.DataFrame().to_csv(csv_path, index=False)
        md_path.write_text("# Online Source Comparison\n\n_No online history found._\n", encoding="utf-8")
        return csv_path, md_path, history

    comparison = (
        history.sort_values("recorded_at_utc")
        .groupby("source", as_index=False)
        .agg(
            runs=("source", "size"),
            latest_recorded_at_utc=("recorded_at_utc", "last"),
            latest_source_used=("source_used", "last"),
            latest_run_kind=("run_kind", "last"),
            latest_cache_hit=("cache_hit", "last"),
            latest_api_success=("api_success", "last"),
            latest_data_realism_flag=("data_realism_flag", "last"),
            latest_impact_status=("online_impact_status", "last"),
            max_changed_candidate_count=("online_changed_candidate_count", "max"),
            max_top10_changed_count=("online_top10_changed_count", "max"),
        )
    )
    comparison.to_csv(csv_path, index=False)

    display = comparison.copy()
    lines = [
        "# Online Source Comparison",
        "",
        f"- Workspace: `{workspace}`",
        "",
        "| " + " | ".join(display.columns) + " |",
        "| " + " | ".join(["---"] * len(display.columns)) + " |",
    ]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in display.columns) + " |")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, md_path, comparison
