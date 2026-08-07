from __future__ import annotations

import math
from typing import Any

import pandas as pd


BV_BRC_SOURCE_TOKENS = ("bvbrc", "bv-brc", "patric")
BV_BRC_ALLOWED_LAYER_SOURCE_TYPES = {"external", "cache"}
BV_BRC_INELIGIBLE_GENERATORS = {
    "packaged_demo",
    "mixed_external_and_demo",
    "proxy_default",
}
BV_BRC_CONSTRAINT_VARIABLE = "evolutionary_constraint_score"
BV_BRC_ADAPTER_VERSION = "nodox_bvbrc_constraint_adapter_v1"
BV_BRC_PROVIDER_PROVENANCE_FIELDS = (
    "conservation_source_record",
    "conservation_source_version",
    "conservation_retrieved_at",
    "conservation_mapping_method",
    "conservation_mapping_status",
    "conservation_evidence_status",
    "conservation_evidence_confidence",
    "conservation_independence_group",
    "conservation_method_scope",
    "conservation_taxon_id",
    "conservation_provider_retrieval_status",
    "conservation_provider_query_cache_key",
    "conservation_provider_source_used",
)


def _norm(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null", "<na>"}:
        return ""
    return text


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def _finite01(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric < 0.0 or numeric > 1.0:
        return None
    return numeric


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        try:
            if math.isnan(float(value)):
                return False
        except (TypeError, ValueError):
            pass
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _contains_bvbrc(value: Any) -> bool:
    normalized = _norm_lower(value).replace("_", "-")
    return any(token in normalized for token in BV_BRC_SOURCE_TOKENS)


def _row_candidate_id(row: pd.Series) -> str:
    for column in (
        "candidate_id",
        "protein_id",
        "accession",
        "uniprot_accession",
        "locus_tag",
    ):
        if column in row.index and (value := _norm(row.get(column))):
            return value
    return ""


def _existing_canonical_payload(row: pd.Series) -> bool:
    if _finite01(row.get(BV_BRC_CONSTRAINT_VARIABLE)) is not None:
        return True
    prefix = BV_BRC_CONSTRAINT_VARIABLE
    if _as_bool(row.get(f"{prefix}_is_explicit")):
        return True
    return any(
        _norm(row.get(f"{prefix}_{suffix}"))
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


def _bvbrc_row_eligibility(row: pd.Series) -> tuple[bool, str]:
    layer_source_type = _norm_lower(row.get("strain_conservation_source_type"))
    source_name = row.get("strain_conservation_source_name")
    database = row.get("conservation_database")
    generated_by = _norm_lower(row.get("strain_conservation_generated_by"))
    retrieval_status = _norm_lower(row.get("strain_conservation_retrieval_status"))
    is_external = _as_bool(row.get("strain_conservation_is_external"))
    is_cached = _as_bool(row.get("strain_conservation_is_cached"))

    if _as_bool(row.get("strain_conservation_is_proxy")):
        return False, "strain_conservation_layer_is_proxy"
    if generated_by in BV_BRC_INELIGIBLE_GENERATORS or "demo" in generated_by:
        return False, "strain_conservation_layer_is_demo_or_mixed_demo"
    if layer_source_type not in BV_BRC_ALLOWED_LAYER_SOURCE_TYPES:
        return False, "strain_conservation_not_external_or_provider_cache"
    if layer_source_type == "external" and not is_external:
        return False, "external_source_type_without_external_provenance_flag"
    if layer_source_type == "cache" and not is_cached:
        return False, "cache_source_type_without_cache_provenance_flag"
    if not (_contains_bvbrc(source_name) or _contains_bvbrc(database)):
        return False, "strain_conservation_source_not_identified_as_bvbrc"
    if retrieval_status in {
        "missing",
        "unresolved",
        "provider_failed",
        "mapping_failed",
        "not_found",
        "verified_empty_payload",
        "response_truncated_no_evidence",
        "paginated_response_incomplete",
    }:
        return False, f"strain_conservation_retrieval_not_usable:{retrieval_status}"

    candidate_id = _row_candidate_id(row)
    gene = _norm(row.get("gene"))
    taxon_id = _norm(row.get("taxon_id"))
    if not candidate_id:
        return False, "missing_candidate_id"
    if not gene:
        return False, "missing_gene_for_exact_gene_and_taxon_mapping"
    if not taxon_id:
        return False, "missing_taxon_id_for_exact_gene_and_taxon_mapping"

    missing_provenance = [
        column
        for column in BV_BRC_PROVIDER_PROVENANCE_FIELDS
        if not _norm(row.get(column))
    ]
    if missing_provenance:
        return False, "missing_original_bvbrc_provenance:" + "|".join(missing_provenance)

    provider_taxon = _norm(row.get("conservation_taxon_id"))
    if provider_taxon != taxon_id:
        return False, "bvbrc_provider_taxon_mismatch"
    if _norm_lower(row.get("conservation_mapping_status")) != "exact_gene_and_taxon":
        return False, "bvbrc_mapping_not_direct_gene_and_taxon"
    if _norm_lower(row.get("conservation_evidence_status")) != "observed":
        return False, "bvbrc_provider_evidence_not_observed"
    if _norm_lower(row.get("conservation_provider_retrieval_status")) != "api_real":
        return False, "bvbrc_original_retrieval_not_api_real"

    if _as_bool(row.get("core_genome_presence_is_placeholder")):
        return False, "core_genome_presence_is_placeholder"
    if _as_bool(row.get("allelic_conservation_is_placeholder")):
        return False, "allelic_conservation_is_placeholder"

    presence = _finite01(row.get("core_genome_presence"))
    allelic = _finite01(row.get("allelic_conservation"))
    if presence is None:
        return False, "missing_or_invalid_core_genome_presence"
    if allelic is None:
        return False, "missing_or_invalid_allelic_conservation"
    return True, "eligible_bvbrc_strain_conservation"


def _set_if_missing(frame: pd.DataFrame, column: str, index: Any, value: Any) -> None:
    if column not in frame.columns:
        frame[column] = pd.NA
    frame.at[index, column] = value


def materialize_provider_evolutionary_evidence(frame: pd.DataFrame) -> pd.DataFrame:
    """Materialize conservative provider-derived Stage 4A evidence.

    Stage 4C currently recognizes one BV-BRC-derived canonical variable:
    `evolutionary_constraint_score`. It intentionally reduces the four historical
    conservation fields to two non-duplicate inputs: core-genome presence and
    allelic conservation. `strain_coverage_score` duplicates the current BV-BRC
    presence calculation and `variant_burden` is the inverse of allelic
    conservation, so neither is counted as an additional evolutionary variable
    or independence group.

    Existing canonical evolutionary evidence is never overwritten. Provider rows
    that cannot prove source class, original provider-query provenance, direct
    gene+taxon mapping, or non-placeholder measurements remain audit-only and do
    not request explicit evidence.
    """

    result = frame.copy()
    result["bvbrc_evolutionary_evidence_eligible"] = False
    result["bvbrc_evolutionary_evidence_reason"] = "not_evaluated"
    result["bvbrc_evolutionary_constraint_score"] = pd.Series(
        [math.nan] * len(result), index=result.index, dtype=float
    )

    required_signal_columns = {"core_genome_presence", "allelic_conservation"}
    if not required_signal_columns.issubset(result.columns):
        result["bvbrc_evolutionary_evidence_reason"] = (
            "missing_bvbrc_conservation_signal_columns"
        )
        return result

    for index, row in result.iterrows():
        eligible, reason = _bvbrc_row_eligibility(row)
        result.at[index, "bvbrc_evolutionary_evidence_reason"] = reason
        if not eligible:
            continue

        presence = float(row["core_genome_presence"])
        allelic = float(row["allelic_conservation"])
        constraint = max(0.0, min(1.0, 0.50 * presence + 0.50 * allelic))
        result.at[index, "bvbrc_evolutionary_constraint_score"] = constraint
        result.at[index, "bvbrc_evolutionary_evidence_eligible"] = True

        if _existing_canonical_payload(row):
            result.at[index, "bvbrc_evolutionary_evidence_reason"] = (
                "eligible_but_existing_canonical_evidence_preserved"
            )
            continue

        database = _norm(row.get("conservation_database")) or "BV-BRC"
        layer_source_type = _norm_lower(row.get("strain_conservation_source_type"))
        source_name = _norm(row.get("strain_conservation_source_name")) or "bvbrc_real"
        provider_source_used = _norm_lower(row.get("conservation_provider_source_used"))
        if layer_source_type == "external" and provider_source_used == "api_real":
            source_type = "real_external_online"
        elif layer_source_type == "external":
            source_type = "real_external"
        else:
            source_type = "computed_from_real_data"

        provider_method_scope = _norm(row.get("conservation_method_scope"))
        method_scope = (
            f"{provider_method_scope}; Stage4C transformation: "
            "constraint=0.5*core_genome_presence+0.5*allelic_conservation; "
            "strain_coverage_score excluded as duplicate of presence in current provider; "
            "variant_burden excluded as inverse of allelic_conservation"
        )
        notes = (
            f"Stage4C adapter={BV_BRC_ADAPTER_VERSION}; source_name={source_name}; "
            "original provider retrieval timestamp, query record, mapping and "
            "snapshot marker were preserved from the BV-BRC manifest; all correlated "
            "BV-BRC transformations share the original single independence group."
        )

        prefix = BV_BRC_CONSTRAINT_VARIABLE
        result.at[index, prefix] = constraint
        _set_if_missing(result, f"{prefix}_is_explicit", index, True)
        _set_if_missing(result, f"{prefix}_source_type", index, source_type)
        _set_if_missing(result, f"{prefix}_source_database", index, database)
        _set_if_missing(
            result,
            f"{prefix}_source_record",
            index,
            _norm(row.get("conservation_source_record")),
        )
        _set_if_missing(
            result,
            f"{prefix}_source_version",
            index,
            _norm(row.get("conservation_source_version")),
        )
        _set_if_missing(
            result,
            f"{prefix}_retrieved_at",
            index,
            _norm(row.get("conservation_retrieved_at")),
        )
        _set_if_missing(
            result,
            f"{prefix}_mapping_method",
            index,
            _norm(row.get("conservation_mapping_method")),
        )
        _set_if_missing(
            result,
            f"{prefix}_mapping_status",
            index,
            _norm_lower(row.get("conservation_mapping_status")),
        )
        _set_if_missing(
            result,
            f"{prefix}_evidence_status",
            index,
            _norm_lower(row.get("conservation_evidence_status")),
        )
        _set_if_missing(
            result,
            f"{prefix}_evidence_confidence",
            index,
            _norm_lower(row.get("conservation_evidence_confidence")),
        )
        _set_if_missing(
            result,
            f"{prefix}_independence_group",
            index,
            _norm(row.get("conservation_independence_group")),
        )
        _set_if_missing(result, f"{prefix}_method_scope", index, method_scope)
        _set_if_missing(
            result,
            f"{prefix}_taxon_id",
            index,
            _norm(row.get("conservation_taxon_id")),
        )
        _set_if_missing(result, f"{prefix}_notes", index, notes)

    return result
