from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .baseline_comparison import write_baseline_comparison
from .functional_node_model import FunctionalNodeModel
from .publication_figures import build_publication_figures
from .publication_validation import build_internal_validation_summary


def build_publication_package(results_dir: Path | str, output_dir: Path | str) -> dict[str, object]:
    results_path = Path(results_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    ranking = _read_csv(results_path / "ranking_nodos.csv")
    model = FunctionalNodeModel()
    scored = model.score_candidates(ranking)
    sensitivity = _read_csv(results_path / "sensitivity_analysis.csv")

    _write_phase1_publication_tables(scored, results_path, output_path)
    baseline = write_baseline_comparison(scored, output_path)
    validation = build_internal_validation_summary(scored, output_path, sensitivity=sensitivity, baseline_comparison=baseline)
    figures = build_publication_figures(output_path, output_path / "figures")
    _update_readme_with_figures(output_path, figures)
    manifest = _write_manifest(output_path, scored, baseline, validation, model, figures)
    return manifest


def _write_phase1_publication_tables(scored: pd.DataFrame, results_dir: Path, output_dir: Path) -> None:
    top_columns = [
        "final_priority_rank",
        "gene",
        "protein_id",
        "therapeutic_role",
        "meta_priority_score",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "functional_node_score",
        "evolutionary_escape_risk_score",
        "interpretation_warning",
    ]
    scored[[column for column in top_columns if column in scored.columns]].head(20).to_csv(
        output_dir / "publication_table_1_top_candidates.csv",
        index=False,
    )
    decomposition_columns = [
        "gene",
        "protein_id",
        "antibiotic_target_score",
        "antivirulence_target_score",
        "functional_node_score",
        "functional_node_theory_score",
        "selectivity_score",
        "clinical_context_score",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "evolutionary_escape_risk_score",
        "meta_priority_score",
    ]
    scored[[column for column in decomposition_columns if column in scored.columns]].to_csv(
        output_dir / "publication_table_2_score_decomposition.csv",
        index=False,
    )
    _copy_or_write(
        results_dir / "evolutionary_escape_risk_audit.csv",
        output_dir / "publication_table_3_evolutionary_risk.csv",
        scored[[column for column in ["gene", "protein_id", "evolutionary_escape_risk_score", "evolutionary_escape_penalty_applied"] if column in scored.columns]],
    )
    _copy_or_write(
        results_dir / "sensitivity_analysis.csv",
        output_dir / "publication_table_4_sensitivity_stability.csv",
        pd.DataFrame(columns=["score_name", "scenario", "protein_id", "rank", "rank_delta_vs_base"]),
    )
    _copy_or_write(
        results_dir / "evidence_strength_audit.csv",
        output_dir / "publication_table_5_evidence_provenance.csv",
        scored[[column for column in ["gene", "protein_id", "evidence_confidence_score", "interpretation_warning"] if column in scored.columns]],
    )
    scored.apply(model_explanation, axis=1).to_frame("candidate_interpretation").to_csv(
        output_dir / "publication_candidate_interpretation.csv",
        index=False,
    )
    _write_summary_markdown(output_dir, scored)


def model_explanation(row: pd.Series) -> str:
    return (
        f"{row.get('gene', 'not_reported')}/{row.get('protein_id', 'not_reported')}: "
        f"candidate functional node ranked as prioritized hypothesis; "
        f"role={row.get('therapeutic_role', 'not_reported')}; "
        f"therapeutic_priority_score={float(row.get('therapeutic_priority_score', 0.0)):.3f}; "
        f"evidence_confidence_score={float(row.get('evidence_confidence_score', 0.0)):.3f}; "
        "requires independent validation."
    )


def _copy_or_write(source: Path, target: Path, fallback: pd.DataFrame) -> None:
    if source.exists():
        pd.read_csv(source).to_csv(target, index=False)
    else:
        fallback.to_csv(target, index=False)


def _write_summary_markdown(output_dir: Path, scored: pd.DataFrame) -> None:
    main_lines = [
        "# Publication Main Results Summary",
        "",
        "This package reports candidate functional node hypotheses from a computational demonstration.",
        "Scores prioritize review; they are not clinical recommendation and require independent validation.",
        "",
        f"- Candidates scored: {len(scored)}",
        "- Main ranking: `publication_table_1_top_candidates.csv`",
        "- Score decomposition: `publication_table_2_score_decomposition.csv`",
        "- Internal validation: `publication_internal_validation.md`",
    ]
    (output_dir / "publication_main_results_summary.md").write_text("\n".join(main_lines), encoding="utf-8")
    methods_lines = [
        "# Publication Methods Model Summary",
        "",
        "The model keeps therapeutic priority, evidence confidence, functional node score and evolutionary escape risk as separate variables.",
        "`evidence_confidence_score` supports interpretation and warnings; it does not automatically create a validated biological conclusion.",
        "The package is generated offline from local result tables.",
    ]
    (output_dir / "publication_methods_model_summary.md").write_text("\n".join(methods_lines), encoding="utf-8")
    limits_lines = [
        "# Publication Limitations",
        "",
        "- Computational demonstration only.",
        "- Candidate functional node rankings are prioritized hypotheses.",
        "- Requires independent validation before biological, pharmacological or clinical use.",
        "- Missing, proxy, demo, controlled, not assessed and not reported labels remain limitations, not negative evidence.",
    ]
    (output_dir / "publication_limitations.md").write_text("\n".join(limits_lines), encoding="utf-8")
    readme_lines = [
        "# README Publication Package",
        "",
        "Reproduce with:",
        "",
        "```bash",
        "python -m src.nodos_funcionales.publication_package_builder --results-dir results --output-dir results/publication_package",
        "```",
    ]
    (output_dir / "README_publication_package.md").write_text("\n".join(readme_lines), encoding="utf-8")


def _update_readme_with_figures(output_dir: Path, figures: list[dict[str, object]]) -> None:
    readme_path = output_dir / "README_publication_package.md"
    existing = readme_path.read_text(encoding="utf-8") if readme_path.exists() else "# README Publication Package\n"
    generated = [item for item in figures if item.get("status") == "generated"]
    skipped = [item for item in figures if item.get("status") != "generated"]
    lines = [
        existing.rstrip(),
        "",
        "## Figures",
        "",
        "The `figures/` folder contains reproducible interpretative figures generated from consolidated local publication tables.",
        "They describe computational demonstration results and do not replace conservative interpretation.",
        "",
    ]
    for item in generated:
        lines.append(f"- `figures/{item['png']}` from `{item['source_file']}`")
    for item in skipped:
        lines.append(f"- `{item['figure']}` skipped: {item['note']}")
    readme_path.write_text("\n".join(lines), encoding="utf-8")


def _write_manifest(
    output_dir: Path,
    scored: pd.DataFrame,
    baseline: pd.DataFrame,
    validation: pd.DataFrame,
    model: FunctionalNodeModel,
    figures: list[dict[str, object]],
) -> dict[str, object]:
    files = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    manifest = {
        "package_type": "publication_computational_model_validation",
        "candidate_count": int(len(scored)),
        "baseline_rows": int(len(baseline)),
        "internal_validation_checks": int(len(validation)),
        "model_config": model.config_as_dict(),
        "files": files,
        "figures": {
            "directory": "figures",
            "items": figures,
            "generated_count": sum(1 for item in figures if item.get("status") == "generated"),
            "skipped_count": sum(1 for item in figures if item.get("status") != "generated"),
        },
        "interpretation": "prioritized hypothesis; computational demonstration; not clinical recommendation",
    }
    (output_dir / "publication_results_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return manifest


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build offline publication package for Nodos Funcionales.")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--output-dir", default="results/publication_package")
    args = parser.parse_args()
    build_publication_package(args.results_dir, args.output_dir)


if __name__ == "__main__":
    main()
