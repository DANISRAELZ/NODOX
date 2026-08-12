from __future__ import annotations

import pytest

from src.nodos_funcionales.stage5a2_candidate_discovery import (
    parse_benchmark_alias_specs,
    provider_profile_settings,
    resolve_natural_benchmark,
    select_stage5a2_records,
)


def _record(
    accession: str,
    gene: str | None = None,
    locus: str | None = None,
    protein_name: str | None = None,
) -> dict[str, object]:
    gene_block: dict[str, object] = {}
    if gene:
        gene_block["geneName"] = {"value": gene}
    if locus:
        gene_block["orderedLocusNames"] = [{"value": locus}]
    return {
        "primaryAccession": accession,
        "uniProtkbId": f"{gene or accession}_HELPY",
        "entryType": "UniProtKB unreviewed (TrEMBL)",
        "genes": [gene_block] if gene_block else [],
        "proteinDescription": {
            "submissionNames": [{"fullName": {"value": protein_name or "test protein"}}]
        },
        "sequence": {"value": "MAAA"},
    }


def test_pbp1a_resolves_by_explicit_exact_accession_or_locus_alias() -> None:
    records = [
        _record(
            "O25319",
            locus="HP_0597",
            protein_name="Penicillin-binding protein 1A (PBP-1A)",
        )
    ]
    aliases = parse_benchmark_alias_specs(["pbp1A=O25319,HP_0597"])
    record, match_type, alias_used, ambiguous = resolve_natural_benchmark(
        records, "pbp1A", aliases
    )
    assert record is not None
    assert record["primaryAccession"] == "O25319"
    assert match_type.startswith("alias_")
    assert alias_used in {"O25319", "HP_0597"}
    assert ambiguous is False


def test_protein_description_is_not_used_as_implicit_alias() -> None:
    records = [
        _record(
            "O25319",
            locus="HP_0597",
            protein_name="Penicillin-binding protein 1A (PBP-1A)",
        )
    ]
    record, _, _, ambiguous = resolve_natural_benchmark(records, "pbp1A", {})
    assert record is None
    assert ambiguous is False


def test_gyra_and_gyrb_remain_separate_exact_benchmarks() -> None:
    records = [_record("P48370", gene="gyrA"), _record("P55992", gene="gyrB")]
    gyr_a = resolve_natural_benchmark(records, "gyrA", {})
    gyr_b = resolve_natural_benchmark(records, "gyrB", {})
    assert gyr_a[0]["primaryAccession"] == "P48370"
    assert gyr_b[0]["primaryAccession"] == "P55992"


def test_blind_alias_mapping_does_not_force_candidates() -> None:
    records = [
        _record("O25319", locus="HP_0597"),
        _record("P48370", gene="gyrA"),
        _record("P55992", gene="gyrB"),
    ]
    aliases = parse_benchmark_alias_specs(["pbp1A=O25319,HP_0597"])
    selected, audit, summary = select_stage5a2_records(
        natural_records=records,
        benchmark_mode="blind",
        benchmark_candidates=["pbp1A", "gyrA", "gyrB"],
        benchmark_aliases=aliases,
        max_candidates=0,
        total_uniprot_results=3,
    )
    assert len(selected) == 3
    assert summary["forced_candidate_count"] == 0
    benchmark = audit.loc[audit["benchmark_requested"].eq(True)]
    assert set(benchmark["candidate_seed_accession"]) == {"O25319", "P48370", "P55992"}
    pbp = benchmark.loc[benchmark["candidate_seed_accession"].eq("O25319")].iloc[0]
    assert bool(pbp["discovered_naturally"]) is True
    assert bool(pbp["benchmark_forced_candidate"]) is False


def test_alias_cannot_be_owned_by_two_benchmarks() -> None:
    with pytest.raises(ValueError, match="more than one canonical target"):
        parse_benchmark_alias_specs(["targetA=O25319", "targetB=O25319"])


def test_benchmark_resilient_profile_skips_only_non_scoring_metadata_providers() -> None:
    resilient = provider_profile_settings("benchmark_resilient")
    full = provider_profile_settings("full")
    assert resilient["enable_interpro"] is False
    assert resilient["enable_literature"] is False
    assert set(resilient["intentionally_skipped_providers"]) == {"interpro", "literature"}
    assert full["enable_interpro"] is True
    assert full["enable_literature"] is True
