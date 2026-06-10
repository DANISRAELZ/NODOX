from __future__ import annotations

from pathlib import Path

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


def summarize_publication_package(package_dir: Path | str) -> dict[str, object]:
    base = Path(package_dir)
    tables = []
    for table_name in PUBLICATION_TABLES:
        table_path = base / table_name
        tables.append(
            {
                "table": table_name,
                "path": str(table_path),
                "exists": table_path.is_file(),
            }
        )
    figures = list_publication_figures(base / "figures")
    return {
        "package_dir": str(base),
        "exists": base.is_dir(),
        "tables": tables,
        "figures": figures,
        "tables_found": sum(1 for item in tables if item["exists"]),
        "figures_found": sum(1 for item in figures if item["exists"]),
    }
