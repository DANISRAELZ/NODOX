from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .organism_metadata import load_organism_metadata


FITNESS_COST_VARIABLE = "fitness_cost_of_escape"
AMRFINDER_SHARED_INDEPENDENCE_GROUP = "ncbi_amrfinderplus_curated_point_mutations"
DEFAULT_FITNESS_COST_CONFIG: dict[str, Any] = {
    "enabled": True,
    "base_dir": "data_curated/organisms",
    "filename": "evolutionary_fitness_cost.csv",
    "allowed_measurement_types": [
        "relative_fitness_ratio",
        "competition_relative_fitness_ratio",
    ],
    "allowed_escape_associations": [
        "direct_resistance_mutation",
        "target_site_resistance_mutation",
    ],
    "aggregation_rule": "minimum_cost_across_valid_escape_routes",
}

REQUIRED_COLUMNS = (
    "gene",
    "taxon_id",
    "mutation",
    "escape_association",
    "relative_fitness",
    "measurement_type",
    "assay_context",
    "source_type",
    "source_database",
    "source_record",
    "source_version",
    "retrieved_at",
    "mapping_method",
    "mapping_status",
    "evidence_status",
    "evidence_confidence",
    "method_scope",
)

EXPLICIT_SOURCE_TYPES = {
    "experimental",
    "literature_curated",
    "user_curated",
}
DIRECT_MAPPING_STATUSES = {
    "exact_gene_and_taxon",
    "exact_accession",
    "exact_locus_tag",
}
CONFIDENCE_LEVELS = {"low", "moderate", "high"}

AUDIT_COLUMNS = [
    "fitness_cost_curated_evidence_eligible",
    "fitness_cost_curated_evidence_reason",
    "fitness_cost_curated_valid_record_count",
    "fitness_cost_curated_rejected_record_count",
    "fitness_cost_curated_selected_mutation",
    "fitness_cost_curated_selected_relative_fitness",
    "fitness_cost_curated_aggregation_rule",
    "fitness_cost_curated_source_records",
    "fitness_cost_curated_independence_reason",
]


def _norm(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.casefold() in {"", "nan", "none", "null", "<na>", "not_reported"}:
        return ""
    return text


def _norm_lower(value: Any) -> str:
    return _norm(value).casefold()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value is pd.NA:
        return False
    if isinstance(value, (int, float)):
        try:
            if math.isnan(float(value)):
                return False
        except (TypeError, ValueError):
            pass
        return bool(value)
    return _norm_lower(value) in {"1", "true", "yes", "y"}


def _slugify(value: Any) -> str:
    text = _norm_lower(value)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _finite_nonnegative(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric < 0.0:
        return None
    return numeric


def _iso_timestamp(value: Any) -> bool:
    text = _norm(value)
    if not text:
        return False
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _effective_mode(config: dict[str, Any]) -> str:
    online = config.get("online_sources", {}) if isinstance(config, dict) else {}
    return str(
        online.get("source_mode_effective")
        or online.get("source_mode")
        or online.get("source_mode_default")
        or ""
    ).strip()


def _config(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("evolutionary_fitness_cost_curated", {}) if isinstance(config, dict) else {}
    merged = {**DEFAULT_FITNESS_COST_CONFIG, **(raw if isinstance(raw, dict) else {})}
    merged["allowed_measurement_types"] = {
        str(item).strip().casefold()
        for item in merged.get("allowed_measurement_types", [])
        if str(item).strip()
    }
    merged["allowed_escape_associations"] = {
        str(item).strip().casefold()
        for item in merged.get("allowed_escape_associations", [])
        if str(item).strip()
    }
    return merged


def _organism_keys(base_dir: Path) -> list[str]:
    metadata = load_organism_metadata(base_dir)
    keys: list[str] = []
    for value in [
        metadata.get("organism"),
        metadata.get("organism_canonical_name"),
        f"{metadata.get('organism', '')}_{metadata.get('strain', '')}",
    ]:
        slug = _slugify(value)
        if slug and slug not in keys:
            keys.append(slug)
    return keys or ["not_reported"]


def _catalog_path(base_dir: Path, cfg: dict[str, Any]) -> Path | None:
    root = Path(str(cfg["base_dir"]))
    if not root.is_absolute():
        candidates = [
            base_dir / root,
            Path.cwd() / root,
            Path(__file__).resolve().parents[2] / root,
        ]
        root = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
    for organism_key in _organism_keys(base_dir):
        candidate = root / organism_key / str(cfg["filename"])
        if candidate.exists():
            return candidate
    return None


def _candidate_id(row: pd.Series) -> str:
    for column in ("candidate_id", "protein_id", "protein_id_canonical", "uniprot_accession", "locus_tag"):
        value = _norm(row.get(column))
        if value:
            return value
    return ""


def _existing_explicit_metadata(row: pd.Series) -> bool:
    if _as_bool(row.get(f"{FITNESS_COST_VARIABLE}_is_explicit", False)):
        return True
    return any(
        _norm(row.get(f"{FITNESS_COST_VARIABLE}_{suffix}"))
        for suffix in (
            "source_type",
            "source_database",
            "source_record",
            "source_version",
            "mapping_method",
            "mapping_status",
            "evidence_status",
            "independence_group",
        )
    )


def _pmid_tokens(value: Any) -> set[str]:
    return set(re.findall(r"(?<!\d)\d{6,9}(?!\d)", _norm(value)))


def _shares_amrfinder_literature(candidate: pd.Series, record: pd.Series) -> bool:
    amrfinder_pmids = _pmid_tokens(candidate.get("amrfinder_pubmed_references"))
    if not amrfinder_pmids:
        return False
    record_pmids: set[str] = set()
    for column in ("pmid", "source_record", "reference"):
        record_pmids.update(_pmid_tokens(record.get(column)))
    return bool(amrfinder_pmids & record_pmids)


def _study_independence_group(record: pd.Series) -> str:
    pmids: set[str] = set()
    for column in ("pmid", "source_record", "reference"):
        pmids.update(_pmid_tokens(record.get(column)))
    if pmids:
        return f"fitness_cost_study:PMID_{sorted(pmids)[0]}"

    doi = _norm_lower(record.get("doi"))
    if doi:
        token = re.sub(r"[^a-z0-9_.:-]+", "_", doi).strip("_")
        return f"fitness_cost_study:DOI_{token}"

    source_record = _norm(record.get("source_record"))
    token = re.sub(r"[^A-Za-z0-9_.:-]+", "_", source_record).strip("_")
    return f"fitness_cost_study:{token}"


def _validate_record(
    record: pd.Series,
    *,
    candidate: pd.Series,
    cfg: dict[str, Any],
) -> tuple[bool, str, float | None]:
    missing = [column for column in REQUIRED_COLUMNS if not _norm(record.get(column))]
    if missing:
        return False, "missing_required_fields:" + "|".join(missing), None

    candidate_gene = _norm_lower(candidate.get("gene"))
    record_gene = _norm_lower(record.get("gene"))
    if not candidate_gene or record_gene != candidate_gene:
        return False, "gene_mismatch", None

    candidate_taxon = _norm(candidate.get("taxon_id"))
    record_taxon = _norm(record.get("taxon_id"))
    if not candidate_taxon or record_taxon != candidate_taxon:
        return False, "taxon_mismatch", None

    source_type = _norm_lower(record.get("source_type"))
    if source_type not in EXPLICIT_SOURCE_TYPES:
        return False, "source_type_not_explicit", None

    mapping_status = _norm_lower(record.get("mapping_status"))
    if mapping_status not in DIRECT_MAPPING_STATUSES:
        return False, "mapping_not_direct", None

    if _norm_lower(record.get("evidence_status")) != "observed":
        return False, "evidence_status_not_observed", None

    confidence = _norm_lower(record.get("evidence_confidence"))
    if confidence not in CONFIDENCE_LEVELS:
        return False, "invalid_evidence_confidence", None

    measurement_type = _norm_lower(record.get("measurement_type"))
    if measurement_type not in cfg["allowed_measurement_types"]:
        return False, "unsupported_measurement_type", None

    association = _norm_lower(record.get("escape_association"))
    if association not in cfg["allowed_escape_associations"]:
        return False, "escape_association_not_direct", None

    if not _norm(record.get("mutation")):
        return False, "missing_escape_mutation", None
    if not _norm(record.get("assay_context")):
        return False, "missing_assay_context", None
    if not _norm(record.get("method_scope")):
        return False, "missing_method_scope", None
    if not _iso_timestamp(record.get("retrieved_at")):
        return False, "invalid_retrieved_at", None

    if not any(_norm(record.get(column)) for column in ("pmid", "doi", "reference")):
        return False, "missing_literature_identifier", None

    relative_fitness = _finite_nonnegative(record.get("relative_fitness"))
    if relative_fitness is None:
        return False, "invalid_relative_fitness", None

    cost = max(0.0, min(1.0, 1.0 - relative_fitness))
    return True, "eligible_experimental_fitness_cost", cost


def _set_column(frame: pd.DataFrame, index: Any, column: str, value: Any) -> None:
    if column not in frame.columns:
        frame[column] = pd.NA
    frame.at[index, column] = value


def _write_outputs(
    base_dir: Path,
    *,
    manifest: dict[str, Any],
    summary_rows: list[dict[str, Any]],
) -> None:
    results = base_dir / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "evolutionary_fitness_cost_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    pd.DataFrame(summary_rows).to_csv(
        results / "evolutionary_fitness_cost_summary.csv",
        index=False,
    )


def apply_curated_fitness_cost_evidence(
    base_dir: Path,
    frame: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Materialize strict experimental fitness-cost evidence for Stage 4E.

    The local catalog is intentionally curated rather than scraped. Only direct
    resistance/escape mutations with a WT-normalized relative-fitness ratio and
    complete literature/provenance metadata are eligible. For candidates with
    multiple valid escape routes, the minimum observed fitness cost is selected
    because the least costly documented route is the conservative choice for
    evolutionary escape risk.

    `online_strict`/`online_only` disable this local evidence source. Missing or
    rejected records never become zero-cost or negative evidence. If the chosen
    fitness-cost study shares a PMID with the AMRFinderPlus evidence already
    attached to the candidate, both observations share one independence group.
    """

    result = frame.copy()
    cfg = _config(config)
    mode = _effective_mode(config)
    strict = mode in {"online_strict", "online_only"}
    global_curated_enabled = bool(
        config.get("curated_real_evidence", {}).get("enabled", True)
        if isinstance(config, dict)
        else True
    )

    if strict or not bool(cfg.get("enabled", True)) or not global_curated_enabled:
        if strict:
            reason = "disabled_by_online_strict_policy"
        elif not global_curated_enabled:
            reason = "disabled_by_curated_real_evidence_policy"
        else:
            reason = "disabled_by_configuration"
        _write_outputs(
            base_dir,
            manifest={
                "stage": "4E",
                "enabled": False,
                "reason": reason,
                "source_mode": mode or "not_reported",
                "catalog_path": "",
                "aggregation_rule": cfg["aggregation_rule"],
                "matched_candidate_count": 0,
                "eligible_candidate_count": 0,
            },
            summary_rows=[],
        )
        return result

    path = _catalog_path(base_dir, cfg)
    if path is None:
        _write_outputs(
            base_dir,
            manifest={
                "stage": "4E",
                "enabled": True,
                "reason": "catalog_not_found",
                "source_mode": mode or "not_reported",
                "catalog_path": "",
                "aggregation_rule": cfg["aggregation_rule"],
                "matched_candidate_count": 0,
                "eligible_candidate_count": 0,
            },
            summary_rows=[],
        )
        return result

    try:
        catalog = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001 - fail closed with explicit manifest.
        _write_outputs(
            base_dir,
            manifest={
                "stage": "4E",
                "enabled": True,
                "reason": "catalog_read_failed",
                "catalog_path": str(path),
                "error": str(exc),
                "aggregation_rule": cfg["aggregation_rule"],
                "matched_candidate_count": 0,
                "eligible_candidate_count": 0,
            },
            summary_rows=[],
        )
        return result

    catalog.columns = [str(column).strip() for column in catalog.columns]
    result["fitness_cost_curated_evidence_eligible"] = False
    result["fitness_cost_curated_evidence_reason"] = "no_matching_curated_record"
    result["fitness_cost_curated_valid_record_count"] = 0
    result["fitness_cost_curated_rejected_record_count"] = 0
    result["fitness_cost_curated_selected_mutation"] = ""
    result["fitness_cost_curated_selected_relative_fitness"] = pd.Series(
        [math.nan] * len(result), index=result.index, dtype=float
    )
    result["fitness_cost_curated_aggregation_rule"] = str(cfg["aggregation_rule"])
    result["fitness_cost_curated_source_records"] = ""
    result["fitness_cost_curated_independence_reason"] = "not_evaluated"

    summary_rows: list[dict[str, Any]] = []
    eligible_candidates = 0
    matched_candidates = 0

    for index, candidate in result.iterrows():
        candidate_gene = _norm_lower(candidate.get("gene"))
        candidate_taxon = _norm(candidate.get("taxon_id"))
        if not candidate_gene or not candidate_taxon:
            result.at[index, "fitness_cost_curated_evidence_reason"] = "candidate_missing_gene_or_taxon"
            continue

        subset = catalog[
            catalog.get("gene", pd.Series([""] * len(catalog), index=catalog.index))
            .fillna("")
            .astype(str)
            .str.strip()
            .str.casefold()
            .eq(candidate_gene)
        ]
        if subset.empty:
            continue
        matched_candidates += 1

        valid: list[tuple[pd.Series, float]] = []
        rejected = 0
        rejection_reasons: list[str] = []
        for _, record in subset.iterrows():
            ok, reason, cost = _validate_record(record, candidate=candidate, cfg=cfg)
            if ok and cost is not None:
                valid.append((record, cost))
            else:
                rejected += 1
                rejection_reasons.append(reason)

        result.at[index, "fitness_cost_curated_valid_record_count"] = len(valid)
        result.at[index, "fitness_cost_curated_rejected_record_count"] = rejected
        if not valid:
            result.at[index, "fitness_cost_curated_evidence_reason"] = (
                "all_matching_records_rejected:" + "|".join(sorted(set(rejection_reasons)))
            )
            summary_rows.append(
                {
                    "candidate_id": _candidate_id(candidate),
                    "gene": candidate_gene,
                    "valid_records": 0,
                    "rejected_records": rejected,
                    "selected_cost": math.nan,
                    "status": result.at[index, "fitness_cost_curated_evidence_reason"],
                }
            )
            continue

        # Minimum cost = least costly documented route = conservative escape-risk view.
        chosen_record, chosen_cost = min(valid, key=lambda item: item[1])
        source_records = sorted(
            {
                _norm(record.get("source_record"))
                for record, _ in valid
                if _norm(record.get("source_record"))
            }
        )
        result.at[index, "fitness_cost_curated_evidence_eligible"] = True
        result.at[index, "fitness_cost_curated_evidence_reason"] = "eligible_experimental_fitness_cost"
        result.at[index, "fitness_cost_curated_selected_mutation"] = _norm(chosen_record.get("mutation"))
        result.at[index, "fitness_cost_curated_selected_relative_fitness"] = float(chosen_record["relative_fitness"])
        result.at[index, "fitness_cost_curated_source_records"] = ";".join(source_records)
        eligible_candidates += 1

        if not _existing_explicit_metadata(candidate):
            source_record = _norm(chosen_record.get("source_record"))
            if _shares_amrfinder_literature(candidate, chosen_record):
                independence_group = AMRFINDER_SHARED_INDEPENDENCE_GROUP
                independence_reason = "shared_pubmed_with_amrfinderplus_same_independence_group"
            else:
                independence_group = _study_independence_group(chosen_record)
                independence_reason = "study_identifier_derived_independence_group"
            result.at[index, "fitness_cost_curated_independence_reason"] = independence_reason

            method_scope = (
                f"{_norm(chosen_record.get('method_scope'))}; Stage4E transformation: "
                "fitness_cost=max(0,min(1,1-relative_fitness)); "
                "aggregation=minimum_cost_across_valid_escape_routes"
            )
            notes = (
                f"Stage4E curated experimental fitness cost; mutation={_norm(chosen_record.get('mutation'))}; "
                f"escape_association={_norm(chosen_record.get('escape_association'))}; "
                f"measurement_type={_norm(chosen_record.get('measurement_type'))}; "
                f"relative_fitness={float(chosen_record['relative_fitness']):.6g}; "
                f"assay_context={_norm(chosen_record.get('assay_context'))}; "
                f"pmid={_norm(chosen_record.get('pmid')) or 'not_reported'}; "
                f"doi={_norm(chosen_record.get('doi')) or 'not_reported'}; "
                f"independence_reason={independence_reason}; "
                "the least costly valid documented route is selected conservatively."
            )

            result.at[index, FITNESS_COST_VARIABLE] = float(chosen_cost)
            _set_column(result, index, f"{FITNESS_COST_VARIABLE}_is_explicit", True)
            _set_column(
                result,
                index,
                f"{FITNESS_COST_VARIABLE}_source_type",
                _norm_lower(chosen_record.get("source_type")),
            )
            _set_column(
                result,
                index,
                f"{FITNESS_COST_VARIABLE}_source_database",
                _norm(chosen_record.get("source_database")),
            )
            _set_column(result, index, f"{FITNESS_COST_VARIABLE}_source_record", source_record)
            _set_column(
                result,
                index,
                f"{FITNESS_COST_VARIABLE}_source_version",
                _norm(chosen_record.get("source_version")),
            )
            _set_column(
                result,
                index,
                f"{FITNESS_COST_VARIABLE}_retrieved_at",
                _norm(chosen_record.get("retrieved_at")),
            )
            _set_column(
                result,
                index,
                f"{FITNESS_COST_VARIABLE}_mapping_method",
                _norm_lower(chosen_record.get("mapping_method")),
            )
            _set_column(
                result,
                index,
                f"{FITNESS_COST_VARIABLE}_mapping_status",
                _norm_lower(chosen_record.get("mapping_status")),
            )
            _set_column(result, index, f"{FITNESS_COST_VARIABLE}_evidence_status", "observed")
            _set_column(
                result,
                index,
                f"{FITNESS_COST_VARIABLE}_evidence_confidence",
                _norm_lower(chosen_record.get("evidence_confidence")),
            )
            _set_column(
                result,
                index,
                f"{FITNESS_COST_VARIABLE}_independence_group",
                independence_group,
            )
            _set_column(result, index, f"{FITNESS_COST_VARIABLE}_method_scope", method_scope)
            _set_column(result, index, f"{FITNESS_COST_VARIABLE}_taxon_id", candidate_taxon)
            _set_column(result, index, f"{FITNESS_COST_VARIABLE}_notes", notes)
        else:
            result.at[index, "fitness_cost_curated_evidence_reason"] = (
                "eligible_but_existing_canonical_fitness_cost_evidence_preserved"
            )
            result.at[index, "fitness_cost_curated_independence_reason"] = (
                "existing_canonical_evidence_preserved"
            )

        summary_rows.append(
            {
                "candidate_id": _candidate_id(candidate),
                "gene": candidate_gene,
                "valid_records": len(valid),
                "rejected_records": rejected,
                "selected_cost": float(chosen_cost),
                "selected_mutation": _norm(chosen_record.get("mutation")),
                "selected_source_record": _norm(chosen_record.get("source_record")),
                "independence_reason": result.at[
                    index, "fitness_cost_curated_independence_reason"
                ],
                "status": result.at[index, "fitness_cost_curated_evidence_reason"],
            }
        )

    _write_outputs(
        base_dir,
        manifest={
            "stage": "4E",
            "enabled": True,
            "reason": "catalog_processed",
            "source_mode": mode or "not_reported",
            "catalog_path": str(path),
            "catalog_row_count": int(len(catalog)),
            "aggregation_rule": cfg["aggregation_rule"],
            "allowed_measurement_types": sorted(cfg["allowed_measurement_types"]),
            "allowed_escape_associations": sorted(cfg["allowed_escape_associations"]),
            "matched_candidate_count": matched_candidates,
            "eligible_candidate_count": eligible_candidates,
            "independence_policy": (
                "Study groups are derived from PMID/DOI/source record. If the selected fitness-cost "
                "record shares a PMID with candidate AMRFinderPlus evidence, both use the AMRFinderPlus "
                "independence group."
            ),
            "interpretation_warning": (
                "Fitness-cost evidence is mutation- and assay-specific. It is not a universal gene property; "
                "absence of curated evidence is not evidence of zero cost."
            ),
        },
        summary_rows=summary_rows,
    )
    return result
