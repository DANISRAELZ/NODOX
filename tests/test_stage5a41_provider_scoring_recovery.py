from pathlib import Path

import pandas as pd

from src.nodos_funcionales.stage5a41_provider_scoring_recovery import (
    _mark_provider_manifest_score_effect,
    _parse_vfdb_snapshot_fields,
    normalize_vfdb_snapshot,
    overlay_deg_essentiality,
)


def test_parse_vfdb_snapshot_fields_exposes_existing_identifiers_only():
    parsed = _parse_vfdb_snapshot_fields(
        "VFG012345(gb|WP_012345678)",
        "VFG012345(gb|WP_012345678) (vacA) vacuolating cytotoxin [Helicobacter pylori 26695]",
    )

    assert parsed["vf_id"] == "VFG012345"
    assert parsed["protein"] == "WP_012345678"
    assert parsed["gene"] == "vacA"
    assert parsed["organism"] == "Helicobacter pylori 26695"
    assert "vacuolating cytotoxin" in parsed["function"]


def test_parse_vfdb_snapshot_fields_does_not_invent_missing_gene_or_alias():
    parsed = _parse_vfdb_snapshot_fields(
        "VFG099999(gb|WP_999999999)",
        "VFG099999(gb|WP_999999999) hypothetical virulence-associated protein [Helicobacter pylori 26695]",
    )

    assert parsed["gene"] == ""
    assert parsed["protein"] == "WP_999999999"
    assert "gyrA" not in parsed.values()
    assert "gyrB" not in parsed.values()
    assert "pbp1A" not in parsed.values()


def test_normalize_vfdb_snapshot_writes_provider_fields_and_version(tmp_path):
    source = tmp_path / "vfdb.csv"
    pd.DataFrame(
        [
            {
                "source": "VFDB",
                "dataset": "VFDB_setA_pro",
                "record_id": "VFG000001(gb|WP_000000001)",
                "description": "VFG000001(gb|WP_000000001) (cagA) effector protein [Helicobacter pylori 26695]",
                "sequence": "MKK",
                "raw_file": "raw.fas.gz",
                "sha256": "abc",
            }
        ]
    ).to_csv(source, index=False)
    source.with_suffix(".version.txt").write_text("dataset=VFDB_setA_pro\n", encoding="utf-8")
    output = tmp_path / "normalized.csv"

    audit = normalize_vfdb_snapshot(source, output)
    normalized = pd.read_csv(output)

    assert audit["record_count"] == 1
    assert audit["gene_parsed_count"] == 1
    assert normalized.loc[0, "vf_id"] == "VFG000001"
    assert normalized.loc[0, "protein"] == "WP_000000001"
    assert normalized.loc[0, "gene"] == "cagA"
    assert normalized.loc[0, "organism"] == "Helicobacter pylori 26695"
    assert output.with_suffix(".version.txt").is_file()


def test_overlay_deg_essentiality_preserves_candidate_universe_and_unknowns():
    candidates = pd.DataFrame(
        [
            {"protein_id": "P1", "gene": "g1", "essential": pd.NA, "evidence": "", "database": "seed"},
            {"protein_id": "P2", "gene": "g2", "essential": pd.NA, "evidence": "", "database": "seed"},
            {"protein_id": "P3", "gene": "g3", "essential": pd.NA, "evidence": "", "database": "seed"},
        ]
    )
    deg = pd.DataFrame(
        [
            {"protein_id": "P2", "gene": "g2", "essential": 1, "evidence": "DEG experimental screen", "database": "deg_real_v1"}
        ]
    )

    combined, audit = overlay_deg_essentiality(candidates, deg)

    assert len(combined) == 3
    assert audit["deg_match_count"] == 1
    assert audit["negative_evidence_inferred_count"] == 0
    assert combined.loc[combined["protein_id"].eq("P2"), "essential"].iloc[0] == 1
    assert combined.loc[combined["protein_id"].eq("P2"), "deg_support"].iloc[0]
    assert pd.isna(combined.loc[combined["protein_id"].eq("P1"), "essential"].iloc[0])
    assert pd.isna(combined.loc[combined["protein_id"].eq("P3"), "essential"].iloc[0])


def test_overlay_deg_essentiality_accepts_all_nan_float_provenance_columns():
    candidates = pd.DataFrame(
        {
            "protein_id": ["P1", "P2"],
            "gene": ["g1", "g2"],
            "essential": pd.Series([float("nan"), float("nan")], dtype="float64"),
            "evidence": pd.Series([float("nan"), float("nan")], dtype="float64"),
            "database": pd.Series([float("nan"), float("nan")], dtype="float64"),
        }
    )
    deg = pd.DataFrame(
        [
            {
                "protein_id": "P2",
                "gene": "g2",
                "essential": 1,
                "evidence": "DEG bacterial essential gene annotation",
                "database": "deg_real_v1",
            }
        ]
    )

    combined, audit = overlay_deg_essentiality(candidates, deg)

    assert audit["deg_match_count"] == 1
    assert str(combined["evidence"].dtype).startswith("string")
    assert str(combined["database"].dtype).startswith("string")
    assert combined.loc[combined["protein_id"].eq("P2"), "evidence"].iloc[0] == "DEG bacterial essential gene annotation"
    assert combined.loc[combined["protein_id"].eq("P2"), "database"].iloc[0] == "deg_real_v1"
    assert pd.isna(combined.loc[combined["protein_id"].eq("P1"), "essential"].iloc[0])


def test_overlay_deg_essentiality_does_not_create_contextual_score():
    candidates = pd.DataFrame(
        [{"protein_id": "P1", "gene": "g1", "essential": pd.NA}]
    )
    deg = pd.DataFrame(
        [{"protein_id": "P1", "gene": "g1", "essential": 1, "evidence": "DEG"}]
    )

    combined, _ = overlay_deg_essentiality(candidates, deg)

    assert "contextual_essentiality_score" not in combined.columns


def test_mark_provider_manifest_score_effect_requires_actual_mapping(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text('{"retrieval_status":"local_dataset_available"}', encoding="utf-8")

    no_hits = _mark_provider_manifest_score_effect(
        path,
        layer_key="virulence",
        provider_name="vfdb",
        matched_count=0,
        evidence_level="versioned_external_virulence_dataset",
        scoring_columns=["virulence_score"],
        interpretation="test",
    )
    assert no_hits["usable_evidence"] is False
    assert no_hits["affects_score"] is False

    hits = _mark_provider_manifest_score_effect(
        path,
        layer_key="virulence",
        provider_name="vfdb",
        matched_count=2,
        evidence_level="versioned_external_virulence_dataset",
        scoring_columns=["virulence_score"],
        interpretation="test",
    )
    assert hits["usable_evidence"] is True
    assert hits["affects_score"] is True
    assert hits["matched_candidate_count"] == 2
