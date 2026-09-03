from pathlib import Path

import pandas as pd

from src.nodos_funcionales.localization_reporting import append_localization_audit_to_rankings


def test_localization_audit_columns_are_appended_to_phase3_ranking(tmp_path: Path) -> None:
    processed = tmp_path / "data_processed"
    results = tmp_path / "results"
    processed.mkdir()
    results.mkdir()

    pd.DataFrame(
        [
            {
                "protein_id": "P0AFI2",
                "localization_reported": "inner_membrane",
                "uniprot_membrane_topology": "Peripheral membrane protein",
                "localization": "inner_membrane_peripheral",
                "localization_scoring_rule": "uniprot_peripheral_membrane;conservative_access_profile=cytoplasm",
                "physical_accessibility": 0.30,
                "small_molecule_feasibility": 0.80,
                "antibody_feasibility": 0.05,
                "membrane_crossing_penalty": 0.55,
                "infection_site_access": 0.20,
                "infection_site_access_score": 0.20,
            }
        ]
    ).to_csv(processed / "phase3_features.csv", index=False)

    pd.DataFrame(
        [{"protein_id": "P0AFI2", "gene": "parC", "rank_phase3": 10}]
    ).to_csv(results / "ranking_nodos_phase3.csv", index=False)

    append_localization_audit_to_rankings(tmp_path)

    ranking = pd.read_csv(results / "ranking_nodos_phase3.csv")
    row = ranking.iloc[0]
    assert row["localization_reported"] == "inner_membrane"
    assert row["uniprot_membrane_topology"] == "Peripheral membrane protein"
    assert row["localization"] == "inner_membrane_peripheral"
    assert float(row["physical_accessibility"]) == 0.30
    assert "conservative_access_profile=cytoplasm" in row["localization_scoring_rule"]
