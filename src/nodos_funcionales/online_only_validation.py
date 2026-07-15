from __future__ import annotations

import json
import re
import ssl
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlencode

import certifi
import pandas as pd
from pandas.errors import EmptyDataError

from .config import load_config
from .discovery import prepare_discovery_workspace
from .human_homology_diamond import materialize_candidate_fasta
from .online_http import classify_provider_failure, urlopen_json
from .pipeline import run_pipeline
from .string_api import fetch_string_functional_network
from .unresolved_virulence import materialize_unresolved_virulence_layer


CONSERVATIVE_NOTE = (
    "Online-only validation outputs are computational hypotheses. Candidate discovery from UniProt, "
    "STRING, VFDB, DEG or other providers is not experimental validation and must not be described as "
    "pharmacological, clinical or wet-lab confirmation."
)

RECOVERABLE_PROVIDER_FAILURES = {
    "not_found",
    "http_error",
    "timeout",
    "provider_unavailable",
    "tls_certificate_verification_failed",
    "mapping_failed",
    "provider_not_implemented",
}


def default_online_only_run_dir(project_root: Path, organism_slug: str, run_date: str | None = None) -> Path:
    date_text = run_date or datetime.now().strftime("%Y%m%d")
    return project_root / "results" / "online_only_runs" / f"{organism_slug}_{date_text}"


def run_online_only_validation(
    project_root: Path,
    organism: str,
    organism_slug: str | None = None,
    taxon_id: int | str | None = None,
    strain: str | None = None,
    strain_slug: str | None = None,
    run_dir: Path | None = None,
    max_candidates: int = 25,
    enable_string: bool = True,
    enable_interpro: bool = True,
    enable_literature: bool = True,
    online_source_mode: str = "online_optional",
    taxon_resolution_mode: str = "online_optional",
    refresh_taxon_cache: bool = False,
    no_write_taxon_cache: bool = True,
    materialize_unresolved_required_fallback: bool = False,
) -> dict[str, Any]:
    """Run an isolated, organism-parameterized validation using online/external layers only."""
    organism = str(organism).strip()
    if not organism:
        raise ValueError("organism must be a non-empty name")
    resolved_organism_slug = _validate_slug(organism_slug or _slugify(organism), "organism_slug")
    resolved_strain_slug = _validate_slug(strain_slug or _slugify(strain), "strain_slug") if strain else None
    output_slug = f"{resolved_organism_slug}_{resolved_strain_slug}" if resolved_strain_slug else resolved_organism_slug
    configured_taxon_id = str(taxon_id).strip() if taxon_id is not None else ""
    if configured_taxon_id and not configured_taxon_id.isdigit():
        raise ValueError("taxon_id must contain digits only")
    base_run_dir = Path(run_dir) if run_dir else default_online_only_run_dir(project_root, output_slug)
    base_run_dir.mkdir(parents=True, exist_ok=True)
    workspace = base_run_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    discovery = prepare_discovery_workspace(
        project_root=project_root,
        organism_name=organism,
        strain=strain,
        acquisition_mode="manual",
        workspace=workspace,
        allow_demo_data=False,
        dry_run=True,
        taxon_resolution_mode=taxon_resolution_mode,
        refresh_taxon_cache=refresh_taxon_cache,
        no_write_taxon_cache=no_write_taxon_cache,
    )
    _write_online_only_config(workspace / "config" / "params.yaml", online_source_mode)

    config = load_config(workspace / "config" / "params.yaml")
    profile = discovery["profile"]
    resolved_taxon_id = configured_taxon_id or str(profile.get("taxon_id") or "").strip()
    if not resolved_taxon_id:
        resolved_taxon_id = _local_taxon_id(project_root, organism) or ""
    _write_run_identity_profile(
        workspace=workspace,
        profile=profile,
        organism=organism,
        strain=strain,
        configured_taxon_id=configured_taxon_id,
        resolved_taxon_id=resolved_taxon_id,
    )
    run_manifest = {
        "organism": organism,
        "organism_slug": resolved_organism_slug,
        "taxon_id": resolved_taxon_id or None,
        "registry_taxon_id": configured_taxon_id or None,
        "provider_taxon_id": str(profile.get("taxon_id") or "").strip() or None,
        "taxon_id_source": "configured" if configured_taxon_id else "discovery_or_local_registry",
        "strain": strain,
        "strain_slug": resolved_strain_slug,
        "output_slug": output_slug,
        "max_candidates": int(max_candidates),
        "enabled_providers": {
            "string": bool(enable_string),
            "interpro": bool(enable_interpro),
            "literature": bool(enable_literature),
        },
        "input_policy": "online_external_only_no_user_curated_or_packaged_demo",
        "online_source_mode": online_source_mode,
        "generated_at_utc": _utc_now(),
    }
    _json_dump(workspace / "results" / "online_only_run_manifest.json", run_manifest)
    seed_result = seed_candidate_essentiality_from_uniprot(
        workspace=workspace,
        organism_name=organism,
        taxon_id=resolved_taxon_id,
        config=config,
        max_candidates=max_candidates,
        mode=online_source_mode,
    )
    enrichment_result = enrich_online_only_downstream_layers(
        workspace=workspace,
        organism_name=organism,
        taxon_id=resolved_taxon_id,
        config=config,
        seed_result=seed_result,
        mode=online_source_mode,
        enable_string=enable_string,
        enable_interpro=enable_interpro,
        enable_literature=enable_literature,
    )
    if materialize_unresolved_required_fallback and not bool(seed_result.get("api_success")):
        _materialize_unresolved_required_external_layers(workspace, config, seed_result)

    pipeline_status = "not_started"
    pipeline_error = ""
    pipeline_result: dict[str, Any] = {}
    try:
        pipeline_result = run_pipeline(
            base_dir=workspace,
            config_path=workspace / "config" / "params.yaml",
            mode="phase3",
            online_source_mode=online_source_mode,
        )
        pipeline_status = "completed"
    except Exception as exc:  # noqa: BLE001 - failure is documented in the validation package.
        pipeline_status = "failed_gracefully"
        pipeline_error = str(exc)
        should_retry_with_unresolved = materialize_unresolved_required_fallback or _can_retry_with_unresolved_layers(
            pipeline_error,
            seed_result,
            workspace,
            config,
        )
        if should_retry_with_unresolved:
            fallback_reason = (
                "explicit_unresolved_required_fallback"
                if materialize_unresolved_required_fallback
                else f"recoverable_provider_failure:{classify_provider_failure(pipeline_error)}"
            )
            _materialize_unresolved_required_external_layers(workspace, config, seed_result, fallback_reason=fallback_reason)
            try:
                pipeline_result = run_pipeline(
                    base_dir=workspace,
                    config_path=workspace / "config" / "params.yaml",
                    mode="phase3",
                    online_source_mode=online_source_mode,
                )
                pipeline_status = "completed_after_unresolved_fallback"
            except Exception as fallback_exc:  # noqa: BLE001 - package documents failure.
                pipeline_error = f"{pipeline_error}; fallback_rerun_failed={fallback_exc}"

    package = build_online_only_review_package(
        run_dir=base_run_dir,
        workspace=workspace,
        organism=organism,
        organism_slug=resolved_organism_slug,
        taxon_id=resolved_taxon_id,
        strain=strain,
        strain_slug=resolved_strain_slug,
        seed_result=seed_result,
        pipeline_status=pipeline_status,
        pipeline_error=pipeline_error,
        pipeline_result=pipeline_result,
        online_source_mode=online_source_mode,
    )
    return {
        "run_dir": str(base_run_dir),
        "workspace": str(workspace),
        "organism": organism,
        "organism_slug": resolved_organism_slug,
        "taxon_id": resolved_taxon_id or None,
        "strain": strain,
        "strain_slug": resolved_strain_slug,
        "pipeline_status": pipeline_status,
        "pipeline_error": pipeline_error,
        "seed_result": seed_result,
        "enrichment_result": enrichment_result,
        "pipeline_result": pipeline_result,
        "package": package,
    }


def run_pseudomonas_online_only_validation(
    project_root: Path,
    run_dir: Path | None = None,
    max_seed_candidates: int = 25,
    online_source_mode: str = "online_optional",
    taxon_resolution_mode: str = "online_optional",
    refresh_taxon_cache: bool = False,
    no_write_taxon_cache: bool = True,
    materialize_unresolved_required_fallback: bool = False,
) -> dict[str, Any]:
    """Compatibility wrapper for the historical Pseudomonas online-only run."""
    return run_online_only_validation(
        project_root=project_root,
        organism="Pseudomonas aeruginosa",
        organism_slug="pseudomonas_aeruginosa",
        taxon_id=287,
        run_dir=run_dir,
        max_candidates=max_seed_candidates,
        online_source_mode=online_source_mode,
        taxon_resolution_mode=taxon_resolution_mode,
        refresh_taxon_cache=refresh_taxon_cache,
        no_write_taxon_cache=no_write_taxon_cache,
        materialize_unresolved_required_fallback=materialize_unresolved_required_fallback,
    )


def _write_run_identity_profile(
    workspace: Path,
    profile: dict[str, Any],
    organism: str,
    strain: str | None,
    configured_taxon_id: str,
    resolved_taxon_id: str,
) -> None:
    """Persist registry/run identity as the primary organism metadata."""
    profile_path = workspace / "results" / "organism_profile.json"
    provider_taxon_id = str(profile.get("taxon_id") or "").strip()
    principal_taxon_id = configured_taxon_id or resolved_taxon_id or provider_taxon_id
    principal_strain = str(strain or "").strip() or "not_reported"
    updated = {
        **profile,
        "organism": organism,
        "strain": principal_strain,
        "taxon_id": principal_taxon_id or None,
        "run_organism": organism,
        "run_strain": principal_strain,
        "run_taxon_id": principal_taxon_id or None,
        "registry_organism": organism,
        "registry_strain": principal_strain,
        "registry_taxon_id": configured_taxon_id or None,
        "provider_taxon_id": provider_taxon_id or None,
        "resolved_taxon_id": provider_taxon_id or None,
        "species_taxon_id": provider_taxon_id or None,
        "metadata_priority": "registry_or_run_identity",
        "metadata_priority_note": (
            "organism, strain and taxon_id are the requested run identity; provider-resolved taxonomy is preserved "
            "in provider_taxon_id/resolved_taxon_id and must not overwrite a registry strain taxon."
        ),
    }
    _json_dump(profile_path, updated)


def seed_candidate_essentiality_from_uniprot(
    workspace: Path,
    organism_name: str,
    taxon_id: str,
    config: dict[str, Any],
    max_candidates: int,
    mode: str,
) -> dict[str, Any]:
    external_dir = workspace / config["layer_resolution"]["external_data_dir"]
    external_dir.mkdir(parents=True, exist_ok=True)
    output_path = external_dir / "essentiality.csv"
    manifest_path = workspace / "results" / "online_only_candidate_seed_manifest.json"
    cfg = config["online_sources"]["uniprot"]
    provider_url = _build_uniprot_seed_url(taxon_id=taxon_id, config=config, max_candidates=max_candidates) if taxon_id else ""
    manifest: dict[str, Any] = {
        "source": "uniprot_candidate_seed",
        "layer_key": "candidate_seed",
        "provider": str(cfg["provider_name"]),
        "provider_name": str(cfg["provider_name"]),
        "provider_endpoint_or_mode": str(cfg["provider_base_url"]),
        "provider_function": "seed_candidate_essentiality_from_uniprot->_query_uniprot_seed",
        "provider_url": provider_url,
        "http_helper_used": "nodos_funcionales.online_http.urlopen_json",
        "sys_executable": sys.executable,
        "certifi_path": certifi.where(),
        "openssl_version": ssl.OPENSSL_VERSION,
        "mode": mode,
        "organism_name": organism_name,
        "taxon_id": taxon_id,
        "max_seed_candidates": int(max_candidates),
        "output_path": str(output_path),
        "source_used": "not_started",
        "retrieval_status": "not_started",
        "cache_hit": False,
        "api_attempted": False,
        "api_success": False,
        "retrieved_record_count": 0,
        "matched_candidate_count": 0,
        "fallback_used": False,
        "fallback_reason": "",
        "data_realism_flag": "unresolved",
        "evidence_level": "unresolved",
        "candidate_count": 0,
        "notes": [CONSERVATIVE_NOTE],
        "generated_at_utc": _utc_now(),
    }
    if mode in {"offline_only", "local", "api_stub"}:
        fallback_rows = _fallback_seed_rows(config, max_candidates)
        pd.DataFrame(fallback_rows, columns=_essentiality_seed_columns()).to_csv(output_path, index=False)
        manifest.update(
            {
                "source_used": "offline_mode_no_seed",
                "retrieval_status": "offline_mode_no_seed",
                "fallback_reason": "online_source_mode_does_not_allow_live_seed",
                "fallback_used": True,
                "candidate_count": int(len(fallback_rows)),
                "matched_candidate_count": int(len(fallback_rows)),
                "data_realism_flag": "unresolved_offline_fallback",
                "evidence_level": "unresolved",
                "notes": manifest["notes"] + ["No online seed was requested in this mode."],
            }
        )
        _json_dump(manifest_path, manifest)
        return manifest
    if not taxon_id:
        manifest.update(
            {
                "source_used": "missing_taxon_id",
                "retrieval_status": "missing_taxon_id",
                "fallback_reason": "taxon_id_required_for_uniprot_seed",
                "notes": manifest["notes"] + ["UniProt candidate seeding requires a taxon_id."],
            }
        )
        _json_dump(manifest_path, manifest)
        pd.DataFrame(columns=_essentiality_seed_columns()).to_csv(output_path, index=False)
        return manifest

    payload, errors = _query_uniprot_seed(taxon_id=taxon_id, config=config, max_candidates=max_candidates)
    manifest["api_attempted"] = True
    if payload is None:
        failure_class = classify_provider_failure("; ".join(errors))
        manifest.update(
            {
                "source_used": "api_failed",
                "retrieval_status": "api_failed",
                "fallback_reason": f"{failure_class}:api_failed_no_seed",
                "fallback_used": True,
                "notes": manifest["notes"] + errors,
            }
        )
        _json_dump(manifest_path, manifest)
        pd.DataFrame(columns=_essentiality_seed_columns()).to_csv(output_path, index=False)
        return manifest

    rows = _build_essentiality_seed_rows(payload, config)
    _json_dump(workspace / "results" / "online_only_uniprot_seed_records.json", payload)
    seed_df = pd.DataFrame(rows, columns=_essentiality_seed_columns())
    seed_df.to_csv(output_path, index=False)
    candidate_count = int(len(seed_df))
    manifest.update(
        {
            "source_used": "api_real",
            "retrieval_status": "api_real" if candidate_count else "api_success_no_candidate_records",
            "api_success": True,
            "retrieved_record_count": int(len(payload.get("results", []) or [])),
            "matched_candidate_count": candidate_count,
            "candidate_count": candidate_count,
            "fallback_reason": "" if candidate_count else "api_success_no_candidate_records",
            "fallback_used": candidate_count == 0,
            "notes": manifest["notes"] + errors,
            "data_realism_flag": "computed_online",
            "confidence": 0.60 if candidate_count else 0.0,
            "evidence_level": "computational_online_annotation" if candidate_count else "unresolved",
            "provenance_summary": (
                f"provider={cfg['provider_name']}; source_used=api_real; "
                "layer=essentiality; evidence_status=unresolved_online_seed"
            ),
        }
    )
    _json_dump(manifest_path, manifest)
    return manifest


def enrich_online_only_downstream_layers(
    workspace: Path,
    organism_name: str,
    taxon_id: str,
    config: dict[str, Any],
    seed_result: dict[str, Any],
    mode: str,
    enable_string: bool = True,
    enable_interpro: bool = True,
    enable_literature: bool = True,
) -> dict[str, Any]:
    """Attempt bounded online-only enrichment for candidates discovered by UniProt."""
    results: dict[str, Any] = {}
    candidates = _load_online_only_seed_candidates(workspace, config)
    _materialize_raw_candidate_context_for_adapters(workspace, config, candidates)
    results["essentiality"] = _write_online_only_provider_manifest(
        workspace=workspace,
        layer_key="essentiality",
        provider_name="uniprot_rest_candidate_seed",
        provider_endpoint_or_mode=str(config["online_sources"]["uniprot"]["provider_base_url"]),
        provider_function="seed_candidate_essentiality_from_uniprot",
        api_attempted=bool(seed_result.get("api_attempted", False)),
        api_success=bool(seed_result.get("api_success", False)),
        retrieved_record_count=int(seed_result.get("retrieved_record_count", 0) or 0),
        matched_candidate_count=int(seed_result.get("matched_candidate_count", 0) or 0),
        fallback_used=bool(seed_result.get("fallback_used", False)),
        fallback_reason=str(seed_result.get("fallback_reason") or "uniprot_seed_is_not_essentiality_evidence"),
        retrieval_status="candidate_seed_only_not_essentiality_evidence",
        source_used="api_real_candidate_seed_only" if seed_result.get("api_success") else "api_failed",
        data_realism_flag="computed_online" if seed_result.get("api_success") else "unresolved",
        evidence_level="unresolved",
        inherited_from_candidate_seed=True,
    )
    results["uniprot_downstream"] = _materialize_uniprot_downstream_from_seed(workspace, config, candidates, seed_result)
    results["human_homology_candidate_fasta"] = materialize_candidate_fasta(
        workspace=workspace,
        raw_cfg=config.get("online_sources", {}).get("human_homology_diamond", {}),
        candidates=candidates,
        mode=mode,
        seed_records=_read_json_if_exists(workspace / "results" / "online_only_uniprot_seed_records.json"),
    )
    provider_calls = {
        "string": (enable_string, "functional_network", "string", _attempt_string_enrichment, (workspace, organism_name, taxon_id, config, mode, candidates)),
        "interpro": (enable_interpro, "host_annotation", "interpro", _attempt_interpro_domain_enrichment, (workspace, organism_name, taxon_id, config, mode, candidates)),
        "literature": (enable_literature, "literature_support", "europe_pmc", _attempt_literature_metadata_enrichment, (workspace, organism_name, config, mode, candidates)),
    }
    for result_key, (enabled, layer_key, provider_name, provider_call, provider_args) in provider_calls.items():
        if enabled:
            results[result_key] = provider_call(*provider_args)
        else:
            results[result_key] = _write_online_only_provider_manifest(
                workspace=workspace,
                layer_key=layer_key,
                provider_name=provider_name,
                provider_endpoint_or_mode="disabled_by_run_configuration",
                provider_function=f"online_only_validation:{provider_call.__name__}",
                api_attempted=False,
                api_success=False,
                retrieved_record_count=0,
                matched_candidate_count=0,
                fallback_used=True,
                fallback_reason="provider_disabled_by_run_configuration",
                retrieval_status="provider_disabled",
                source_used="provider_disabled",
                data_realism_flag="unresolved",
                evidence_level="unresolved",
                inherited_from_candidate_seed=False,
            )
    for layer_key, provider_name, reason in [
        ("virulence", "vfdb", "vfdb_live_provider_not_available"),
        ("contextual_essentiality", "deg", "deg_live_provider_not_available"),
        ("strain_conservation", "bvbrc", "bvbrc_live_conservation_provider_not_available"),
        ("evolutionary_escape", "not_implemented", "evolutionary_escape_provider_not_implemented"),
        ("evolutionary_escape_risk", "not_implemented", "evolutionary_escape_risk_provider_not_implemented"),
        ("redundancy", "not_implemented", "redundancy_provider_not_implemented"),
        ("collateral_sensitivity", "not_implemented", "collateral_sensitivity_provider_not_implemented"),
    ]:
        results[layer_key] = _write_online_only_provider_manifest(
            workspace=workspace,
            layer_key=layer_key,
            provider_name=provider_name,
            provider_endpoint_or_mode=_provider_endpoint_or_mode(layer_key, provider_name),
            provider_function="online_only_validation:provider_not_implemented_marker",
            api_attempted=False,
            api_success=False,
            retrieved_record_count=0,
            matched_candidate_count=0,
            fallback_used=True,
            fallback_reason=reason,
            retrieval_status="provider_not_implemented",
            source_used="provider_not_implemented",
            data_realism_flag="unresolved",
            evidence_level="unresolved",
            inherited_from_candidate_seed=False,
        )
        if layer_key == "virulence" and not candidates.empty:
            materialize_unresolved_virulence_layer(workspace)
    return results


def build_online_only_review_package(
    run_dir: Path,
    workspace: Path,
    organism: str,
    seed_result: dict[str, Any],
    pipeline_status: str,
    pipeline_error: str,
    pipeline_result: dict[str, Any],
    online_source_mode: str,
    organism_slug: str | None = None,
    taxon_id: str | None = None,
    strain: str | None = None,
    strain_slug: str | None = None,
) -> dict[str, str]:
    package_dir = run_dir / "review_package"
    package_dir.mkdir(parents=True, exist_ok=True)
    results_dir = workspace / "results"
    copied: dict[str, str] = {}
    provider_audit = build_online_only_provider_audit(workspace, seed_result)
    for filename in [
        "ranking_nodos.csv",
        "ranking_nodos_phase3.csv",
        "candidate_audit.csv",
        "evidence_strength_audit.csv",
        "layer_resolution_summary.csv",
        "layer_resolution_summary.md",
        "layer_resolution_manifest.json",
        "online_source_manifest.json",
        "online_source_report.md",
        "online_only_candidate_seed_manifest.json",
        "online_only_run_manifest.json",
        "online_only_essentiality_manifest.json",
        "online_only_localization_manifest.json",
        "online_only_functional_network_manifest.json",
        "online_only_host_annotation_manifest.json",
        "online_only_literature_support_manifest.json",
        "online_only_virulence_manifest.json",
        "online_only_contextual_essentiality_manifest.json",
        "online_only_strain_conservation_manifest.json",
        "online_only_evolutionary_escape_manifest.json",
        "online_only_evolutionary_escape_risk_manifest.json",
        "online_only_redundancy_manifest.json",
        "online_only_collateral_sensitivity_manifest.json",
        "deg_essentiality_manifest.json",
        "vfdb_virulence_manifest.json",
        "bvbrc_conservation_manifest.json",
        "string_mapping_audit.csv",
        "online_source_report.md",
    ]:
        source = results_dir / filename
        if source.exists():
            target = package_dir / filename
            shutil.copy2(source, target)
            if filename in {"ranking_nodos.csv", "ranking_nodos_phase3.csv"}:
                _sanitize_online_only_ranking(target, seed_result)
            if filename == "layer_resolution_manifest.json":
                _enrich_layer_resolution_manifest(target, provider_audit)
            if filename == "layer_resolution_summary.csv":
                _enrich_layer_resolution_summary_csv(target, provider_audit)
            if filename == "layer_resolution_summary.md":
                _rewrite_layer_resolution_summary_md(target, provider_audit)
            copied[filename] = str(target)

    provider_audit_path = package_dir / "online_only_provider_audit.csv"
    provider_audit.to_csv(provider_audit_path, index=False)
    copied["online_only_provider_audit.csv"] = str(provider_audit_path)

    provenance_summary = build_online_only_provenance_summary(workspace)
    provenance_path = package_dir / "online_only_provenance_summary.csv"
    provenance_summary.to_csv(provenance_path, index=False)
    copied["online_only_provenance_summary.csv"] = str(provenance_path)

    interpretation = build_online_only_candidate_interpretation(workspace)
    interpretation_path = package_dir / "online_only_candidate_interpretation.csv"
    interpretation.to_csv(interpretation_path, index=False)
    copied["online_only_candidate_interpretation.csv"] = str(interpretation_path)

    review_path = package_dir / "ONLINE_ONLY_REVIEW.md"
    review_path.write_text(
        _build_review_markdown(
            organism=organism,
            organism_slug=organism_slug,
            taxon_id=taxon_id,
            strain=strain,
            strain_slug=strain_slug,
            workspace=workspace,
            package_dir=package_dir,
            seed_result=seed_result,
            provenance_summary=provenance_summary,
            provider_audit=provider_audit,
            pipeline_status=pipeline_status,
            pipeline_error=pipeline_error,
            pipeline_result=pipeline_result,
            online_source_mode=online_source_mode,
        ),
        encoding="utf-8",
    )
    copied["ONLINE_ONLY_REVIEW.md"] = str(review_path)
    return copied


def build_online_only_provenance_summary(workspace: Path) -> pd.DataFrame:
    manifest_path = workspace / "results" / "layer_resolution_manifest.json"
    if not manifest_path.exists():
        return pd.DataFrame(
            [
                {
                    "layer_key": "not_available",
                    "source_type": "missing",
                    "source_name": "missing",
                    "retrieval_status": "layer_resolution_manifest_missing",
                    "is_user_supplied": False,
                    "is_external": False,
                    "confidence": 0.0,
                    "online_evidence_availability": "unresolved_or_missing",
                }
            ]
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest:
        return _empty_provenance_summary()
    rows = []
    provider_audit = build_online_only_provider_audit(workspace, _load_seed_manifest(workspace))
    provider_by_layer = {str(row["layer_key"]): row for _, row in provider_audit.iterrows()}
    for layer_key, item in manifest.items():
        is_user = bool(item.get("is_user_supplied"))
        is_external = bool(item.get("is_external"))
        status = str(item.get("retrieval_status", "not_reported"))
        source_type = str(item.get("source_type", "not_reported"))
        audit_row = provider_by_layer.get(layer_key, {})
        has_audit = isinstance(audit_row, pd.Series) or bool(audit_row)
        api_success = bool(audit_row.get("api_success", False)) if has_audit else False
        evidence_level = str(audit_row.get("evidence_level", "unresolved") if has_audit else "unresolved")
        availability = (
            "online_provider_success"
            if api_success
            else ("external_controlled_or_fallback" if is_external and status not in {"missing_optional_layer"} else "unresolved_or_missing")
        )
        if is_user or source_type == "user":
            availability = "invalid_user_curated_detected"
        rows.append(
            {
                "layer_key": layer_key,
                "source_type": source_type,
                "source_name": item.get("source_name", "not_reported"),
                "retrieval_status": status,
                "is_user_supplied": is_user,
                "is_external": is_external,
                "is_cached": bool(item.get("is_cached")),
                "is_proxy": bool(item.get("is_proxy")),
                "confidence": float(item.get("confidence", 0.0) or 0.0),
                "api_attempted": bool(audit_row.get("api_attempted", False)) if has_audit else False,
                "api_success": api_success,
                "provider_name": audit_row.get("provider_name", item.get("source_name", "not_reported")) if has_audit else item.get("source_name", "not_reported"),
                "source_used": audit_row.get("source_used", status) if has_audit else status,
                "fallback_reason": audit_row.get("fallback_reason", "") if has_audit else "",
                "evidence_level": evidence_level,
                "experimental_validation_supported": False,
                "online_evidence_availability": availability,
            }
        )
    return pd.DataFrame(rows)


def _empty_provenance_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "layer_key",
            "source_type",
            "source_name",
            "retrieval_status",
            "is_user_supplied",
            "is_external",
            "is_cached",
            "is_proxy",
            "confidence",
            "api_attempted",
            "api_success",
            "provider_name",
            "source_used",
            "fallback_reason",
            "evidence_level",
            "experimental_validation_supported",
            "online_evidence_availability",
        ]
    )


def build_online_only_provider_audit(workspace: Path, seed_result: dict[str, Any]) -> pd.DataFrame:
    manifest = _load_layer_resolution_manifest(workspace)
    seed_manifest = seed_result or _load_seed_manifest(workspace)
    rows: list[dict[str, Any]] = [_provider_audit_row_from_seed(seed_manifest)]
    layer_to_manifest = {
        "candidate_seed": workspace / "results" / "online_only_candidate_seed_manifest.json",
        "localization": workspace / "results" / "online_source_manifest.json",
        "functional_network": workspace / "results" / "online_source_manifest.json",
        "host_annotation": workspace / "results" / "online_only_host_annotation_manifest.json",
        "human_homologs": workspace / "results" / "human_homology_diamond_manifest.json",
        "literature_support": workspace / "results" / "online_only_literature_support_manifest.json",
        "virulence": workspace / "results" / "vfdb_virulence_manifest.json",
        "essentiality": workspace / "results" / "deg_essentiality_manifest.json",
        "strain_conservation": workspace / "results" / "bvbrc_conservation_manifest.json",
        "contextual_essentiality": workspace / "results" / "online_only_contextual_essentiality_manifest.json",
        "evolutionary_escape": workspace / "results" / "online_only_evolutionary_escape_manifest.json",
        "evolutionary_escape_risk": workspace / "results" / "online_only_evolutionary_escape_risk_manifest.json",
        "redundancy": workspace / "results" / "online_only_redundancy_manifest.json",
        "collateral_sensitivity": workspace / "results" / "online_only_collateral_sensitivity_manifest.json",
    }
    preferred_manifests = {
        "essentiality": workspace / "results" / "online_only_essentiality_manifest.json",
        "localization": workspace / "results" / "online_only_localization_manifest.json",
        "functional_network": workspace / "results" / "online_only_functional_network_manifest.json",
        "virulence": workspace / "results" / "online_only_virulence_manifest.json",
        "strain_conservation": workspace / "results" / "online_only_strain_conservation_manifest.json",
    }
    for layer_key, item in manifest.items():
        provider_name = str(item.get("source_name") or item.get("layer_key") or layer_key)
        source_used = str(item.get("retrieval_status", "not_reported"))
        provider_manifest = _read_json_if_exists(preferred_manifests.get(layer_key)) or _read_json_if_exists(layer_to_manifest.get(layer_key))
        if provider_manifest:
            provider_name = str(provider_manifest.get("provider_name") or provider_manifest.get("provider") or provider_manifest.get("source") or provider_name)
            source_used = str(provider_manifest.get("source_used") or provider_manifest.get("retrieval_status") or source_used)
        api_attempted = bool(provider_manifest.get("api_attempted", False)) if provider_manifest else _infer_attempted(item)
        api_success = bool(provider_manifest.get("api_success", False)) if provider_manifest else False
        retrieved_count = _provider_count(provider_manifest, ["retrieved_record_count", "protein_count_requested", "records_retrieved", "edge_count"])
        matched_count = _provider_count(provider_manifest, ["matched_candidate_count", "protein_count_mapped", "exact_gene_match_count", "mapped_protein_count"])
        evidence_level = str(provider_manifest.get("evidence_level") or _evidence_level_for_layer(layer_key, api_success, source_used, item)) if provider_manifest else _evidence_level_for_layer(layer_key, api_success, source_used, item)
        fallback_reason = str(provider_manifest.get("fallback_reason") or _fallback_reason_for_layer(layer_key, item, source_used))
        fallback_used = bool(fallback_reason) or str(item.get("source_name", "")).find("fallback") >= 0
        rows.append(
            {
                "layer_key": layer_key,
                "provider_name": _canonical_provider_name(layer_key, provider_name),
                "provider_endpoint_or_mode": _provider_endpoint_or_mode(layer_key, provider_name),
                "provider_function": str(provider_manifest.get("provider_function") or "not_reported") if provider_manifest else "not_reported",
                "api_attempted": api_attempted,
                "api_success": api_success,
                "retrieved_record_count": int(retrieved_count),
                "matched_candidate_count": int(matched_count),
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason,
                "retrieval_status": str(provider_manifest.get("retrieval_status") or _provider_retrieval_status(layer_key, item, source_used, api_attempted, api_success)) if provider_manifest else _provider_retrieval_status(layer_key, item, source_used, api_attempted, api_success),
                "source_used": source_used,
                "data_realism_flag": str(provider_manifest.get("data_realism_flag") or ("computed_online" if api_success else ("controlled_context" if source_used == "controlled_provider_materialized" else "unresolved"))) if provider_manifest else ("computed_online" if api_success else ("controlled_context" if source_used == "controlled_provider_materialized" else "unresolved")),
                "evidence_level": evidence_level,
                "experimental_validation_supported": False,
                "inherited_from_candidate_seed": bool(provider_manifest.get("inherited_from_candidate_seed", False)) if provider_manifest else False,
                "generated_at_utc": str(provider_manifest.get("generated_at_utc") or _utc_now()) if provider_manifest else _utc_now(),
            }
        )
    return pd.DataFrame(rows).drop_duplicates(subset=["layer_key"], keep="last").reset_index(drop=True)


def build_online_only_candidate_interpretation(workspace: Path) -> pd.DataFrame:
    ranking_path = workspace / "results" / "ranking_nodos.csv"
    if not ranking_path.exists():
        return pd.DataFrame(
            [
                {
                    "protein_id": "not_available",
                    "gene": "not_available",
                    "therapeutic_priority_score": pd.NA,
                    "evidence_confidence_score": pd.NA,
                    "online_only_validation_status": "ranking_not_generated",
                    "experimental_validation_supported": False,
                    "interpretation_note": "No ranking was generated; no candidate validation claim can be made.",
                }
            ]
        )
    ranking = pd.read_csv(ranking_path)
    provider_audit = build_online_only_provider_audit(workspace, _load_seed_manifest(workspace))
    succeeded = ";".join(provider_audit.loc[provider_audit["api_success"].astype(bool), "provider_name"].astype(str).tolist()) or "none"
    unresolved_layers = ";".join(
        provider_audit.loc[provider_audit["evidence_level"].astype(str).eq("unresolved"), "layer_key"].astype(str).tolist()
    ) or "none"
    rows = []
    for _, row in ranking.iterrows():
        rows.append(
            {
                "protein_id": row.get("protein_id", ""),
                "gene": row.get("gene", ""),
                "therapeutic_priority_score": row.get("therapeutic_priority_score", pd.NA),
                "evidence_confidence_score": row.get("evidence_confidence_score", pd.NA),
                "therapeutic_role": row.get("therapeutic_role", "not_reported"),
                "online_only_validation_status": "computational_hypothesis_only",
                "experimental_validation_supported": False,
                "online_evidence_availability": "partial_online_computational" if succeeded != "none" else "unresolved_or_fallback_only",
                "providers_succeeded": succeeded,
                "unresolved_or_missing_evidence": row.get("missing_evidence_flags", row.get("evidence_limitations", "not_reported")),
                "unresolved_layers": unresolved_layers,
                "confidence_evidence_tier_corrected": row.get("confidence_evidence_tier", "not_reported"),
                "provenance_status_corrected": row.get("provenance_status", "not_reported"),
                "retrieval_mode_corrected": row.get("retrieval_mode", "not_reported"),
                "data_realism_flag_corrected": row.get("data_realism_flag", "not_reported"),
                "interpretation_note": (
                    "This package did not retrieve experimental validation for this candidate. "
                    "Read any internal source-class labels together with the explicit provenance summary."
                ),
            }
        )
    return pd.DataFrame(rows)


def _build_review_markdown(
    organism: str,
    organism_slug: str | None,
    taxon_id: str | None,
    strain: str | None,
    strain_slug: str | None,
    workspace: Path,
    package_dir: Path,
    seed_result: dict[str, Any],
    provenance_summary: pd.DataFrame,
    provider_audit: pd.DataFrame,
    pipeline_status: str,
    pipeline_error: str,
    pipeline_result: dict[str, Any],
    online_source_mode: str,
) -> str:
    user_rows = provenance_summary[provenance_summary["is_user_supplied"].astype(bool)]
    unresolved = provenance_summary[
        provenance_summary["online_evidence_availability"].astype(str).eq("unresolved_or_missing")
    ]
    attempted = provider_audit[provider_audit["api_attempted"].astype(bool)]
    succeeded = provider_audit[provider_audit["api_success"].astype(bool)]
    failed = attempted[~attempted["api_success"].astype(bool)]
    not_implemented = provider_audit[
        provider_audit["retrieval_status"].astype(str).str.contains("provider_not_implemented", na=False)
    ]
    inherited = provider_audit[
        provider_audit.get("inherited_from_candidate_seed", pd.Series(False, index=provider_audit.index)).astype(bool)
    ]
    resolved_online = provider_audit[provider_audit["data_realism_flag"].astype(str).eq("computed_online")]
    ranking_path = package_dir / "ranking_nodos.csv"
    ranking_note = "not_generated"
    if ranking_path.exists():
        ranking = pd.read_csv(ranking_path)
        ranking_note = f"generated_rows={len(ranking)}"
        for column in ["therapeutic_priority_score", "evidence_confidence_score"]:
            if column not in ranking.columns:
                ranking_note += f"; missing_{column}"
    lines = [
        f"# {organism} Online-Only Validation Review",
        "",
        f"- Organism: `{organism}`",
        f"- Organism slug: `{organism_slug or _slugify(organism)}`",
        f"- Taxon id: `{taxon_id or 'not provided'}`",
        f"- Strain: `{strain or 'not provided'}`",
        f"- Strain slug: `{strain_slug or 'not provided'}`",
        f"- Workspace: `{workspace}`",
        f"- Online source mode: `{online_source_mode}`",
        f"- Pipeline status: `{pipeline_status}`",
        f"- Candidate seed source used: `{seed_result.get('source_used')}`",
        f"- Candidate seed count: `{seed_result.get('candidate_count', 0)}`",
        f"- Candidate seed fallback reason: `{seed_result.get('fallback_reason') or 'none'}`",
        f"- Ranking status: `{ranking_note}`",
        f"- User-curated layers detected: `{len(user_rows)}`",
        f"- Unresolved or missing layers: `{len(unresolved)}`",
        f"- Providers attempted: `{'; '.join(attempted['provider_name'].astype(str).tolist()) or 'none'}`",
        f"- Providers succeeded: `{'; '.join(succeeded['provider_name'].astype(str).tolist()) or 'none'}`",
        f"- Providers failed or unresolved: `{'; '.join(failed['provider_name'].astype(str).tolist()) or 'none'}`",
        f"- Providers not implemented: `{'; '.join(not_implemented['provider_name'].astype(str).tolist()) or 'none'}`",
        f"- Layers resolved from live online providers: `{'; '.join(resolved_online['layer_key'].astype(str).tolist()) or 'none'}`",
        f"- Layers inherited from UniProt seed: `{'; '.join(inherited['layer_key'].astype(str).tolist()) or 'none'}`",
        f"- Layers unresolved/missing: `{'; '.join(unresolved['layer_key'].astype(str).tolist()) or 'none'}`",
        "",
        "## Interpretation Guardrails",
        "",
        f"- {CONSERVATIVE_NOTE}",
        "- `therapeutic_priority_score` ranks model priority only.",
        "- `evidence_confidence_score` describes evidence support and interpretability constraints.",
        "- Online evidence availability reports whether a layer resolved from external/online provenance.",
        "- Missing online evidence remains unresolved; it is not converted into negative evidence.",
        "- Candidates must not be described as experimentally validated unless a retrieved layer explicitly supports that claim.",
        "",
        "## Pipeline Result",
        "",
        f"- Result object: `{json.dumps(pipeline_result, sort_keys=True)}`",
    ]
    if pipeline_error:
        lines.append(f"- Graceful failure: `{pipeline_error}`")
    lines.extend(
        [
            "",
            "## Provider Audit",
            "",
            _markdown_table(provider_audit),
            "",
            "## Provenance Summary",
            "",
            _markdown_table(provenance_summary),
            "",
            "## Candidate Interpretation",
            "",
            "See `online_only_candidate_interpretation.csv`. In this package, "
            "`experimental_validation_supported=false` means no generated candidate should be described as experimentally validated.",
            "",
            "## Seed Notes",
            "",
        ]
    )
    lines.extend([f"- {note}" for note in seed_result.get("notes", [])] or ["- none"])
    return "\n".join(lines)


def _sanitize_online_only_ranking(path: Path, seed_result: dict[str, Any]) -> None:
    ranking = pd.read_csv(path)
    seed_success = bool(seed_result.get("api_success")) and str(seed_result.get("source_used")) == "api_real"
    ranking["confidence_evidence_tier"] = "partial_online_computational" if seed_success else "online_seed_only_unresolved"
    ranking["confidence_source_class"] = "partial_online_computational" if seed_success else "online_unresolved_fallback"
    ranking["provenance_status"] = "partial_external_online" if seed_success else "external_unresolved_fallback"
    ranking["retrieval_mode"] = "online_optional_partial" if seed_success else "offline_unresolved_fallback"
    ranking["data_realism_flag"] = "computed_online" if seed_success else "unresolved_fallback_only"
    ranking["evidence_level"] = "computational_online_annotation" if seed_success else "unresolved"
    ranking["evidence_source"] = "online_provider_audit"
    ranking["experimental_validation_supported"] = False
    ranking["online_only_label_policy"] = (
        "publication_safe_online_computational_not_experimental"
    )
    if "interpretation_warning" in ranking.columns:
        ranking["interpretation_warning"] = ranking["interpretation_warning"].fillna("").astype(str) + (
            " Online-only provider retrieval is computational evidence, not experimental validation."
        )
    ranking.to_csv(path, index=False)


def _enrich_layer_resolution_manifest(path: Path, provider_audit: pd.DataFrame) -> None:
    manifest = _read_json_if_exists(path)
    audit_by_layer = {str(row["layer_key"]): row for _, row in provider_audit.iterrows()}
    for layer_key, item in manifest.items():
        audit = audit_by_layer.get(layer_key)
        if audit is None:
            continue
        item.update(
            {
                "provider_name": audit.get("provider_name", "not_reported"),
                "provider_endpoint_or_mode": audit.get("provider_endpoint_or_mode", "not_reported"),
                "provider_function": audit.get("provider_function", "not_reported"),
                "api_attempted": bool(audit.get("api_attempted", False)),
                "api_success": bool(audit.get("api_success", False)),
                "retrieved_record_count": int(audit.get("retrieved_record_count", 0) or 0),
                "matched_candidate_count": int(audit.get("matched_candidate_count", 0) or 0),
                "fallback_used": bool(audit.get("fallback_used", False)),
                "fallback_reason": audit.get("fallback_reason", ""),
                "source_used": audit.get("source_used", item.get("retrieval_status", "not_reported")),
                "data_realism_flag": audit.get("data_realism_flag", "unresolved"),
                "evidence_level": audit.get("evidence_level", "unresolved"),
                "experimental_validation_supported": False,
                "inherited_from_candidate_seed": bool(audit.get("inherited_from_candidate_seed", False)),
            }
        )
    _json_dump(path, manifest)


def _enrich_layer_resolution_summary_csv(path: Path, provider_audit: pd.DataFrame) -> None:
    summary = pd.read_csv(path)
    if "layer_key" not in summary.columns:
        return
    audit_columns = [
        "layer_key",
        "provider_name",
        "provider_endpoint_or_mode",
        "provider_function",
        "api_attempted",
        "api_success",
        "retrieved_record_count",
        "matched_candidate_count",
        "fallback_used",
        "fallback_reason",
        "source_used",
        "data_realism_flag",
        "evidence_level",
        "experimental_validation_supported",
        "inherited_from_candidate_seed",
    ]
    enriched = summary.merge(provider_audit[audit_columns], on="layer_key", how="left")
    enriched["experimental_validation_supported"] = enriched["experimental_validation_supported"].fillna(False)
    enriched.to_csv(path, index=False)


def _rewrite_layer_resolution_summary_md(path: Path, provider_audit: pd.DataFrame) -> None:
    lines = [
        "# Layer Resolution Summary",
        "",
        "This online-only package appends provider audit fields. Online computational retrieval is not experimental validation.",
        "",
        _markdown_table(provider_audit),
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_online_only_config(config_path: Path, online_source_mode: str) -> None:
    # Load and rewrite one mapping instead of appending duplicate YAML root keys. Duplicate
    # ``online_sources`` keys discarded the configured DIAMOND provider in Phase 9B v5.
    config = load_config(config_path)
    online_sources = config.setdefault("online_sources", {})
    online_sources["source_mode_effective"] = online_source_mode
    online_sources["source_mode_default"] = online_source_mode

    layer_resolution = config.setdefault("layer_resolution", {})
    layer_resolution["write_cache_from_external"] = False
    layers = layer_resolution.setdefault("layers", {})
    provider_overrides = {
        "essentiality": "uniprot_candidate_seed",
        "virulence": "vfdb_real",
        "human_homologs": "human_homology_diamond",
        "localization": "uniprot_real",
        "host_annotation": "interpro_domain_overlap",
        "strain_conservation": "bvbrc_real",
        "functional_network": "string_real",
        "clinical_impact": "controlled_therapeutic_context_v2",
        "curated_disease_context": "controlled_therapeutic_context_v2",
        "therapy_site_context": "controlled_therapeutic_context_v2",
        "literature_support": "curated_online_examples",
    }
    for layer_key, provider_name in provider_overrides.items():
        layer_cfg = layers.setdefault(layer_key, {})
        layer_cfg["strategy"] = "external_preferred"
        layer_cfg["external_provider"] = provider_name
        if layer_key in {"clinical_impact", "curated_disease_context", "therapy_site_context"}:
            layer_cfg["proxy_name"] = "scoring_proxy_default"

    config_path.write_text(_dump_simple_yaml(config) + "\n", encoding="utf-8")


def _dump_simple_yaml(mapping: dict[str, Any], indent: int = 0) -> str:
    """Serialize the mapping subset supported by config.parse_simple_yaml."""
    lines: list[str] = []
    prefix = " " * indent
    for key, value in mapping.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_dump_simple_yaml(value, indent + 2))
        else:
            if value is True:
                scalar = "true"
            elif value is False:
                scalar = "false"
            elif value is None:
                scalar = "null"
            elif value == "":
                scalar = '""'
            else:
                scalar = str(value)
            lines.append(f"{prefix}{key}: {scalar}")
    return "\n".join(lines)


def _provider_audit_row_from_seed(seed_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "layer_key": "candidate_seed",
        "provider_name": str(seed_manifest.get("provider_name") or seed_manifest.get("provider") or "uniprot_rest"),
        "provider_endpoint_or_mode": str(seed_manifest.get("provider_endpoint_or_mode") or seed_manifest.get("mode") or "not_reported"),
        "provider_function": str(seed_manifest.get("provider_function") or "seed_candidate_essentiality_from_uniprot"),
        "api_attempted": bool(seed_manifest.get("api_attempted", False)),
        "api_success": bool(seed_manifest.get("api_success", False)),
        "retrieved_record_count": int(seed_manifest.get("retrieved_record_count", seed_manifest.get("candidate_count", 0)) or 0),
        "matched_candidate_count": int(seed_manifest.get("matched_candidate_count", seed_manifest.get("candidate_count", 0)) or 0),
        "fallback_used": bool(seed_manifest.get("fallback_used", False)),
        "fallback_reason": str(seed_manifest.get("fallback_reason") or ""),
        "retrieval_status": str(seed_manifest.get("retrieval_status") or seed_manifest.get("source_used") or "not_reported"),
        "source_used": str(seed_manifest.get("source_used") or "not_reported"),
        "data_realism_flag": str(seed_manifest.get("data_realism_flag") or ("computed_online" if seed_manifest.get("api_success") else "unresolved")),
        "evidence_level": str(seed_manifest.get("evidence_level") or ("computational_online_annotation" if seed_manifest.get("api_success") else "unresolved")),
        "experimental_validation_supported": False,
        "inherited_from_candidate_seed": False,
        "generated_at_utc": str(seed_manifest.get("generated_at_utc") or _utc_now()),
    }


def _load_seed_manifest(workspace: Path) -> dict[str, Any]:
    return _read_json_if_exists(workspace / "results" / "online_only_candidate_seed_manifest.json")


def _load_layer_resolution_manifest(workspace: Path) -> dict[str, Any]:
    return _read_json_if_exists(workspace / "results" / "layer_resolution_manifest.json")


def _read_json_if_exists(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _provider_count(manifest: dict[str, Any], keys: list[str]) -> int:
    for key in keys:
        value = manifest.get(key)
        if value is not None and str(value) != "":
            try:
                return int(float(value))
            except (TypeError, ValueError):
                continue
    return 0


def _infer_attempted(layer_resolution: dict[str, Any]) -> bool:
    status = str(layer_resolution.get("retrieval_status", ""))
    source_name = str(layer_resolution.get("source_name", ""))
    if status in {"external_not_requested", "missing_optional_layer", "proxy_default"}:
        return False
    return any(token in source_name or token in status for token in ["api", "uniprot", "string", "vfdb", "deg", "bvbrc", "interpro"])


def _canonical_provider_name(layer_key: str, provider_name: str) -> str:
    lowered = provider_name.lower()
    if layer_key in {"candidate_seed", "localization"} or "uniprot" in lowered:
        return "uniprot_rest"
    if layer_key == "functional_network" or "string" in lowered:
        return "string_api"
    if layer_key == "virulence" or "vfdb" in lowered:
        return "vfdb"
    if layer_key in {"human_homologs"}:
        return "uniprot_rest"
    if layer_key == "host_annotation" or "interpro" in lowered:
        return "interpro_api"
    if layer_key == "literature_support":
        return "pubmed_or_literature_metadata"
    if layer_key in {"essentiality", "contextual_essentiality"} or "deg" in lowered:
        return "deg"
    if layer_key == "strain_conservation" or "bvbrc" in lowered:
        return "bvbrc"
    if "controlled_therapeutic_context" in lowered:
        return "controlled_therapeutic_context"
    return provider_name or "not_reported"


def _provider_endpoint_or_mode(layer_key: str, provider_name: str) -> str:
    provider = _canonical_provider_name(layer_key, provider_name)
    endpoints = {
        "uniprot_rest": "https://rest.uniprot.org/uniprotkb/search",
        "string_api": "https://string-db.org/api",
        "vfdb": "VFDB live source if implemented; otherwise unresolved",
        "deg": "DEG live source if implemented; otherwise unresolved",
        "interpro_api": "https://www.ebi.ac.uk/interpro/api",
        "bvbrc": "BV-BRC API",
        "pubmed_or_literature_metadata": "NCBI E-utilities or literature metadata mode",
        "controlled_therapeutic_context": "controlled_provider_materialized",
    }
    return endpoints.get(provider, provider)


def _evidence_level_for_layer(layer_key: str, api_success: bool, source_used: str, item: dict[str, Any]) -> str:
    if api_success:
        if layer_key in {"candidate_seed", "localization"}:
            return "computational_online_annotation"
        if layer_key == "functional_network":
            return "computational_online_interaction"
        if layer_key == "literature_support":
            return "literature_metadata_only"
        return "computational_online_evidence"
    if source_used == "controlled_provider_materialized":
        return "fallback_controlled"
    if str(item.get("retrieval_status")) == "missing_optional_layer":
        return "unresolved"
    if str(item.get("retrieval_status")) == "external_not_requested":
        return "unresolved"
    if "fallback" in str(item.get("source_name", "")).lower():
        return "unresolved"
    return "unresolved"


def _fallback_reason_for_layer(layer_key: str, item: dict[str, Any], source_used: str) -> str:
    status = str(item.get("retrieval_status", ""))
    if status == "missing_optional_layer":
        return "provider_not_implemented_or_no_matched_online_evidence"
    if status == "external_not_requested":
        if layer_key == "virulence":
            return "vfdb_live_provider_not_available_or_preexisting_external_fallback"
        if layer_key in {"essentiality", "contextual_essentiality"}:
            return "essentiality_live_provider_not_implemented_or_not_used_for_seed"
        return "provider_not_requested"
    if source_used == "controlled_provider_materialized":
        return "controlled_context_not_experimental"
    return ""


def _provider_retrieval_status(
    layer_key: str,
    item: dict[str, Any],
    source_used: str,
    api_attempted: bool,
    api_success: bool,
) -> str:
    if api_success:
        return str(source_used or "api_real")
    status = str(item.get("retrieval_status", "not_reported"))
    if status == "external_not_requested":
        return "provider_unavailable_or_not_implemented"
    if layer_key in {"human_homologs", "host_annotation"} and not api_success:
        return "unresolved_online_homology"
    if api_attempted and not api_success:
        return "api_attempted_no_success"
    return status


def _local_taxon_id(project_root: Path, organism_name: str) -> str:
    alias_path = project_root / "config" / "taxon_aliases.json"
    if not alias_path.exists():
        return ""
    try:
        catalog = json.loads(alias_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    normalized = organism_name.strip().casefold()
    for entry in catalog.get("entries", []) or []:
        names = [entry.get("canonical_name", ""), *(entry.get("aliases", []) or [])]
        if normalized in {str(name).strip().casefold() for name in names}:
            return str(entry.get("taxon_id") or "").strip()
    return ""


def _slugify(value: str | None) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or "organism"


def _validate_slug(value: str, field_name: str) -> str:
    if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", value):
        raise ValueError(f"{field_name} must use lowercase letters, digits and single underscores")
    return value


def _load_online_only_seed_candidates(workspace: Path, config: dict[str, Any]) -> pd.DataFrame:
    path = workspace / config["layer_resolution"]["external_data_dir"] / "essentiality.csv"
    if not path.exists():
        return pd.DataFrame(columns=["protein_id", "gene", "candidate_seed_accession"])
    df = pd.read_csv(path)
    for column in ["protein_id", "gene", "candidate_seed_accession"]:
        if column not in df.columns:
            df[column] = ""
    return df[df["protein_id"].fillna("").astype(str).str.strip().ne("")].copy()


def _materialize_raw_candidate_context_for_adapters(workspace: Path, config: dict[str, Any], candidates: pd.DataFrame) -> None:
    if candidates.empty:
        return
    raw_dir = workspace / "data_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_seed = raw_dir / "essentiality.csv"
    if not raw_seed.exists():
        candidates.to_csv(raw_seed, index=False)



def _normalize_online_localization(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "unknown"

    text = text.replace("_", " ")
    text = text.replace(",", ";")

    if "outer membrane" in text:
        return "outer_membrane"
    if "inner membrane" in text:
        return "inner_membrane"
    if "cell wall" in text:
        return "cell_wall"
    if "cell envelope" in text or "envelope" in text:
        return "cell_wall"
    if "periplasm" in text:
        return "periplasm"
    if "secreted" in text or "extracellular" in text:
        return "extracellular"
    if "fimbrium" in text or "pilus" in text or "flagellum" in text or "cell surface" in text or "surface" in text:
        return "outer_membrane"
    if "cytoplasm" in text or "cytosol" in text:
        return "cytoplasm"
    if "membrane" in text:
        return "inner_membrane"

    return "unknown"

def _materialize_uniprot_downstream_from_seed(
    workspace: Path,
    config: dict[str, Any],
    candidates: pd.DataFrame,
    seed_result: dict[str, Any],
) -> dict[str, Any]:
    payload = _read_json_if_exists(workspace / "results" / "online_only_uniprot_seed_records.json")
    entries = payload.get("results", []) if isinstance(payload, dict) else []
    by_accession = {
        str(entry.get("primaryAccession") or entry.get("uniProtkbId") or "").strip().upper(): entry
        for entry in entries
        if isinstance(entry, dict)
    }
    rows = []
    annotations = []
    for _, candidate in candidates.iterrows():
        protein_id = str(candidate.get("protein_id") or "").strip().upper()
        accession = str(candidate.get("candidate_seed_accession") or protein_id).strip().upper()
        entry = by_accession.get(accession, {})
        gene = str(candidate.get("gene") or _extract_first_gene_name(entry) or protein_id).strip()
        location = _extract_uniprot_subcellular_location(entry) if entry else ""
        annotations.append(
            {
                "protein_id": protein_id,
                "gene": gene,
                "uniprot_accession": accession,
                "uniprot_id": str(entry.get("uniProtkbId") or ""),
                "uniprot_reviewed": "reviewed" if str(entry.get("entryType", "")).lower().find("reviewed") >= 0 else "unreviewed",
                "uniprot_protein_name": _extract_uniprot_protein_name(entry),
                "uniprot_gene_primary": _extract_first_gene_name(entry),
                "uniprot_gene_names": _extract_uniprot_gene_names(entry),
                "uniprot_annotation_score": entry.get("annotationScore", ""),
                "uniprot_organism_name": str((entry.get("organism") or {}).get("scientificName") or ""),
                "uniprot_subcellular_location": location,
                "uniprot_match_status": "inherited_from_candidate_seed" if entry else "missing_seed_record",
                "provider": "uniprot_rest",
                "source_used": "api_real",
                "api_attempted": True,
                "api_success": bool(entry),
                "data_realism_flag": "computed_online" if entry else "unresolved",
            }
        )
        rows.append(
            {
                "protein_id": protein_id,
                "gene": gene,
                "localization": _normalize_online_localization(location),
                "database": str(config["online_sources"]["uniprot"]["database_label"]) + ":candidate_seed_reuse",
                "evidence_source_type": "online_external_source",
                "source_used": "api_real" if entry else "api_success_no_localization_records",
                "data_realism_flag": "computed_online" if entry and location else "unresolved",
                "evidence_level": "computational_online_annotation" if entry and location else "unresolved",
                "inherited_from_candidate_seed": True,
                "experimental_validation_supported": False,
                "localization_missing_flags": "none" if location else "api_success_no_localization_records",
            }
        )
    external_dir = workspace / config["layer_resolution"]["external_data_dir"]
    external_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(external_dir / "localization.csv", index=False)
    pd.DataFrame(annotations).to_csv(workspace / "data_raw" / "uniprot_annotations.csv", index=False)
    matched = int(sum(1 for row in rows if row["evidence_level"] != "unresolved"))
    return _write_online_only_provider_manifest(
        workspace=workspace,
        layer_key="localization",
        provider_name="uniprot_rest",
        provider_endpoint_or_mode=str(config["online_sources"]["uniprot"]["provider_base_url"]),
        provider_function="online_only_validation:_materialize_uniprot_downstream_from_seed",
        api_attempted=bool(seed_result.get("api_attempted", False)),
        api_success=bool(seed_result.get("api_success", False) and len(rows) > 0),
        retrieved_record_count=int(seed_result.get("retrieved_record_count", len(entries)) or 0),
        matched_candidate_count=matched,
        fallback_used=matched == 0,
        fallback_reason="" if matched else "api_success_no_localization_records",
        retrieval_status="inherited_from_candidate_seed" if rows else "api_success_no_candidate_records",
        source_used="api_real" if rows else "unresolved",
        data_realism_flag="computed_online" if rows else "unresolved",
        evidence_level="computational_online_annotation" if matched else "unresolved",
        inherited_from_candidate_seed=True,
    )


def _attempt_string_enrichment(
    workspace: Path,
    organism_name: str,
    taxon_id: str,
    config: dict[str, Any],
    mode: str,
    candidates: pd.DataFrame,
) -> dict[str, Any]:
    if candidates.empty:
        return _write_online_only_provider_manifest(
            workspace, "functional_network", "string_api", "https://string-db.org/api",
            "string_api.fetch_string_functional_network", False, False, 0, 0, True,
            "no_candidate_records", "unresolved", "unresolved", "unresolved", "unresolved", False,
        )
    try:
        result = fetch_string_functional_network(
            workspace=workspace,
            organism_name=organism_name,
            taxon_id=taxon_id,
            config=config,
            mode=mode,
            replace_existing=True,
        )
        df = result["functional_network"]
        manifest = result["manifest"]
        external_path = workspace / config["layer_resolution"]["external_data_dir"] / "functional_network.csv"
        external_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(external_path, index=False)
        api_success = bool(manifest.get("api_success", False))
        matched = int(len(df)) if api_success else 0
        return _write_online_only_provider_manifest(
            workspace=workspace,
            layer_key="functional_network",
            provider_name="string_api",
            provider_endpoint_or_mode=str(config["online_sources"]["string"]["provider_base_url"]),
            provider_function="string_api.fetch_string_functional_network",
            api_attempted=True,
            api_success=api_success,
            retrieved_record_count=int(manifest.get("edge_count", 0) or 0),
            matched_candidate_count=matched,
            fallback_used=not api_success,
            fallback_reason=str(manifest.get("fallback_reason") or ("" if api_success else "mapping_failed")),
            retrieval_status=str(manifest.get("source_used") or ("api_real" if api_success else "mapping_failed")),
            source_used=str(manifest.get("source_used") or ("api_real" if api_success else "api_failed")),
            data_realism_flag="computed_online" if api_success else "unresolved",
            evidence_level="computational_online_interaction" if api_success else "unresolved",
            inherited_from_candidate_seed=False,
        )
    except Exception as exc:  # noqa: BLE001 - provider failures are audited.
        failure = classify_provider_failure(exc)
        return _write_online_only_provider_manifest(
            workspace, "functional_network", "string_api", "https://string-db.org/api",
            "string_api.fetch_string_functional_network", True, False, 0, 0, True,
            failure, failure, "api_failed", "unresolved", "unresolved", False,
        )


def _attempt_interpro_domain_enrichment(
    workspace: Path,
    organism_name: str,
    taxon_id: str,
    config: dict[str, Any],
    mode: str,
    candidates: pd.DataFrame,
) -> dict[str, Any]:
    cfg = config["online_sources"]["interpro"]
    rows: list[dict[str, Any]] = []
    retrieved = 0
    attempted = False
    notes: list[str] = []
    for _, candidate in candidates.iterrows():
        accession = str(candidate.get("candidate_seed_accession") or candidate.get("protein_id") or "").strip()
        if not accession:
            continue
        attempted = True
        url = _build_interpro_url(accession, cfg)
        try:
            payload = urlopen_json(
                url,
                timeout=float(cfg["provider_timeout_seconds"]),
                headers={"User-Agent": str(cfg["provider_user_agent"]), "Accept": "application/json"},
            )
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{accession}:{classify_provider_failure(exc)}")
            continue
        domains = _extract_interpro_accessions(payload)
        retrieved += len(domains)
        if domains:
            rows.append(
                {
                    "protein_id": str(candidate.get("protein_id") or accession).strip().upper(),
                    "gene": str(candidate.get("gene") or accession).strip(),
                    "domain_overlap_score": float(config["imputation"]["neutral_unknown_score"]),
                    "host_criticality_penalty": float(config["imputation"]["neutral_unknown_score"]),
                    "database": str(cfg["database_label"]),
                    "interpro_bacterial_accession": accession,
                    "interpro_bacterial_entries": ";".join(sorted(domains)),
                    "interpro_rule": "online_only_bacterial_domain_metadata_no_human_comparison",
                    "interpro_missing_flags": "no_human_comparable_domain_workflow",
                    "evidence_source_type": "online_external_source",
                    "evidence_level": "computational_online_domain_annotation",
                    "data_realism_flag": "computed_online",
                    "experimental_validation_supported": False,
                }
            )
    external_path = workspace / config["layer_resolution"]["external_data_dir"] / "host_annotation.csv"
    if rows:
        external_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(external_path, index=False)
    fallback = "" if rows else ("api_success_no_domain_records" if attempted and not notes else ";".join(notes) or "no_candidate_records")
    api_success = attempted and not notes
    return _write_online_only_provider_manifest(
        workspace=workspace,
        layer_key="host_annotation",
        provider_name="interpro_api",
        provider_endpoint_or_mode=str(cfg["provider_base_url"]),
        provider_function="online_only_validation:_attempt_interpro_domain_enrichment",
        api_attempted=attempted,
        api_success=api_success,
        retrieved_record_count=retrieved,
        matched_candidate_count=len(rows),
        fallback_used=not bool(rows),
        fallback_reason=fallback,
        retrieval_status="api_real" if rows else ("api_success_no_domain_records" if api_success else classify_provider_failure(fallback)),
        source_used="api_real" if api_success else "api_failed",
        data_realism_flag="computed_online" if rows else "unresolved",
        evidence_level="computational_online_domain_annotation" if rows else "unresolved",
        inherited_from_candidate_seed=False,
    )


def _attempt_literature_metadata_enrichment(
    workspace: Path,
    organism_name: str,
    config: dict[str, Any],
    mode: str,
    candidates: pd.DataFrame,
) -> dict[str, Any]:
    endpoint = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    rows: list[dict[str, Any]] = []
    attempted = False
    retrieved = 0
    notes: list[str] = []
    for _, candidate in candidates.head(10).iterrows():
        gene = str(candidate.get("gene") or candidate.get("protein_id") or "").strip()
        protein_id = str(candidate.get("protein_id") or gene).strip().upper()
        if not gene:
            continue
        query = f'"{organism_name}" AND ({gene} OR {protein_id})'
        url = f"{endpoint}?{urlencode({'query': query, 'format': 'json', 'pageSize': 5})}"
        attempted = True
        try:
            payload = urlopen_json(url, timeout=20, headers={"User-Agent": "nodos-funcionales-literature/1.0"})
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{gene}:{classify_provider_failure(exc)}")
            continue
        records = ((payload or {}).get("resultList") or {}).get("result", []) or []
        retrieved += len(records)
        if records:
            first = records[0]
            rows.append(
                {
                    "protein_id": protein_id,
                    "gene": gene,
                    "organism": organism_name,
                    "literature_support_score": 0.25,
                    "evidence_type": "literature_metadata_only",
                    "reference": str(first.get("title") or ""),
                    "citation": str(first.get("authorString") or ""),
                    "pubmed_id": str(first.get("pmid") or ""),
                    "year": first.get("pubYear", ""),
                    "evidence_strength": 0.25,
                    "source_quality": 0.50,
                    "database": "europe_pmc_metadata",
                    "evidence_source_type": "online_external_source",
                    "notes": "Metadata hit only; not therapeutic or experimental validation.",
                }
            )
    external_path = workspace / config["layer_resolution"]["external_data_dir"] / "literature_support.csv"
    if rows:
        external_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(external_path, index=False)
    api_success = attempted and not notes
    fallback = "" if rows else ("api_success_no_literature_records" if api_success else ";".join(notes) or "no_candidate_records")
    return _write_online_only_provider_manifest(
        workspace=workspace,
        layer_key="literature_support",
        provider_name="pubmed_or_europepmc",
        provider_endpoint_or_mode=endpoint,
        provider_function="online_only_validation:_attempt_literature_metadata_enrichment",
        api_attempted=attempted,
        api_success=api_success,
        retrieved_record_count=retrieved,
        matched_candidate_count=len(rows),
        fallback_used=not bool(rows),
        fallback_reason=fallback,
        retrieval_status="api_real" if rows else ("api_success_no_literature_records" if api_success else classify_provider_failure(fallback)),
        source_used="api_real" if api_success else "api_failed",
        data_realism_flag="computed_online" if rows else "unresolved",
        evidence_level="literature_metadata_only" if rows else "unresolved",
        inherited_from_candidate_seed=False,
    )


def _write_online_only_provider_manifest(
    workspace: Path,
    layer_key: str,
    provider_name: str,
    provider_endpoint_or_mode: str,
    provider_function: str,
    api_attempted: bool,
    api_success: bool,
    retrieved_record_count: int,
    matched_candidate_count: int,
    fallback_used: bool,
    fallback_reason: str,
    retrieval_status: str,
    source_used: str,
    data_realism_flag: str,
    evidence_level: str,
    inherited_from_candidate_seed: bool,
) -> dict[str, Any]:
    manifest = {
        "layer_key": layer_key,
        "provider_name": provider_name,
        "provider": provider_name,
        "provider_endpoint_or_mode": provider_endpoint_or_mode,
        "provider_function": provider_function,
        "api_attempted": bool(api_attempted),
        "api_success": bool(api_success),
        "retrieved_record_count": int(retrieved_record_count),
        "matched_candidate_count": int(matched_candidate_count),
        "fallback_used": bool(fallback_used),
        "fallback_reason": str(fallback_reason or ""),
        "retrieval_status": str(retrieval_status),
        "source_used": str(source_used),
        "data_realism_flag": str(data_realism_flag),
        "evidence_level": str(evidence_level),
        "experimental_validation_supported": False,
        "inherited_from_candidate_seed": bool(inherited_from_candidate_seed),
        "generated_at_utc": _utc_now(),
    }
    _json_dump(workspace / "results" / f"online_only_{layer_key}_manifest.json", manifest)
    return manifest


def _build_interpro_url(accession: str, cfg: dict[str, Any]) -> str:
    base = str(cfg["provider_base_url"]).rstrip("/")
    return f"{base}/entry/interpro/protein/uniprot/{quote_plus(accession)}/?page_size={int(cfg.get('page_size', 200))}"


def _extract_interpro_accessions(payload: Any) -> set[str]:
    domains: set[str] = set()
    if not isinstance(payload, dict):
        return domains
    for item in payload.get("results", []) or []:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata", {}) or {}
        accession = str(metadata.get("accession") or item.get("accession") or "").strip().upper()
        if accession:
            domains.add(accession)
    return domains


def _extract_uniprot_subcellular_location(entry: dict[str, Any]) -> str:
    locations: list[str] = []
    for comment in entry.get("comments", []) or []:
        if str(comment.get("commentType") or "").strip().lower() != "subcellular location":
            continue
        for location in comment.get("subcellularLocations", []) or []:
            value = (((location.get("location") or {}).get("value")) or "").strip()
            if value and value not in locations:
                locations.append(value)
    return ";".join(locations)


def _extract_uniprot_protein_name(entry: dict[str, Any]) -> str:
    description = entry.get("proteinDescription", {}) or {}
    recommended = description.get("recommendedName", {}) or {}
    full = recommended.get("fullName", {}) or {}
    if full.get("value"):
        return str(full["value"])
    for submitted in description.get("submissionNames", []) or []:
        value = ((submitted.get("fullName") or {}).get("value")) or ""
        if value:
            return str(value)
    return ""


def _extract_uniprot_gene_names(entry: dict[str, Any]) -> str:
    names: list[str] = []
    for gene in entry.get("genes", []) or []:
        gene_name = gene.get("geneName", {})
        if gene_name.get("value"):
            names.append(str(gene_name["value"]))
        for field in ["synonyms", "orderedLocusNames", "orfNames"]:
            for item in gene.get(field, []) or []:
                value = item.get("value")
                if value:
                    names.append(str(value))
    deduped = []
    for name in names:
        if name not in deduped:
            deduped.append(name)
    return ";".join(deduped)


def _materialize_unresolved_required_external_layers(
    workspace: Path,
    config: dict[str, Any],
    seed_result: dict[str, Any],
    fallback_reason: str = "unresolved_required_layer_fallback",
) -> None:
    external_dir = workspace / config["layer_resolution"]["external_data_dir"]
    seed_path = external_dir / "essentiality.csv"
    if not seed_path.exists():
        seed = pd.DataFrame()
    else:
        try:
            seed = pd.read_csv(seed_path)
        except EmptyDataError:
            seed = pd.DataFrame()
    if seed.empty or "protein_id" not in seed.columns:
        seed = pd.DataFrame(_fallback_seed_rows(config, 3), columns=_essentiality_seed_columns())
        seed["candidate_seed_note"] = (
            "Explicit unresolved fallback row created after live online seed failed; not retrieved evidence."
        )
        seed.to_csv(seed_path, index=False)
    base = seed[["protein_id", "gene"]].copy()
    base["gene"] = base["gene"].fillna(base["protein_id"]).astype(str)
    source_note = str(seed_result.get("source_used", "not_reported"))
    unresolved_database = f"provider_not_found:{source_note}"
    virulence = base.copy()
    virulence["virulence_score"] = pd.NA
    virulence["virulence_factor"] = pd.NA
    virulence["database"] = unresolved_database
    virulence["source_database"] = "provider_not_found"
    virulence["evidence"] = "unresolved"
    virulence["evidence_source_type"] = "unresolved_online_required_fallback"
    virulence["retrieval_status"] = "unresolved"
    virulence["unresolved_evidence_note"] = "Provider evidence could not be retrieved; no virulence evidence inferred."
    virulence.to_csv(external_dir / "virulence.csv", index=False)

    preserved_layers: list[str] = []
    homologs_path = external_dir / "human_homologs.csv"
    if _is_usable_diamond_homology_layer(workspace, homologs_path):
        preserved_layers.append("human_homologs")
    else:
        homologs = base.copy()
        homologs["human_homolog"] = pd.NA
        homologs["evalue"] = pd.NA
        homologs["human_gene"] = "none"
        homologs["database"] = unresolved_database
        homologs["source_database"] = "provider_not_found"
        homologs["evidence"] = "unresolved"
        homologs["evidence_source_type"] = "unresolved_online_required_fallback"
        homologs["retrieval_status"] = "unresolved"
        homologs["homology_lookup_status"] = "unresolved_online_provider_not_available"
        homologs["homology_evidence_tier"] = "unresolved"
        homologs["homology_confidence_score"] = 0.0
        homologs["homology_missing_flags"] = "provider_not_run_or_failed"
        homologs.to_csv(homologs_path, index=False)

    localization = base.copy()
    localization["localization"] = "unknown"
    localization["database"] = unresolved_database
    localization["source_database"] = "provider_not_found"
    localization["evidence"] = "unresolved"
    localization["evidence_source_type"] = "unresolved_online_required_fallback"
    localization["retrieval_status"] = "unresolved"
    localization["localization_missing_flags"] = "provider_not_run_or_failed"
    localization.to_csv(external_dir / "localization.csv", index=False)

    _write_unresolved_required_fallback_audit(workspace, seed_result, fallback_reason, preserved_layers)

    raw_dir = workspace / "data_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    uniprot_annotations_path = raw_dir / "uniprot_annotations.csv"
    annotation_columns = [
        "protein_id",
        "gene",
        "uniprot_accession",
        "uniprot_id",
        "uniprot_reviewed",
        "uniprot_protein_name",
        "uniprot_gene_primary",
        "uniprot_gene_names",
        "uniprot_match_status",
        "provider",
        "source_used",
    ]
    if not uniprot_annotations_path.exists() or uniprot_annotations_path.stat().st_size <= 2:
        pd.DataFrame(columns=annotation_columns).to_csv(uniprot_annotations_path, index=False)


def _is_usable_diamond_homology_layer(workspace: Path, homologs_path: Path) -> bool:
    """Return true only for a non-empty canonical layer backed by a successful DIAMOND manifest."""
    manifest = _read_json_if_exists(workspace / "results" / "human_homology_diamond_manifest.json")
    successful_statuses = {"diamond_blastp_executed", "diamond_cached_tsv_materialized"}
    if str(manifest.get("status") or manifest.get("retrieval_status")) not in successful_statuses:
        return False
    if not homologs_path.exists() or homologs_path.stat().st_size <= 2:
        return False
    try:
        homologs = pd.read_csv(homologs_path)
    except (EmptyDataError, OSError, ValueError):
        return False
    required = {"protein_id", "homology_lookup_status", "homology_evidence_tier", "source_database"}
    if homologs.empty or not required.issubset(homologs.columns):
        return False
    source_is_diamond = homologs["source_database"].fillna("").astype(str).str.contains("diamond", case=False).any()
    status_is_diamond = homologs["homology_lookup_status"].fillna("").astype(str).str.startswith("diamond_").any()
    return bool(source_is_diamond or status_is_diamond)


def _write_unresolved_required_fallback_audit(
    workspace: Path,
    seed_result: dict[str, Any],
    fallback_reason: str,
    preserved_layers: list[str] | None = None,
) -> None:
    payload = {
        "retrieval_status": "unresolved",
        "source_database": "provider_not_found",
        "evidence": "unresolved",
        "fallback_reason": fallback_reason,
        "preserved_valid_layers": list(preserved_layers or []),
        "seed_source_used": str(seed_result.get("source_used", "not_reported")),
        "seed_retrieval_status": str(seed_result.get("retrieval_status", "not_reported")),
        "interpretation": "Provider evidence was not recovered; this is not negative biological evidence.",
        "generated_at_utc": _utc_now(),
    }
    _json_dump(workspace / "results" / "online_only_unresolved_required_fallback_manifest.json", payload)


def _fallback_seed_rows(config: dict[str, Any], max_candidates: int) -> list[dict[str, Any]]:
    seed_ids = [
        ("PA0001", "online_seed_placeholder_1"),
        ("PA0002", "online_seed_placeholder_2"),
        ("PA0003", "online_seed_placeholder_3"),
    ][: max(0, min(int(max_candidates), 3))]
    rows = []
    for protein_id, gene in seed_ids:
        rows.append(
            {
                "protein_id": protein_id,
                "gene": gene,
                "essential": pd.NA,
                "evidence": "",
                "database": str(config["online_sources"]["uniprot"]["database_label"]) + ":offline_unresolved_candidate_seed",
                "essentiality_status": "unresolved_online_seed_not_retrieved",
                "evidence_source_type": "online_external_candidate_discovery_unavailable",
                "candidate_seed_provider": str(config["online_sources"]["uniprot"]["provider_name"]),
                "candidate_seed_accession": "",
                "candidate_seed_note": "Offline fallback placeholder for pipeline contract testing; not retrieved evidence.",
            }
        )
    return rows


def _build_uniprot_seed_url(taxon_id: str, config: dict[str, Any], max_candidates: int) -> str:
    cfg = config["online_sources"]["uniprot"]
    query = f"(organism_id:{taxon_id})"
    params = {
        "query": query,
        "format": "json",
        "size": int(max_candidates),
        "fields": str(cfg["fields"]),
    }
    return f"{str(cfg['provider_base_url'])}?{urlencode(params)}"


def _query_uniprot_seed(taxon_id: str, config: dict[str, Any], max_candidates: int) -> tuple[dict[str, Any] | None, list[str]]:
    cfg = config["online_sources"]["uniprot"]
    url = _build_uniprot_seed_url(taxon_id=taxon_id, config=config, max_candidates=max_candidates)
    headers = {
        "User-Agent": str(cfg["provider_user_agent"]),
        "Accept": "application/json",
    }
    timeout = float(cfg["provider_timeout_seconds"])
    retries = int(cfg["provider_max_retries"])
    backoff = float(cfg["provider_backoff_seconds"])
    errors: list[str] = []
    for attempt in range(retries + 1):
        try:
            return urlopen_json(url, timeout=timeout, headers=headers), errors
        except HTTPError as exc:
            errors.append(f"HTTP {exc.code} from UniProt candidate seed")
            if exc.code == 429 and attempt < retries:
                time.sleep(backoff)
                continue
            break
        except ssl.SSLCertVerificationError as exc:
            errors.append(f"TLS certificate verification failed from UniProt candidate seed: {exc}")
            break
        except URLError as exc:
            errors.append(f"Network error from UniProt candidate seed: {exc.reason}")
            break
        except TimeoutError:
            errors.append("Timeout from UniProt candidate seed")
            break
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"Could not decode UniProt candidate seed response: {exc}")
            break
    return None, errors


def _can_retry_with_unresolved_layers(
    pipeline_error: str,
    seed_result: dict[str, Any],
    workspace: Path,
    config: dict[str, Any],
) -> bool:
    """Allow retry only for provider retrieval failures after candidate identifiers exist."""
    if classify_provider_failure(pipeline_error) not in RECOVERABLE_PROVIDER_FAILURES:
        return False
    if _seed_candidate_count(seed_result) > 0:
        return True
    seed_path = workspace / config["layer_resolution"]["external_data_dir"] / "essentiality.csv"
    if not seed_path.exists():
        return False
    try:
        seed = pd.read_csv(seed_path)
    except EmptyDataError:
        return False
    return not seed.empty and "protein_id" in seed.columns and seed["protein_id"].notna().any()


def _seed_candidate_count(seed_result: dict[str, Any]) -> int:
    for key in ("candidate_count", "matched_candidate_count", "retrieved_record_count"):
        try:
            value = int(seed_result.get(key, 0) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    return 0


def _build_essentiality_seed_rows(payload: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    seen: set[str] = set()
    for entry in payload.get("results", []) or []:
        accession = str(entry.get("primaryAccession") or entry.get("uniProtkbId") or "").strip()
        if not accession:
            continue
        protein_id = accession.upper()
        if protein_id in seen:
            continue
        seen.add(protein_id)
        gene = _extract_first_gene_name(entry) or protein_id
        rows.append(
            {
                "protein_id": protein_id,
                "gene": gene,
                "essential": pd.NA,
                "evidence": "",
                "database": str(config["online_sources"]["uniprot"]["database_label"]) + ":candidate_seed",
                "essentiality_status": "unresolved_online_seed",
                "evidence_source_type": "online_external_candidate_discovery",
                "candidate_seed_provider": str(config["online_sources"]["uniprot"]["provider_name"]),
                "candidate_seed_accession": accession,
                "candidate_seed_note": "UniProt-derived candidate seed only; essentiality not experimentally validated by this row.",
            }
        )
    return rows


def _extract_first_gene_name(entry: dict[str, Any]) -> str:
    for gene in entry.get("genes", []) or []:
        gene_name = gene.get("geneName", {})
        if gene_name.get("value"):
            return str(gene_name["value"]).strip()
        for field in ["orderedLocusNames", "orfNames", "synonyms"]:
            for item in gene.get(field, []) or []:
                if item.get("value"):
                    return str(item["value"]).strip()
    return ""


def _essentiality_seed_columns() -> list[str]:
    return [
        "protein_id",
        "gene",
        "essential",
        "evidence",
        "database",
        "essentiality_status",
        "evidence_source_type",
        "candidate_seed_provider",
        "candidate_seed_accession",
        "candidate_seed_note",
    ]


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    columns = list(df.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in df.iterrows():
        values = [str(row.get(column, "")).replace("|", "/") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
