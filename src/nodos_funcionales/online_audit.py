from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from .config import load_config
from .discovery import resolve_taxon
from .online_history import classify_online_run
from .online_reporting import build_before_after_ranking_audit, snapshot_pre_enrichment_state
from .online_sources import fetch_online_source
from .pipeline import run_pipeline


SCORE_COLUMNS = [
    "legacy_score_final",
    "antibiotic_target_score",
    "antivirulence_target_score",
    "functional_node_score",
    "meta_priority_score",
]

PROVENANCE_COLUMNS = [
    "provider",
    "source_database",
    "source_used",
    "cache_hit",
    "api_attempted",
    "api_success",
    "fallback_reason",
    "data_realism_flag",
    "optional_data_source_summary",
    "network_database",
    "host_annotation_database",
    "conservation_database",
]


def _ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.parent.mkdir(parents=True, exist_ok=True)


def _copy_workspace(workspace: Path, target: Path) -> None:
    _ensure_clean_dir(target)
    shutil.copytree(workspace, target)


def _remove_path(path: Path) -> bool:
    if not path.exists():
        return False
    path.unlink()
    return True


def _looks_like_source_output(path: Path, provider_name: str, database_label: str) -> bool:
    if not path.exists():
        return False
    try:
        df = pd.read_csv(path)
    except Exception:
        return False
    providers = set(df.get("provider", pd.Series(dtype=str)).fillna("").astype(str))
    databases = set(df.get("database", pd.Series(dtype=str)).fillna("").astype(str))
    return provider_name in providers or database_label in databases


def _remove_results_artifacts(results_dir: Path) -> None:
    for artifact in [
        "online_source_manifest.json",
        "online_source_report.md",
        "online_enrichment_impact.csv",
        "online_enrichment_impact.md",
        "online_enrichment_before.csv",
        "online_enrichment_before.json",
        "online_source_history.jsonl",
        "online_source_comparison.csv",
        "online_source_comparison.md",
    ]:
        _remove_path(results_dir / artifact)


def _reset_source_layer(clone_workspace: Path, source: str, config: dict[str, Any]) -> tuple[str, list[str]]:
    removed: list[str] = []
    raw_dir = clone_workspace / "data_raw"
    results_dir = clone_workspace / "results"
    if source == "string":
        path = raw_dir / "functional_network.csv"
        cfg = config["online_sources"]["string"]
        if _looks_like_source_output(path, str(cfg["provider_name"]), str(cfg["database_label"])):
            if _remove_path(path):
                removed.append(str(path))
            status = "clean_reset_applied"
        else:
            status = "baseline_not_clean_non_string_network_preserved" if path.exists() else "clean_reset_applied"
    elif source == "uniprot":
        path = raw_dir / "uniprot_annotations.csv"
        cfg = config["online_sources"]["uniprot"]
        if _looks_like_source_output(path, str(cfg["provider_name"]), str(cfg["database_label"])):
            if _remove_path(path):
                removed.append(str(path))
            status = "clean_reset_applied"
        else:
            status = "baseline_not_clean_non_uniprot_annotations_preserved" if path.exists() else "clean_reset_applied"
    else:
        status = "unsupported_source"

    _remove_results_artifacts(results_dir)
    return status, removed


def _reset_sources(clone_workspace: Path, sources: list[str], config: dict[str, Any], reset_history: bool) -> tuple[str, list[str]]:
    statuses: list[str] = []
    removed_paths: list[str] = []
    for source in sources:
        status, removed = _reset_source_layer(clone_workspace, source, config)
        statuses.append(status)
        removed_paths.extend(removed)
    if reset_history:
        _remove_results_artifacts(clone_workspace / "results")
    if not statuses:
        return "no_source_reset", removed_paths
    if all(status == "clean_reset_applied" for status in statuses):
        return "clean_reset_applied", removed_paths
    return ";".join(statuses), removed_paths


def _source_cache_file(workspace: Path, source: str, config: dict[str, Any]) -> Path | None:
    if source == "string":
        return workspace / "config" / str(config["online_sources"]["string"]["cache_filename"])
    if source == "uniprot":
        return workspace / "config" / str(config["online_sources"]["uniprot"]["cache_filename"])
    return None


def _disable_cache_read(workspace: Path, sources: list[str], config: dict[str, Any]) -> list[str]:
    removed = []
    for source in sources:
        cache_path = _source_cache_file(workspace, source, config)
        if cache_path and cache_path.exists():
            cache_path.unlink()
            removed.append(str(cache_path))
    return removed


def _resolve_taxon_id(project_root: Path, clone_workspace: Path, organism_name: str, strain: str | None, config: dict[str, Any]) -> str | None:
    profile_path = clone_workspace / "results" / "organism_profile.json"
    if profile_path.exists():
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if profile.get("taxon_id"):
            return str(profile.get("taxon_id"))
    for resolution_mode in ["cache_first", "online_optional", "offline_only"]:
        kwargs = {}
        if resolution_mode == "offline_only":
            kwargs = {"refresh_cache": True, "no_write_cache": True}
        taxon_profile = resolve_taxon(project_root, organism_name, strain, resolution_mode=resolution_mode, config=config, **kwargs)
        if taxon_profile.get("taxon_id"):
            return str(taxon_profile.get("taxon_id"))
    return None


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _top_candidate(path: Path) -> tuple[str, str, float | None]:
    ranking = _read_csv_if_exists(path)
    if ranking.empty:
        return "", "", None
    top = ranking.iloc[0]
    score = top.get("meta_priority_score")
    return str(top.get("protein_id", "")), str(top.get("gene", "")), None if pd.isna(score) else float(score)


def _scenario_definitions(sources: list[str], compare_fresh_vs_cache: bool) -> list[dict[str, Any]]:
    ordered_sources = [source for source in sources if source in {"string", "uniprot"}]
    scenarios = [
        {
            "scenario": "baseline_no_online",
            "source_combination": "none",
            "sources": [],
            "refresh_requested": False,
            "cache_read_allowed": False,
            "cache_write_allowed": False,
            "comparison_group": "baseline",
        }
    ]
    for source in ordered_sources:
        scenarios.append(
            {
                "scenario": f"{source}_only_fresh",
                "source_combination": source,
                "sources": [source],
                "refresh_requested": True,
                "cache_read_allowed": False,
                "cache_write_allowed": True,
                "comparison_group": "fresh",
            }
        )
    if ordered_sources:
        scenarios.append(
            {
                "scenario": "combined_online_fresh",
                "source_combination": "+".join(ordered_sources),
                "sources": ordered_sources,
                "refresh_requested": True,
                "cache_read_allowed": False,
                "cache_write_allowed": True,
                "comparison_group": "fresh",
            }
        )
    if compare_fresh_vs_cache:
        for source in ordered_sources:
            scenarios.append(
                {
                    "scenario": f"{source}_only_cache",
                    "source_combination": source,
                    "sources": [source],
                    "refresh_requested": False,
                    "cache_read_allowed": True,
                    "cache_write_allowed": True,
                    "comparison_group": "cache",
                }
            )
        if ordered_sources:
            scenarios.append(
                {
                    "scenario": "combined_online_cache",
                    "source_combination": "+".join(ordered_sources),
                    "sources": ordered_sources,
                    "refresh_requested": False,
                    "cache_read_allowed": True,
                    "cache_write_allowed": True,
                    "comparison_group": "cache",
                }
            )
    return scenarios


def _merge_on_protein(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    if before.empty and after.empty:
        return pd.DataFrame()
    merged = before.merge(after, on="protein_id", how="outer", suffixes=("_before", "_after"))
    return merged


def _count_changed_columns(before: pd.DataFrame, after: pd.DataFrame, columns: list[str]) -> tuple[int, list[str]]:
    if before.empty or after.empty:
        return 0, []
    merged = _merge_on_protein(before[["protein_id"] + [col for col in columns if col in before.columns]], after[["protein_id"] + [col for col in columns if col in after.columns]])
    changed = []
    for column in columns:
        before_col = f"{column}_before"
        after_col = f"{column}_after"
        if before_col not in merged.columns or after_col not in merged.columns:
            continue
        left = merged[before_col].fillna("__NA__").astype(str)
        right = merged[after_col].fillna("__NA__").astype(str)
        if (left != right).any():
            changed.append(column)
    return len(changed), changed


def _ranking_comparison(before: pd.DataFrame, after: pd.DataFrame) -> tuple[bool, bool, int, str, int, pd.DataFrame]:
    if before.empty or after.empty:
        return False, False, 0, "", 0, pd.DataFrame()
    before_rank = before.reset_index().rename(columns={"index": "rank_before"})
    after_rank = after.reset_index().rename(columns={"index": "rank_after"})
    before_rank["rank_before"] += 1
    after_rank["rank_after"] += 1
    merged = before_rank[["protein_id", "rank_before"]].merge(after_rank[["protein_id", "rank_after"]], on="protein_id", how="outer")
    merged["rank_delta"] = merged["rank_before"].fillna(999).astype(int) - merged["rank_after"].fillna(999).astype(int)
    ranking_changed = bool((merged["rank_before"] != merged["rank_after"]).any())
    top10_before = before_rank.head(10)["protein_id"].tolist()
    top10_after = after_rank.head(10)["protein_id"].tolist()
    top10_changed = top10_before != top10_after
    overlap = len(set(top10_before) & set(top10_after))
    strongest = merged.loc[merged["rank_delta"].abs().idxmax()] if not merged.empty else {}
    strongest_candidate = str(strongest.get("protein_id", "")) if isinstance(strongest, pd.Series) else ""
    strongest_delta = int(strongest.get("rank_delta", 0)) if isinstance(strongest, pd.Series) else 0
    return ranking_changed, top10_changed, overlap, strongest_candidate, strongest_delta, merged


def _impacted_strategy(before_scores: pd.DataFrame, after_scores: pd.DataFrame) -> str:
    if before_scores.empty or after_scores.empty:
        return ""
    merged = before_scores[["protein_id"] + SCORE_COLUMNS].merge(after_scores[["protein_id"] + SCORE_COLUMNS], on="protein_id", how="inner", suffixes=("_before", "_after"))
    deltas = {}
    for column in SCORE_COLUMNS[1:]:
        deltas[column] = (merged[f"{column}_after"] - merged[f"{column}_before"]).abs().mean()
    if not deltas:
        return ""
    return max(deltas, key=deltas.get)


def _impact_status(provenance_changed_count: int, features_changed_count: int, scores_changed_count: int, ranking_changed: bool, top10_changed: bool) -> str:
    if top10_changed:
        return "top10_level_effect"
    if ranking_changed:
        return "ranking_level_effect"
    if scores_changed_count > 0:
        return "score_level_effect"
    if features_changed_count > 0:
        return "feature_level_effect"
    if provenance_changed_count > 0:
        return "annotation_or_provenance_only"
    return "no_detectable_effect"


def _scenario_run_kind(manifests: list[dict[str, Any]]) -> str:
    if not manifests:
        return "no_online_run"
    component = [classify_online_run(manifest) for manifest in manifests]
    if len(component) == 1:
        return component[0]
    return "mixed_run"


def _fallback_reason(manifests: list[dict[str, Any]]) -> str:
    reasons = [str(manifest.get("fallback_reason") or "").strip() for manifest in manifests]
    reasons = [reason for reason in reasons if reason]
    return ";".join(reasons)


def _causal_reading(run_kind: str, impact_status: str) -> str:
    if run_kind == "no_online_run":
        return "baseline_reference"
    if run_kind == "fallback_after_api_failure":
        return "api_failed_fallback_used"
    if run_kind == "fresh_api_run" and impact_status in {"feature_level_effect", "score_level_effect", "ranking_level_effect", "top10_level_effect"}:
        return "fresh_effect_confirmed"
    if run_kind == "cache_reuse_run" and impact_status != "no_detectable_effect":
        return "cache_reuse_effect_observed"
    if impact_status in {"no_detectable_effect", "annotation_or_provenance_only"}:
        return "no_detectable_effect"
    return "mixed_effect_observed"


def _capture_state(workspace: Path) -> dict[str, pd.DataFrame]:
    return {
        "features": _read_csv_if_exists(workspace / "data_processed" / "phase2_features.csv"),
        "scores": _read_csv_if_exists(workspace / "data_processed" / "scored_nodes.csv"),
        "ranking": _read_csv_if_exists(workspace / "results" / "ranking_nodos.csv"),
        "candidate_audit": _read_csv_if_exists(workspace / "results" / "candidate_audit.csv"),
        "top10_scientific": _read_csv_if_exists(workspace / "results" / "top10_scientific_audit.csv"),
    }


def _candidate_shift_rows(ranking_delta: pd.DataFrame, scenario: str) -> pd.DataFrame:
    if ranking_delta.empty:
        return pd.DataFrame()
    rows = ranking_delta.copy()
    rows["scenario"] = scenario
    return rows


def run_audit_scenario(
    project_root: Path,
    workspace: Path,
    organism_name: str,
    strain: str | None,
    scenario: dict[str, Any],
    mode: str,
    pipeline_mode: str,
    disable_cache_write: bool,
    reset_history: bool,
    run_pipeline_flag: bool,
    dry_run: bool,
) -> tuple[dict[str, Any], pd.DataFrame]:
    project_root = Path(project_root)
    workspace = Path(workspace)
    clone_workspace = project_root / ".tmp_source_audit" / f"{workspace.name}_{scenario['scenario']}_{uuid.uuid4().hex[:8]}"
    _copy_workspace(workspace, clone_workspace)
    config_path = clone_workspace / "config" / "params.yaml"
    config = load_config(config_path if config_path.exists() else project_root / "config" / "params.yaml")
    taxon_id = _resolve_taxon_id(project_root, clone_workspace, organism_name, strain, config)

    baseline_sources = list(scenario["sources"]) if scenario["sources"] else ["string", "uniprot"]
    reset_status, removed_paths = _reset_sources(clone_workspace, baseline_sources, config, reset_history=reset_history)
    removed_cache_paths: list[str] = []
    if not scenario["cache_read_allowed"]:
        removed_cache_paths = _disable_cache_read(clone_workspace, list(scenario["sources"]), config)

    if run_pipeline_flag and not dry_run:
        run_pipeline(clone_workspace, config_path if config_path.exists() else project_root / "config" / "params.yaml", mode=pipeline_mode)
    baseline_state = _capture_state(clone_workspace)
    before_protein, before_gene, before_score = _top_candidate(clone_workspace / "results" / "ranking_nodos.csv")

    manifests: list[dict[str, Any]] = []
    if not dry_run:
        snapshot_pre_enrichment_state(clone_workspace, scenario["source_combination"])
    for source in scenario["sources"]:
        if dry_run:
            continue
        result = fetch_online_source(
            source=source,
            workspace=clone_workspace,
            organism_name=organism_name,
            taxon_id=taxon_id,
            config=config,
            mode=mode,
            refresh_cache=bool(scenario["refresh_requested"]),
            no_write_cache=bool(disable_cache_write or not scenario["cache_write_allowed"]),
            replace_existing=True,
        )
        manifests.append(result["manifest"])

    if run_pipeline_flag and not dry_run:
        run_pipeline(clone_workspace, config_path if config_path.exists() else project_root / "config" / "params.yaml", mode=pipeline_mode)
    impact_paths = build_before_after_ranking_audit(clone_workspace) if not dry_run else None
    after_state = _capture_state(clone_workspace)
    after_protein, after_gene, after_score = _top_candidate(clone_workspace / "results" / "ranking_nodos.csv")

    feature_columns = [
        column
        for column in after_state["features"].columns
        if column not in SCORE_COLUMNS + PROVENANCE_COLUMNS + ["protein_id", "protein_id_original", "protein_id_canonical", "gene", "gene_symbol_normalized", "top_positive_drivers", "top_negative_drivers", "candidate_audit_summary", "confidence_summary"]
    ] if not after_state["features"].empty else []
    provenance_changed_count, provenance_changed_columns = _count_changed_columns(baseline_state["features"], after_state["features"], [column for column in PROVENANCE_COLUMNS if column in after_state["features"].columns])
    features_changed_count, feature_changed_columns = _count_changed_columns(baseline_state["features"], after_state["features"], feature_columns)
    scores_changed_count, score_changed_columns = _count_changed_columns(baseline_state["scores"], after_state["scores"], [column for column in SCORE_COLUMNS if column in after_state["scores"].columns])
    ranking_changed, top10_changed, top10_overlap, strongest_candidate, strongest_delta, ranking_delta = _ranking_comparison(
        baseline_state["ranking"], after_state["ranking"]
    )
    candidate_audit_changed_count, _ = _count_changed_columns(
        baseline_state["candidate_audit"],
        after_state["candidate_audit"],
        [column for column in ["preferred_strategy", "strategy_margin_score", "candidate_audit_summary"] if column in after_state["candidate_audit"].columns],
    )
    top10_scientific_changed_count, _ = _count_changed_columns(
        baseline_state["top10_scientific"],
        after_state["top10_scientific"],
        [column for column in ["audit_class", "audit_confidence", "biological_interpretation"] if column in after_state["top10_scientific"].columns],
    )
    impacted_strategy = _impacted_strategy(baseline_state["scores"], after_state["scores"])
    impact_status = _impact_status(
        provenance_changed_count=provenance_changed_count,
        features_changed_count=features_changed_count,
        scores_changed_count=scores_changed_count,
        ranking_changed=ranking_changed,
        top10_changed=top10_changed,
    )
    run_kind = _scenario_run_kind(manifests)
    api_attempted = any(bool(manifest.get("api_attempted")) for manifest in manifests)
    api_success = all(bool(manifest.get("api_success")) for manifest in manifests) if manifests else False
    limitations = []
    if not scenario["sources"]:
        limitations.append("baseline scenario sin enriquecimiento online")
    if not taxon_id:
        limitations.append("taxon_id no resuelto para el clon")
    if run_kind == "fallback_after_api_failure":
        limitations.append("la API falló y se usó fallback a caché")
    if not scenario["cache_read_allowed"]:
        limitations.append("cache read deshabilitado para forzar corrida fresca")
    if dry_run:
        limitations.append("dry_run: no se ejecutaron fetches ni pipeline")

    row = {
        "scenario": scenario["scenario"],
        "source_combination": scenario["source_combination"],
        "run_kind": run_kind,
        "component_run_kinds": ";".join(classify_online_run(manifest) for manifest in manifests),
        "workspace": str(clone_workspace),
        "cache_read_allowed": bool(scenario["cache_read_allowed"]),
        "cache_write_allowed": bool(scenario["cache_write_allowed"]) and not disable_cache_write,
        "refresh_requested": bool(scenario["refresh_requested"]),
        "api_attempted": api_attempted,
        "api_success": api_success,
        "fallback_reason": _fallback_reason(manifests),
        "provenance_changed_count": provenance_changed_count,
        "features_changed_count": features_changed_count,
        "scores_changed_count": scores_changed_count,
        "candidate_audit_changed_count": candidate_audit_changed_count,
        "top10_scientific_changed_count": top10_scientific_changed_count,
        "ranking_changed": bool(ranking_changed),
        "top10_changed": bool(top10_changed),
        "top_candidate_before": before_protein,
        "top_candidate_after": after_protein,
        "top_gene_before": before_gene,
        "top_gene_after": after_gene,
        "top_score_before": before_score,
        "top_score_after": after_score,
        "top10_overlap": top10_overlap,
        "strongest_shift_candidate": strongest_candidate,
        "strongest_shift_delta": strongest_delta,
        "impacted_strategy": impacted_strategy,
        "impact_status": impact_status,
        "causal_reading": _causal_reading(run_kind, impact_status),
        "comparison_group": scenario["comparison_group"],
        "reset_status": reset_status,
        "removed_paths": ";".join(removed_paths),
        "removed_cache_paths": ";".join(removed_cache_paths),
        "limitations": "; ".join(limitations) if limitations else "",
        "feature_changed_columns": ";".join(feature_changed_columns),
        "score_changed_columns": ";".join(score_changed_columns),
        "provenance_changed_columns": ";".join(provenance_changed_columns),
    }
    return row, _candidate_shift_rows(ranking_delta, scenario["scenario"])


def _effect_level(status: str) -> int:
    levels = {
        "no_detectable_effect": 0,
        "annotation_or_provenance_only": 1,
        "feature_level_effect": 2,
        "score_level_effect": 3,
        "ranking_level_effect": 4,
        "top10_level_effect": 5,
    }
    return levels.get(status, 0)


def build_fresh_vs_cache_comparison(audit_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if audit_df.empty:
        return pd.DataFrame(rows)
    fresh = audit_df.loc[audit_df["comparison_group"] == "fresh"].copy()
    cache = audit_df.loc[audit_df["comparison_group"] == "cache"].copy()
    if fresh.empty or cache.empty:
        return pd.DataFrame(rows)

    for _, fresh_row in fresh.iterrows():
        source_combination = fresh_row["source_combination"]
        cache_match = cache.loc[cache["source_combination"] == source_combination]
        if cache_match.empty:
            continue
        cache_row = cache_match.iloc[0]
        fresh_level = _effect_level(str(fresh_row["impact_status"]))
        cache_level = _effect_level(str(cache_row["impact_status"]))
        if str(fresh_row["run_kind"]) == "fallback_after_api_failure":
            label = "api_failed_fallback_used"
        elif fresh_level > 1 and fresh_level >= cache_level:
            label = "fresh_effect_confirmed"
        elif cache_level > 1 and fresh_level <= 1:
            label = "effect_not_reproduced_fresh"
        elif cache_level > fresh_level:
            label = "cache_only_effect"
        else:
            label = "no_detectable_effect"
        rows.append(
            {
                "source_combination": source_combination,
                "fresh_scenario": fresh_row["scenario"],
                "cache_scenario": cache_row["scenario"],
                "fresh_run_kind": fresh_row["run_kind"],
                "cache_run_kind": cache_row["run_kind"],
                "fresh_impact_status": fresh_row["impact_status"],
                "cache_impact_status": cache_row["impact_status"],
                "fresh_scores_changed_count": fresh_row["scores_changed_count"],
                "cache_scores_changed_count": cache_row["scores_changed_count"],
                "fresh_ranking_changed": fresh_row["ranking_changed"],
                "cache_ranking_changed": cache_row["ranking_changed"],
                "comparison_label": label,
                "comparison_summary": (
                    f"fresh={fresh_row['impact_status']} (run_kind={fresh_row['run_kind']}); "
                    f"cache={cache_row['impact_status']} (run_kind={cache_row['run_kind']})"
                ),
            }
        )
    return pd.DataFrame(rows)


def _write_markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sin datos_"
    lines = [
        "| " + " | ".join(df.columns) + " |",
        "| " + " | ".join(["---"] * len(df.columns)) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in df.columns) + " |")
    return "\n".join(lines)


def write_fresh_audit_outputs(
    project_root: Path,
    workspace: Path,
    audit_df: pd.DataFrame,
    fresh_vs_cache_df: pd.DataFrame,
    candidate_shifts_df: pd.DataFrame,
) -> dict[str, Path]:
    workspace_results = Path(workspace) / "results"
    global_results = Path(project_root) / "results"
    workspace_results.mkdir(parents=True, exist_ok=True)
    global_results.mkdir(parents=True, exist_ok=True)

    paths = {}
    for root in [workspace_results, global_results]:
        fresh_csv = root / "online_source_fresh_audit.csv"
        fresh_md = root / "online_source_fresh_audit.md"
        compare_csv = root / "online_source_fresh_vs_cache.csv"
        compare_md = root / "online_source_fresh_vs_cache.md"
        shifts_csv = root / "online_source_candidate_shifts_fresh.csv"
        audit_df.to_csv(fresh_csv, index=False)
        fresh_md.write_text(
            "\n".join(
                [
                    "# Online Source Fresh Audit",
                    "",
                    f"- Workspace: `{workspace}`",
                    "",
                    _write_markdown_table(audit_df),
                ]
            ),
            encoding="utf-8",
        )
        fresh_vs_cache_df.to_csv(compare_csv, index=False)
        compare_md.write_text(
            "\n".join(
                [
                    "# Online Source Fresh vs Cache",
                    "",
                    f"- Workspace: `{workspace}`",
                    "",
                    _write_markdown_table(fresh_vs_cache_df),
                ]
            ),
            encoding="utf-8",
        )
        candidate_shifts_df.to_csv(shifts_csv, index=False)
        if root == workspace_results:
            paths = {
                "fresh_csv": fresh_csv,
                "fresh_md": fresh_md,
                "compare_csv": compare_csv,
                "compare_md": compare_md,
                "candidate_shifts_csv": shifts_csv,
            }
    return paths


def run_experimental_online_audit(
    project_root: Path,
    workspace: Path,
    organism_name: str,
    strain: str | None,
    sources: list[str],
    mode: str = "online_optional",
    pipeline_mode: str = "compare",
    force_refresh: bool = False,
    disable_cache_read: bool = False,
    disable_cache_write: bool = False,
    reset_history: bool = False,
    run_pipeline_flag: bool = True,
    compare_fresh_vs_cache: bool = False,
    dry_run: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Path]]:
    if force_refresh and compare_fresh_vs_cache:
        raise ValueError("force_refresh no es compatible con compare_fresh_vs_cache porque los escenarios cache dejarian de ser comparables.")

    scenarios = _scenario_definitions(sources, compare_fresh_vs_cache=compare_fresh_vs_cache)
    rows = []
    shift_frames = []
    for scenario in scenarios:
        scenario = dict(scenario)
        if scenario["comparison_group"] == "fresh":
            # Fresh scenarios are defined to bypass cache reads and request a new API fetch.
            scenario["refresh_requested"] = True
            scenario["cache_read_allowed"] = False
        elif force_refresh and scenario["sources"]:
            # Compatibility override for callers that want every online scenario to skip cache reads.
            scenario["refresh_requested"] = True
            scenario["cache_read_allowed"] = False
        elif disable_cache_read:
            scenario["cache_read_allowed"] = False
        if disable_cache_write:
            scenario["cache_write_allowed"] = False
        row, shifts = run_audit_scenario(
            project_root=project_root,
            workspace=workspace,
            organism_name=organism_name,
            strain=strain,
            scenario=scenario,
            mode=mode,
            pipeline_mode=pipeline_mode,
            disable_cache_write=disable_cache_write,
            reset_history=reset_history,
            run_pipeline_flag=run_pipeline_flag,
            dry_run=dry_run,
        )
        rows.append(row)
        if not shifts.empty:
            shift_frames.append(shifts)
    audit_df = pd.DataFrame(rows)
    fresh_vs_cache_df = build_fresh_vs_cache_comparison(audit_df)
    candidate_shifts_df = pd.concat(shift_frames, ignore_index=True) if shift_frames else pd.DataFrame()
    paths = write_fresh_audit_outputs(project_root, workspace, audit_df, fresh_vs_cache_df, candidate_shifts_df)
    return audit_df, fresh_vs_cache_df, candidate_shifts_df, paths


def write_clean_online_audit(
    project_root: Path,
    workspace: Path,
    organism_name: str,
    strain: str | None,
    sources: list[str],
    mode: str = "cache_first",
    pipeline_mode: str = "compare",
) -> tuple[Path, Path, pd.DataFrame]:
    audit_df, _, _, paths = run_experimental_online_audit(
        project_root=project_root,
        workspace=workspace,
        organism_name=organism_name,
        strain=strain,
        sources=sources,
        mode=mode,
        pipeline_mode=pipeline_mode,
        force_refresh=False,
        disable_cache_read=False,
        disable_cache_write=False,
        reset_history=True,
        run_pipeline_flag=True,
        compare_fresh_vs_cache=False,
        dry_run=False,
    )
    clean_df = audit_df.loc[audit_df["scenario"] != "baseline_no_online"].copy()
    results_dir = Path(workspace) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_path = results_dir / "online_source_clean_audit.csv"
    md_path = results_dir / "online_source_clean_audit.md"
    clean_df.to_csv(csv_path, index=False)
    md_path.write_text(
        "\n".join(
            [
                "# Online Source Clean Audit",
                "",
                f"- Workspace: `{workspace}`",
                "",
                _write_markdown_table(clean_df),
            ]
        ),
        encoding="utf-8",
    )
    return csv_path, md_path, clean_df
