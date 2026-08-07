from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .organism_metadata import load_organism_metadata


SCREENING_FILENAME = "evolutionary_fitness_cost_screened.csv"
STAGE4E_FILENAME = "evolutionary_fitness_cost.csv"
SUPPORTED_MEASUREMENT_TYPES = {
    "relative_fitness_ratio",
    "competition_relative_fitness_ratio",
}
REQUIRED_SCREENING_COLUMNS = {
    "gene",
    "taxon_id",
    "mutation",
    "candidate_scope",
    "assay_context",
    "finding_direction",
    "reported_metric",
    "relative_fitness",
    "measurement_type",
    "source_type",
    "source_database",
    "source_record",
    "mapping_status",
    "evidence_status",
    "method_scope",
}


def _norm(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if text.casefold() in {"", "nan", "none", "null", "<na>", "not_reported"}:
        return ""
    return text


def _norm_lower(value: Any) -> str:
    return _norm(value).casefold()


def _slugify(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _norm_lower(value)).strip("_")


def _effective_mode(config: dict[str, Any]) -> str:
    online = config.get("online_sources", {}) if isinstance(config, dict) else {}
    return str(
        online.get("source_mode_effective")
        or online.get("source_mode")
        or online.get("source_mode_default")
        or ""
    ).strip()


def _curated_enabled(config: dict[str, Any]) -> bool:
    curated = config.get("curated_real_evidence", {}) if isinstance(config, dict) else {}
    return bool(curated.get("enabled", True))


def _curated_root(base_dir: Path, config: dict[str, Any]) -> Path:
    curated = config.get("curated_real_evidence", {}) if isinstance(config, dict) else {}
    configured = Path(str(curated.get("base_dir", "data_curated/organisms")))
    if configured.is_absolute():
        return configured
    candidates = [
        base_dir / configured,
        Path.cwd() / configured,
        Path(__file__).resolve().parents[2] / configured,
    ]
    return next((candidate for candidate in candidates if candidate.exists()), candidates[0])


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


def _screening_path(base_dir: Path, config: dict[str, Any]) -> Path | None:
    root = _curated_root(base_dir, config)
    for key in _organism_keys(base_dir):
        candidate = root / key / SCREENING_FILENAME
        if candidate.exists():
            return candidate
    return None


def _finite_nonnegative(value: Any) -> float | None:
    text = _norm(value)
    if not text:
        return None
    try:
        numeric = float(text)
    except ValueError:
        return None
    if not math.isfinite(numeric) or numeric < 0.0:
        return None
    return numeric


def _has_literature_identifier(row: pd.Series) -> bool:
    return any(_norm(row.get(column)) for column in ("pmid", "doi", "reference"))


def _derived_screening_status(row: pd.Series) -> tuple[str, bool]:
    if _norm_lower(row.get("candidate_scope")) != "protein_candidate":
        return "screening_only_non_protein_candidate_scope", False

    if not _has_literature_identifier(row):
        return "screening_only_missing_literature_identifier", False

    numeric = _finite_nonnegative(row.get("relative_fitness"))
    if numeric is None:
        return "screening_only_missing_numeric_relative_fitness", False

    if _norm_lower(row.get("measurement_type")) not in SUPPORTED_MEASUREMENT_TYPES:
        return "screening_only_unsupported_measurement_type", False

    if _norm_lower(row.get("mapping_status")) not in {
        "exact_gene_and_taxon",
        "exact_accession",
        "exact_locus_tag",
    }:
        return "screening_only_non_direct_mapping", False

    if _norm_lower(row.get("evidence_status")) != "observed":
        return "screening_only_non_observed_evidence", False

    required_provenance = (
        "gene",
        "taxon_id",
        "mutation",
        "assay_context",
        "source_type",
        "source_database",
        "source_record",
        "method_scope",
    )
    missing = [column for column in required_provenance if not _norm(row.get(column))]
    if missing:
        return "screening_only_incomplete_provenance:" + "|".join(missing), False

    return "quantitative_candidate_requires_stage4e_catalog", True


def _production_keys(path: Path) -> set[tuple[str, str, str]]:
    if not path.exists():
        return set()
    try:
        table = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception:  # noqa: BLE001 - audit must fail closed, never change scoring.
        return set()
    keys: set[tuple[str, str, str]] = set()
    for _, row in table.iterrows():
        gene = _norm_lower(row.get("gene"))
        mutation = _norm_lower(row.get("mutation"))
        source = _norm_lower(row.get("source_record")) or _norm_lower(row.get("pmid"))
        if gene and mutation and source:
            keys.add((gene, mutation, source))
    return keys


def _row_key(row: pd.Series) -> tuple[str, str, str]:
    gene = _norm_lower(row.get("gene"))
    mutation = _norm_lower(row.get("mutation"))
    source = _norm_lower(row.get("source_record")) or _norm_lower(row.get("pmid"))
    return gene, mutation, source


def _write_outputs(base_dir: Path, manifest: dict[str, Any], summary: pd.DataFrame) -> None:
    results = base_dir / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "evolutionary_fitness_cost_literature_screening_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    summary.to_csv(
        results / "evolutionary_fitness_cost_literature_screening_summary.csv",
        index=False,
    )


def audit_screened_fitness_cost_literature(
    base_dir: Path,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Audit Stage 4F screened literature without changing candidate scores.

    Screening records are intentionally separated from the Stage 4E production
    catalog. A qualitative fitness defect, advantage, or context dependence is
    useful evidence for curation, but it cannot be converted into a numeric
    `fitness_cost_of_escape` unless a supported quantitative metric is available.

    This function writes audit artifacts only. It never mutates a candidate frame
    and never promotes a screening row into the Stage 4E production catalog.
    """

    mode = _effective_mode(config)
    strict = mode in {"online_strict", "online_only"}
    enabled = _curated_enabled(config) and not strict
    if not enabled:
        reason = "disabled_by_online_strict_policy" if strict else "disabled_by_curated_real_evidence_policy"
        summary = pd.DataFrame()
        _write_outputs(
            base_dir,
            {
                "stage": "4F",
                "status": "disabled",
                "reason": reason,
                "source_mode": mode or "not_reported",
                "scoring_effect": False,
                "screened_record_count": 0,
                "quantitative_candidate_count": 0,
                "promoted_record_count": 0,
            },
            summary,
        )
        return summary

    path = _screening_path(base_dir, config)
    if path is None:
        summary = pd.DataFrame()
        _write_outputs(
            base_dir,
            {
                "stage": "4F",
                "status": "screening_catalog_not_found",
                "source_mode": mode or "not_reported",
                "scoring_effect": False,
                "screened_record_count": 0,
                "quantitative_candidate_count": 0,
                "promoted_record_count": 0,
            },
            summary,
        )
        return summary

    try:
        table = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as exc:  # noqa: BLE001 - audit failure must remain non-scoring.
        summary = pd.DataFrame()
        _write_outputs(
            base_dir,
            {
                "stage": "4F",
                "status": "screening_catalog_read_failed",
                "catalog_path": str(path),
                "error": str(exc),
                "scoring_effect": False,
                "screened_record_count": 0,
                "quantitative_candidate_count": 0,
                "promoted_record_count": 0,
            },
            summary,
        )
        return summary

    table.columns = [str(column).strip() for column in table.columns]
    missing_columns = sorted(REQUIRED_SCREENING_COLUMNS - set(table.columns))
    if missing_columns:
        summary = table.copy()
        summary["derived_screening_status"] = "invalid_screening_schema"
        summary["promotion_candidate"] = False
        summary["stage4e_catalog_match"] = False
        _write_outputs(
            base_dir,
            {
                "stage": "4F",
                "status": "invalid_screening_schema",
                "catalog_path": str(path),
                "missing_columns": missing_columns,
                "scoring_effect": False,
                "screened_record_count": int(len(table)),
                "quantitative_candidate_count": 0,
                "promoted_record_count": 0,
            },
            summary,
        )
        return summary

    production_path = path.parent / STAGE4E_FILENAME
    production_keys = _production_keys(production_path)
    rows: list[dict[str, Any]] = []
    for _, row in table.iterrows():
        status, quantitative = _derived_screening_status(row)
        production_match = _row_key(row) in production_keys
        if quantitative and production_match:
            status = "promoted_to_stage4e_catalog"
        elif quantitative:
            status = "quantitative_candidate_not_promoted"

        record = row.to_dict()
        record.update(
            {
                "derived_screening_status": status,
                "promotion_candidate": bool(quantitative),
                "stage4e_catalog_match": bool(production_match),
                "declared_status_matches_derived": (
                    _norm_lower(row.get("screening_status")) == status.casefold()
                    or (
                        not quantitative
                        and _norm_lower(row.get("screening_status"))
                        == "screening_only_missing_numeric_relative_fitness"
                        and status == "screening_only_missing_numeric_relative_fitness"
                    )
                ),
            }
        )
        rows.append(record)

    summary = pd.DataFrame(rows)
    quantitative_count = int(summary["promotion_candidate"].fillna(False).astype(bool).sum()) if not summary.empty else 0
    promoted_count = int(summary["stage4e_catalog_match"].fillna(False).astype(bool).sum()) if not summary.empty else 0
    _write_outputs(
        base_dir,
        {
            "stage": "4F",
            "status": "screening_audited",
            "catalog_path": str(path),
            "stage4e_catalog_path": str(production_path),
            "source_mode": mode or "not_reported",
            "scoring_effect": False,
            "auto_promotion_enabled": False,
            "screened_record_count": int(len(summary)),
            "quantitative_candidate_count": quantitative_count,
            "promoted_record_count": promoted_count,
            "screening_only_count": int(len(summary) - quantitative_count),
            "interpretation_warning": (
                "Screened literature is not scoring evidence. Qualitative findings remain unresolved for "
                "fitness_cost_of_escape until a supported numeric measurement is curated into the Stage 4E catalog."
            ),
        },
        summary,
    )
    return summary
