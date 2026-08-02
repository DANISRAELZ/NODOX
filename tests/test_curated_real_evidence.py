from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.curated_real_evidence import apply_curated_real_evidence
from src.nodos_funcionales.functional_node_theory import compute_functional_node_theory_score
from tests.helpers import PROJECT_ROOT


def _write_profile(workspace: Path) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "organism_profile.json").write_text(
        json.dumps(
            {
                "organism_canonical_name": "Helicobacter pylori",
                "strain_canonical": None,
                "taxon_id": "210",
            }
        ),
        encoding="utf-8",
    )


def _base_config(workspace: Path) -> dict:
    config = load_config(PROJECT_ROOT / "config" / "params.yaml")
    config["curated_real_evidence"]["base_dir"] = str(workspace / "data_curated" / "organisms")
    config["curated_real_evidence"]["enabled"] = True
    return config


def _candidate_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "protein_id": ["HP_UREA", "HP_RPOB"],
            "protein_id_canonical": ["HP_UREA", "HP_RPOB"],
            "gene": ["ureA", "rpoB"],
            "meta_priority_score": [0.4, 0.4],
            "functional_node_score": [0.0, 0.2],
            "evidence_level": ["unresolved", "external"],
            "source_used": ["provider_not_found", "uniprot"],
            "retrieval_status": ["provider_not_found", "resolved"],
            "data_realism_flag": ["mixed_or_computed", "curated_or_experimental"],
        }
    )


def _hp_candidate_table_with_float_placeholders() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "protein_id": ["HP_UREA", "HP_UREB", "HP_CAGA", "HP_VACA"],
            "protein_id_canonical": ["HP_UREA", "HP_UREB", "HP_CAGA", "HP_VACA"],
            "gene": ["ureA", "ureB", "cagA", "vacA"],
            "meta_priority_score": [0.4, 0.4, 0.4, 0.4],
            "functional_node_score": [0.2, 0.2, 0.2, 0.2],
            "evidence_level": ["unresolved", "unresolved", "unresolved", "unresolved"],
            "source_used": ["provider_not_found", "provider_not_found", "provider_not_found", "provider_not_found"],
            "retrieval_status": ["provider_not_found", "provider_not_found", "provider_not_found", "provider_not_found"],
            "data_realism_flag": ["mixed_or_computed", "mixed_or_computed", "mixed_or_computed", "mixed_or_computed"],
            "essential": pd.Series([float("nan")] * 4, dtype="float64"),
            "virulence_factor": pd.Series([float("nan")] * 4, dtype="float64"),
        }
    )


def _write_curated_tables(workspace: Path) -> None:
    root = workspace / "data_curated" / "organisms" / "helicobacter_pylori"
    root.mkdir(parents=True, exist_ok=True)
    common = {
        "evidence_status": "curated_fixture",
        "evidence_source": "phase9A_test_fixture",
        "source_database": "curated_fixture",
        "reference": "fixture_reference",
        "confidence": 0.85,
        "notes": "fixture only, not experimental validation",
    }
    pd.DataFrame([{**common, "gene": "ureA", "protein_id": "HP_UREA", "essential": 1, "essentiality_score": 0.75}]).to_csv(
        root / "essentiality.csv",
        index=False,
    )
    pd.DataFrame([{**common, "gene": "ureA", "protein_id": "HP_UREA", "virulence_factor": 1, "virulence_score": 0.70}]).to_csv(
        root / "virulence.csv",
        index=False,
    )
    pd.DataFrame(
        [
            {
                **common,
                "gene": "ureA",
                "protein_id": "HP_UREA",
                "network_centrality": 0.70,
                "pathway_bottleneck_score": 0.68,
                "functional_dependency_score": 0.72,
                "interaction_count": 12,
                "network_source": "curated_fixture_network",
            }
        ]
    ).to_csv(root / "functional_network.csv", index=False)
    pd.DataFrame(
        [
            {
                **common,
                "gene": "ureA",
                "protein_id": "HP_UREA",
                "strain_coverage_score": 0.80,
                "core_genome_presence": 1,
                "allelic_conservation": 0.75,
                "variant_burden": 0.10,
            }
        ]
    ).to_csv(root / "strain_conservation.csv", index=False)
    pd.DataFrame(
        [
            {
                **common,
                "gene": "ureA",
                "protein_id": "HP_UREA",
                "redundancy_penalty": 0.20,
                "low_redundancy_score": 0.80,
                "paralog_count": 0,
                "alternative_pathway_count": 0,
            }
        ]
    ).to_csv(root / "redundancy.csv", index=False)
    pd.DataFrame(
        [
            {
                **common,
                "gene": "ureA",
                "protein_id": "HP_UREA",
                "literature_support_score": 0.60,
                "pmid": "fixture_pmid",
                "finding": "fixture finding",
                "experimental_support": "curated_fixture",
            }
        ]
    ).to_csv(root / "literature_support.csv", index=False)


def _write_textual_curated_tables(workspace: Path) -> None:
    root = workspace / "data_curated" / "organisms" / "helicobacter_pylori"
    root.mkdir(parents=True, exist_ok=True)
    common = {
        "evidence_status": "curated_fixture",
        "evidence_source": "phase9A_dtype_regression",
        "source_database": "curated_fixture",
        "reference": "fixture_reference",
        "confidence": 0.85,
        "notes": "fixture only, not experimental validation",
    }
    pd.DataFrame(
        [
            {
                **common,
                "gene": "ureA",
                "protein_id": "HP_UREA",
                "essential": "contextual_colonization_essential",
                "essentiality_score": 0.80,
            },
            {
                **common,
                "gene": "ureB",
                "protein_id": "HP_UREB",
                "essential": "contextual_colonization_dependency",
                "essentiality_score": 0.80,
            },
            {
                **common,
                "gene": "cagA",
                "protein_id": "HP_CAGA",
                "essential": "not_viability_essential_known",
                "essentiality_score": 0.30,
            },
            {
                **common,
                "gene": "vacA",
                "protein_id": "HP_VACA",
                "essential": "not_viability_essential_known",
                "essentiality_score": 0.30,
            },
        ]
    ).to_csv(root / "essentiality.csv", index=False)
    pd.DataFrame(
        [
            {
                **common,
                "gene": "ureA",
                "protein_id": "HP_UREA",
                "virulence_factor": "urease_acid_survival_colonization",
                "virulence_score": 0.90,
            },
            {
                **common,
                "gene": "ureB",
                "protein_id": "HP_UREB",
                "virulence_factor": "urease_acid_survival_colonization",
                "virulence_score": 0.90,
            },
            {
                **common,
                "gene": "cagA",
                "protein_id": "HP_CAGA",
                "virulence_factor": "cagA_virulence_effector",
                "virulence_score": 0.95,
            },
            {
                **common,
                "gene": "vacA",
                "protein_id": "HP_VACA",
                "virulence_factor": "vacuolating_cytotoxin",
                "virulence_score": 0.90,
            },
        ]
    ).to_csv(root / "virulence.csv", index=False)


def test_missing_curated_tables_do_not_change_candidate_values(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    config = _base_config(tmp_path)
    candidates = _candidate_table()

    enriched = apply_curated_real_evidence(tmp_path, candidates, config)

    assert enriched["protein_id"].tolist() == candidates["protein_id"].tolist()
    assert "curated_evidence_missing_layers" in enriched.columns
    assert (tmp_path / "results" / "curated_real_evidence_manifest.json").exists()
    assert (tmp_path / "results" / "curated_real_evidence_summary.csv").exists()


def test_curated_fixture_enriches_unresolved_candidate_and_feeds_theory_components(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_curated_tables(tmp_path)
    config = _base_config(tmp_path)

    enriched = apply_curated_real_evidence(tmp_path, _candidate_table(), config)
    scored = compute_functional_node_theory_score(enriched, config)
    ure_a = scored.loc[scored["gene"] == "ureA"].iloc[0]

    assert "essentiality" in ure_a["curated_evidence_layers"]
    assert "functional_network" in ure_a["curated_evidence_layers"]
    assert "fixture_reference" in ure_a["curated_evidence_references"]
    assert float(ure_a["dependency_component"]) >= 0.70
    assert float(ure_a["functional_impact_component"]) >= 0.70
    assert float(ure_a["redundancy_constraint_component"]) >= 0.75
    assert float(ure_a["evidence_quality_component"]) >= 0.85
    assert ure_a["functional_node_theory_label"] in {
        "low_confidence_functional_node_candidate",
        "moderate_confidence_functional_node",
    }
    assert ure_a["functional_node_theory_label"] != "high_confidence_functional_node"


def test_curated_low_confidence_or_fixture_evidence_cannot_force_high_confidence(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_curated_tables(tmp_path)
    config = _base_config(tmp_path)
    candidates = _candidate_table()
    candidates.loc[candidates["gene"] == "ureA", "functional_node_score"] = 1.0

    enriched = apply_curated_real_evidence(tmp_path, candidates, config)
    scored = compute_functional_node_theory_score(enriched, config)

    assert not scored["functional_node_theory_label"].eq("high_confidence_functional_node").any()


def test_preserves_higher_confidence_online_real_evidence(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_curated_tables(tmp_path)
    config = _base_config(tmp_path)
    candidates = _candidate_table()
    candidates.loc[candidates["gene"] == "rpoB", "essential"] = 1
    candidates.loc[candidates["gene"] == "rpoB", "essentiality_confidence"] = 0.95
    candidates.loc[candidates["gene"] == "rpoB", "essentiality_source_type"] = "external"
    root = tmp_path / "data_curated" / "organisms" / "helicobacter_pylori"
    pd.DataFrame(
        [
            {
                "gene": "rpoB",
                "protein_id": "HP_RPOB",
                "essential": 0,
                "essentiality_score": 0.1,
                "evidence_status": "curated_fixture",
                "source_database": "curated_fixture",
                "reference": "fixture_conflict",
                "confidence": 0.5,
            }
        ]
    ).to_csv(root / "essentiality.csv", index=False)

    enriched = apply_curated_real_evidence(tmp_path, candidates, config)
    rpo_b = enriched.loc[enriched["gene"] == "rpoB"].iloc[0]

    assert int(rpo_b["essential"]) == 1
    assert "preserved_existing" in rpo_b["curated_evidence_conflict_flags"]


def test_curated_text_values_are_safe_when_existing_columns_are_float64(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_textual_curated_tables(tmp_path)
    config = _base_config(tmp_path)

    enriched = apply_curated_real_evidence(tmp_path, _hp_candidate_table_with_float_placeholders(), config)
    scored = compute_functional_node_theory_score(enriched, config)

    by_gene = enriched.set_index("gene")
    assert by_gene.loc["ureA", "virulence_factor"] == "urease_acid_survival_colonization"
    assert by_gene.loc["ureB", "virulence_factor"] == "urease_acid_survival_colonization"
    assert by_gene.loc["cagA", "virulence_factor"] == "cagA_virulence_effector"
    assert by_gene.loc["vacA", "virulence_factor"] == "vacuolating_cytotoxin"
    assert int(by_gene.loc["ureA", "essential"]) == 1
    assert int(by_gene.loc["ureB", "essential"]) == 1
    assert int(by_gene.loc["cagA", "essential"]) == 0
    assert "contextual_colonization_essential" in by_gene.loc["ureA", "curated_essentiality_label"]
    assert "contextual_colonization_dependency" in by_gene.loc["ureB", "essentiality_context"]
    assert by_gene["curated_evidence_layers"].ne("none").all()
    assert {"ureA", "ureB", "cagA", "vacA"} <= set(by_gene.index[by_gene["curated_evidence_layers"].str.contains("virulence")])
    assert not scored["functional_node_theory_label"].eq("high_confidence_functional_node").any()


def test_online_strict_never_loads_local_curated_evidence(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_curated_tables(tmp_path)
    config = _base_config(tmp_path)
    config["online_sources"]["source_mode_effective"] = "online_strict"

    original = _candidate_table()
    enriched = apply_curated_real_evidence(tmp_path, original, config)
    manifest = json.loads((tmp_path / "results" / "curated_real_evidence_manifest.json").read_text(encoding="utf-8"))

    pd.testing.assert_frame_equal(enriched, original)
    assert manifest["enabled"] is False
    assert manifest["reason"] == "disabled_by_online_strict_policy"
    assert manifest["matched_candidate_count"] == 0
    assert manifest["updated_cell_count"] == 0


def test_hybrid_curated_explicitly_allows_local_curated_evidence(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_curated_tables(tmp_path)
    config = _base_config(tmp_path)
    config["online_sources"]["source_mode_effective"] = "hybrid_curated"

    enriched = apply_curated_real_evidence(tmp_path, _candidate_table(), config)
    manifest = json.loads((tmp_path / "results" / "curated_real_evidence_manifest.json").read_text(encoding="utf-8"))

    assert manifest["enabled"] is True
    assert manifest["evidence_policy"] == "hybrid_curated"
    assert manifest["updated_cell_count"] > 0
    assert "essentiality" in enriched.loc[enriched["gene"].eq("ureA"), "curated_evidence_layers"].iloc[0]
