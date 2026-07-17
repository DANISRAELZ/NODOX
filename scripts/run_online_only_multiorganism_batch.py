from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_online_only_validation import load_organism_registry
from src.nodos_funcionales.external_evidence_normalization import write_external_evidence_package
from src.nodos_funcionales.external_provider_capture import validate_real_provider_captures
from src.nodos_funcionales.online_provider_connectivity import run_provider_connectivity_audit
from src.nodos_funcionales.online_only_validation import CONSERVATIVE_NOTE, run_online_only_validation


DEFAULT_VALIDATION_ORGANISMS = (
    "pseudomonas_aeruginosa",
    "escherichia_coli",
    "mycobacterium_tuberculosis",
    "mycobacterium_tuberculosis_h37rv",
)
STATUS_COLUMNS = (
    "organism_key",
    "organism",
    "strain",
    "taxon_id",
    "run_dir",
    "pipeline_status",
    "candidate_seed_status",
    "candidate_seed_count",
    "user_curated_layers_detected",
    "ranking_rows",
    "providers_attempted",
    "providers_success",
    "providers_unresolved",
    "providers_failed",
    "layers_resolved",
    "layers_unresolved",
    "therapeutic_priority_score_present",
    "evidence_confidence_score_present",
    "scoring_modified",
    "notes",
)


def run_online_only_multiorganism_batch(
    project_root: Path,
    organism_keys: list[str],
    run_label: str,
    max_candidates: int = 25,
    enable_string: bool = True,
    enable_interpro: bool = True,
    enable_literature: bool = True,
    continue_on_error: bool = False,
    check_provider_connectivity: bool = False,
    normalize_external_evidence: bool = False,
    validate_real_provider_captures_enabled: bool = False,
    provider_capture_paths: list[Path] | None = None,
    output_dir: Path | None = None,
    organism_runner: Callable[..., dict[str, Any]] = run_online_only_validation,
) -> dict[str, Any]:
    """Run configured organisms sequentially and build an auditable comparison package."""
    project_root = Path(project_root)
    run_label = _validate_run_label(run_label)
    registry = load_organism_registry(project_root / "config" / "online_only_organisms.json")
    selected_keys = _validate_organism_keys(organism_keys, registry)
    batch_dir = Path(output_dir) if output_dir else project_root / "results" / "online_only_multiorganism_runs" / run_label
    organism_runs_dir = batch_dir / "organism_runs"
    organism_runs_dir.mkdir(parents=True, exist_ok=True)

    started_at = _utc_now()
    scoring_before = _scoring_hashes(project_root)
    status_rows: list[dict[str, Any]] = []
    provider_rows: list[dict[str, Any]] = []
    layer_rows: list[dict[str, Any]] = []
    seed_rows: list[dict[str, Any]] = []
    ranking_rows: list[dict[str, Any]] = []
    run_records: list[dict[str, Any]] = []

    for organism_key in selected_keys:
        organism_config = dict(registry[organism_key])
        run_dir = organism_runs_dir / organism_key
        try:
            result = organism_runner(
                project_root=project_root,
                **organism_config,
                run_dir=run_dir,
                max_candidates=max_candidates,
                enable_string=enable_string,
                enable_interpro=enable_interpro,
                enable_literature=enable_literature,
                online_source_mode="online_optional",
                taxon_resolution_mode="online_optional",
                no_write_taxon_cache=True,
                materialize_unresolved_required_fallback=True,
            )
            collected = _collect_organism_run(organism_key, organism_config, run_dir, result)
            status_rows.append(collected["status"])
            provider_rows.extend(collected["providers"])
            layer_rows.extend(collected["layers"])
            seed_rows.append(collected["seed"])
            ranking_rows.append(collected["ranking"])
            run_records.append(
                {
                    "organism_key": organism_key,
                    "run_dir": str(run_dir),
                    "pipeline_status": result.get("pipeline_status", "not_reported"),
                    "error": result.get("pipeline_error", ""),
                }
            )
        except Exception as exc:  # noqa: BLE001 - batch must preserve each provider/run failure.
            status_rows.append(_failed_status_row(organism_key, organism_config, run_dir, exc))
            seed_rows.append(_failed_seed_row(organism_key, organism_config, exc))
            ranking_rows.append(_empty_ranking_row(organism_key, organism_config, "run_failed"))
            run_records.append(
                {
                    "organism_key": organism_key,
                    "run_dir": str(run_dir),
                    "pipeline_status": "batch_runner_exception",
                    "error": str(exc),
                }
            )
            if not continue_on_error:
                break

    phase_7c: dict[str, Any] | None = None
    phase_7d: dict[str, Any] | None = None
    phase_7f: dict[str, Any] | None = None
    if check_provider_connectivity or normalize_external_evidence:
        organisms = [
            {
                "organism_label": " ".join(filter(None, [registry[key]["organism"], registry[key].get("strain", "")])),
                "taxon_id": registry[key].get("taxon_id", ""),
            }
            for key in selected_keys
        ]
        connectivity_dir = project_root / "results" / "online_only_provider_connectivity" / run_label
        phase_7c = run_provider_connectivity_audit(organisms, connectivity_dir)
    if normalize_external_evidence:
        evidence_dir = project_root / "results" / "online_only_external_evidence" / run_label
        candidates = _collect_normalization_candidates(organism_runs_dir, selected_keys, registry)
        phase_7d = write_external_evidence_package(phase_7c["rows"] if phase_7c else [], candidates, evidence_dir)
    if validate_real_provider_captures_enabled:
        capture_paths = provider_capture_paths or sorted(
            (project_root / "tests" / "fixtures" / "external_providers" / "real_captures_sanitized").glob("*.json")
        )
        if not capture_paths:
            raise FileNotFoundError("no sanitized external provider captures were found")
        capture_output = project_root / "results" / "online_only_external_evidence" / run_label / "real_capture_validation"
        phase_7f = validate_real_provider_captures(capture_paths, capture_output)

    scoring_after = _scoring_hashes(project_root)
    scoring_modified = scoring_before != scoring_after
    for row in status_rows:
        row["scoring_modified"] = scoring_modified

    artifacts = {
        "batch_provider_audit.csv": provider_rows,
        "batch_layer_resolution_summary.csv": layer_rows,
        "batch_candidate_seed_summary.csv": seed_rows,
        "batch_ranking_summary.csv": ranking_rows,
        "batch_run_status.csv": status_rows,
    }
    for filename, rows in artifacts.items():
        preferred = list(STATUS_COLUMNS) if filename == "batch_run_status.csv" else None
        _write_csv(batch_dir / filename, rows, preferred)

    completed_at = _utc_now()
    manifest = {
        "phase": "7B_online_only_multiorganism_real_execution",
        "run_label": run_label,
        "batch_dir": str(batch_dir),
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "organism_keys_requested": selected_keys,
        "organism_registry_entries": {key: registry[key] for key in selected_keys},
        "max_candidates": int(max_candidates),
        "continue_on_error": bool(continue_on_error),
        "phase_7c_enabled": bool(check_provider_connectivity or normalize_external_evidence),
        "phase_7d_enabled": bool(normalize_external_evidence),
        "phase_7f_enabled": bool(validate_real_provider_captures_enabled),
        "provider_connectivity_output": phase_7c["output_dir"] if phase_7c else "",
        "external_evidence_output": phase_7d["output_dir"] if phase_7d else "",
        "real_capture_validation_output": phase_7f["output_dir"] if phase_7f else "",
        "enabled_providers": {
            "string": bool(enable_string),
            "interpro": bool(enable_interpro),
            "literature": bool(enable_literature),
        },
        "input_policy": "online_only_no_user_curated_no_hidden_snapshot_fallback",
        "scoring_hashes_before": scoring_before,
        "scoring_hashes_after": scoring_after,
        "scoring_modified": scoring_modified,
        "runs": run_records,
        "generated_artifacts": sorted([*artifacts, "ONLINE_ONLY_MULTIORGANISM_REVIEW.md"]),
    }
    _write_json(batch_dir / "batch_manifest.json", manifest)
    review = _build_review_markdown(manifest, status_rows, provider_rows, layer_rows)
    (batch_dir / "ONLINE_ONLY_MULTIORGANISM_REVIEW.md").write_text(review, encoding="utf-8")
    return {
        "batch_dir": str(batch_dir),
        "manifest": manifest,
        "status_rows": status_rows,
        "provider_rows": provider_rows,
        "layer_rows": layer_rows,
        "seed_rows": seed_rows,
        "ranking_rows": ranking_rows,
        "provider_connectivity": phase_7c,
        "external_evidence": phase_7d,
        "real_capture_validation": phase_7f,
    }


def _collect_normalization_candidates(
    organism_runs_dir: Path, organism_keys: list[str], registry: dict[str, Any]
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for key in organism_keys:
        package = organism_runs_dir / key / "review_package"
        workspace_results = organism_runs_dir / key / "workspace" / "results"
        rows = _read_csv(_first_existing(
            package / "ranking_nodos_phase3.csv", package / "ranking_nodos.csv",
            workspace_results / "ranking_nodos_phase3.csv", workspace_results / "ranking_nodos.csv",
        ))
        config = registry[key]
        label = " ".join(filter(None, [config["organism"], config.get("strain", "")]))
        for row in rows:
            candidates.append({
                "organism_label": label, "taxon_id": config.get("taxon_id", ""),
                "candidate_gene": row.get("gene", row.get("candidate_gene", "")),
                "protein_id": row.get("protein_id", ""),
            })
    return candidates


def _collect_organism_run(
    organism_key: str,
    config: dict[str, Any],
    run_dir: Path,
    result: dict[str, Any],
) -> dict[str, Any]:
    package_dir = run_dir / "review_package"
    workspace_results = run_dir / "workspace" / "results"
    seed = _read_json(_first_existing(package_dir / "online_only_candidate_seed_manifest.json", workspace_results / "online_only_candidate_seed_manifest.json"))
    providers = _read_csv(_first_existing(package_dir / "online_only_provider_audit.csv", workspace_results / "online_only_provider_audit.csv"))
    layers = _read_csv(_first_existing(package_dir / "layer_resolution_summary.csv", workspace_results / "layer_resolution_summary.csv"))
    provenance = _read_csv(_first_existing(package_dir / "online_only_provenance_summary.csv", workspace_results / "online_only_provenance_summary.csv"))
    ranking_path = _first_existing(package_dir / "ranking_nodos_phase3.csv", package_dir / "ranking_nodos.csv", workspace_results / "ranking_nodos_phase3.csv", workspace_results / "ranking_nodos.csv")
    rankings = _read_csv(ranking_path)

    identity = {
        "organism_key": organism_key,
        "organism": config["organism"],
        "strain": config.get("strain", ""),
        "taxon_id": config.get("taxon_id", ""),
        "run_dir": str(run_dir),
    }
    providers = _supplement_provider_audit(providers, package_dir, workspace_results)
    layers = _supplement_layer_summary(layers, providers)
    tagged_providers = [{**identity, **row} for row in providers]
    tagged_layers = [{**identity, **row} for row in layers]
    attempted_names = _provider_names(providers, lambda row: _as_bool(row.get("api_attempted")))
    success_names = _provider_names(providers, lambda row: _as_bool(row.get("api_success")))
    failed_names = _provider_names(
        providers,
        lambda row: _as_bool(row.get("api_attempted")) and not _as_bool(row.get("api_success")),
    )
    unresolved_names = _provider_names(
        providers,
        lambda row: not _as_bool(row.get("api_success")) or "unresolved" in str(row.get("evidence_level", "")).lower(),
    )
    resolved_layers = _layer_names(layers, resolved=True)
    unresolved_layers = _layer_names(layers, resolved=False)
    user_curated_count = sum(
        1
        for row in provenance
        if _as_bool(row.get("is_user_supplied")) or str(row.get("source_type", "")).lower() in {"user", "user_curated"}
    )
    ranking_columns = set(rankings[0]) if rankings else set()
    notes = []
    if result.get("pipeline_error"):
        notes.append(str(result["pipeline_error"]))
    if user_curated_count:
        notes.append("invalid_user_curated_layers_detected_and_not_accepted_as_online_evidence")
    if not providers:
        notes.append("provider_audit_not_generated")
    status = {
        **identity,
        "pipeline_status": result.get("pipeline_status", "not_reported"),
        "candidate_seed_status": seed.get("retrieval_status", seed.get("source_used", "manifest_missing")),
        "candidate_seed_count": _as_int(seed.get("candidate_count", 0)),
        "user_curated_layers_detected": user_curated_count,
        "ranking_rows": len(rankings),
        "providers_attempted": ";".join(attempted_names),
        "providers_success": ";".join(success_names),
        "providers_unresolved": ";".join(unresolved_names),
        "providers_failed": ";".join(failed_names),
        "layers_resolved": ";".join(resolved_layers),
        "layers_unresolved": ";".join(unresolved_layers),
        "therapeutic_priority_score_present": "therapeutic_priority_score" in ranking_columns,
        "evidence_confidence_score_present": "evidence_confidence_score" in ranking_columns,
        "scoring_modified": False,
        "notes": "; ".join(notes),
    }
    return {
        "status": status,
        "providers": tagged_providers,
        "layers": tagged_layers,
        "seed": {
            **identity,
            "candidate_seed_status": status["candidate_seed_status"],
            "candidate_seed_count": status["candidate_seed_count"],
            "api_attempted": seed.get("api_attempted", False),
            "api_success": seed.get("api_success", False),
            "provider_name": seed.get("provider_name", seed.get("provider", "not_reported")),
            "fallback_reason": seed.get("fallback_reason", ""),
        },
        "ranking": _summarize_ranking(identity, rankings),
    }


def _supplement_provider_audit(
    providers: list[dict[str, Any]], package_dir: Path, workspace_results: Path
) -> list[dict[str, Any]]:
    """Include enrichment manifests even when the pipeline failed before layer resolution."""
    supplemented = list(providers)
    known_layers = {str(row.get("layer_key", "")) for row in supplemented}
    manifest_dir = package_dir if package_dir.exists() else workspace_results
    for path in sorted(manifest_dir.glob("online_only_*_manifest.json")):
        if path.name in {"online_only_run_manifest.json", "online_only_candidate_seed_manifest.json"}:
            continue
        manifest = _read_json(path)
        layer_key = str(manifest.get("layer_key", "")).strip()
        if not layer_key or layer_key in known_layers:
            continue
        supplemented.append(
            {
                "layer_key": layer_key,
                "provider_name": manifest.get("provider_name", manifest.get("provider", "not_reported")),
                "provider_endpoint_or_mode": manifest.get("provider_endpoint_or_mode", "not_reported"),
                "provider_function": manifest.get("provider_function", "not_reported"),
                "api_attempted": manifest.get("api_attempted", False),
                "api_success": manifest.get("api_success", False),
                "retrieved_record_count": manifest.get("retrieved_record_count", 0),
                "matched_candidate_count": manifest.get("matched_candidate_count", 0),
                "fallback_used": manifest.get("fallback_used", False),
                "fallback_reason": manifest.get("fallback_reason", ""),
                "retrieval_status": manifest.get("retrieval_status", "not_reported"),
                "source_used": manifest.get("source_used", "not_reported"),
                "data_realism_flag": manifest.get("data_realism_flag", "unresolved"),
                "evidence_level": manifest.get("evidence_level", "unresolved"),
                "experimental_validation_supported": False,
                "inherited_from_candidate_seed": manifest.get("inherited_from_candidate_seed", False),
                "generated_at_utc": manifest.get("generated_at_utc", "not_reported"),
            }
        )
        known_layers.add(layer_key)
    return supplemented


def _supplement_layer_summary(
    layers: list[dict[str, Any]], providers: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    supplemented = list(layers)
    known_layers = {str(row.get("layer_key", row.get("layer", ""))) for row in supplemented}
    for provider in providers:
        layer_key = str(provider.get("layer_key", "")).strip()
        if not layer_key or layer_key in known_layers:
            continue
        success = _as_bool(provider.get("api_success"))
        supplemented.append(
            {
                "layer_key": layer_key,
                "source_type": "external" if success else "missing",
                "source_name": provider.get("provider_name", "not_reported"),
                "retrieval_status": provider.get("retrieval_status", "not_reported"),
                "is_user_supplied": False,
                "is_external": success,
                "is_cached": False,
                "is_proxy": False,
                "confidence": "not_reported",
                "batch_summary_source": "online_only_provider_manifest",
            }
        )
        known_layers.add(layer_key)
    return supplemented


def _summarize_ranking(identity: dict[str, Any], rows: list[dict[str, str]]) -> dict[str, Any]:
    if not rows:
        return {**identity, **_empty_ranking_row(identity["organism_key"], identity, "ranking_not_generated")}
    priorities = _numeric_values(rows, "therapeutic_priority_score")
    confidences = _numeric_values(rows, "evidence_confidence_score")
    roles = sorted({str(row.get("therapeutic_role", "")).strip() for row in rows if row.get("therapeutic_role")})
    return {
        **identity,
        "ranking_rows": len(rows),
        "therapeutic_priority_score_present": bool(priorities),
        "therapeutic_priority_score_min": min(priorities) if priorities else "",
        "therapeutic_priority_score_max": max(priorities) if priorities else "",
        "evidence_confidence_score_present": bool(confidences),
        "evidence_confidence_score_mean": sum(confidences) / len(confidences) if confidences else "",
        "therapeutic_roles": ";".join(roles),
        "notes": "computational_ranking_not_experimental_validation",
    }


def _empty_ranking_row(organism_key: str, config: dict[str, Any], note: str) -> dict[str, Any]:
    return {
        "organism_key": organism_key,
        "organism": config.get("organism", ""),
        "strain": config.get("strain", ""),
        "taxon_id": config.get("taxon_id", ""),
        "ranking_rows": 0,
        "therapeutic_priority_score_present": False,
        "therapeutic_priority_score_min": "",
        "therapeutic_priority_score_max": "",
        "evidence_confidence_score_present": False,
        "evidence_confidence_score_mean": "",
        "therapeutic_roles": "",
        "notes": note,
    }


def _failed_status_row(organism_key: str, config: dict[str, Any], run_dir: Path, exc: Exception) -> dict[str, Any]:
    return {
        "organism_key": organism_key,
        "organism": config.get("organism", ""),
        "strain": config.get("strain", ""),
        "taxon_id": config.get("taxon_id", ""),
        "run_dir": str(run_dir),
        "pipeline_status": "batch_runner_exception",
        "candidate_seed_status": "not_available_after_exception",
        "candidate_seed_count": 0,
        "user_curated_layers_detected": 0,
        "ranking_rows": 0,
        "providers_attempted": "",
        "providers_success": "",
        "providers_unresolved": "run_exception",
        "providers_failed": "run_exception",
        "layers_resolved": "",
        "layers_unresolved": "run_exception",
        "therapeutic_priority_score_present": False,
        "evidence_confidence_score_present": False,
        "scoring_modified": False,
        "notes": str(exc),
    }


def _failed_seed_row(organism_key: str, config: dict[str, Any], exc: Exception) -> dict[str, Any]:
    return {
        "organism_key": organism_key,
        "organism": config.get("organism", ""),
        "strain": config.get("strain", ""),
        "taxon_id": config.get("taxon_id", ""),
        "candidate_seed_status": "not_available_after_exception",
        "candidate_seed_count": 0,
        "api_attempted": False,
        "api_success": False,
        "provider_name": "not_available",
        "fallback_reason": str(exc),
    }


def _build_review_markdown(
    manifest: dict[str, Any],
    statuses: list[dict[str, Any]],
    providers: list[dict[str, Any]],
    layers: list[dict[str, Any]],
) -> str:
    user_count = sum(_as_int(row.get("user_curated_layers_detected", 0)) for row in statuses)
    recommendation = _recommend_demo(statuses)
    provider_summary = _aggregate_provider_rows(providers)
    layer_summary = _aggregate_layer_rows(layers)
    lines = [
        "# Online-Only Multiorganism Validation Review",
        "",
        "## Purpose",
        "",
        "This phase evaluates whether one parameterized online-only workflow can retrieve and audit computational evidence across multiple bacterial organisms without source-code edits between runs.",
        "",
        f"- Started at UTC: `{manifest['started_at_utc']}`",
        f"- Completed at UTC: `{manifest['completed_at_utc']}`",
        f"- Run label: `{manifest['run_label']}`",
        f"- Organisms requested: `{'; '.join(manifest['organism_keys_requested'])}`",
        f"- Input policy: `{manifest['input_policy']}`",
        f"- User-curated layers detected: `{user_count}`",
        f"- Scoring modified: `{manifest['scoring_modified']}`",
        "",
        "## Run Comparison",
        "",
        _markdown_table(statuses, list(STATUS_COLUMNS)),
        "",
        "## Provider Comparison",
        "",
        _markdown_table(provider_summary),
        "",
        "## Layer Resolution Comparison",
        "",
        _markdown_table(layer_summary),
        "",
        "## Conservative Warnings",
        "",
        f"- {CONSERVATIVE_NOTE}",
        "- This package is online-only computational validation, not experimental validation.",
        "- Candidate seeding, enrichment, ranking and interpretation remain separate auditable stages.",
        "- Missing, failed, empty or timed-out provider responses remain unresolved rather than becoming negative biological evidence.",
        "- Curated snapshots and packaged demo data are not hidden fallbacks in this batch.",
        "- `therapeutic_priority_score` and `evidence_confidence_score` retain their existing separate meanings.",
        "",
        "## Manuscript Interpretation",
        "",
        "This phase demonstrates portability of the same external computational workflow and its provenance controls across configured organisms. It does not demonstrate target efficacy, essentiality in vivo, druggability, clinical benefit or experimental reproducibility. Provider failures limit evidence completeness but remain scientifically useful as explicit audit records: `unresolved` identifies absence of usable retrieved evidence without inventing a result.",
        "",
        "## Demo Recommendation",
        "",
        recommendation,
    ]
    return "\n".join(lines)


def _recommend_demo(statuses: list[dict[str, Any]]) -> str:
    eligible = [
        row
        for row in statuses
        if _as_int(row.get("user_curated_layers_detected", 0)) == 0
        and (
            _as_int(row.get("ranking_rows", 0)) > 0
            or _as_int(row.get("candidate_seed_count", 0)) > 0
            or bool(_split_values(row.get("providers_success", "")))
        )
    ]
    if not eligible:
        return (
            "No principal demo is recommended from this batch because no organism produced a candidate seed, "
            "successful provider evidence or a ranking. Resolve the audited connectivity limitation and rerun "
            "before selecting a manuscript demo."
        )
    best = max(
        eligible,
        key=lambda row: (
            row.get("pipeline_status") in {"completed", "completed_after_unresolved_fallback"},
            _as_int(row.get("ranking_rows", 0)),
            _as_int(row.get("candidate_seed_count", 0)),
            len(_split_values(row.get("providers_success", ""))),
        ),
    )
    complementary = [row["organism_key"] for row in statuses if row is not best]
    suffix = f" Use `{'; '.join(complementary)}` as complementary external validation." if complementary else ""
    return f"Use `{best['organism_key']}` as the principal computational demo because it has the strongest completed auditable output in this batch.{suffix}"


def _aggregate_provider_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("organism_key", "")), str(row.get("provider_name", "not_reported")))
        item = grouped.setdefault(
            key,
            {"organism_key": key[0], "provider_name": key[1], "attempted": 0, "success": 0, "unresolved": 0, "failed": 0},
        )
        attempted = _as_bool(row.get("api_attempted"))
        success = _as_bool(row.get("api_success"))
        item["attempted"] += int(attempted)
        item["success"] += int(success)
        item["unresolved"] += int(not success)
        item["failed"] += int(attempted and not success)
    return list(grouped.values())


def _aggregate_layer_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = []
    for row in rows:
        layer = str(row.get("layer_key", row.get("layer", "not_reported")))
        status = str(row.get("retrieval_status", row.get("status", "not_reported")))
        resolved = _layer_is_resolved(row)
        summary.append(
            {
                "organism_key": row.get("organism_key", ""),
                "layer_key": layer,
                "retrieval_status": status,
                "resolved": resolved,
                "source_type": row.get("source_type", "not_reported"),
            }
        )
    return summary


def _provider_names(rows: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]) -> list[str]:
    return sorted({str(row.get("provider_name", "not_reported")) for row in rows if predicate(row)})


def _layer_names(rows: list[dict[str, Any]], resolved: bool) -> list[str]:
    return sorted(
        {
            str(row.get("layer_key", row.get("layer", "not_reported")))
            for row in rows
            if _layer_is_resolved(row) is resolved
        }
    )


def _layer_is_resolved(row: dict[str, Any]) -> bool:
    status = str(row.get("retrieval_status", row.get("status", ""))).lower()
    source_type = str(row.get("source_type", "")).lower()
    unresolved_tokens = ("missing", "unresolved", "failed", "not_available", "not_implemented", "disabled")
    return source_type not in {"", "missing"} and not any(token in status for token in unresolved_tokens)


def _scoring_hashes(project_root: Path) -> dict[str, str]:
    hashes = {}
    for relative in ("src/nodos_funcionales/scoring.py", "src/nodos_funcionales/scoring_components.py"):
        path = project_root / relative
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _validate_organism_keys(keys: list[str], registry: dict[str, Any]) -> list[str]:
    if not keys:
        raise ValueError("at least one organism key is required")
    missing = [key for key in keys if key not in registry]
    if missing:
        raise ValueError(f"unknown organism keys: {', '.join(missing)}")
    return list(dict.fromkeys(keys))


def _validate_run_label(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError("run_label must contain only letters, digits, dots, underscores or hyphens")
    return value


def _numeric_values(rows: list[dict[str, str]], column: str) -> list[float]:
    values = []
    for row in rows:
        try:
            values.append(float(row[column]))
        except (KeyError, TypeError, ValueError):
            pass
    return values


def _first_existing(*paths: Path) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path | None) -> list[dict[str, str]]:
    if path is None:
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], preferred: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(preferred or [])
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    if not fieldnames:
        fieldnames = ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _markdown_table(rows: list[dict[str, Any]], preferred: list[str] | None = None) -> str:
    if not rows:
        return "No records were generated."
    columns = list(preferred or rows[0].keys())
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        values = [str(row.get(column, "")).replace("|", "\\|").replace("\n", " ") for column in columns]
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *body])


def _as_bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def _as_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _split_values(value: Any) -> list[str]:
    return [item for item in str(value or "").split(";") if item]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run and audit online-only validation across configured organisms.")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--organism-keys", nargs="+", help="Keys from config/online_only_organisms.json.")
    selection.add_argument("--all-default-validation-organisms", action="store_true")
    parser.add_argument("--run-label", required=True)
    parser.add_argument("--max-candidates", type=int, default=25)
    parser.add_argument("--disable-string", action="store_true")
    parser.add_argument("--disable-interpro", action="store_true")
    parser.add_argument("--disable-literature", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--check-provider-connectivity", action="store_true")
    parser.add_argument("--normalize-external-evidence", action="store_true")
    parser.add_argument("--validate-real-provider-captures", action="store_true")
    parser.add_argument("--output-dir")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    keys = list(DEFAULT_VALIDATION_ORGANISMS) if args.all_default_validation_organisms else args.organism_keys
    result = run_online_only_multiorganism_batch(
        project_root=PROJECT_ROOT,
        organism_keys=keys,
        run_label=args.run_label,
        max_candidates=args.max_candidates,
        enable_string=not args.disable_string,
        enable_interpro=not args.disable_interpro,
        enable_literature=not args.disable_literature,
        continue_on_error=args.continue_on_error,
        check_provider_connectivity=args.check_provider_connectivity,
        normalize_external_evidence=args.normalize_external_evidence,
        validate_real_provider_captures_enabled=args.validate_real_provider_captures,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps(result["manifest"], indent=2, ensure_ascii=True))
    failed = any(row["pipeline_status"] == "batch_runner_exception" for row in result["status_rows"])
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
