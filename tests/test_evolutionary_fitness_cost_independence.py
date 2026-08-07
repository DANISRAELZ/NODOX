from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.evolutionary_fitness_cost_evidence import (
    apply_curated_fitness_cost_evidence,
)


def _workspace(tmp_path: Path) -> Path:
    results = tmp_path / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "organism_profile.json").write_text(
        json.dumps(
            {
                "organism": "Helicobacter pylori",
                "organism_canonical_name": "Helicobacter pylori",
                "taxon_id": "210",
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def _candidate() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "protein_id": "HP_GYRA",
                "protein_id_canonical": "HP_GYRA",
                "gene": "gyrA",
                "taxon_id": "210",
            }
        ]
    )


def _catalog_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "gene": "gyrA",
        "taxon_id": "210",
        "mutation": "N87K",
        "escape_association": "target_site_resistance_mutation",
        "relative_fitness": 0.80,
        "measurement_type": "relative_fitness_ratio",
        "assay_context": "competition against isogenic WT",
        "source_type": "literature_curated",
        "source_database": "PubMed",
        "source_record": "PMID:12345678:gyrA_N87K",
        "source_version": "publication_snapshot_v1",
        "retrieved_at": "2026-08-07T18:00:00+00:00",
        "mapping_method": "manual_gene_taxon_curation",
        "mapping_status": "exact_gene_and_taxon",
        "evidence_status": "observed",
        "evidence_confidence": "high",
        "method_scope": "relative fitness of resistant mutant versus isogenic WT",
        "pmid": "12345678",
        "doi": "10.1000/example.fitness",
        "reference": "experimental fitness study",
        "independence_group": "free_text_group_that_must_not_control_counting",
    }
    row.update(overrides)
    return row


def _write_catalog(workspace: Path, row: dict[str, object]) -> None:
    root = workspace / "data_curated" / "organisms" / "helicobacter_pylori"
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(root / "evolutionary_fitness_cost.csv", index=False)


def _config(workspace: Path, *, global_curated_enabled: bool = True) -> dict:
    return {
        "online_sources": {"source_mode_effective": "hybrid_curated"},
        "curated_real_evidence": {
            "enabled": global_curated_enabled,
            "base_dir": str(workspace / "data_curated" / "organisms"),
        },
        "evolutionary_fitness_cost_curated": {
            "enabled": True,
            "base_dir": str(workspace / "data_curated" / "organisms"),
        },
    }


def test_independence_group_is_derived_from_study_identifier_not_free_text(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _write_catalog(workspace, _catalog_row())

    result = apply_curated_fitness_cost_evidence(
        workspace,
        _candidate(),
        _config(workspace),
    )

    assert result.loc[0, "fitness_cost_of_escape_independence_group"] == (
        "fitness_cost_study:PMID_12345678"
    )
    assert result.loc[0, "fitness_cost_curated_independence_reason"] == (
        "study_identifier_derived_independence_group"
    )
    assert "free_text_group" not in str(result.loc[0, "fitness_cost_of_escape_independence_group"])


def test_global_curated_disable_blocks_stage4e_even_if_stage4e_flag_is_enabled(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _write_catalog(workspace, _catalog_row())
    original = _candidate()

    result = apply_curated_fitness_cost_evidence(
        workspace,
        original,
        _config(workspace, global_curated_enabled=False),
    )

    pd.testing.assert_frame_equal(result, original)
    manifest = json.loads(
        (workspace / "results" / "evolutionary_fitness_cost_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["enabled"] is False
    assert manifest["reason"] == "disabled_by_curated_real_evidence_policy"
