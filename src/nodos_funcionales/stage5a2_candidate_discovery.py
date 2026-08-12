from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .config import load_config
from .online.provider_modes import normalize_provider_mode
from .online_only_validation import run_online_only_validation
from .stage5a_candidate_discovery import (
    _accession,
    _dedupe,
    _gene,
    _sequence,
    finalize_stage5a_audit,
    write_stage5a_candidate_seed_snapshot,
)
from .stage5a1_candidate_discovery import (
    _identifiers,
    _proteome,
    _slug,
    _target,
    fetch_scoped_records,
)

STAGE = "5A.2"
STAGE_NAME = "Stage 5A.2 — Alias-aware benchmark identity and resilient full-proteome scoring"
BENCHMARK_MODES = {"blind", "conditional"}
PROVIDER_PROFILES = {"benchmark_resilient", "full"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_benchmark_alias_specs(specs: list[str] | None) -> dict[str, list[str]]:
    """Parse repeatable CANONICAL=ALIAS[,ALIAS...] specifications.

    Aliases are benchmark labels only. They never change the natural UniProt
    candidate query in blind mode and therefore cannot inject a candidate.
    """
    mapping: dict[str, list[str]] = {}
    alias_owner: dict[str, str] = {}
    for raw in specs or []:
        text = str(raw).strip()
        if "=" not in text:
            raise ValueError("benchmark alias must use CANONICAL=ALIAS syntax")
        canonical, values = (part.strip() for part in text.split("=", 1))
        aliases = [item.strip() for item in values.split(",") if item.strip()]
        if not canonical or not aliases:
            raise ValueError("benchmark alias must contain a canonical token and at least one alias")
        canonical_key = _norm_identifier(canonical)
        for alias in aliases:
            alias_key = _norm_identifier(alias)
            owner = alias_owner.get(alias_key)
            if owner is not None and owner != canonical_key:
                raise ValueError(
                    f"benchmark alias {alias!r} is assigned to more than one canonical target"
                )
            alias_owner[alias_key] = canonical_key
            bucket = mapping.setdefault(canonical, [])
            if alias not in bucket and _norm_identifier(alias) != canonical_key:
                bucket.append(alias)
    return mapping


def _norm_identifier(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().casefold())


def _aliases_for(token: str, alias_map: dict[str, list[str]] | None) -> list[str]:
    wanted = _norm_identifier(token)
    out: list[str] = []
    for canonical, aliases in (alias_map or {}).items():
        if _norm_identifier(canonical) != wanted:
            continue
        for alias in aliases:
            if alias and alias not in out:
                out.append(alias)
    return out


def _match_record_values(
    record: dict[str, Any],
    token: str,
    aliases: list[str],
) -> list[tuple[str, str]]:
    identifiers = _identifiers(record)
    matches: list[tuple[str, str]] = []
    canonical_key = _norm_identifier(token)
    if canonical_key in identifiers:
        matches.append(("", f"canonical_{identifiers[canonical_key]}"))
    for alias in aliases:
        key = _norm_identifier(alias)
        if key in identifiers:
            matches.append((alias, f"alias_{identifiers[key]}"))
    return matches


def resolve_natural_benchmark(
    records: list[dict[str, Any]],
    token: str,
    alias_map: dict[str, list[str]] | None = None,
) -> tuple[dict[str, Any] | None, str, str, bool]:
    """Resolve one benchmark against the already-discovered natural seed.

    Resolution is exact across accession, UniProtKB id, gene names and locus
    identifiers. Protein-description matching and substring matching are never
    used. Multiple aliases that point to the same accession remain unambiguous.
    """
    aliases = _aliases_for(token, alias_map)
    by_accession: dict[str, tuple[dict[str, Any], list[tuple[str, str]]]] = {}
    for record in _dedupe(records):
        matches = _match_record_values(record, token, aliases)
        if not matches:
            continue
        accession = _accession(record)
        if accession:
            by_accession[accession] = (record, matches)
    if not by_accession:
        return None, "", "", False
    if len(by_accession) > 1:
        return None, "", "", True
    record, matches = next(iter(by_accession.values()))
    matches.sort(key=lambda item: (0 if item[0] == "" else 1, 0 if "accession" in item[1] else 1))
    alias_used, match_type = matches[0]
    return record, match_type, alias_used, False


def _resolve_conditional_benchmark(
    *,
    token: str,
    aliases: list[str],
    taxon: str,
    proteome: str,
    config: dict[str, Any],
) -> tuple[dict[str, Any] | None, str, str, bool]:
    found: dict[str, tuple[dict[str, Any], str, str]] = {}
    for value, source in [(token, "canonical"), *[(alias, "alias") for alias in aliases]]:
        record, kind = _target(value, taxon, proteome, config)
        if kind == "ambiguous":
            return None, "", "", True
        if record is None:
            continue
        accession = _accession(record)
        if accession:
            found[accession] = (
                record,
                f"{source}_{kind or 'exact_identifier'}",
                "" if source == "canonical" else value,
            )
    if not found:
        return None, "", "", False
    if len(found) > 1:
        return None, "", "", True
    return (*next(iter(found.values())), False)


def select_stage5a2_records(
    *,
    natural_records: list[dict[str, Any]],
    benchmark_mode: str,
    benchmark_candidates: list[str] | None,
    benchmark_aliases: dict[str, list[str]] | None,
    max_candidates: int,
    total_uniprot_results: int | None = None,
    conditional_resolved: dict[str, tuple[dict[str, Any] | None, str, str, bool]] | None = None,
) -> tuple[list[dict[str, Any]], pd.DataFrame, dict[str, Any]]:
    mode, limit = str(benchmark_mode).casefold(), int(max_candidates)
    if mode not in BENCHMARK_MODES or limit < 0:
        raise ValueError("invalid benchmark mode or candidate limit")
    targets = list(dict.fromkeys(str(x).strip() for x in (benchmark_candidates or []) if str(x).strip()))
    natural = _dedupe(natural_records)
    pool = list(natural)
    meta: dict[str, dict[str, Any]] = {}
    for rank, record in enumerate(natural, 1):
        accession = _accession(record)
        meta[accession] = {
            "candidate_seed_accession": accession,
            "protein_id": accession,
            "gene": _gene(record) or accession,
            "benchmark_token": [],
            "benchmark_alias_used": [],
            "benchmark_match_type": [],
            "benchmark_requested": False,
            "benchmark_mode": mode,
            "discovered_naturally": True,
            "benchmark_forced_candidate": False,
            "seed_sources": ["uniprot_paginated_scope_query"],
            "seed_initial_rank": rank,
            "seed_selected_rank": pd.NA,
            "selected_for_scoring": True,
            "exclusion_reason": "",
            "sequence_available": bool(_sequence(record)),
        }

    unresolved: list[str] = []
    ambiguous: list[str] = []
    forced: list[str] = []
    alias_resolved: list[str] = []
    resolved_map = conditional_resolved or {}

    for token in targets:
        record, match_type, alias_used, is_ambiguous = resolve_natural_benchmark(
            natural, token, benchmark_aliases
        )
        if record is None and not is_ambiguous and mode == "conditional":
            record, match_type, alias_used, is_ambiguous = resolved_map.get(
                token, (None, "", "", False)
            )
        if is_ambiguous:
            ambiguous.append(token)
            unresolved.append(token)
            continue
        if record is None:
            unresolved.append(token)
            continue

        accession = _accession(record)
        if accession not in meta:
            if mode != "conditional":
                unresolved.append(token)
                continue
            pool.append(record)
            forced.append(accession)
            meta[accession] = {
                "candidate_seed_accession": accession,
                "protein_id": accession,
                "gene": _gene(record) or accession,
                "benchmark_token": [],
                "benchmark_alias_used": [],
                "benchmark_match_type": [],
                "benchmark_requested": True,
                "benchmark_mode": mode,
                "discovered_naturally": False,
                "benchmark_forced_candidate": True,
                "seed_sources": ["uniprot_targeted_benchmark_query_exact_alias"],
                "seed_initial_rank": pd.NA,
                "seed_selected_rank": pd.NA,
                "selected_for_scoring": True,
                "exclusion_reason": "",
                "sequence_available": bool(_sequence(record)),
            }
        row = meta[accession]
        row["benchmark_requested"] = True
        row["benchmark_token"].append(token)
        row["benchmark_match_type"].append(match_type or "exact_identifier")
        row["benchmark_alias_used"].append(alias_used)
        if alias_used:
            alias_resolved.append(token)

    if mode == "conditional" and limit and len(targets) > limit:
        raise ValueError("max_candidates cannot be smaller than conditional benchmark target count")

    selected = list(pool)
    dropped: list[str] = []
    if limit and len(selected) > limit:
        protected = {acc for acc, row in meta.items() if row["benchmark_requested"]}
        for index in range(len(selected) - 1, -1, -1):
            if len(selected) <= limit:
                break
            accession = _accession(selected[index])
            if accession not in protected:
                dropped.append(accession)
                selected.pop(index)
        if len(selected) > limit:
            raise ValueError("conditional benchmark targets exceed the candidate bound")

    for accession in dropped:
        meta[accession]["selected_for_scoring"] = False
        meta[accession]["exclusion_reason"] = "displaced_by_conditional_benchmark_candidate"
    for rank, record in enumerate(selected, 1):
        meta[_accession(record)]["seed_selected_rank"] = rank

    rows: list[dict[str, Any]] = []
    for record in pool:
        row = dict(meta[_accession(record)])
        row["benchmark_token"] = ";".join(row["benchmark_token"])
        row["benchmark_alias_used"] = ";".join(x for x in row["benchmark_alias_used"] if x)
        row["benchmark_match_type"] = ";".join(row["benchmark_match_type"])
        row["seed_sources"] = ";".join(dict.fromkeys(row["seed_sources"]))
        rows.append(row)

    for token in unresolved:
        if token in ambiguous:
            reason = "ambiguous_exact_benchmark_identity"
        elif mode == "conditional":
            reason = "benchmark_candidate_not_resolved_in_scoped_uniprot"
        elif limit and total_uniprot_results and total_uniprot_results > len(natural):
            reason = "not_observed_within_bounded_scoped_seed"
        else:
            reason = "benchmark_candidate_not_resolved_in_natural_scoped_seed"
        rows.append(
            {
                "candidate_seed_accession": "",
                "protein_id": "",
                "gene": "",
                "benchmark_token": token,
                "benchmark_alias_used": "",
                "benchmark_match_type": "",
                "benchmark_requested": True,
                "benchmark_mode": mode,
                "discovered_naturally": False,
                "benchmark_forced_candidate": False,
                "seed_sources": "",
                "seed_initial_rank": pd.NA,
                "seed_selected_rank": pd.NA,
                "selected_for_scoring": False,
                "exclusion_reason": reason,
                "sequence_available": False,
            }
        )

    summary = {
        "benchmark_mode": mode,
        "benchmark_candidates": targets,
        "benchmark_aliases": {token: _aliases_for(token, benchmark_aliases) for token in targets},
        "benchmark_matching_policy": "exact_identifier_plus_explicit_exact_alias_no_substring_no_protein_description",
        "blind_alias_semantics": "aliases label already-discovered records only; blind mode never performs target-specific retrieval or injection",
        "natural_record_count": len(natural),
        "candidate_count_selected": len(selected),
        "forced_candidate_count": len(forced),
        "forced_candidate_accessions": forced,
        "unresolved_benchmark_candidates": unresolved,
        "ambiguous_benchmark_candidates": ambiguous,
        "alias_resolved_benchmark_candidates": list(dict.fromkeys(alias_resolved)),
        "displaced_natural_candidate_count": len(dropped),
        "displaced_natural_accessions": list(reversed(dropped)),
        "max_candidates_requested": limit,
        "total_uniprot_results": total_uniprot_results,
    }
    return selected, pd.DataFrame(rows), summary


def provider_profile_settings(profile: str) -> dict[str, Any]:
    profile = str(profile).strip().casefold()
    if profile not in PROVIDER_PROFILES:
        raise ValueError("provider_profile must be 'benchmark_resilient' or 'full'")
    if profile == "benchmark_resilient":
        return {
            "profile": profile,
            "enable_interpro": False,
            "enable_literature": False,
            "intentionally_skipped_providers": ["interpro", "literature"],
            "rationale": (
                "InterPro is per-candidate and metadata-only in the current NODOX implementation; "
                "literature retrieval is metadata-only. Both have affects_score=false, so they are skipped "
                "for full-proteome benchmark throughput without changing scoring semantics."
            ),
        }
    return {
        "profile": profile,
        "enable_interpro": True,
        "enable_literature": True,
        "intentionally_skipped_providers": [],
        "rationale": "Use the existing full provider orchestration.",
    }


def run_stage5a2_validation(
    *,
    project_root: Path,
    organism: str,
    taxon_id: int | str,
    proteome_id: str | None = None,
    organism_slug: str | None = None,
    strain: str | None = None,
    strain_slug: str | None = None,
    run_dir: Path | None = None,
    max_candidates: int = 0,
    page_size: int = 500,
    benchmark_mode: str = "blind",
    benchmark_candidates: list[str] | None = None,
    benchmark_aliases: dict[str, list[str]] | None = None,
    provider_profile: str = "benchmark_resilient",
    online_source_mode: str = "online_strict",
    **pipeline_kwargs: Any,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    organism = str(organism).strip()
    taxon = str(taxon_id).strip()
    proteome = _proteome(proteome_id)
    if not organism or not taxon.isdigit():
        raise ValueError("Stage 5A.2 requires organism and numeric taxon_id")
    mode = str(benchmark_mode).casefold()
    if mode not in BENCHMARK_MODES:
        raise ValueError("benchmark_mode must be 'blind' or 'conditional'")

    profile = provider_profile_settings(provider_profile)
    base = (
        Path(run_dir)
        if run_dir
        else root / "results" / "stage5a2_runs" / f"{_slug(organism)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    base = base if base.is_absolute() else root / base
    base.mkdir(parents=True, exist_ok=True)

    config = load_config(root / "config" / "params.yaml")
    natural, stats = fetch_scoped_records(
        taxon_id=taxon,
        proteome_id=proteome,
        config=config,
        max_candidates=max_candidates,
        page_size=page_size,
    )
    targets = list(dict.fromkeys(str(x).strip() for x in (benchmark_candidates or []) if str(x).strip()))

    conditional_resolved: dict[str, tuple[dict[str, Any] | None, str, str, bool]] = {}
    if mode == "conditional":
        for token in targets:
            natural_match = resolve_natural_benchmark(natural, token, benchmark_aliases)
            if natural_match[0] is not None or natural_match[3]:
                conditional_resolved[token] = natural_match
                continue
            conditional_resolved[token] = _resolve_conditional_benchmark(
                token=token,
                aliases=_aliases_for(token, benchmark_aliases),
                taxon=taxon,
                proteome=proteome,
                config=config,
            )

    selected, audit, summary = select_stage5a2_records(
        natural_records=natural,
        benchmark_mode=mode,
        benchmark_candidates=targets,
        benchmark_aliases=benchmark_aliases,
        max_candidates=max_candidates,
        total_uniprot_results=stats.get("total_uniprot_results"),
        conditional_resolved=conditional_resolved,
    )
    audit["proteome_id"] = proteome
    audit["candidate_scope"] = stats["candidate_scope"]
    audit["provider_profile"] = profile["profile"]

    identity_map = {
        "schema_version": "1.0",
        "stage": STAGE,
        "benchmark_mode": mode,
        "matching_policy": summary["benchmark_matching_policy"],
        "blind_alias_semantics": summary["blind_alias_semantics"],
        "targets": [
            {"canonical": token, "aliases": _aliases_for(token, benchmark_aliases)}
            for token in targets
        ],
        "generated_at_utc": _now(),
    }
    identity_path = base / "stage5a2_benchmark_identity_map.json"
    identity_path.write_text(json.dumps(identity_map, indent=2, ensure_ascii=False), encoding="utf-8")

    snapshot_dir = base / "stage5a2_candidate_seed_snapshot"
    snapshot = write_stage5a_candidate_seed_snapshot(
        snapshot_dir=snapshot_dir,
        organism_name=organism,
        taxon_id=taxon,
        records=selected,
        config=config,
        selection_summary={
            **stats,
            **summary,
            "stage": STAGE,
            "proteome_id": proteome or None,
            "provider_profile": profile["profile"],
        },
    )
    snapshot["stage"] = STAGE
    snapshot["stage_name"] = STAGE_NAME
    snapshot["proteome_id"] = proteome or None
    snapshot["benchmark_identity_map"] = str(identity_path)
    (snapshot_dir / "snapshot_manifest.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    pre_audit_path = base / "stage5a2_candidate_seed_audit_pre_pipeline.csv"
    audit.to_csv(pre_audit_path, index=False)
    preflight = {
        "schema_version": "1.0",
        "stage": STAGE,
        "stage_name": STAGE_NAME,
        "organism": organism,
        "strain": strain,
        "taxon_id": taxon,
        "proteome_id": proteome or None,
        "candidate_scope": stats["candidate_scope"],
        "natural_record_count": stats["natural_record_count"],
        "candidate_count_selected": len(selected),
        "benchmark_mode": mode,
        "benchmark_candidates": targets,
        "benchmark_aliases": summary["benchmark_aliases"],
        "alias_resolved_benchmark_candidates": summary["alias_resolved_benchmark_candidates"],
        "unresolved_benchmark_candidates": summary["unresolved_benchmark_candidates"],
        "provider_profile": profile,
        "snapshot_path": str(snapshot_dir),
        "pre_pipeline_audit_path": str(pre_audit_path),
        "generated_at_utc": _now(),
    }
    preflight_path = base / "stage5a2_preflight_manifest.json"
    preflight_path.write_text(json.dumps(preflight, indent=2, ensure_ascii=False), encoding="utf-8")

    pipeline_kwargs = dict(pipeline_kwargs)
    pipeline_kwargs.pop("candidate_seed_snapshot", None)
    pipeline_kwargs.pop("max_candidates", None)
    requested_interpro = bool(pipeline_kwargs.pop("enable_interpro", True))
    requested_literature = bool(pipeline_kwargs.pop("enable_literature", True))
    pipeline_kwargs["enable_interpro"] = requested_interpro and bool(profile["enable_interpro"])
    pipeline_kwargs["enable_literature"] = requested_literature and bool(profile["enable_literature"])

    try:
        core = run_online_only_validation(
            project_root=root,
            organism=organism,
            organism_slug=organism_slug,
            taxon_id=taxon,
            strain=strain,
            strain_slug=strain_slug,
            run_dir=base,
            max_candidates=len(selected),
            candidate_seed_snapshot=snapshot_dir,
            online_source_mode=normalize_provider_mode(online_source_mode),
            **pipeline_kwargs,
        )
    except Exception as exc:
        failure = {
            **preflight,
            "orchestration_status": "failed_before_core_return",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "interpretation": "Candidate discovery completed; failure occurred during provider orchestration before Stage 5A.2 could finalize ranking audit.",
        }
        (base / "stage5a2_failure_manifest.json").write_text(
            json.dumps(failure, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        raise

    workspace = Path(core["workspace"])
    ranking_path = workspace / "results" / "ranking_nodos.csv"
    final = finalize_stage5a_audit(audit, ranking_path)
    audit_path = workspace / "results" / "stage5a2_candidate_seed_audit.csv"
    final.to_csv(audit_path, index=False)

    ranking_exists = ranking_path.exists()
    manifest = {
        "schema_version": "1.0",
        "stage": STAGE,
        "stage_name": STAGE_NAME,
        "organism": organism,
        "strain": strain,
        "taxon_id": taxon,
        "proteome_id": proteome or None,
        "candidate_scope": stats["candidate_scope"],
        "uniprot_query": stats["uniprot_query"],
        "benchmark_mode": mode,
        "benchmark_candidates": targets,
        "benchmark_aliases": summary["benchmark_aliases"],
        "benchmark_matching_policy": summary["benchmark_matching_policy"],
        "blind_alias_semantics": summary["blind_alias_semantics"],
        "provider_profile": profile,
        "natural_record_count": stats["natural_record_count"],
        "candidate_count_selected": len(selected),
        "total_uniprot_results": stats.get("total_uniprot_results"),
        "forced_candidate_count": summary["forced_candidate_count"],
        "unresolved_benchmark_candidates": summary["unresolved_benchmark_candidates"],
        "ambiguous_benchmark_candidates": summary["ambiguous_benchmark_candidates"],
        "alias_resolved_benchmark_candidates": summary["alias_resolved_benchmark_candidates"],
        "snapshot_id": snapshot["snapshot_id"],
        "benchmark_identity_map_path": str(identity_path),
        "audit_path": str(audit_path),
        "pipeline_status": core.get("pipeline_status"),
        "pipeline_error": core.get("pipeline_error", ""),
        "ranking_nodos_exists": ranking_exists,
        "scoring_reached": ranking_exists,
        "scoring_model_changed": False,
        "functional_node_theory_weights_changed": False,
        "experimental_validation_supported": False,
        "generated_at_utc": _now(),
        "notes": [
            "Blind alias mapping labels only records already present in the natural scoped seed; it never retrieves or injects a candidate.",
            "Benchmark-resilient provider profile skips only InterPro and literature metadata by default; both are non-scoring in the current NODOX orchestration.",
            "Missing provider evidence remains unresolved and must not be interpreted as negative biological evidence.",
            "Scoring and Functional Node Theory weights are unchanged.",
        ],
    }
    manifest_path = workspace / "results" / "stage5a2_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    review_package = base / "review_package"
    if review_package.is_dir():
        final.to_csv(review_package / "stage5a2_candidate_seed_audit.csv", index=False)
        (review_package / "stage5a2_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (review_package / "stage5a2_benchmark_identity_map.json").write_text(
            json.dumps(identity_map, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    return {
        **core,
        "stage5a2_manifest": str(manifest_path),
        "stage5a2_audit": str(audit_path),
        "stage5a2_identity_map": str(identity_path),
        "stage5a2_summary": manifest,
    }
