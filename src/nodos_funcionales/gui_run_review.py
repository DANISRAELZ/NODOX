from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .pipeline_runner import CONSERVATIVE_INTERPRETATION, read_gui_run_manifest, write_run_manifest
from .publication_gui_readers import PUBLICATION_FIGURES, PUBLICATION_TABLES, summarize_publication_package
from .publication_package_builder import build_publication_package


CRITICAL_COLUMNS = [
    "gene",
    "protein_id",
    "therapeutic_priority_score",
    "evidence_confidence_score",
    "evolutionary_escape_risk_score",
]


def get_gui_run_paths(run_dir: Path | str) -> dict[str, Path]:
    base = Path(run_dir)
    return {
        "run_dir": base,
        "manifest": base / "run_manifest.json",
        "stdout_log": base / "pipeline_stdout.log",
        "stderr_log": base / "pipeline_stderr.log",
        "outputs": base / "outputs",
        "publication_package": base / "publication_package",
        "review": base / "review",
        "run_summary": base / "review" / "run_summary.md",
        "comparison_summary": base / "review" / "run_comparison_summary.md",
        "run_status": base / "review" / "run_status.json",
    }


def summarize_gui_run(run_dir: Path | str) -> dict[str, object]:
    paths = get_gui_run_paths(run_dir)
    manifest, manifest_error = read_gui_run_manifest(paths["run_dir"])
    return {
        "run_id": manifest.get("run_id", paths["run_dir"].name) if manifest else paths["run_dir"].name,
        "status": manifest.get("status", "not_reported") if manifest else "not_reported",
        "has_stdout_log": paths["stdout_log"].is_file(),
        "has_stderr_log": paths["stderr_log"].is_file(),
        "has_outputs_dir": paths["outputs"].is_dir(),
        "has_publication_package": paths["publication_package"].is_dir(),
        "has_review": paths["review"].is_dir(),
        "warnings": manifest.get("warnings", []) if manifest else [],
        "errors": ([manifest_error] if manifest_error else []) + (manifest.get("errors", []) if manifest else []),
        "conservative_interpretation": get_conservative_run_review_warning(),
    }


def read_run_logs(run_dir: Path | str, max_chars: int = 12000) -> dict[str, object]:
    paths = get_gui_run_paths(run_dir)
    logs = {}
    for key, path_key in [("stdout", "stdout_log"), ("stderr", "stderr_log")]:
        path = paths[path_key]
        if not path.is_file():
            logs[key] = {"exists": False, "text": "", "truncated": False, "path": str(path)}
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        logs[key] = {
            "exists": True,
            "text": text[:max_chars],
            "truncated": len(text) > max_chars,
            "path": str(path),
        }
    return logs


def detect_run_outputs(run_dir: Path | str) -> list[dict[str, object]]:
    outputs_dir = get_gui_run_paths(run_dir)["outputs"]
    if not outputs_dir.is_dir():
        return []
    rows = []
    for path in sorted(outputs_dir.rglob("*")):
        if path.is_file():
            rows.append(
                {
                    "relative_path": str(path.relative_to(outputs_dir)),
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    return rows


def detect_run_publication_package(run_dir: Path | str) -> dict[str, object]:
    return summarize_publication_package(get_gui_run_paths(run_dir)["publication_package"])


def write_run_summary(run_dir: Path | str) -> dict[str, object]:
    paths = get_gui_run_paths(run_dir)
    paths["review"].mkdir(parents=True, exist_ok=True)
    summary = summarize_gui_run(run_dir)
    package_summary = detect_run_publication_package(run_dir)
    lines = [
        "# GUI Run Summary",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- status: `{summary['status']}`",
        f"- stdout log: `{summary['has_stdout_log']}`",
        f"- stderr log: `{summary['has_stderr_log']}`",
        f"- outputs detected: `{len(detect_run_outputs(run_dir))}`",
        f"- run publication package: `{summary['has_publication_package']}`",
        f"- publication tables found: `{package_summary.get('tables_found', 0)}`",
        f"- publication figures found: `{package_summary.get('figures_found', 0)}`",
        "",
        get_conservative_run_review_warning(),
    ]
    paths["run_summary"].write_text("\n".join(lines), encoding="utf-8")
    return {"summary_path": str(paths["run_summary"]), "summary": summary}


def compare_publication_packages(
    base_package_dir: Path | str,
    run_package_dir: Path | str,
    output_dir: Path | str,
) -> dict[str, object]:
    base = Path(base_package_dir)
    run = Path(run_package_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table_rows = [
        {"table": name, "base_exists": (base / name).is_file(), "run_exists": (run / name).is_file()}
        for name in PUBLICATION_TABLES
    ]
    figure_rows = [
        {
            "figure": name,
            "base_exists": (base / "figures" / name).is_file(),
            "run_exists": (run / "figures" / name).is_file(),
        }
        for name in PUBLICATION_FIGURES
    ]
    candidate_summary = {
        "base_candidate_count": len(_top_candidates(base)),
        "run_candidate_count": len(_top_candidates(run)),
        "base_top_genes": _top_genes(base),
        "run_top_genes": _top_genes(run),
        "base_critical_columns_present": _critical_columns(base),
        "run_critical_columns_present": _critical_columns(run),
    }
    status = {
        "base_package_dir": str(base),
        "run_package_dir": str(run),
        "base_summary": summarize_publication_package(base),
        "run_summary": summarize_publication_package(run),
        "tables": table_rows,
        "figures": figure_rows,
        "candidate_summary": candidate_summary,
        "conservative_interpretation": get_conservative_run_review_warning(),
    }
    (out / "run_status.json").write_text(json.dumps(status, indent=2, ensure_ascii=True), encoding="utf-8")
    lines = [
        "# GUI Run Publication Package Comparison",
        "",
        f"- Base package: `{base}`",
        f"- Run package: `{run}`",
        f"- Base candidates: `{candidate_summary['base_candidate_count']}`",
        f"- Run candidates: `{candidate_summary['run_candidate_count']}`",
        f"- Base top genes: `{', '.join(candidate_summary['base_top_genes']) or 'not_reported'}`",
        f"- Run top genes: `{', '.join(candidate_summary['run_top_genes']) or 'not_reported'}`",
        "",
        "## Tables",
        "",
        *[f"- {row['table']}: base={row['base_exists']}; run={row['run_exists']}" for row in table_rows],
        "",
        "## Figures",
        "",
        *[f"- {row['figure']}: base={row['base_exists']}; run={row['run_exists']}" for row in figure_rows],
        "",
        get_conservative_run_review_warning(),
    ]
    (out / "run_comparison_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return status


def build_run_publication_package(run_dir: Path | str, source_results_dir: Path | str | None = None) -> dict[str, object]:
    paths = get_gui_run_paths(run_dir)
    results_dir = Path(source_results_dir) if source_results_dir is not None else paths["outputs"] / "results"
    output_dir = paths["publication_package"]
    if not (results_dir / "ranking_nodos.csv").is_file():
        return {
            "status": "skipped",
            "error": f"Missing isolated source results table: {results_dir / 'ranking_nodos.csv'}",
            "publication_package_dir": str(output_dir),
        }
    manifest = build_publication_package(results_dir, output_dir)
    run_manifest, error = read_gui_run_manifest(paths["run_dir"])
    if not error and run_manifest:
        write_run_manifest(
            run_dir=paths["run_dir"],
            run_id=str(run_manifest.get("run_id", paths["run_dir"].name)),
            command=list(run_manifest.get("command", [])),
            input_paths=dict(run_manifest.get("input_paths", {})),
            output_dir=run_manifest.get("output_dir", paths["outputs"]),
            status=str(run_manifest.get("status", "not_reported")),
            return_code=run_manifest.get("return_code"),
            warnings=list(run_manifest.get("warnings", [])),
            errors=list(run_manifest.get("errors", [])),
            execution_mode=str(run_manifest.get("execution_mode", "controlled_gui")),
            allow_execution=bool(run_manifest.get("allow_execution", False)),
            package_generated=True,
            comparison_generated=bool(run_manifest.get("comparison_generated", False)),
            completed_at=run_manifest.get("completed_at"),
        )
    return {"status": "generated", "publication_package_dir": str(output_dir), "manifest": manifest}


def get_conservative_run_review_warning() -> str:
    return CONSERVATIVE_INTERPRETATION


def _top_candidates(package_dir: Path) -> pd.DataFrame:
    path = package_dir / "publication_table_1_top_candidates.csv"
    if not path.is_file():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, UnicodeDecodeError, pd.errors.ParserError):
        return pd.DataFrame()


def _top_genes(package_dir: Path) -> list[str]:
    table = _top_candidates(package_dir)
    if table.empty or "gene" not in table.columns:
        return []
    return table["gene"].dropna().astype(str).head(10).tolist()


def _critical_columns(package_dir: Path) -> list[str]:
    table = _top_candidates(package_dir)
    if table.empty:
        return []
    return [column for column in CRITICAL_COLUMNS if column in table.columns]
