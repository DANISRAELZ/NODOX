from __future__ import annotations

import json
import shutil

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.organism_metadata import apply_organism_metadata, load_organism_metadata
from src.nodos_funcionales.reporting import export_results
from src.nodos_funcionales.scoring import build_features_and_scores
from src.nodos_funcionales.validation import load_and_validate_all
from src.nodos_funcionales.online_only_validation import _write_run_identity_profile
from tests.helpers import PROJECT_ROOT


@pytest.mark.unit
def test_load_organism_metadata_from_results_profile_with_null_strain(tmp_path) -> None:
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "organism_profile.json").write_text(
        json.dumps(
            {
                "organism_canonical_name": "Helicobacter pylori",
                "taxon_id": 210,
                "strain": None,
            }
        ),
        encoding="utf-8",
    )

    metadata = load_organism_metadata(tmp_path)

    assert metadata == {
        "organism": "Helicobacter pylori",
        "taxon_id": 210,
        "strain": "not_reported",
    }


@pytest.mark.unit
def test_load_organism_metadata_uses_alternative_fields(tmp_path) -> None:
    (tmp_path / "organism_profile.json").write_text(
        json.dumps(
            {
                "organism": "Pseudomonas aeruginosa",
                "ncbi_taxon_id": 287,
                "strain": "PAO1",
            }
        ),
        encoding="utf-8",
    )

    metadata = load_organism_metadata(tmp_path)

    assert metadata == {
        "organism": "Pseudomonas aeruginosa",
        "taxon_id": 287,
        "strain": "PAO1",
    }


@pytest.mark.unit
def test_run_metadata_priority_preserves_pseudomonas_registry_taxon_id(tmp_path) -> None:
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    _write_run_identity_profile(
        workspace=tmp_path,
        profile={"organism_canonical_name": "Pseudomonas aeruginosa", "taxon_id": None},
        organism="Pseudomonas aeruginosa",
        strain=None,
        configured_taxon_id="287",
        resolved_taxon_id="",
    )

    metadata = load_organism_metadata(tmp_path)
    profile = json.loads((results_dir / "organism_profile.json").read_text(encoding="utf-8"))

    assert metadata == {
        "organism": "Pseudomonas aeruginosa",
        "taxon_id": "287",
        "strain": "not_reported",
    }
    assert profile["provider_taxon_id"] is None
    assert profile["registry_taxon_id"] == "287"


@pytest.mark.unit
def test_run_metadata_priority_preserves_h37rv_strain_taxon_over_species_taxon(tmp_path) -> None:
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    _write_run_identity_profile(
        workspace=tmp_path,
        profile={
            "organism_canonical_name": "Mycobacterium tuberculosis",
            "strain_canonical": "H37Rv",
            "taxon_id": "1773",
            "resolution_confidence": 0.9,
        },
        organism="Mycobacterium tuberculosis",
        strain="H37Rv",
        configured_taxon_id="83332",
        resolved_taxon_id="83332",
    )

    metadata = load_organism_metadata(tmp_path)
    profile = json.loads((results_dir / "organism_profile.json").read_text(encoding="utf-8"))

    assert metadata == {
        "organism": "Mycobacterium tuberculosis",
        "taxon_id": "83332",
        "strain": "H37Rv",
    }
    assert profile["taxon_id"] == "83332"
    assert profile["provider_taxon_id"] == "1773"
    assert profile["resolved_taxon_id"] == "1773"
    assert profile["resolution_confidence"] == 0.9


@pytest.mark.unit
def test_profile_without_registry_still_uses_resolved_metadata(tmp_path) -> None:
    (tmp_path / "results").mkdir()
    _write_run_identity_profile(
        workspace=tmp_path,
        profile={"organism_canonical_name": "Helicobacter pylori", "taxon_id": "210"},
        organism="Helicobacter pylori",
        strain=None,
        configured_taxon_id="",
        resolved_taxon_id="210",
    )

    metadata = load_organism_metadata(tmp_path)

    assert metadata == {
        "organism": "Helicobacter pylori",
        "taxon_id": "210",
        "strain": "not_reported",
    }


@pytest.mark.unit
def test_load_organism_metadata_without_profile_returns_explicit_defaults(tmp_path) -> None:
    metadata = load_organism_metadata(tmp_path)

    assert metadata == {
        "organism": "not_reported",
        "taxon_id": "not_reported",
        "strain": "not_reported",
    }


@pytest.mark.unit
def test_apply_organism_metadata_repairs_absent_or_not_reported_values() -> None:
    records = pd.DataFrame(
        {
            "protein_id": ["A", "B"],
            "organism": ["not_reported", "Existing bacterium"],
            "strain": ["nan", ""],
        }
    )

    repaired = apply_organism_metadata(
        records,
        {"organism": "Helicobacter pylori", "strain": "not_reported", "taxon_id": 210},
        overwrite_not_reported=True,
    )

    assert repaired["organism"].tolist() == ["Helicobacter pylori", "Existing bacterium"]
    assert repaired["strain"].tolist() == ["not_reported", "not_reported"]
    assert repaired["taxon_id"].tolist() == ["210", "210"]


@pytest.mark.integration
@pytest.mark.slow
def test_metadata_flows_from_results_profile_to_processed_and_ranking_outputs(tmp_path) -> None:
    project_dir = tmp_path / "metadata_flow_workspace"
    for dirname in ["data_raw", "config", "data_processed", "results"]:
        (project_dir / dirname).mkdir(parents=True, exist_ok=True)
    for path in (PROJECT_ROOT / "data_raw").glob("*.csv"):
        shutil.copyfile(path, project_dir / "data_raw" / path.name)
    shutil.copyfile(PROJECT_ROOT / "config" / "params.yaml", project_dir / "config" / "params.yaml")
    (project_dir / "results" / "organism_profile.json").write_text(
        json.dumps(
            {
                "organism_canonical_name": "Helicobacter pylori",
                "taxon_id": 210,
                "strain": None,
            }
        ),
        encoding="utf-8",
    )
    config = load_config(project_dir / "config" / "params.yaml")
    config["online_sources"]["source_mode_effective"] = "offline_only"
    for layer in config["layer_resolution"]["layers"].values():
        if layer.get("strategy") == "external_preferred":
            layer["strategy"] = "user_preferred"

    load_and_validate_all(project_dir, config)
    normalize_all(project_dir, config)
    integrated = integrate_tables(project_dir)
    features, scored = build_features_and_scores(project_dir, config)
    export_results(project_dir, config, mode="online_only")

    dataframes = {
        "integrated": integrated,
        "features": features,
        "scored": scored,
        "ranking": pd.read_csv(project_dir / "results" / "ranking_nodos.csv"),
        "legacy": pd.read_csv(project_dir / "results" / "ranking_nodos_legacy.csv"),
        "snapshot": pd.read_csv(project_dir / "results" / "ranking_snapshot.csv"),
    }
    for name, df in dataframes.items():
        assert set(["organism", "strain", "taxon_id"]).issubset(df.columns), name
        assert set(df["organism"].astype(str)) == {"Helicobacter pylori"}, name
        assert set(df["strain"].astype(str)) == {"not_reported"}, name
        assert set(df["taxon_id"].astype(str)) == {"210"}, name
