from __future__ import annotations

from pathlib import Path

import pandas as pd


LOCALIZATION_AUDIT_COLUMNS = [
    "localization_reported",
    "uniprot_membrane_topology",
    "localization",
    "localization_scoring_rule",
    "physical_accessibility",
    "small_molecule_feasibility",
    "antibody_feasibility",
    "membrane_crossing_penalty",
    "infection_site_access",
    "infection_site_access_score",
]


def append_localization_audit_to_rankings(base_dir: Path) -> None:
    """Append observable localization/accessibility semantics to exported rankings.

    This never recomputes scores. It only joins already-materialized feature
    columns by protein_id so every localization value that affected scoring is
    visible in the publication-facing ranking.
    """
    base_dir = Path(base_dir)
    feature_path = base_dir / "data_processed" / "phase3_features.csv"
    if not feature_path.is_file():
        feature_path = base_dir / "data_processed" / "phase2_features.csv"
    if not feature_path.is_file():
        return

    features = pd.read_csv(feature_path, low_memory=False)
    if "protein_id" not in features.columns:
        return
    available = [column for column in LOCALIZATION_AUDIT_COLUMNS if column in features.columns]
    if not available:
        return
    audit = features[["protein_id", *available]].drop_duplicates(subset="protein_id", keep="first")

    results_dir = base_dir / "results"
    for filename in [
        "ranking_nodos.csv",
        "ranking_nodos_phase3.csv",
        "ranking_nodos_phase3_real_candidates.csv",
    ]:
        path = results_dir / filename
        if not path.is_file():
            continue
        ranking = pd.read_csv(path, low_memory=False)
        if "protein_id" not in ranking.columns:
            continue
        stale = [column for column in available if column in ranking.columns]
        if stale:
            ranking = ranking.drop(columns=stale)
        ranking = ranking.merge(audit, on="protein_id", how="left")
        ranking.to_csv(path, index=False)
