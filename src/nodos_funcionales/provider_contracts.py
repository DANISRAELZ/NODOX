from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "7J-2026-06-24"


@dataclass(frozen=True)
class DegradationContract:
    final_status: str
    conservative_reason: str
    affects_score: bool
    blocks_ranking: bool
    evidence_inferred: bool


@dataclass(frozen=True)
class ProviderContract:
    provider_name: str
    provider_role: str
    accepted_payload_types: tuple[str, ...]
    accepted_content_types: tuple[str, ...]
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...]
    accepted_statuses: tuple[str, ...]
    degraded_statuses: tuple[DegradationContract, ...]
    evidence_flags_allowed: tuple[str, ...]
    blocks_ranking: bool
    affects_score_on_degradation: bool
    parser_name: str
    provenance_required: bool
    current_connection_status: str
    publication_readiness: str
    limitation_for_manuscript: str


def _degraded(*statuses: tuple[str, str]) -> tuple[DegradationContract, ...]:
    return tuple(
        DegradationContract(
            final_status=status,
            conservative_reason=reason,
            affects_score=False,
            blocks_ranking=False,
            evidence_inferred=False,
        )
        for status, reason in statuses
    )


PROVIDER_CONTRACTS: dict[str, ProviderContract] = {
    "candidate_seed": ProviderContract(
        provider_name="candidate_seed",
        provider_role="online-only candidate universe seed",
        accepted_payload_types=("json",),
        accepted_content_types=("application/json",),
        required_fields=("protein_id", "gene", "candidate_seed_accession"),
        optional_fields=("candidate_seed_provider", "candidate_seed_note", "taxon_id"),
        accepted_statuses=("api_real_candidate_seed_only", "cache_hit", "offline_unresolved_candidate_seed"),
        degraded_statuses=(
            DegradationContract(
                final_status="candidate_seed_unresolved",
                conservative_reason="No candidate universe can be constructed without seed records.",
                affects_score=False,
                blocks_ranking=True,
                evidence_inferred=False,
            ),
        ),
        evidence_flags_allowed=("computational_online_annotation",),
        blocks_ranking=True,
        affects_score_on_degradation=False,
        parser_name="uniprot_candidate_seed_json_parser",
        provenance_required=True,
        current_connection_status="required_seed_layer",
        publication_readiness="contract_ready_blocking_seed",
        limitation_for_manuscript="Candidate seed defines the computable universe and is not therapeutic evidence.",
    ),
    "uniprot": ProviderContract(
        provider_name="UniProt",
        provider_role="candidate seed and localization enrichment",
        accepted_payload_types=("json",),
        accepted_content_types=("application/json",),
        required_fields=("primaryAccession", "genes", "proteinDescription"),
        optional_fields=("entryType", "annotationScore", "organism", "comments"),
        accepted_statuses=("connected_structured_payload", "api_real", "cache_hit", "inherited_from_candidate_seed"),
        degraded_statuses=_degraded(
            ("ssl_error", "Windows/OpenSSL or TLS failure is provider transport degradation."),
            ("network_error", "Network failure prevents retrieval but does not imply biological absence."),
            ("invalid_payload", "Payload cannot be parsed as structured UniProt JSON."),
            ("empty_payload", "Empty payload is unresolved, not negative evidence."),
        ),
        evidence_flags_allowed=("computational_online_annotation", "localization_metadata"),
        blocks_ranking=False,
        affects_score_on_degradation=False,
        parser_name="uniprot_json_results_parser",
        provenance_required=True,
        current_connection_status="structured_json_supported",
        publication_readiness="ready_with_transport_limitations",
        limitation_for_manuscript="UniProt provides computational annotations; absence or transport failure is unresolved.",
    ),
    "string": ProviderContract(
        provider_name="STRING",
        provider_role="functional network enrichment",
        accepted_payload_types=("json",),
        accepted_content_types=("application/json",),
        required_fields=("stringId", "preferredName", "score"),
        optional_fields=("queryItem", "stringId_A", "stringId_B", "ncbiTaxonId"),
        accepted_statuses=("connected_structured_payload", "api_real", "cache_hit"),
        degraded_statuses=_degraded(
            ("ssl_error", "Windows/OpenSSL or TLS failure is provider transport degradation."),
            ("network_error", "Network failure prevents retrieval but does not imply no interactions."),
            ("invalid_payload", "Payload is not structured STRING JSON."),
            ("not_found", "Endpoint did not provide records for the query."),
        ),
        evidence_flags_allowed=("functional_network_metadata",),
        blocks_ranking=False,
        affects_score_on_degradation=False,
        parser_name="string_json_list_parser",
        provenance_required=True,
        current_connection_status="structured_json_supported",
        publication_readiness="ready_with_transport_limitations",
        limitation_for_manuscript="STRING associations are computational network metadata, not experimental validation.",
    ),
    "interpro": ProviderContract(
        provider_name="InterPro",
        provider_role="host-annotation domain overlap enrichment",
        accepted_payload_types=("json",),
        accepted_content_types=("application/json",),
        required_fields=("results", "metadata.accession"),
        optional_fields=("entry_protein_locations", "extra_fields", "page_size"),
        accepted_statuses=("connected_structured_payload", "api_real", "api_real_partial", "cache_hit"),
        degraded_statuses=_degraded(
            ("ssl_error", "Windows/OpenSSL or TLS failure is provider transport degradation."),
            ("network_error", "Network failure prevents retrieval but does not imply no domain overlap."),
            ("invalid_payload", "HTML, text, or malformed payload is not domain evidence."),
            ("unresolved", "Missing accessions or no comparable pairs remain unresolved."),
        ),
        evidence_flags_allowed=("domain_overlap_metadata",),
        blocks_ranking=False,
        affects_score_on_degradation=False,
        parser_name="interpro_json_results_parser",
        provenance_required=True,
        current_connection_status="structured_json_supported",
        publication_readiness="ready_with_transport_limitations",
        limitation_for_manuscript="InterPro overlap is structural metadata; unresolved status is not host-safety evidence.",
    ),
    "bvbrc": ProviderContract(
        provider_name="BV-BRC",
        provider_role="strain conservation and genome metadata enrichment",
        accepted_payload_types=("json",),
        accepted_content_types=("application/json",),
        required_fields=("genome_id", "genome_name"),
        optional_fields=("taxon_id", "patric_id", "annotation", "amr"),
        accepted_statuses=("connected_structured_payload", "api_real", "verified_empty"),
        degraded_statuses=_degraded(
            ("empty_payload", "Empty payload is unresolved or verified empty, not negative evidence."),
            ("auth_or_permission_error", "Permission failure prevents retrieval and is not biological absence."),
            ("not_found", "404 is provider/query status, not evidence of absence."),
            ("network_error", "Network failure prevents retrieval."),
            ("invalid_payload", "Malformed payload cannot support conservation evidence."),
        ),
        evidence_flags_allowed=("structured_genome_metadata",),
        blocks_ranking=False,
        affects_score_on_degradation=False,
        parser_name="bvbrc_json_records_parser",
        provenance_required=True,
        current_connection_status="structured_json_supported_when_query_resolves",
        publication_readiness="conditional_ready",
        limitation_for_manuscript="BV-BRC interpretation depends on query resolution and should not treat empty payloads as strong negatives.",
    ),
    "vfdb": ProviderContract(
        provider_name="VFDB",
        provider_role="virulence provider endpoint audit",
        accepted_payload_types=("json", "tabular_text"),
        accepted_content_types=("application/json", "text/tab-separated-values", "text/plain"),
        required_fields=("gene", "virulence_factor"),
        optional_fields=("vfdb_id", "organism", "category"),
        accepted_statuses=("connected_structured_payload", "api_real"),
        degraded_statuses=_degraded(
            ("html_instead_of_structured_payload", "HTML is a web page response, not virulence evidence."),
            ("not_found", "404 is provider/query status, not absence of virulence."),
            ("network_error", "Network failure prevents retrieval."),
            ("invalid_payload", "Unexpected payload cannot support virulence evidence."),
        ),
        evidence_flags_allowed=("explicit_virulence_record",),
        blocks_ranking=False,
        affects_score_on_degradation=False,
        parser_name="vfdb_structured_record_parser",
        provenance_required=True,
        current_connection_status="degraded_no_stable_programmatic_route_verified",
        publication_readiness="not_ready_for_automatic_evidence",
        limitation_for_manuscript="VFDB requires a stable programmatic route before automatic virulence evidence can be claimed.",
    ),
    "deg": ProviderContract(
        provider_name="DEG",
        provider_role="essentiality provider endpoint audit",
        accepted_payload_types=("json", "tabular_text"),
        accepted_content_types=("application/json", "text/tab-separated-values", "text/plain"),
        required_fields=("gene", "essentiality_status"),
        optional_fields=("deg_id", "organism", "condition"),
        accepted_statuses=("connected_structured_payload", "api_real"),
        degraded_statuses=_degraded(
            ("html_instead_of_structured_payload", "HTML is a web page response, not essentiality evidence."),
            ("unsupported_structured_archive", "ZIP download requires a formal adapter before use."),
            ("network_error", "Network failure prevents retrieval."),
            ("invalid_payload", "Unexpected payload cannot support essentiality evidence."),
        ),
        evidence_flags_allowed=("explicit_essentiality_record",),
        blocks_ranking=False,
        affects_score_on_degradation=False,
        parser_name="deg_structured_record_parser",
        provenance_required=True,
        current_connection_status="degraded_zip_requires_adapter",
        publication_readiness="not_ready_for_automatic_evidence",
        limitation_for_manuscript="DEG ZIP/downloads need a versioned adapter before automatic essentiality evidence can be claimed.",
    ),
    "europe_pmc": ProviderContract(
        provider_name="Europe PMC",
        provider_role="literature metadata enrichment",
        accepted_payload_types=("json",),
        accepted_content_types=("application/json",),
        required_fields=("resultList.result",),
        optional_fields=("title", "authorString", "journalTitle", "pubYear", "doi"),
        accepted_statuses=("connected_structured_payload", "api_real", "api_success_no_records"),
        degraded_statuses=_degraded(
            ("network_error", "Network failure prevents retrieval and is not absence of literature."),
            ("invalid_payload", "Unexpected payload cannot support literature metadata."),
            ("empty_payload", "Empty payload is unresolved, not evidence against the candidate."),
        ),
        evidence_flags_allowed=("literature_metadata",),
        blocks_ranking=False,
        affects_score_on_degradation=False,
        parser_name="europe_pmc_json_result_parser",
        provenance_required=True,
        current_connection_status="structured_json_supported",
        publication_readiness="ready_as_metadata_only",
        limitation_for_manuscript="Literature metadata is not experimental validation unless explicitly curated later.",
    ),
    "taxonomy": ProviderContract(
        provider_name="Taxonomy",
        provider_role="organism identity and taxon resolution",
        accepted_payload_types=("json",),
        accepted_content_types=("application/json",),
        required_fields=("esearchresult.idlist", "result.uids"),
        optional_fields=("scientificname", "rank", "taxid", "uid"),
        accepted_statuses=("online_exact_name_match", "online_exact_strain_match", "online_partial_name_match"),
        degraded_statuses=_degraded(
            ("network_error", "Network failure prevents taxon lookup."),
            ("online_no_match", "No match means unresolved taxonomy, not biological evidence."),
            ("invalid_payload", "Unexpected payload cannot resolve taxonomy."),
        ),
        evidence_flags_allowed=("taxonomy_resolution_metadata",),
        blocks_ranking=False,
        affects_score_on_degradation=False,
        parser_name="ncbi_taxonomy_json_parser",
        provenance_required=True,
        current_connection_status="structured_json_supported",
        publication_readiness="ready_as_identity_metadata",
        limitation_for_manuscript="Taxonomy resolution identifies the run context and does not validate therapeutic evidence.",
    ),
    "human_essentiality": ProviderContract(
        provider_name="Human essentiality",
        provider_role="host essentiality context for host annotation",
        accepted_payload_types=("tabular_text", "json"),
        accepted_content_types=("text/tab-separated-values", "text/plain", "application/json"),
        required_fields=("human_gene", "human_essentiality_score"),
        optional_fields=("entrez_gene_id", "human_essential", "human_essentiality_lookup_status"),
        accepted_statuses=("local_file", "api_real", "cache_hit"),
        degraded_statuses=_degraded(
            ("network_error", "Network failure prevents human essentiality lookup."),
            ("not_found", "Missing human record is unresolved context, not safety evidence."),
            ("empty_payload", "Empty payload does not imply low host risk."),
            ("invalid_payload", "Unexpected payload cannot support host context."),
        ),
        evidence_flags_allowed=("host_context_metadata",),
        blocks_ranking=False,
        affects_score_on_degradation=False,
        parser_name="human_essentiality_table_parser",
        provenance_required=True,
        current_connection_status="local_or_structured_download_supported",
        publication_readiness="ready_as_contextual_metadata",
        limitation_for_manuscript="Human essentiality context is incomplete and should not be overread as host safety validation.",
    ),
}


def expected_provider_names() -> tuple[str, ...]:
    return tuple(PROVIDER_CONTRACTS.keys())


def contracts_as_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for key, contract in PROVIDER_CONTRACTS.items():
        record = asdict(contract)
        record["provider_key"] = key
        record["degraded_statuses"] = [asdict(item) for item in contract.degraded_statuses]
        records.append(record)
    return records


def contract_matrix_records() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for key, contract in PROVIDER_CONTRACTS.items():
        rejected_payloads = sorted(
            {"html", "zip", "unexpected_text", "empty", "network_error", "ssl_error", "invalid_payload"}
            - set(contract.accepted_payload_types)
        )
        rows.append(
            {
                "provider_key": key,
                "provider": contract.provider_name,
                "role": contract.provider_role,
                "current_connection_status": contract.current_connection_status,
                "accepted_payload": ";".join(contract.accepted_payload_types),
                "rejected_payloads": ";".join(rejected_payloads),
                "evidence_can_be_inferred": str(bool(contract.evidence_flags_allowed)).lower(),
                "degradation_statuses": ";".join(item.final_status for item in contract.degraded_statuses),
                "blocks_ranking": str(contract.blocks_ranking).lower(),
                "affects_score_when_degraded": str(contract.affects_score_on_degradation).lower(),
                "provenance_required": str(contract.provenance_required).lower(),
                "publication_readiness": contract.publication_readiness,
                "limitation_for_manuscript": contract.limitation_for_manuscript,
            }
        )
    return rows


def write_contract_matrix(csv_path: Path, json_path: Path) -> None:
    rows = contract_matrix_records()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(
        json.dumps({"contract_version": CONTRACT_VERSION, "providers": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
