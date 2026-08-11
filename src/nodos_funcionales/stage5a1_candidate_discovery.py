from __future__ import annotations

import json, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd

from .config import load_config
from .online.provider_modes import normalize_provider_mode
from .online_only_validation import run_online_only_validation
from .stage5a_candidate_discovery import (
    _accession, _dedupe, _fields, _gene, _http_json, _norm, _sequence,
    finalize_stage5a_audit, write_stage5a_candidate_seed_snapshot,
)

STAGE = "5A.1"
STAGE_NAME = "Stage 5A.1 — Strain-specific candidate discovery and strict benchmark matching"
_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')
_PROTEOME_RE = re.compile(r"^UP\d{9}$", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_") or "organism"


def _proteome(value: str | None) -> str:
    text = str(value or "").strip().upper()
    if text and not _PROTEOME_RE.fullmatch(text):
        raise ValueError("proteome_id must look like UP000000429")
    return text


def _identifiers(record: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for value, kind in ((_accession(record), "accession"), (record.get("uniProtkbId"), "uniprotkb_id")):
        key = _norm(value)
        if key:
            out.setdefault(key, kind)
    for gene in record.get("genes", []) or []:
        if not isinstance(gene, dict):
            continue
        fields = [gene.get("geneName")] + sum((gene.get(k, []) or [] for k in ("synonyms", "orderedLocusNames", "orfNames")), [])
        for item in fields:
            if isinstance(item, dict):
                key = _norm(item.get("value"))
                if key:
                    out.setdefault(key, "gene_exact")
    return out


def strict_benchmark_match(record: dict[str, Any], token: str) -> tuple[bool, str]:
    kind = _identifiers(record).get(_norm(token), "")
    return bool(kind), kind


def _scope(taxon: str, proteome: str) -> str:
    return f"(organism_id:{taxon})" + (f" AND (proteome:{proteome})" if proteome else "")


def fetch_scoped_records(*, taxon_id: str, proteome_id: str | None, config: dict[str, Any], max_candidates: int = 0, page_size: int = 500):
    taxon, proteome, limit = str(taxon_id).strip(), _proteome(proteome_id), int(max_candidates)
    if not taxon.isdigit() or limit < 0 or not 1 <= int(page_size) <= 500:
        raise ValueError("invalid Stage 5A.1 taxon, candidate limit, or page size")
    cfg = config["online_sources"]["uniprot"]
    params = {"query": _scope(taxon, proteome), "format": "json", "size": int(page_size), "fields": _fields(config)}
    url = f"{cfg['provider_base_url']}?{urlencode(params)}"
    records, seen, pages, total = [], set(), 0, None
    while url:
        payload, headers = _http_json(url, config); pages += 1
        if total is None:
            raw = headers.get("x-total-results") or headers.get("X-Total-Results")
            total = int(raw) if raw is not None and str(raw).isdigit() else None
        for record in payload.get("results", []) or []:
            if not isinstance(record, dict):
                continue
            acc = _accession(record)
            if acc and acc not in seen:
                seen.add(acc); records.append(record)
            if limit and len(records) >= limit:
                break
        if limit and len(records) >= limit:
            break
        match = _NEXT_RE.search(str(headers.get("Link") or headers.get("link") or ""))
        url = match.group(1) if match else None
    return records, {"taxon_id": taxon, "proteome_id": proteome or None, "candidate_scope": "proteome_strain_specific" if proteome else "taxon_specific", "uniprot_query": _scope(taxon, proteome), "page_count": pages, "page_size": int(page_size), "natural_record_count": len(records), "total_uniprot_results": total, "full_result_set_requested": limit == 0}


def _matches(records: list[dict[str, Any]], token: str):
    return [(r, strict_benchmark_match(r, token)[1]) for r in records if strict_benchmark_match(r, token)[0]]


def _target(token: str, taxon: str, proteome: str, config: dict[str, Any]):
    cfg = config["online_sources"]["uniprot"]
    safe = token if re.fullmatch(r"[A-Za-z0-9_.-]+", token) else '"' + token.replace('"', '\\"') + '"'
    for term in (f"accession:{safe}", f"gene:{safe}"):
        query = f"({_scope(taxon, proteome)}) AND ({term})"
        url = f"{cfg['provider_base_url']}?{urlencode({'query': query, 'format': 'json', 'size': 25, 'fields': _fields(config)})}"
        try:
            payload, _ = _http_json(url, config)
        except RuntimeError:
            continue
        exact = _matches(_dedupe([x for x in payload.get("results", []) or [] if isinstance(x, dict)]), token)
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            return None, "ambiguous"
    return None, ""


def select_records(*, natural_records: list[dict[str, Any]], benchmark_mode: str, benchmark_candidates: list[str] | None, max_candidates: int, resolved: dict[str, tuple[dict[str, Any] | None, str]] | None = None, total_uniprot_results: int | None = None):
    mode, limit = str(benchmark_mode).casefold(), int(max_candidates)
    if mode not in {"blind", "conditional"} or limit < 0:
        raise ValueError("invalid benchmark mode or candidate limit")
    targets = list(dict.fromkeys(str(x).strip() for x in (benchmark_candidates or []) if str(x).strip()))
    natural, pool, meta = _dedupe(natural_records), [], {}
    for rank, record in enumerate(natural, 1):
        acc = _accession(record); pool.append(record)
        meta[acc] = {"candidate_seed_accession": acc, "protein_id": acc, "gene": _gene(record) or acc, "benchmark_token": [], "benchmark_match_type": [], "benchmark_requested": False, "benchmark_mode": mode, "discovered_naturally": True, "benchmark_forced_candidate": False, "seed_sources": ["uniprot_paginated_scope_query"], "seed_initial_rank": rank, "seed_selected_rank": pd.NA, "selected_for_scoring": True, "exclusion_reason": "", "sequence_available": bool(_sequence(record))}
    unresolved, ambiguous, forced = [], [], []
    for token in targets:
        exact = _matches(natural, token)
        record = kind = None
        if len(exact) == 1:
            record, kind = exact[0]
        elif len(exact) > 1:
            ambiguous.append(token); unresolved.append(token); continue
        elif mode == "conditional":
            record, kind = (resolved or {}).get(token, (None, ""))
            if kind == "ambiguous":
                ambiguous.append(token); unresolved.append(token); continue
        if record is None:
            unresolved.append(token); continue
        acc = _accession(record)
        if acc not in meta:
            pool.append(record); forced.append(acc)
            meta[acc] = {"candidate_seed_accession": acc, "protein_id": acc, "gene": _gene(record) or acc, "benchmark_token": [], "benchmark_match_type": [], "benchmark_requested": True, "benchmark_mode": mode, "discovered_naturally": False, "benchmark_forced_candidate": True, "seed_sources": ["uniprot_targeted_benchmark_query_strict"], "seed_initial_rank": pd.NA, "seed_selected_rank": pd.NA, "selected_for_scoring": True, "exclusion_reason": "", "sequence_available": bool(_sequence(record))}
        meta[acc]["benchmark_requested"] = True; meta[acc]["benchmark_token"].append(token); meta[acc]["benchmark_match_type"].append(kind or "exact_identifier")
    selected, dropped = list(pool), []
    if limit and len(selected) > limit:
        protected = {a for a, row in meta.items() if row["benchmark_requested"]}
        for i in range(len(selected) - 1, -1, -1):
            if len(selected) <= limit: break
            acc = _accession(selected[i])
            if acc not in protected: dropped.append(acc); selected.pop(i)
    for acc in dropped:
        meta[acc]["selected_for_scoring"] = False; meta[acc]["exclusion_reason"] = "displaced_by_conditional_benchmark_candidate"
    for rank, record in enumerate(selected, 1): meta[_accession(record)]["seed_selected_rank"] = rank
    rows = []
    for record in pool:
        row = dict(meta[_accession(record)]); row["benchmark_token"] = ";".join(row["benchmark_token"]); row["benchmark_match_type"] = ";".join(row["benchmark_match_type"]); row["seed_sources"] = ";".join(dict.fromkeys(row["seed_sources"])); rows.append(row)
    for token in unresolved:
        reason = "ambiguous_exact_benchmark_identifier" if token in ambiguous else ("benchmark_candidate_not_resolved_in_scoped_uniprot" if mode == "conditional" else ("not_observed_within_bounded_scoped_seed" if limit and total_uniprot_results and total_uniprot_results > len(natural) else "benchmark_candidate_not_resolved_in_natural_scoped_seed"))
        rows.append({"candidate_seed_accession": "", "protein_id": "", "gene": "", "benchmark_token": token, "benchmark_match_type": "", "benchmark_requested": True, "benchmark_mode": mode, "discovered_naturally": False, "benchmark_forced_candidate": False, "seed_sources": "", "seed_initial_rank": pd.NA, "seed_selected_rank": pd.NA, "selected_for_scoring": False, "exclusion_reason": reason, "sequence_available": False})
    summary = {"benchmark_mode": mode, "benchmark_candidates": targets, "benchmark_matching_policy": "exact_accession_or_exact_gene_identifier_no_substring", "natural_record_count": len(natural), "candidate_count_selected": len(selected), "forced_candidate_count": len(forced), "forced_candidate_accessions": forced, "unresolved_benchmark_candidates": unresolved, "ambiguous_benchmark_candidates": ambiguous, "displaced_natural_candidate_count": len(dropped), "max_candidates_requested": limit, "total_uniprot_results": total_uniprot_results}
    return selected, pd.DataFrame(rows), summary


def run_stage5a1_validation(*, project_root: Path, organism: str, taxon_id: int | str, proteome_id: str | None = None, organism_slug: str | None = None, strain: str | None = None, strain_slug: str | None = None, run_dir: Path | None = None, max_candidates: int = 0, page_size: int = 500, benchmark_mode: str = "blind", benchmark_candidates: list[str] | None = None, online_source_mode: str = "online_strict", **pipeline_kwargs: Any):
    root, organism, taxon, proteome = Path(project_root).resolve(), str(organism).strip(), str(taxon_id).strip(), _proteome(proteome_id)
    if not organism or not taxon.isdigit(): raise ValueError("Stage 5A.1 requires organism and numeric taxon_id")
    base = Path(run_dir) if run_dir else root / "results" / "stage5a1_runs" / f"{_slug(organism)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    base = base if base.is_absolute() else root / base; base.mkdir(parents=True, exist_ok=True)
    config = load_config(root / "config" / "params.yaml")
    natural, stats = fetch_scoped_records(taxon_id=taxon, proteome_id=proteome, config=config, max_candidates=max_candidates, page_size=page_size)
    targets = list(dict.fromkeys(str(x).strip() for x in (benchmark_candidates or []) if str(x).strip()))
    resolved = {token: (_matches(natural, token)[0] if len(_matches(natural, token)) == 1 else _target(token, taxon, proteome, config)) for token in targets} if benchmark_mode == "conditional" else {}
    selected, audit, summary = select_records(natural_records=natural, benchmark_mode=benchmark_mode, benchmark_candidates=targets, max_candidates=max_candidates, resolved=resolved, total_uniprot_results=stats.get("total_uniprot_results"))
    audit["proteome_id"], audit["candidate_scope"] = proteome, stats["candidate_scope"]
    snapshot_dir = base / "stage5a1_candidate_seed_snapshot"
    snapshot = write_stage5a_candidate_seed_snapshot(snapshot_dir=snapshot_dir, organism_name=organism, taxon_id=taxon, records=selected, config=config, selection_summary={**stats, **summary, "stage": STAGE, "proteome_id": proteome or None})
    audit.to_csv(base / "stage5a1_candidate_seed_audit_pre_pipeline.csv", index=False)
    core = run_online_only_validation(project_root=root, organism=organism, organism_slug=organism_slug, taxon_id=taxon, strain=strain, strain_slug=strain_slug, run_dir=base, max_candidates=len(selected), candidate_seed_snapshot=snapshot_dir, online_source_mode=normalize_provider_mode(online_source_mode), **pipeline_kwargs)
    workspace = Path(core["workspace"]); final = finalize_stage5a_audit(audit, workspace / "results" / "ranking_nodos.csv"); audit_path = workspace / "results" / "stage5a1_candidate_seed_audit.csv"; final.to_csv(audit_path, index=False)
    manifest = {"schema_version": "1.0", "stage": STAGE, "stage_name": STAGE_NAME, "organism": organism, "strain": strain, "taxon_id": taxon, "proteome_id": proteome or None, "candidate_scope": stats["candidate_scope"], "uniprot_query": stats["uniprot_query"], "benchmark_mode": benchmark_mode, "benchmark_candidates": targets, "benchmark_matching_policy": summary["benchmark_matching_policy"], "natural_record_count": stats["natural_record_count"], "candidate_count_selected": len(selected), "total_uniprot_results": stats.get("total_uniprot_results"), "forced_candidate_count": summary["forced_candidate_count"], "unresolved_benchmark_candidates": summary["unresolved_benchmark_candidates"], "ambiguous_benchmark_candidates": summary["ambiguous_benchmark_candidates"], "snapshot_id": snapshot["snapshot_id"], "audit_path": str(audit_path), "pipeline_status": core.get("pipeline_status"), "scoring_model_changed": False, "functional_node_theory_weights_changed": False, "generated_at_utc": _now(), "notes": ["Exact accession/gene matching only; no protein-name substring matching.", "Proteome scope is applied to natural and conditional UniProt retrieval.", "Scoring and Functional Node Theory weights are unchanged."]}
    manifest_path = workspace / "results" / "stage5a1_manifest.json"; manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {**core, "stage5a1_manifest": str(manifest_path), "stage5a1_audit": str(audit_path), "stage5a1_summary": manifest}
