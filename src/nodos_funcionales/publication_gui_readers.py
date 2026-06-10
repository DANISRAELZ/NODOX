from __future__ import annotations

from pathlib import Path
import json

import pandas as pd


PUBLICATION_TABLES = [
    "publication_table_1_top_candidates.csv",
    "publication_table_2_score_decomposition.csv",
    "publication_table_3_evolutionary_risk.csv",
    "publication_table_4_sensitivity_stability.csv",
    "publication_table_5_evidence_provenance.csv",
    "publication_table_6_baseline_comparison.csv",
]

PUBLICATION_FIGURES = [
    "figure_1_top_candidates_meta_priority.png",
    "figure_2_priority_vs_confidence.png",
    "figure_3_score_decomposition.png",
    "figure_4_evolutionary_risk_vs_priority.png",
    "figure_5_ranking_stability.png",
    "figure_6_therapeutic_role_distribution.png",
]
PUBLICATION_README = "README_publication_package.md"
PUBLICATION_MANIFEST = "publication_results_manifest.json"
CONSERVATIVE_GUI_WARNING = (
    "This candidate should be interpreted as a computationally prioritized "
    "hypothesis requiring independent validation."
)


def check_publication_package_exists(package_dir: Path | str) -> bool:
    return Path(package_dir).is_dir()


def load_publication_table(path: Path | str) -> tuple[pd.DataFrame, str | None]:
    table_path = Path(path)
    if not table_path.exists():
        return pd.DataFrame(), f"Missing publication table: {table_path}"
    if not table_path.is_file():
        return pd.DataFrame(), f"Publication table path is not a file: {table_path}"
    try:
        return pd.read_csv(table_path), None
    except (OSError, UnicodeDecodeError, pd.errors.ParserError) as exc:
        return pd.DataFrame(), f"Could not read publication table {table_path}: {exc}"


def list_publication_tables(package_dir: Path | str) -> list[dict[str, object]]:
    base = Path(package_dir)
    rows = []
    for table_name in PUBLICATION_TABLES:
        table_path = base / table_name
        rows.append(
            {
                "table": table_name,
                "path": str(table_path),
                "exists": table_path.is_file(),
            }
        )
    return rows


def list_publication_figures(figures_dir: Path | str) -> list[dict[str, object]]:
    base = Path(figures_dir)
    rows = []
    for figure_name in PUBLICATION_FIGURES:
        figure_path = base / figure_name
        rows.append(
            {
                "figure": figure_name,
                "path": str(figure_path),
                "exists": figure_path.is_file(),
            }
        )
    return rows


def load_publication_manifest(package_dir: Path | str) -> tuple[dict[str, object], str | None]:
    manifest_path = Path(package_dir) / PUBLICATION_MANIFEST
    if not manifest_path.exists():
        return {}, f"Missing publication manifest: {manifest_path}"
    if not manifest_path.is_file():
        return {}, f"Publication manifest path is not a file: {manifest_path}"
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {}, f"Could not read publication manifest {manifest_path}: {exc}"


def summarize_publication_package(package_dir: Path | str) -> dict[str, object]:
    base = Path(package_dir)
    tables = list_publication_tables(base)
    figures = list_publication_figures(base / "figures")
    manifest, manifest_error = load_publication_manifest(base)
    readme_path = base / PUBLICATION_README
    return {
        "package_dir": str(base),
        "exists": base.is_dir(),
        "tables": tables,
        "figures": figures,
        "tables_found": sum(1 for item in tables if item["exists"]),
        "figures_found": sum(1 for item in figures if item["exists"]),
        "manifest_exists": manifest_error is None,
        "manifest": manifest,
        "manifest_error": manifest_error,
        "readme_path": str(readme_path),
        "readme_exists": readme_path.is_file(),
    }


def build_candidate_index(package_dir: Path | str) -> list[dict[str, object]]:
    table, error = load_publication_table(Path(package_dir) / "publication_table_1_top_candidates.csv")
    if error or table.empty:
        return []
    rows = []
    for row_number, row in table.reset_index(drop=True).iterrows():
        gene = _text(row.get("gene", ""))
        protein_id = _text(row.get("protein_id", ""))
        label_parts = [part for part in [gene, protein_id] if part]
        label = " / ".join(label_parts) if label_parts else f"candidate_{row_number + 1}"
        rank = row.get("final_priority_rank", row.get("rank", row_number + 1))
        rows.append(
            {
                "candidate_id": protein_id or gene or label,
                "label": f"{rank}. {label}",
                "rank": rank,
                "gene": gene or "not_reported",
                "protein_id": protein_id or "not_reported",
            }
        )
    return rows


def get_candidate_details(package_dir: Path | str, candidate_id: str) -> dict[str, object]:
    base = Path(package_dir)
    details: dict[str, object] = {
        "candidate_id": candidate_id,
        "identification": {},
        "scores": {},
        "interpretation": {
            "fixed_warning": get_conservative_gui_warning(),
        },
        "source_rows": {},
        "warnings": [],
    }
    top_table, error = load_publication_table(base / "publication_table_1_top_candidates.csv")
    if error:
        details["warnings"].append(error)
        return details
    row = _find_candidate_row(top_table, candidate_id)
    if row is None:
        details["warnings"].append(f"Candidate not found in top candidates table: {candidate_id}")
        return details

    details["identification"] = _select_existing(
        row,
        ["final_priority_rank", "rank", "gene", "protein_id", "product", "organism", "therapeutic_role"],
    )
    details["scores"] = _select_existing(
        row,
        [
            "meta_priority_score",
            "therapeutic_priority_score",
            "evidence_confidence_score",
            "functional_node_score",
            "functional_node_theory_score",
            "evolutionary_escape_risk_score",
            "evolutionary_escape_penalty_applied",
        ],
    )
    details["interpretation"].update(
        _select_existing(
            row,
            [
                "interpretation_warning",
                "top_positive_drivers",
                "top_negative_drivers",
                "missing_evidence_flags",
                "evidence_strength",
                "evidence_level",
                "provenance_status",
                "retrieval_mode",
                "cache_status",
            ],
        )
    )

    decomposition, _ = load_publication_table(base / "publication_table_2_score_decomposition.csv")
    evolutionary, _ = load_publication_table(base / "publication_table_3_evolutionary_risk.csv")
    sensitivity, _ = load_publication_table(base / "publication_table_4_sensitivity_stability.csv")
    provenance, _ = load_publication_table(base / "publication_table_5_evidence_provenance.csv")
    baseline, _ = load_publication_table(base / "publication_table_6_baseline_comparison.csv")

    for name, table in [
        ("score_decomposition", decomposition),
        ("evolutionary_risk", evolutionary),
        ("evidence_provenance", provenance),
    ]:
        matched = _find_candidate_row(table, candidate_id)
        if matched is not None:
            details["source_rows"][name] = matched.to_dict()

    stability = _candidate_stability_summary(sensitivity, candidate_id)
    if stability:
        details["interpretation"]["ranking_stability_label"] = stability["ranking_stability_label"]
        details["source_rows"]["sensitivity_stability"] = stability

    baseline_summary = _candidate_baseline_summary(baseline, candidate_id)
    if baseline_summary:
        details["interpretation"]["baseline_comparison_summary"] = baseline_summary

    return details


def get_conservative_gui_warning() -> str:
    return CONSERVATIVE_GUI_WARNING


def _candidate_stability_summary(table: pd.DataFrame, candidate_id: str) -> dict[str, object]:
    if table.empty or "rank_delta_vs_base" not in table.columns:
        return {}
    matched = _matching_rows(table, candidate_id)
    if matched.empty:
        return {}
    deltas = pd.to_numeric(matched["rank_delta_vs_base"], errors="coerce").abs().dropna()
    max_delta = float(deltas.max()) if not deltas.empty else 0.0
    if max_delta <= 1:
        label = "stable_or_low_shift"
    elif max_delta <= 3:
        label = "moderate_shift_review"
    else:
        label = "high_shift_review"
    return {
        "max_abs_rank_delta": max_delta,
        "ranking_stability_label": label,
    }


def _candidate_baseline_summary(table: pd.DataFrame, candidate_id: str) -> str:
    if table.empty:
        return ""
    matched = _matching_rows(table, candidate_id)
    if matched.empty:
        return ""
    parts = []
    for _, row in matched.head(6).iterrows():
        baseline = _text(row.get("baseline_name", "baseline"))
        delta = row.get("rank_delta", "not_reported")
        baseline_rank = row.get("baseline_rank", "not_reported")
        parts.append(f"{baseline}: baseline_rank={baseline_rank}; rank_delta={delta}")
    return " | ".join(parts)


def _matching_rows(table: pd.DataFrame, candidate_id: str) -> pd.DataFrame:
    if table.empty:
        return pd.DataFrame()
    candidate = str(candidate_id).strip()
    masks = []
    for column in ["protein_id", "gene", "candidate_id"]:
        if column in table.columns:
            masks.append(table[column].fillna("").astype(str).str.strip().eq(candidate))
    if not masks:
        return pd.DataFrame()
    mask = masks[0]
    for extra in masks[1:]:
        mask = mask | extra
    return table.loc[mask].copy()


def _find_candidate_row(table: pd.DataFrame, candidate_id: str) -> pd.Series | None:
    matched = _matching_rows(table, candidate_id)
    if matched.empty:
        return None
    return matched.iloc[0]


def _select_existing(row: pd.Series, columns: list[str]) -> dict[str, object]:
    return {column: row[column] for column in columns if column in row.index}


def _text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()
