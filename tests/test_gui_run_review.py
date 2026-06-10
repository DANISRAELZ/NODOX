from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.gui_run_review import (
    compare_publication_packages,
    detect_run_outputs,
    detect_run_publication_package,
    get_conservative_run_review_warning,
    read_run_logs,
    summarize_gui_run,
    write_run_summary,
)
from src.nodos_funcionales.pipeline_runner import write_run_manifest
from src.nodos_funcionales.publication_gui_readers import PUBLICATION_FIGURES, PUBLICATION_TABLES


FORBIDDEN_PHRASES = [
    "clinically" + " validated",
    "experimentally" + " validated",
    "safe" + " target",
    "confirmed" + " therapeutic target",
    "validated" + " therapeutic target",
]


def test_summarize_gui_run_tolerates_incomplete_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "gui_runs" / "gui_run_incomplete"
    run_dir.mkdir(parents=True)

    summary = summarize_gui_run(run_dir)

    assert summary["run_id"] == "gui_run_incomplete"
    assert summary["has_stdout_log"] is False
    assert summary["has_publication_package"] is False
    assert summary["errors"]


def test_read_run_logs_truncates_long_logs(tmp_path: Path) -> None:
    run_dir = tmp_path / "gui_run_logs"
    run_dir.mkdir()
    (run_dir / "pipeline_stdout.log").write_text("x" * 50, encoding="utf-8")

    logs = read_run_logs(run_dir, max_chars=10)

    assert logs["stdout"]["text"] == "x" * 10
    assert logs["stdout"]["truncated"] is True
    assert logs["stderr"]["exists"] is False


def test_detect_run_outputs_lists_files(tmp_path: Path) -> None:
    run_dir = tmp_path / "gui_run_outputs"
    output_file = run_dir / "outputs" / "results" / "ranking_nodos.csv"
    output_file.parent.mkdir(parents=True)
    output_file.write_text("gene,protein_id\nA,P1\n", encoding="utf-8")

    outputs = detect_run_outputs(run_dir)

    assert outputs[0]["relative_path"] == "results\\ranking_nodos.csv" or outputs[0]["relative_path"] == "results/ranking_nodos.csv"


def test_detect_run_publication_package_finds_tables_and_figures(tmp_path: Path) -> None:
    run_dir = tmp_path / "gui_run_package"
    package_dir = run_dir / "publication_package"
    figures_dir = package_dir / "figures"
    figures_dir.mkdir(parents=True)
    for table in PUBLICATION_TABLES:
        pd.DataFrame([{"gene": "A", "protein_id": "P1"}]).to_csv(package_dir / table, index=False)
    for figure in PUBLICATION_FIGURES:
        (figures_dir / figure).write_bytes(b"png")

    summary = detect_run_publication_package(run_dir)

    assert summary["tables_found"] == 6
    assert summary["figures_found"] == 6


def test_write_run_summary_creates_markdown(tmp_path: Path) -> None:
    run_dir = tmp_path / "gui_run_summary"
    write_run_manifest(
        run_dir=run_dir,
        run_id="gui_run_summary",
        command=["python", "run_pipeline.py"],
        input_paths={"organism": "Example bacterium"},
        output_dir=run_dir / "outputs",
        status="not_started",
        return_code=None,
    )

    result = write_run_summary(run_dir)

    summary_path = Path(result["summary_path"])
    assert summary_path.is_file()
    assert "computationally prioritized hypotheses requiring independent validation" in summary_path.read_text(encoding="utf-8")


def test_compare_publication_packages_creates_outputs_without_modifying_base(tmp_path: Path) -> None:
    base = tmp_path / "base_package"
    run = tmp_path / "run_package"
    review = tmp_path / "review"
    base.mkdir()
    run.mkdir()
    pd.DataFrame(
        [
            {
                "gene": "base_gene",
                "protein_id": "B1",
                "therapeutic_priority_score": 0.5,
                "evidence_confidence_score": 0.4,
                "evolutionary_escape_risk_score": 0.2,
            }
        ]
    ).to_csv(base / "publication_table_1_top_candidates.csv", index=False)
    pd.DataFrame(
        [
            {
                "gene": "run_gene",
                "protein_id": "R1",
                "therapeutic_priority_score": 0.6,
                "evidence_confidence_score": 0.3,
                "evolutionary_escape_risk_score": 0.1,
            }
        ]
    ).to_csv(run / "publication_table_1_top_candidates.csv", index=False)
    before = sorted(path.name for path in base.iterdir())

    status = compare_publication_packages(base, run, review)

    after = sorted(path.name for path in base.iterdir())
    assert before == after
    assert (review / "run_comparison_summary.md").is_file()
    assert (review / "run_status.json").is_file()
    assert status["candidate_summary"]["base_candidate_count"] == 1
    assert status["candidate_summary"]["run_top_genes"] == ["run_gene"]


def test_gui_run_review_language_is_conservative() -> None:
    text = get_conservative_run_review_warning().lower()
    assert "computationally prioritized hypotheses requiring independent validation" in text
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in text
