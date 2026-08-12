from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


_TEXT_COVERAGE_COLUMNS = (
    "layer_key",
    "before_provider_name",
    "before_retrieval_status",
    "before_evidence_level",
    "before_fallback_reason",
    "after_provider_name",
    "after_retrieval_status",
    "after_evidence_level",
    "after_fallback_reason",
)


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes"}


def _normalize_coverage_dtypes(coverage: pd.DataFrame) -> pd.DataFrame:
    """Make audit text columns safe for post-read provenance updates.

    CSV columns containing only empty strings are commonly inferred by pandas as
    float64/NaN. Stage 5A.4.1 reconciliation writes textual provenance back into
    those columns, so they must use pandas' nullable string dtype first.
    """
    result = coverage.copy()
    for column in _TEXT_COVERAGE_COLUMNS:
        if column not in result.columns:
            result[column] = pd.Series(pd.NA, index=result.index, dtype="string")
        else:
            result[column] = result[column].astype("string")
    return result


def reconcile_stage5a41_audit(result: dict[str, Any]) -> dict[str, Any]:
    """Reconcile Stage 5A.4.1 coverage with the final DEG essentiality manifest.

    The second Phase 3 pass may cause the generic online-only audit to retain the
    pre-overlay essentiality semantics. This function does not change scoring or
    ranking. It only makes the Stage 5A.4.1 coverage/summary reflect the explicit
    final `online_only_essentiality_manifest.json` written after the DEG overlay.
    """
    if str(result.get("status") or "") != "completed":
        return result

    workspace_text = str(result.get("workspace") or "").strip()
    if not workspace_text:
        return result
    workspace = Path(workspace_text)
    results_dir = workspace / "results"

    coverage_path = results_dir / "stage5a41_evidence_coverage.csv"
    manifest_path = results_dir / "stage5a41_manifest.json"
    essentiality_path = results_dir / "online_only_essentiality_manifest.json"
    if not (coverage_path.is_file() and manifest_path.is_file() and essentiality_path.is_file()):
        return result

    coverage = _normalize_coverage_dtypes(pd.read_csv(coverage_path, low_memory=False))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    essentiality = json.loads(essentiality_path.read_text(encoding="utf-8"))

    selected = coverage.index[coverage["layer_key"].astype(str).eq("essentiality")]
    if len(selected) != 1:
        return result
    idx = selected[0]

    matched = int(essentiality.get("matched_candidate_count", essentiality.get("protein_count_mapped", 0)) or 0)
    candidate_count = int(
        manifest.get("candidate_count_after_overlay")
        or (manifest.get("deg_overlay") or {}).get("candidate_count")
        or manifest.get("candidate_count")
        or 0
    )

    coverage.loc[idx, "after_provider_name"] = str(
        essentiality.get("provider_name") or essentiality.get("provider") or "deg"
    )
    coverage.loc[idx, "after_retrieval_status"] = str(
        essentiality.get("retrieval_status") or "versioned_local_dataset_integrated"
    )
    coverage.loc[idx, "after_usable_evidence"] = _safe_bool(essentiality.get("usable_evidence", False))
    coverage.loc[idx, "after_affects_score"] = _safe_bool(essentiality.get("affects_score", False))
    coverage.loc[idx, "after_matched_candidate_count"] = matched
    coverage.loc[idx, "after_evidence_level"] = str(essentiality.get("evidence_level") or "unresolved")
    coverage.loc[idx, "after_fallback_reason"] = str(essentiality.get("fallback_reason") or "")
    coverage.loc[idx, "after_coverage_fraction"] = matched / candidate_count if candidate_count > 0 else None

    before_usable = _safe_bool(coverage.loc[idx, "before_usable_evidence"])
    after_usable = _safe_bool(coverage.loc[idx, "after_usable_evidence"])
    before_affects = _safe_bool(coverage.loc[idx, "before_affects_score"])
    after_affects = _safe_bool(coverage.loc[idx, "after_affects_score"])
    coverage.loc[idx, "usable_evidence_recovered"] = after_usable and not before_usable
    coverage.loc[idx, "score_affecting_evidence_recovered"] = after_affects and not before_affects

    coverage.to_csv(coverage_path, index=False)

    before_usable_series = coverage["before_usable_evidence"].map(_safe_bool)
    after_usable_series = coverage["after_usable_evidence"].map(_safe_bool)
    before_affects_series = coverage["before_affects_score"].map(_safe_bool)
    after_affects_series = coverage["after_affects_score"].map(_safe_bool)
    usable_recovered = coverage["usable_evidence_recovered"].map(_safe_bool)
    score_recovered = coverage["score_affecting_evidence_recovered"].map(_safe_bool)

    manifest["usable_scoring_layers_before"] = int(before_usable_series.sum())
    manifest["usable_scoring_layers_after"] = int(after_usable_series.sum())
    manifest["score_affecting_layers_before"] = int(before_affects_series.sum())
    manifest["score_affecting_layers_after"] = int(after_affects_series.sum())
    manifest["new_usable_evidence_layers"] = coverage.loc[usable_recovered, "layer_key"].astype(str).tolist()
    manifest["new_score_affecting_layers"] = coverage.loc[score_recovered, "layer_key"].astype(str).tolist()
    manifest["audit_reconciled_after_deg_overlay"] = True
    manifest["audit_reconciliation_source"] = str(essentiality_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    updated = dict(result)
    updated["new_score_affecting_layers"] = manifest["new_score_affecting_layers"]
    updated["new_usable_evidence_layers"] = manifest["new_usable_evidence_layers"]
    updated["audit_reconciled_after_deg_overlay"] = True
    return updated
