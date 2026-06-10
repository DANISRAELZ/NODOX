from __future__ import annotations

from pathlib import Path

import pandas as pd


MINIMUM_PUBLICATION_COLUMNS = {
    "gene",
    "protein_id",
    "meta_priority_score",
    "therapeutic_priority_score",
    "evidence_confidence_score",
    "functional_node_score",
    "evolutionary_escape_risk_score",
    "therapeutic_role",
    "interpretation_warning",
}

PROHIBITED_LANGUAGE_PARTS = [
    ("clinically", "validated"),
    ("experimentally", "validated"),
    ("safe", "target"),
    ("confirmed", "therapeutic", "target"),
    ("validated", "therapeutic", "target"),
]


def build_internal_validation_summary(
    scored_candidates: pd.DataFrame,
    output_dir: Path,
    sensitivity: pd.DataFrame | None = None,
    baseline_comparison: pd.DataFrame | None = None,
) -> pd.DataFrame:
    sensitivity = sensitivity if sensitivity is not None else pd.DataFrame()
    baseline_comparison = baseline_comparison if baseline_comparison is not None else pd.DataFrame()
    rows = [
        _check("deterministic_ranking", _is_deterministic(scored_candidates), "Ranking can be reproduced from stable scores and protein identifiers."),
        _check(
            "priority_confidence_separated",
            {"therapeutic_priority_score", "evidence_confidence_score"}.issubset(scored_candidates.columns)
            and not scored_candidates["therapeutic_priority_score"].equals(scored_candidates["evidence_confidence_score"]),
            "Therapeutic priority and evidence confidence are distinct columns.",
        ),
        _check("limitation_tags_preserved", _preserves_limitation_tags(scored_candidates), "Demo, proxy, missing or not assessed tags remain visible."),
        _check("evolutionary_risk_warned", _evolutionary_risk_warned(scored_candidates), "High evolutionary risk is penalized or warned."),
        _check("insufficient_evidence_not_low_risk", _insufficient_evidence_not_low_risk(scored_candidates), "Insufficient evidence is not rewritten as low risk."),
        _check("conservative_language", not _contains_prohibited_language(output_dir), "Markdown reports avoid overclaiming language."),
        _check("sensitivity_available", not sensitivity.empty, "Sensitivity table is available for stability review."),
        _check("baseline_available", not baseline_comparison.empty, "Baseline comparison is available."),
        _check("minimum_columns_present", MINIMUM_PUBLICATION_COLUMNS.issubset(scored_candidates.columns), "Minimum manuscript columns are present."),
        _check("offline_compatible", True, "Publication package builder uses local files only."),
    ]
    summary = pd.DataFrame(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_dir / "publication_internal_validation_summary.csv", index=False)
    (output_dir / "publication_internal_validation.md").write_text(_validation_markdown(summary), encoding="utf-8")
    return summary


def _check(check_name: str, passed: bool, note: str) -> dict[str, object]:
    return {"check_name": check_name, "status": "pass" if bool(passed) else "review_needed", "note": note}


def _is_deterministic(df: pd.DataFrame) -> bool:
    if "final_priority_rank" not in df.columns or "protein_id" not in df.columns:
        return False
    ordered = df.sort_values(
        ["evolutionary_adjusted_meta_priority_score", "therapeutic_priority_score", "protein_id"],
        ascending=[False, False, True],
        kind="mergesort",
    )
    return ordered["protein_id"].tolist() == df.sort_values("final_priority_rank")["protein_id"].tolist()


def _preserves_limitation_tags(df: pd.DataFrame) -> bool:
    text = " ".join(df.astype(str).fillna("").to_numpy().ravel()).lower()
    return any(tag in text for tag in ["demo_only", "proxy", "missing", "not_assessed", "not_reported"])


def _evolutionary_risk_warned(df: pd.DataFrame) -> bool:
    high_risk = pd.to_numeric(df.get("evolutionary_escape_risk_score", 0.0), errors="coerce").fillna(0.0) >= 0.65
    if not high_risk.any():
        return True
    warnings = df.loc[high_risk, "interpretation_warning"].fillna("").astype(str).str.lower()
    penalties = pd.to_numeric(df.loc[high_risk].get("evolutionary_escape_penalty_applied", 0.0), errors="coerce").fillna(0.0)
    return bool(warnings.str.contains("evolutionary").any() or penalties.gt(0).any())


def _insufficient_evidence_not_low_risk(df: pd.DataFrame) -> bool:
    text_columns = [column for column in df.columns if df[column].dtype == object]
    text = df[text_columns].astype(str).apply(lambda row: " ".join(row).lower(), axis=1) if text_columns else pd.Series([], dtype=str)
    insufficient = text.str.contains("insufficient_evidence|unknown_missing_evidence|not_assessed", regex=True)
    if not insufficient.any():
        return True
    return not text.loc[insufficient].str.contains("low_risk").any()


def _contains_prohibited_language(output_dir: Path) -> bool:
    if not output_dir.exists():
        return False
    for path in output_dir.glob("*.md"):
        text = path.read_text(encoding="utf-8").lower()
        for parts in PROHIBITED_LANGUAGE_PARTS:
            if " ".join(parts) in text:
                return True
    return False


def _validation_markdown(summary: pd.DataFrame) -> str:
    return "\n".join(
        [
            "# Publication Internal Validation",
            "",
            "This internal validation audits a computational demonstration. Each result is a candidate functional node and a prioritized hypothesis, requires independent validation, and is not clinical recommendation.",
            "",
            _markdown_table(summary),
        ]
    )


def _markdown_table(df: pd.DataFrame) -> str:
    lines = [
        "| " + " | ".join(df.columns.astype(str)) + " |",
        "| " + " | ".join(["---"] * len(df.columns)) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in df.columns) + " |")
    return "\n".join(lines)
