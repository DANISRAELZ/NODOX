from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from .config import load_config
from .online.provider_modes import normalize_provider_mode
from .online_http import get_ssl_context
from .online_only_validation import run_online_only_validation

STAGE5A_NAME = "Stage 5A — High-recall candidate discovery and benchmark audit"
BENCHMARK_MODES = {"blind", "conditional"}
_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_") or "organism"


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _accession(record: dict[str, Any]) -> str:
    return str(record.get("primaryAccession") or record.get("uniProtkbId") or "").strip()


def _sequence(record: dict[str, Any]) -> str:
    value = record.get("sequence")
    return str(value.get("value") or "").replace("\n", "").strip() if isinstance(value, dict) else ""


def _gene(record: dict[str, Any]) -> str:
    for item in record.get("genes", []) or []:
        if not isinstance(item, dict):
            continue
        primary = item.get("geneName")
        if isinstance(primary, dict) and primary.get("value"):
            return str(primary["value"]).strip()
        for key in ("synonyms", "orderedLocusNames", "orfNames"):
            for alias in item.get(key, []) or []:
                if isinstance(alias, dict) and alias.get("value"):
                    return str(alias["value"]).strip()
    return ""


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_strings(item))
        return out
    if isinstance(value, dict):
        out = []
        for item in value.values():
            out.extend(_strings(item))
        return out
    return []


def _aliases(record: dict[str, Any]) -> list[str]:
    values = [_accession(record), str(record.get("uniProtkbId") or "")]
    values.extend(_strings(record.get("genes", [])))
    values.extend(_strings(record.get("proteinDescription", {})))
    return [value.strip() for value in values if str(value).strip()]


def _matches(record: dict[str, Any], token: str) -> bool:
    wanted = _norm(token)
    if not wanted:
        return False
    for alias in _aliases(record):
        candidate = _norm(alias)
        if candidate == wanted or (len(wanted) >= 4 and wanted in candidate):
            return True
    return False


def _dedupe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        accession = _accession(record)
        if accession and accession not in seen:
            seen.add(accession)
            out.append(record)
    return out


def _fields(config: dict[str, Any]) -> str:
    fields = [x.strip() for x in str(config["online_sources"]["uniprot"].get("fields") or "").split(",") if x.strip()]
    if "sequence" not in fields:
        fields.append("sequence")
    return ",".join(fields)


def _http_json(url: str, config: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    cfg = config["online_sources"]["uniprot"]
    if sys.platform == "win32" and os.environ.get("NODOS_ALLOW_WINDOWS_REAL_HTTPS") != "1":
        raise URLError("windows_real_https_requires_diagnostic_opt_in")
    error: Exception | None = None
    for attempt in range(int(cfg["provider_max_retries"]) + 1):
        request = Request(url, headers={"User-Agent": str(cfg["provider_user_agent"]), "Accept": "application/json"})
        try:
            context = None if sys.platform == "win32" else get_ssl_context()
            with urlopen(request, timeout=float(cfg["provider_timeout_seconds"]), context=context) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("UniProt response must be a JSON object")
                return payload, response.headers
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            error = exc
            retryable = not isinstance(exc, HTTPError) or exc.code in {429, 500, 502, 503, 504}
            if attempt >= int(cfg["provider_max_retries"]) or not retryable:
                break
            time.sleep(float(cfg["provider_backoff_seconds"]) * (attempt + 1))
    raise RuntimeError(f"UniProt Stage 5A retrieval failed: {error}") from error


def fetch_high_recall_uniprot_records(
    *, taxon_id: str, config: dict[str, Any], max_candidates: int = 0, page_size: int = 500
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    taxon = str(taxon_id).strip()
    limit = int(max_candidates)
    if not taxon.isdigit():
        raise ValueError("taxon_id must contain digits only for Stage 5A")
    if limit < 0:
        raise ValueError("max_candidates must be zero or positive")
    if not 1 <= int(page_size) <= 500:
        raise ValueError("page_size must be between 1 and 500")
    cfg = config["online_sources"]["uniprot"]
    params = {"query": f"(organism_id:{taxon})", "format": "json", "size": int(page_size), "fields": _fields(config)}
    url: str | None = f"{cfg['provider_base_url']}?{urlencode(params)}"
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    pages = 0
    total: int | None = None
    while url:
        payload, headers = _http_json(url, config)
        pages += 1
        if total is None:
            raw = headers.get("x-total-results") or headers.get("X-Total-Results")
            total = int(raw) if raw is not None and str(raw).isdigit() else None
        for record in payload.get("results", []) or []:
            if not isinstance(record, dict):
                continue
            accession = _accession(record)
            if accession and accession not in seen:
                seen.add(accession)
                records.append(record)
            if limit and len(records) >= limit:
                break
        if limit and len(records) >= limit:
            break
        match = _NEXT_RE.search(str(headers.get("Link") or headers.get("link") or ""))
        url = match.group(1) if match else None
    return records, {
        "taxon_id": taxon,
        "page_size": int(page_size),
        "page_count": pages,
        "max_candidates_requested": limit,
        "natural_record_count": len(records),
        "total_uniprot_results": total,
        "full_result_set_requested": limit == 0,
    }


def _target_record(token: str, taxon_id: str, config: dict[str, Any]) -> dict[str, Any] | None:
    cfg = config["online_sources"]["uniprot"]
    safe = token if re.fullmatch(r"[A-Za-z0-9_.-]+", token) else '"' + token.replace('"', '\\"') + '"'
    for term in (f"accession:{safe}", f"gene:{safe}", safe):
        query = f"(organism_id:{taxon_id}) AND ({term})"
        url = f"{cfg['provider_base_url']}?{urlencode({'query': query, 'format': 'json', 'size': 25, 'fields': _fields(config)})}"
        try:
            payload, _ = _http_json(url, config)
        except RuntimeError:
            continue
        candidates = _dedupe([x for x in payload.get("results", []) or [] if isinstance(x, dict)])
        exact = next((record for record in candidates if _matches(record, token)), None)
        if exact is not None:
            return exact
        if candidates:
            return candidates[0]
    return None


def select_stage5a_records(
    *,
    natural_records: list[dict[str, Any]],
    benchmark_mode: str,
    benchmark_candidates: list[str] | None = None,
    max_candidates: int = 0,
    resolved_benchmark_records: dict[str, dict[str, Any] | None] | None = None,
    total_uniprot_results: int | None = None,
) -> tuple[list[dict[str, Any]], pd.DataFrame, dict[str, Any]]:
    mode = str(benchmark_mode).casefold()
    if mode not in BENCHMARK_MODES:
        raise ValueError("benchmark_mode must be 'blind' or 'conditional'")
    limit = int(max_candidates)
    if limit < 0:
        raise ValueError("max_candidates must be zero or positive")
    targets = list(dict.fromkeys(str(x).strip() for x in (benchmark_candidates or []) if str(x).strip()))
    natural = _dedupe(natural_records)
    pool = list(natural)
    meta: dict[str, dict[str, Any]] = {}
    for rank, record in enumerate(natural, 1):
        accession = _accession(record)
        meta[accession] = {
            "candidate_seed_accession": accession, "protein_id": accession, "gene": _gene(record) or accession,
            "benchmark_token": [], "benchmark_requested": False, "benchmark_mode": mode,
            "discovered_naturally": True, "benchmark_forced_candidate": False,
            "seed_sources": ["uniprot_paginated_organism_query"], "seed_initial_rank": rank,
            "seed_selected_rank": pd.NA, "selected_for_scoring": True, "exclusion_reason": "",
            "sequence_available": bool(_sequence(record)),
        }
    unresolved: list[str] = []
    forced: list[str] = []
    resolved = resolved_benchmark_records or {}
    for token in targets:
        record = next((x for x in natural if _matches(x, token)), None)
        if record is None and mode == "conditional":
            record = resolved.get(token)
        if record is None or not _accession(record):
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
                "candidate_seed_accession": accession, "protein_id": accession, "gene": _gene(record) or accession,
                "benchmark_token": [], "benchmark_requested": True, "benchmark_mode": mode,
                "discovered_naturally": False, "benchmark_forced_candidate": True,
                "seed_sources": ["uniprot_targeted_benchmark_query"], "seed_initial_rank": pd.NA,
                "seed_selected_rank": pd.NA, "selected_for_scoring": True, "exclusion_reason": "",
                "sequence_available": bool(_sequence(record)),
            }
        elif mode == "conditional" and resolved.get(token) is not None:
            meta[accession]["seed_sources"].append("uniprot_targeted_benchmark_resolution")
        meta[accession]["benchmark_requested"] = True
        meta[accession]["benchmark_token"].append(token)
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
        row["seed_sources"] = ";".join(dict.fromkeys(row["seed_sources"]))
        rows.append(row)
    for token in unresolved:
        reason = "benchmark_candidate_not_resolved_in_uniprot" if mode == "conditional" else (
            "not_observed_within_bounded_seed" if limit and total_uniprot_results and total_uniprot_results > len(natural)
            else "benchmark_candidate_not_resolved_in_natural_seed"
        )
        rows.append({
            "candidate_seed_accession": "", "protein_id": "", "gene": "", "benchmark_token": token,
            "benchmark_requested": True, "benchmark_mode": mode, "discovered_naturally": False,
            "benchmark_forced_candidate": False, "seed_sources": "", "seed_initial_rank": pd.NA,
            "seed_selected_rank": pd.NA, "selected_for_scoring": False, "exclusion_reason": reason,
            "sequence_available": False,
        })
    return selected, pd.DataFrame(rows), {
        "benchmark_mode": mode, "benchmark_candidates": targets, "natural_record_count": len(natural),
        "candidate_count_selected": len(selected), "forced_candidate_count": len(forced),
        "forced_candidate_accessions": forced, "unresolved_benchmark_candidates": unresolved,
        "displaced_natural_candidate_count": len(dropped), "displaced_natural_accessions": list(reversed(dropped)),
        "max_candidates_requested": limit, "total_uniprot_results": total_uniprot_results,
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_stage5a_candidate_seed_snapshot(
    *, snapshot_dir: Path, organism_name: str, taxon_id: str, records: list[dict[str, Any]],
    config: dict[str, Any], selection_summary: dict[str, Any]
) -> dict[str, Any]:
    records = _dedupe(records)
    if not records:
        raise ValueError("Stage 5A candidate seed is empty")
    missing = [_accession(x) for x in records if not _sequence(x)]
    if missing:
        raise ValueError("Stage 5A candidate records lack sequence data: " + ", ".join(missing[:10]))
    snapshot_dir = Path(snapshot_dir)
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    snapshot_dir.mkdir(parents=True)
    records_path = snapshot_dir / "uniprot_seed_records.json"
    records_path.write_text(json.dumps({"results": records, "stage5a": selection_summary}, indent=2, ensure_ascii=False), encoding="utf-8")
    provider = str(config["online_sources"]["uniprot"]["provider_name"])
    database = str(config["online_sources"]["uniprot"]["database_label"]) + ":candidate_seed"
    seed = pd.DataFrame([{
        "protein_id": _accession(x), "gene": _gene(x) or _accession(x), "essential": pd.NA, "evidence": "",
        "database": database, "essentiality_status": "unresolved_online_seed",
        "evidence_source_type": "online_external_candidate_discovery", "candidate_seed_provider": provider,
        "candidate_seed_accession": _accession(x),
        "candidate_seed_note": "Stage 5A high-recall UniProt candidate seed; essentiality is not validated by this row.",
    } for x in records])
    seed_path = snapshot_dir / "candidate_seed.csv"
    seed.to_csv(seed_path, index=False)
    fasta: list[str] = []
    for record in records:
        accession, uid = _accession(record), str(record.get("uniProtkbId") or _accession(record))
        entry_type = str(record.get("entryType") or "").casefold()
        prefix = "sp" if "reviewed" in entry_type and "unreviewed" not in entry_type else "tr"
        fasta.append(f">{prefix}|{accession}|{uid}")
        seq = _sequence(record)
        fasta.extend(seq[i:i + 60] for i in range(0, len(seq), 60))
    fasta_path = snapshot_dir / "candidate_proteins.faa"
    fasta_path.write_text("\n".join(fasta) + "\n", encoding="utf-8")
    files = {name: {"sha256": _sha(snapshot_dir / name), "size_bytes": (snapshot_dir / name).stat().st_size}
             for name in ("uniprot_seed_records.json", "candidate_seed.csv", "candidate_proteins.faa")}
    digest = hashlib.sha256("\n".join(_accession(x) for x in records).encode()).hexdigest()[:16]
    manifest = {
        "schema_version": "1.0", "snapshot_id": f"stage5a_{taxon_id}_{digest}",
        "snapshot_type": "versioned_uniprot_candidate_seed", "stage": "5A", "stage_name": STAGE5A_NAME,
        "organism_name": organism_name, "taxon_id": str(taxon_id), "candidate_count": len(records),
        "provider_name": provider, "selection_summary": selection_summary, "files": files,
        "generated_at_utc": _utc_now(),
        "notes": ["Conditional candidates are diagnostic and do not count as blind discovery successes."],
    }
    (snapshot_dir / "snapshot_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def finalize_stage5a_audit(audit: pd.DataFrame, ranking_path: Path) -> pd.DataFrame:
    out = audit.copy()
    out["ranking_match"], out["final_rank"], out["final_score"], out["final_score_column"], out["functional_node_theory_rank"] = False, pd.NA, pd.NA, "", pd.NA
    if not ranking_path.exists():
        return out
    ranking = pd.read_csv(ranking_path)
    if ranking.empty:
        return out
    rank_col = next((x for x in ("final_rank", "rank", "nodo_rank", "ranking_position") if x in ranking.columns), None)
    score_col = next((x for x in ("final_score", "therapeutic_priority_score", "nodo_score", "functional_node_theory_score", "score") if x in ranking.columns), None)
    fnt_ranks = pd.to_numeric(ranking["functional_node_theory_score"], errors="coerce").rank(method="min", ascending=False, na_option="bottom") if "functional_node_theory_score" in ranking.columns else None
    lookup: dict[str, int] = {}
    for idx, row in ranking.iterrows():
        for col in ("candidate_seed_accession", "protein_id", "accession", "gene"):
            if col in ranking.columns and _norm(row.get(col)):
                lookup.setdefault(_norm(row.get(col)), idx)
    for idx, row in out.iterrows():
        if not bool(row.get("selected_for_scoring", False)):
            continue
        match = next((lookup[key] for key in (_norm(row.get("candidate_seed_accession")), _norm(row.get("protein_id")), _norm(row.get("gene"))) if key in lookup), None)
        if match is None:
            continue
        out.at[idx, "ranking_match"] = True
        out.at[idx, "final_rank"] = ranking.loc[match, rank_col] if rank_col else list(ranking.index).index(match) + 1
        if score_col:
            out.at[idx, "final_score"], out.at[idx, "final_score_column"] = ranking.loc[match, score_col], score_col
        if fnt_ranks is not None and pd.notna(fnt_ranks.loc[match]):
            out.at[idx, "functional_node_theory_rank"] = int(fnt_ranks.loc[match])
    return out


def run_stage5a_validation(
    *, project_root: Path, organism: str, taxon_id: int | str, organism_slug: str | None = None,
    strain: str | None = None, strain_slug: str | None = None, run_dir: Path | None = None,
    max_candidates: int = 0, page_size: int = 500, benchmark_mode: str = "blind",
    benchmark_candidates: list[str] | None = None, online_source_mode: str = "online_strict", **pipeline_kwargs: Any,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    organism = str(organism).strip()
    taxon = str(taxon_id).strip()
    if not organism or not taxon.isdigit():
        raise ValueError("Stage 5A requires organism and numeric taxon_id")
    mode = str(benchmark_mode).casefold()
    if mode not in BENCHMARK_MODES:
        raise ValueError("benchmark_mode must be 'blind' or 'conditional'")
    base = Path(run_dir) if run_dir else root / "results" / "stage5a_runs" / f"{_slug(organism)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    base = base if base.is_absolute() else root / base
    base.mkdir(parents=True, exist_ok=True)
    config = load_config(root / "config" / "params.yaml")
    natural, stats = fetch_high_recall_uniprot_records(taxon_id=taxon, config=config, max_candidates=max_candidates, page_size=page_size)
    targets = list(dict.fromkeys(str(x).strip() for x in (benchmark_candidates or []) if str(x).strip()))
    resolved: dict[str, dict[str, Any] | None] = {}
    if mode == "conditional":
        for token in targets:
            natural_match = next((x for x in natural if _matches(x, token)), None)
            resolved[token] = natural_match or _target_record(token, taxon, config)
    selected, audit, summary = select_stage5a_records(
        natural_records=natural, benchmark_mode=mode, benchmark_candidates=targets, max_candidates=max_candidates,
        resolved_benchmark_records=resolved, total_uniprot_results=stats.get("total_uniprot_results"),
    )
    snapshot_dir = base / "stage5a_candidate_seed_snapshot"
    snapshot = write_stage5a_candidate_seed_snapshot(
        snapshot_dir=snapshot_dir, organism_name=organism, taxon_id=taxon, records=selected,
        config=config, selection_summary={**stats, **summary},
    )
    audit.to_csv(base / "stage5a_candidate_seed_audit_pre_pipeline.csv", index=False)
    pipeline_kwargs = dict(pipeline_kwargs)
    pipeline_kwargs.pop("max_candidates", None)
    pipeline_kwargs.pop("candidate_seed_snapshot", None)
    core = run_online_only_validation(
        project_root=root, organism=organism, organism_slug=organism_slug, taxon_id=taxon, strain=strain,
        strain_slug=strain_slug, run_dir=base, max_candidates=len(selected), candidate_seed_snapshot=snapshot_dir,
        online_source_mode=normalize_provider_mode(online_source_mode), **pipeline_kwargs,
    )
    workspace = Path(core["workspace"])
    final_audit = finalize_stage5a_audit(audit, workspace / "results" / "ranking_nodos.csv")
    audit_path = workspace / "results" / "stage5a_candidate_seed_audit.csv"
    final_audit.to_csv(audit_path, index=False)
    total = stats.get("total_uniprot_results")
    manifest = {
        "schema_version": "1.0", "stage": "5A", "stage_name": STAGE5A_NAME, "organism": organism,
        "taxon_id": taxon, "benchmark_mode": mode, "benchmark_candidates": targets,
        "candidate_discovery_policy": "high_recall_paginated_uniprot", "max_candidates_requested": int(max_candidates),
        "max_candidates_semantics": "0 means full UniProt organism result set", "page_size": int(page_size),
        "total_uniprot_results": total, "natural_record_count": stats["natural_record_count"],
        "candidate_count_selected": len(selected),
        "candidate_coverage_fraction": len(selected) / total if isinstance(total, int) and total > 0 else None,
        "forced_candidate_count": summary["forced_candidate_count"],
        "forced_candidate_accessions": summary["forced_candidate_accessions"],
        "unresolved_benchmark_candidates": summary["unresolved_benchmark_candidates"],
        "displaced_natural_candidate_count": summary["displaced_natural_candidate_count"],
        "snapshot_id": snapshot["snapshot_id"], "snapshot_path": str(snapshot_dir), "audit_path": str(audit_path),
        "pipeline_status": core.get("pipeline_status"), "scoring_model_changed": False,
        "functional_node_theory_weights_changed": False, "experimental_validation_supported": False,
        "generated_at_utc": _utc_now(),
        "notes": [
            "Stage 5A changes candidate discovery and benchmark auditing only; it does not recalibrate scoring.",
            "Conditional forced candidates must not be counted as blind discovery successes.",
            "Provider-specific downstream caps can still limit enrichment breadth after discovery.",
        ],
    }
    manifest_path = workspace / "results" / "stage5a_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    review = base / "review_package"
    if review.exists():
        shutil.copy2(audit_path, review / audit_path.name)
        shutil.copy2(manifest_path, review / manifest_path.name)
    return {**core, "stage5a": {"manifest": manifest, "manifest_path": str(manifest_path), "candidate_seed_audit_path": str(audit_path), "candidate_seed_snapshot_path": str(snapshot_dir)}}
