from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.nodos_funcionales.localization_semantics import (
    INNER_PERIPHERAL_CLASS,
    apply_frozen_uniprot_topology_semantics,
    install_peripheral_membrane_profiles,
)

pytestmark = pytest.mark.unit


def _write_seed_record(base_dir: Path, *, accession: str, topology: str) -> None:
    results_dir = base_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "results": [
            {
                "primaryAccession": accession,
                "comments": [
                    {
                        "commentType": "SUBCELLULAR LOCATION",
                        "subcellularLocations": [
                            {
                                "location": {"value": "Cell membrane"},
                                "topology": {"value": topology},
                            }
                        ],
                    }
                ],
            }
        ]
    }
    (results_dir / "online_only_uniprot_seed_records.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_explicit_peripheral_inner_membrane_is_not_scored_as_integral(tmp_path: Path) -> None:
    _write_seed_record(
        tmp_path,
        accession="P0AFI2",
        topology="Peripheral membrane protein",
    )
    integrated = pd.DataFrame(
        [{"protein_id": "P0AFI2", "gene": "parC", "localization": "inner_membrane"}]
    )

    result = apply_frozen_uniprot_topology_semantics(tmp_path, integrated)

    assert result.loc[0, "localization_reported"] == "inner_membrane"
    assert result.loc[0, "localization"] == INNER_PERIPHERAL_CLASS
    assert result.loc[0, "uniprot_membrane_topology"] == "Peripheral membrane protein"
    assert "conservative_access_profile=cytoplasm" in result.loc[0, "localization_scoring_rule"]


def test_integral_membrane_topology_keeps_reported_compartment(tmp_path: Path) -> None:
    _write_seed_record(
        tmp_path,
        accession="PTEST1",
        topology="Multi-pass membrane protein",
    )
    integrated = pd.DataFrame(
        [{"protein_id": "PTEST1", "gene": "mem", "localization": "inner_membrane"}]
    )

    result = apply_frozen_uniprot_topology_semantics(tmp_path, integrated)

    assert result.loc[0, "localization"] == "inner_membrane"
    assert result.loc[0, "localization_reported"] == "inner_membrane"
    assert result.loc[0, "localization_scoring_rule"] == "reported_compartment"


def test_missing_topology_does_not_reclassify_localization(tmp_path: Path) -> None:
    integrated = pd.DataFrame(
        [{"protein_id": "PTEST2", "gene": "x", "localization": "inner_membrane"}]
    )

    result = apply_frozen_uniprot_topology_semantics(tmp_path, integrated)

    assert result.loc[0, "localization"] == "inner_membrane"
    assert result.loc[0, "uniprot_membrane_topology"] == ""


def test_peripheral_profile_reuses_existing_cytoplasmic_values_without_new_calibration() -> None:
    config = {
        "localization": {
            "physical_accessibility": {"inner_membrane": 0.55, "cytoplasm": 0.30, "periplasm": 0.65},
            "small_molecule_feasibility": {"inner_membrane": 0.70, "cytoplasm": 0.80, "periplasm": 0.75},
            "antibody_feasibility": {"inner_membrane": 0.25, "cytoplasm": 0.05, "periplasm": 0.35},
            "membrane_crossing_penalty": {"inner_membrane": 0.45, "cytoplasm": 0.55, "periplasm": 0.30},
            "infection_site_access": {"inner_membrane": 0.35, "cytoplasm": 0.20, "periplasm": 0.55},
        }
    }

    install_peripheral_membrane_profiles(config)

    for mapping in config["localization"].values():
        assert mapping[INNER_PERIPHERAL_CLASS] == pytest.approx(mapping["cytoplasm"])
