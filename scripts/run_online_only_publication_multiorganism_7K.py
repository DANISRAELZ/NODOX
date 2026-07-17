from __future__ import annotations

import argparse
import csv
import json
import platform
import shutil
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.online_only_validation import run_online_only_validation
from src.nodos_funcionales.provider_contracts import PROVIDER_CONTRACTS, ProviderContract


PHASE = "7K_online_only_publication_multiorganism"
DEFAULT_7K_ORGANISMS = (
    {
        "organism_key": "pseudomonas_aeruginosa",
        "organism": "Pseudomonas aeruginosa",
        "organism_slug": "pseudomonas_aeruginosa",
        "taxon_id": 287,
    },
    {
        "organism_key": "escherichia_coli",
        "organism": "Escherichia coli",
        "organism_slug": "escherichia_coli",
        "taxon_id": 562,
    },
    {
        "organism_key": "mycobacterium_tuberculosis",
        "organism": "Mycobacterium tuberculosis",
        "organism_slug": "mycobacterium_tuberculosis",
        "taxon_id": 1773,
    },
)


def run_publication_multiorganism_7k(
    project_root: Path,
    output_dir: Path | None = None,
    timestamp: str | None = None,
    max_candidates: int = 25,
    continue_on_error: bool = True,
    organism_runner: Callable[..., dict[str, Any]] = run_online_only_validation,
) -> dict[str, Any]:
    project_root = Path(project_root)
    run_id = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(output_dir) if output_dir else project_root / "results" / "online_only_multiorganism_7K" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    started_at = _utc_now()
    organism_summaries: list[dict[str, Any]] = []
    provider_matrix: list[dict[str, Any]] = []
    candidate_summary: list[dict[str, Any]] = []

    for organism_config in DEFAULT_7K_ORGANISMS:
        organism_key = str(organism_config["organism_key"])
        organism_dir = run_dir / organism_key
        organism_dir.mkdir(parents=True, exist_ok=True)
        raw_run_dir = organism_dir / "raw_online_only_run"
        try:
            result = organism_runner(
                project_root=project_root,
                organism=organism_config["organism"],
                organism_slug=organism_config["organism_slug"],
                taxon_id=organism_config["taxon_id"],
                run_dir=raw_run_dir,
                max_candidates=max_candidates,
                enable_string=True,
                enable_interpro=True,
                enable_literature=True,
                online_source_mode="online_optional",
                taxon_resolution_mode="online_optional",
                no_write_taxon_cache=True,
            )
        except Exception as exc:  # noqa: BLE001 - publication audit must preserve failures.
            result = {"pipeline_status": "runner_exception", "pipeline_error": str(exc)}
            if not continue_on_error:
                raise
        package = _package_dir(raw_run_dir)
        workspace_results = raw_run_dir / "workspace" / "results"
        seed_manifest = _read_json(_first_existing(package / "online_only_candidate_seed_manifest.json", workspace_results / "online_only_candidate_seed_manifest.json"))
        provider_audit = _read_csv(_first_existing(package / "online_only_provider_audit.csv", workspace_results / "online_only_provider_audit.csv"))
        ranking_rows = _read_csv(
            _first_existing(
                package / "ranking_nodos_phase3.csv",
                package / "ranking_nodos.csv",
                workspace_results / "ranking_nodos_phase3.csv",
                workspace_results / "ranking_nodos.csv",
            )
        )
        provider_rows = _provider_rows_for_organism(organism_config, seed_manifest, provider_audit, result)
        accepted_rows = [row for row in provider_rows if _as_bool(row["evidence_inferred"])]
        degraded_rows = [row for row in provider_rows if not _as_bool(row["evidence_inferred"])]
        seed_ok = _as_int(seed_manifest.get("candidate_count", 0)) > 0 and _as_bool(seed_manifest.get("api_success"))
        ranking_allowed = bool(seed_ok)
        if not ranking_allowed:
            ranking_rows = []

        _write_json(organism_dir / "candidate_seed_manifest.json", seed_manifest or _missing_seed_manifest(result))
        _write_csv(organism_dir / "provider_status.csv", provider_rows)
        _write_json(organism_dir / "provider_status.json", {"providers": provider_rows})
        _write_csv(organism_dir / "accepted_evidence_summary.csv", accepted_rows)
        _write_csv(organism_dir / "degraded_provider_summary.csv", degraded_rows)
        _write_csv(organism_dir / "online_only_candidates.csv", ranking_rows)
        _write_json(
            organism_dir / "provenance_manifest.json",
            _organism_provenance_manifest(organism_config, result, seed_manifest, provider_rows, raw_run_dir),
        )
        (organism_dir / "online_only_review.md").write_text(
            _organism_review(organism_config, result, seed_manifest, provider_rows, len(ranking_rows), ranking_allowed),
            encoding="utf-8",
        )

        organism_summary = {
            "organism": organism_config["organism"],
            "organism_key": organism_key,
            "taxon_id": organism_config["taxon_id"],
            "pipeline_status": result.get("pipeline_status", "not_reported"),
            "candidate_seed_count": _as_int(seed_manifest.get("candidate_count", 0)),
            "ranking_allowed": ranking_allowed,
            "candidate_count_reported": len(ranking_rows),
            "accepted_provider_count": len(accepted_rows),
            "degraded_provider_count": len(degraded_rows),
            "organism_dir": str(organism_dir),
        }
        organism_summaries.append(organism_summary)
        candidate_summary.append(organism_summary)
        provider_matrix.extend(provider_rows)

    _write_csv(run_dir / "multiorganism_provider_matrix_7K.csv", provider_matrix)
    _write_json(run_dir / "multiorganism_provider_matrix_7K.json", {"phase": PHASE, "providers": provider_matrix})
    _write_csv(run_dir / "multiorganism_candidate_summary_7K.csv", candidate_summary)
    (run_dir / "multiorganism_online_only_review_7K.md").write_text(
        _multiorganism_review(organism_summaries, provider_matrix),
        encoding="utf-8",
    )
    (run_dir / "publication_limitations_7K.md").write_text(_publication_limitations(), encoding="utf-8")
    manifest = {
        "phase": PHASE,
        "run_dir": str(run_dir),
        "started_at_utc": started_at,
        "completed_at_utc": _utc_now(),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "openssl_version": ssl.OPENSSL_VERSION,
        "certifi_path": _certifi_path(),
        "organisms": organism_summaries,
        "contracts_used": sorted(PROVIDER_CONTRACTS),
        "candidate_seed_only_blocking": True,
        "scoring_modified": False,
        "ranking_rules_modified": False,
        "gui_modified": False,
    }
    _write_json(run_dir / "reproducibility_manifest_7K.json", manifest)
    return {"run_dir": str(run_dir), "manifest": manifest, "provider_matrix": provider_matrix, "organisms": organism_summaries}


def _provider_rows_for_organism(
    organism: dict[str, Any],
    seed_manifest: dict[str, Any],
    provider_audit: list[dict[str, str]],
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    audit_by_contract = _audit_by_contract(provider_audit)
    rows = []
    for provider_key, contract in PROVIDER_CONTRACTS.items():
        audit = audit_by_contract.get(provider_key, {})
        if provider_key == "candidate_seed":
            row = _candidate_seed_row(organism, seed_manifest, contract, result)
        else:
            row = _contract_row(organism, provider_key, contract, audit)
        rows.append(row)
    return rows


def _candidate_seed_row(
    organism: dict[str, Any],
    seed: dict[str, Any],
    contract: ProviderContract,
    result: dict[str, Any],
) -> dict[str, Any]:
    count = _as_int(seed.get("candidate_count", 0))
    success = _as_bool(seed.get("api_success")) and count > 0
    degraded = contract.degraded_statuses[0]
    return {
        "organism": organism["organism"],
        "taxon_id": organism["taxon_id"],
        "provider": contract.provider_name,
        "final_status": seed.get("retrieval_status", "connected_structured_payload") if success else degraded.final_status,
        "payload_type": "json" if success else "unresolved",
        "evidence_inferred": str(success).lower(),
        "affects_score": "false",
        "blocks_ranking": str(not success).lower(),
        "number_of_records": count,
        "conservative_reason": "Candidate seed defines the online-only universe." if success else degraded.conservative_reason,
        "publication_limitation": contract.limitation_for_manuscript,
        "provenance_required": str(contract.provenance_required).lower(),
        "pipeline_status": result.get("pipeline_status", "not_reported"),
    }


def _contract_row(
    organism: dict[str, Any],
    provider_key: str,
    contract: ProviderContract,
    audit: dict[str, str],
) -> dict[str, Any]:
    success = _as_bool(audit.get("api_success"))
    record_count = _as_int(audit.get("retrieved_record_count", audit.get("matched_candidate_count", 0)))
    if success:
        final_status = str(audit.get("retrieval_status") or next(iter(contract.accepted_statuses)))
        payload_type = next(iter(contract.accepted_payload_types), "structured")
        evidence_inferred = record_count > 0
        reason = "Structured provider payload accepted under Phase 7J contract."
    else:
        degraded = _select_degradation(contract, str(audit.get("retrieval_status", "")))
        final_status = str(audit.get("retrieval_status") or degraded.final_status)
        payload_type = _payload_type_from_status(final_status)
        evidence_inferred = False
        reason = degraded.conservative_reason
    return {
        "organism": organism["organism"],
        "taxon_id": organism["taxon_id"],
        "provider": contract.provider_name,
        "final_status": final_status,
        "payload_type": payload_type,
        "evidence_inferred": str(evidence_inferred).lower(),
        "affects_score": "false",
        "blocks_ranking": "false",
        "number_of_records": record_count,
        "conservative_reason": reason,
        "publication_limitation": contract.limitation_for_manuscript,
        "provenance_required": str(contract.provenance_required).lower(),
        "pipeline_status": audit.get("pipeline_status", ""),
    }


def _audit_by_contract(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    mapped: dict[str, dict[str, str]] = {}
    for row in rows:
        text = " ".join(str(row.get(key, "")) for key in ("layer_key", "provider_name", "provider_function")).lower()
        if "candidate_seed" in text:
            mapped["candidate_seed"] = row
        elif "string" in text:
            mapped["string"] = row
        elif "interpro" in text or "host_annotation" in text:
            mapped["interpro"] = row
        elif "literature" in text or "europe" in text:
            mapped["europe_pmc"] = row
        elif "bvbrc" in text or "strain_conservation" in text:
            mapped["bvbrc"] = row
        elif "vfdb" in text or "virulence" in text:
            mapped["vfdb"] = row
        elif "deg" in text or "essentiality" in text:
            mapped["deg"] = row
        elif "uniprot" in text or "localization" in text:
            mapped["uniprot"] = row
    return mapped


def _select_degradation(contract: ProviderContract, status: str):
    lowered = status.lower()
    for item in contract.degraded_statuses:
        if item.final_status.lower() in lowered:
            return item
    for token in ("ssl", "network", "empty", "html", "zip", "not_found", "invalid", "unresolved"):
        if token in lowered:
            for item in contract.degraded_statuses:
                if token in item.final_status:
                    return item
    return contract.degraded_statuses[0]


def _payload_type_from_status(status: str) -> str:
    lowered = status.lower()
    if "html" in lowered:
        return "html"
    if "zip" in lowered or "archive" in lowered:
        return "zip"
    if "empty" in lowered:
        return "empty"
    if "ssl" in lowered:
        return "ssl_error"
    if "network" in lowered or "timeout" in lowered:
        return "network_error"
    if "text" in lowered:
        return "unexpected_text"
    return "unresolved"


def _organism_review(
    organism: dict[str, Any],
    result: dict[str, Any],
    seed: dict[str, Any],
    provider_rows: list[dict[str, Any]],
    candidate_count: int,
    ranking_allowed: bool,
) -> str:
    accepted = [row for row in provider_rows if _as_bool(row["evidence_inferred"])]
    degraded = [row for row in provider_rows if not _as_bool(row["evidence_inferred"])]
    return "\n".join(
        [
            f"# Online-only review 7K: {organism['organism']}",
            "",
            f"- Taxon id: `{organism['taxon_id']}`",
            f"- Pipeline status: `{result.get('pipeline_status', 'not_reported')}`",
            f"- Candidate seed count: `{_as_int(seed.get('candidate_count', 0))}`",
            f"- Ranking allowed: `{ranking_allowed}`",
            f"- Candidate rows exported: `{candidate_count}`",
            f"- Structured evidence providers: `{'; '.join(row['provider'] for row in accepted) or 'none'}`",
            f"- Degraded providers: `{'; '.join(row['provider'] for row in degraded) or 'none'}`",
            "",
            "This run is computational and online-only. It does not clinically validate therapeutic targets. Score highness is not experimental validation. Degraded providers and empty payloads remain unresolved and are not biological absence.",
        ]
    )


def _organism_provenance_manifest(
    organism: dict[str, Any],
    result: dict[str, Any],
    seed: dict[str, Any],
    provider_rows: list[dict[str, Any]],
    raw_run_dir: Path,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "organism": organism["organism"],
        "taxon_id": organism["taxon_id"],
        "raw_run_dir": str(raw_run_dir),
        "pipeline_status": result.get("pipeline_status", "not_reported"),
        "candidate_seed_manifest": seed,
        "provider_contracts_used": sorted(PROVIDER_CONTRACTS),
        "provider_statuses": provider_rows,
        "no_user_curated_evidence_added": True,
        "no_hidden_snapshots_used": True,
    }


def _multiorganism_review(organisms: list[dict[str, Any]], providers: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# Multiorganism online-only review 7K",
            "",
            "This package compares Pseudomonas aeruginosa, Escherichia coli and Mycobacterium tuberculosis under the same online-only provider contracts.",
            "",
            _markdown_table(organisms),
            "",
            "## Conservative interpretation",
            "",
            "- This run does not clinically validate therapeutic targets.",
            "- High score does not equal experimental validation.",
            "- Degraded provider status is not negative biological evidence.",
            "- Empty payload is not biological absence.",
            "- Online availability at retrieval time limits completeness.",
            "- candidate_seed is the only strict blocking layer.",
            "",
            "## Provider Matrix",
            "",
            _markdown_table(providers),
        ]
    )


def _publication_limitations() -> str:
    return "\n".join(
        [
            "# Publication limitations 7K",
            "",
            "- This online-only run is computational and does not validate targets clinically.",
            "- Score highness is not experimental validation.",
            "- Provider degradation is unresolved operational status, not evidence against a candidate.",
            "- Empty payloads do not imply biological absence.",
            "- HTML, unsupported ZIP, free text, SSL errors, network errors and invalid payloads do not generate positive evidence.",
            "- Non-blocking external layers can enrich confidence only when structured payloads satisfy Phase 7J contracts.",
            "- candidate_seed is the only strict blocking layer.",
            "- VFDB needs a stable programmatic route before automatic evidence use.",
            "- DEG needs a formal ZIP/download adapter before automatic evidence use.",
            "- BV-BRC should be validated with real structured queries before strain-level manuscript claims.",
        ]
    )


def _package_dir(run_dir: Path) -> Path:
    return run_dir / "review_package"


def _missing_seed_manifest(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "api_success": False,
        "candidate_count": 0,
        "retrieval_status": "candidate_seed_unresolved",
        "fallback_reason": result.get("pipeline_error", "candidate_seed_missing"),
    }


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
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


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No records generated."
    columns = list(rows[0])
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")).replace("|", "\\|") for column in columns) + " |")
    return "\n".join(lines)


def _first_existing(*paths: Path) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def _as_bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def _as_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _certifi_path() -> str:
    try:
        import certifi

        return str(certifi.where())
    except Exception:  # noqa: BLE001 - optional runtime metadata.
        return "not_available"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase 7K online-only publication multiorganism audit.")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--timestamp")
    parser.add_argument("--max-candidates", type=int, default=25)
    parser.add_argument("--stop-on-error", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_publication_multiorganism_7k(
        project_root=PROJECT_ROOT,
        output_dir=args.output_dir,
        timestamp=args.timestamp,
        max_candidates=args.max_candidates,
        continue_on_error=not args.stop_on_error,
    )
    print(json.dumps(result["manifest"], indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
