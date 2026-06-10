from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.nodos_funcionales.publication_gui_readers import (
    PUBLICATION_FIGURES,
    PUBLICATION_TABLES,
    check_publication_package_exists,
    list_publication_figures,
    load_publication_table,
    summarize_publication_package,
)


def test_publication_gui_readers_summarize_existing_package(tmp_path: Path) -> None:
    package_dir = tmp_path / "publication_package"
    figures_dir = package_dir / "figures"
    figures_dir.mkdir(parents=True)
    for table_name in PUBLICATION_TABLES:
        pd.DataFrame([{"gene": "a", "protein_id": "P1"}]).to_csv(package_dir / table_name, index=False)
    for figure_name in PUBLICATION_FIGURES:
        (figures_dir / figure_name).write_bytes(b"not-a-real-png-for-reader-test")

    summary = summarize_publication_package(package_dir)

    assert check_publication_package_exists(package_dir)
    assert summary["exists"] is True
    assert summary["tables_found"] == 6
    assert summary["figures_found"] == 6
    assert [item["table"] for item in summary["tables"]] == PUBLICATION_TABLES
    assert [item["figure"] for item in summary["figures"]] == PUBLICATION_FIGURES


def test_load_publication_table_reports_missing_without_exception(tmp_path: Path) -> None:
    table, error = load_publication_table(tmp_path / "missing.csv")

    assert table.empty
    assert error is not None
    assert "Missing publication table" in error


def test_list_publication_figures_marks_missing_files(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()
    (figures_dir / PUBLICATION_FIGURES[0]).write_bytes(b"placeholder")

    figures = list_publication_figures(figures_dir)

    assert figures[0]["exists"] is True
    assert all(item["exists"] is False for item in figures[1:])
