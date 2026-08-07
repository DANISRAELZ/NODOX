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

AMRFINDER_SOURCE_TOKENS = (
    "amrfinder",
    "amrfinderplus",
    "ncbi_amrfinderplus",
)
AMRFINDER_ALLOWED_LAYER_SOURCE_TYPES = {"external", "cache"}
AMRFINDER_INELIGIBLE_GENERATORS = {
    "packaged_demo",
    "mixed_external_and_demo",
    "proxy_default",
}
AMRFINDER_RESISTANCE_VARIABLE = "resistance_emergence_risk"
AMRFINDER_ADAPTER_VERSION = "nodox_amrfinderplus_resistance_adapter_v1"
AMRFINDER_PROVIDER_PROVENANCE_FIELDS = (
    "amrfinder_source_record",
    "amrfinder_source_version",
    "amrfinder_retrieved_at",
    "amrfinder_catalog_sha256",
    "amrfinder_mapping_method",
    "amrfinder_mapping_status",
    "amrfinder_evidence_status",
    "amrfinder_evidence_confidence",
    "amrfinder_independence_group",
    "amrfinder_method_scope",
    "amrfinder_taxon_id",
    "amrfinder_organism_group",
    "amrfinder_mutation_symbols",
    "amrfinder_mutation_count",
    "amrfinder_provider_retrieval_status",
    "amrfinder_provider_source_used",
    "amrfinder_provider_url",
)

EVIDENCE_METADATA_SUFFIXES = (
    "source_type",
    "source_database",
    "source_record",
    "source_version",
    "retrieved_at",
    "mapping_method",
    "mapping_status",
    "evidence_status",
    "evidence_confidence",
    "independence_group",
    "method_scope",
    "taxon_id",
    "notes",
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


def _contains_token(value: Any, tokens: tuple[str, ...]) -> bool:
    normalized = _norm_lower(value).replace("_", "-")
    normalized_compact = normalized.replace("-", "")
    return any(
        token.replace("_", "-") in normalized
        or token.replace("_", "").replace("-", "") in normalized_compact
        for token in tokens
    )


def _contains_bvbrc(value: Any) -> bool:
    return _contains_token(value, BV_BRC_SOURCE_TOKENS)


def _contains_amrfinder(value: Any) -> bool:
    return _contains_token(value, AMRFINDER_SOURCE_TOKENS)


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


def _existing_variable_evidence_metadata(row: pd.Series, variable: str) -> bool:
    if _as_bool(row.get(f"{variable}_is_explicit")):
        return True
    return any(
        _norm(row.get(f"{variable}_{suffix}"))
        for suffix in EVIDENCE_METADATA_SUFFIXES
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


def _amrfinder_row_eligibility(row: pd.Series) -> tuple[bool, str]:
    risk = _finite01(row.get(AMRFINDER_RESISTANCE_VARIABLE))
    if risk is None or not math.isclose(risk, 1.0, rel_tol=0.0, abs_tol=1e-12):
        return False, "no_positive_amrfinder_point_mutation_evidence"

    layer_source_type = _norm_lower(row.get("evolutionary_escape_risk_source_type"))
    source_name = row.get("evolutionary_escape_risk_source_name")
    database = row.get("evolutionary_escape_risk_database")
    evidence_source = row.get("evolutionary_escape_risk_evidence_source")
    generated_by = _norm_lower(row.get("evolutionary_escape_risk_generated_by"))
    is_external = _as_bool(row.get("evolutionary_escape_risk_is_external"))
    is_cached = _as_bool(row.get("evolutionary_escape_risk_is_cached"))

    if _as_bool(row.get("evolutionary_escape_risk_is_proxy")):
        return False, "evolutionary_escape_risk_layer_is_proxy"
    if generated_by in AMRFINDER_INELIGIBLE_GENERATORS or "demo" in generated_by:
        return False, "evolutionary_escape_risk_layer_is_demo_or_mixed_demo"
    if layer_source_type not in AMRFINDER_ALLOWED_LAYER_SOURCE_TYPES:
        return False, "amrfinder_layer_not_external_or_provider_cache"
    if layer_source_type == "external" and not is_external:
        return False, "amrfinder_external_source_without_external_flag"
    if layer_source_type == "cache" and not is_cached:
        return False, "amrfinder_cache_source_without_cache_flag"
    if not (
        _contains_amrfinder(source_name)
        or _contains_amrfinder(database)
        or _contains_amrfinder(evidence_source)
    ):
        return False, "evolutionary_escape_risk_source_not_identified_as_amrfinderplus"

    candidate_id = _row_candidate_id(row)
    gene = _norm(row.get("gene"))
    taxon_id = _norm(row.get("taxon_id"))
    if not candidate_id:
        return False, "missing_candidate_id"
    if not gene:
        return False, "missing_gene_for_amrfinder_mapping"
    if not taxon_id:
        return False, "missing_taxon_id_for_amrfinder_mapping"

    missing_provenance = [
        column
        for column in AMRFINDER_PROVIDER_PROVENANCE_FIELDS
        if not _norm(row.get(column))
    ]
    if missing_provenance:
        return False, "missing_original_amrfinder_provenance:" + "|".join(missing_provenance)

    if _norm(row.get("amrfinder_taxon_id")) != taxon_id:
        return False, "amrfinder_provider_taxon_mismatch"
    if _norm_lower(row.get("amrfinder_mapping_status")) != "exact_gene_and_taxon":
        return False, "amrfinder_mapping_not_direct_gene_and_taxon"
    if _norm_lower(row.get("amrfinder_evidence_status")) != "observed":
        return False, "amrfinder_evidence_not_observed"
    if _norm_lower(row.get("amrfinder_provider_source_used")) != "api_real":
        return False, "amrfinder_original_source_not_api_real"
    if _norm_lower(row.get("amrfinder_provider_retrieval_status")) != "api_real":
        return False, "amrfinder_original_retrieval_not_api_real"

    mutation_count = pd.to_numeric(
        pd.Series([row.get("amrfinder_mutation_count")]), errors="coerce"
    ).iloc[0]
    if pd.isna(mutation_count) or float(mutation_count) < 1.0:
        return False, "amrfinder_positive_row_without_mutation_count"
    if not _norm(row.get("amrfinder_mutation_symbols")):
        return False, "amrfinder_positive_row_without_mutation_symbols"
    if len(_norm(row.get("amrfinder_catalog_sha256"))) != 64:
        return False, "amrfinder_invalid_catalog_sha256"
    return True, "eligible_amrfinderplus_point_mutation_evidence"


def _set_if_missing(frame: pd.DataFrame, column: str, index: Any, value: Any) -> None:
    if column not in frame.columns:
        frame[column] = pd.NA
    frame.at[index, column] = value


def _materialize_bvbrc_evidence(result: pd.DataFrame) -> pd.DataFrame:
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


def _materialize_amrfinder_evidence(result: pd.DataFrame) -> pd.DataFrame:
    result["amrfinder_evolutionary_evidence_eligible"] = False
    result["amrfinder_evolutionary_evidence_reason"] = "not_evaluated"
    result["amrfinder_resistance_emergence_risk"] = pd.Series(
        [math.nan] * len(result), index=result.index, dtype=float
    )

    if AMRFINDER_RESISTANCE_VARIABLE not in result.columns:
        result["amrfinder_evolutionary_evidence_reason"] = (
            "missing_amrfinder_resistance_signal"
        )
        return result

    for index, row in result.iterrows():
        eligible, reason = _amrfinder_row_eligibility(row)
        result.at[index, "amrfinder_evolutionary_evidence_reason"] = reason
        if not eligible:
            continue

        risk = float(row[AMRFINDER_RESISTANCE_VARIABLE])
        result.at[index, "amrfinder_resistance_emergence_risk"] = risk
        result.at[index, "amrfinder_evolutionary_evidence_eligible"] = True

        if _existing_variable_evidence_metadata(row, AMRFINDER_RESISTANCE_VARIABLE):
            result.at[index, "amrfinder_evolutionary_evidence_reason"] = (
                "eligible_but_existing_resistance_evidence_preserved"
            )
            continue

        database = _norm(row.get("evolutionary_escape_risk_database")) or (
            "NCBI AMRFinderPlus"
        )
        input_source_type = _norm_lower(
            row.get("evolutionary_escape_risk_input_source_type")
        )
        source_type = (
            input_source_type
            if input_source_type in {
                "literature_curated",
                "real_external",
                "real_external_online",
                "computed_from_real_data",
            }
            else (
                "literature_curated"
                if _norm(row.get("amrfinder_pubmed_references"))
                else "real_external"
            )
        )
        provider_scope = _norm(row.get("amrfinder_method_scope"))
        method_scope = (
            f"{provider_scope}; Stage4D interpretation: positive target-level evidence "
            "that at least one curated AMR point mutation exists for this gene and "
            "organism. The value 1.0 denotes a documented escape route, not a "
            "prospective probability and not evidence that the current sequence "
            "already carries the mutation."
        )
        notes = (
            f"Stage4D adapter={AMRFINDER_ADAPTER_VERSION}; mutations="
            f"{_norm(row.get('amrfinder_mutation_symbols'))}; drug_classes="
            f"{_norm(row.get('amrfinder_drug_classes')) or 'not_reported'}; "
            f"drug_subclasses={_norm(row.get('amrfinder_drug_subclasses')) or 'not_reported'}; "
            f"pubmed={_norm(row.get('amrfinder_pubmed_references')) or 'not_reported'}; "
            f"catalog_sha256={_norm(row.get('amrfinder_catalog_sha256'))}; "
            "absence of an AMRFinderPlus catalog match is never encoded as low risk."
        )

        prefix = AMRFINDER_RESISTANCE_VARIABLE
        result.at[index, prefix] = risk
        _set_if_missing(result, f"{prefix}_is_explicit", index, True)
        _set_if_missing(result, f"{prefix}_source_type", index, source_type)
        _set_if_missing(result, f"{prefix}_source_database", index, database)
        _set_if_missing(
            result,
            f"{prefix}_source_record",
            index,
            _norm(row.get("amrfinder_source_record")),
        )
        _set_if_missing(
            result,
            f"{prefix}_source_version",
            index,
            _norm(row.get("amrfinder_source_version")),
        )
        _set_if_missing(
            result,
            f"{prefix}_retrieved_at",
            index,
            _norm(row.get("amrfinder_retrieved_at")),
        )
        _set_if_missing(
            result,
            f"{prefix}_mapping_method",
            index,
            _norm_lower(row.get("amrfinder_mapping_method")),
        )
        _set_if_missing(
            result,
            f"{prefix}_mapping_status",
            index,
            _norm_lower(row.get("amrfinder_mapping_status")),
        )
        _set_if_missing(
            result,
            f"{prefix}_evidence_status",
            index,
            _norm_lower(row.get("amrfinder_evidence_status")),
        )
        _set_if_missing(
            result,
            f"{prefix}_evidence_confidence",
            index,
            _norm_lower(row.get("amrfinder_evidence_confidence")),
        )
        _set_if_missing(
            result,
            f"{prefix}_independence_group",
            index,
            _norm(row.get("amrfinder_independence_group")),
        )
        _set_if_missing(result, f"{prefix}_method_scope", index, method_scope)
        _set_if_missing(
            result,
            f"{prefix}_taxon_id",
            index,
            _norm(row.get("amrfinder_taxon_id")),
        )
        _set_if_missing(result, f"{prefix}_notes", index, notes)

    return result


def materialize_provider_evolutionary_evidence(frame: pd.DataFrame) -> pd.DataFrame:
    """Materialize conservative provider-derived Stage 4A evidence.

    Stage 4C contributes one BV-BRC-derived `evolutionary_constraint_score` from
    non-duplicate comparative-genomic signals. Stage 4D can additionally promote
    positive NCBI AMRFinderPlus point-mutation catalog matches to one independent
    `resistance_emergence_risk` variable.

    Both adapters fail closed. Correlated BV-BRC transformations remain one
    independence group; AMRFinderPlus contributes a separate curated resistance
    mutation group. Missing provider matches are never converted into negative
    biological evidence. Existing canonical evidence metadata is preserved.
    """

    result = frame.copy()
    result = _materialize_bvbrc_evidence(result)
    result = _materialize_amrfinder_evidence(result)
    return result
