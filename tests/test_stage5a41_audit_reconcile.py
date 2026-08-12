import json
from pathlib import Path

import pandas as pd
import pytest

from src.nodos_funcionales.stage5a41_audit_reconcile import reconcile_stage5a41_audit


def test_reconcile_stage5a41_audit_adds_essentiality_as_recovered_layer(tmp_path: Path):
    workspace = tmp_path / "workspace"
    results = workspace / "results"
    results.mkdir(parents=True)

    coverage = pd.DataFrame(
        [
            {
                "layer_key": "essentiality",
                "before_provider_name": "uniprot_seed",
                "before_retrieval_status": "seed_not_essentiality_evidence",
                "before_usable_evidence": False,
                "before_affects_score": False,
                "before_matched_candidate_count": 0,
                "before_evidence_level": "unresolved",
                "before_fallback_reason": "",
                "before_coverage_fraction": 0.0,
                "after_provider_name": "uniprot_seed",
                "after_retrieval_status": "seed_not_essentiality_evidence",
                "after_usable_evidence": False,
                "after_affects_score": False,
                "after_matched_candidate_count": 0,
                "after_evidence_level": "unresolved",
                "after_fallback_reason": "",
                "after_coverage_fraction": 0.0,
                "usable_evidence_recovered": False,
                "score_affecting_evidence_recovered": False,
            },
            {
                "layer_key": "virulence",
                "before_provider_name": "vfdb",
                "before_retrieval_status": "invalid",
                "before_usable_evidence": False,
                "before_affects_score": False,
                "before_matched_candidate_count": 0,
                "before_evidence_level": "unresolved",
                "before_fallback_reason": "",
                "before_coverage_fraction": 0.0,
                "after_provider_name": "vfdb",
                "after_retrieval_status": "local_dataset_available",
                "after_usable_evidence": True,
                "after_affects_score": True,
                "after_matched_candidate_count": 39,
                "after_evidence_level": "versioned_external_virulence_dataset",
                "after_fallback_reason": "",
                "after_coverage_fraction": 39 / 1554,
                "usable_evidence_recovered": True,
                "score_affecting_evidence_recovered": True,
            },
        ]
    )
    coverage.to_csv(results / "stage5a41_evidence_coverage.csv", index=False)

    manifest = {
        "candidate_count_after_overlay": 1554,
        "deg_overlay": {"candidate_count": 1554, "deg_match_count": 307},
        "usable_scoring_layers_before": 0,
        "usable_scoring_layers_after": 1,
        "score_affecting_layers_before": 0,
        "score_affecting_layers_after": 1,
        "new_usable_evidence_layers": ["virulence"],
        "new_score_affecting_layers": ["virulence"],
    }
    (results / "stage5a41_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    essentiality = {
        "provider": "deg",
        "provider_name": "deg",
        "retrieval_status": "versioned_local_dataset_integrated",
        "matched_candidate_count": 307,
        "protein_count_mapped": 307,
        "usable_evidence": True,
        "affects_score": True,
        "evidence_level": "versioned_external_essentiality_dataset",
    }
    (results / "online_only_essentiality_manifest.json").write_text(
        json.dumps(essentiality), encoding="utf-8"
    )

    result = reconcile_stage5a41_audit(
        {"status": "completed", "workspace": str(workspace), "new_score_affecting_layers": ["virulence"]}
    )

    updated_coverage = pd.read_csv(results / "stage5a41_evidence_coverage.csv")
    row = updated_coverage.loc[updated_coverage["layer_key"].eq("essentiality")].iloc[0]
    assert bool(row["after_usable_evidence"]) is True
    assert bool(row["after_affects_score"]) is True
    assert row["after_matched_candidate_count"] == 307
    assert row["after_coverage_fraction"] == pytest.approx(307 / 1554)
    assert bool(row["usable_evidence_recovered"]) is True
    assert bool(row["score_affecting_evidence_recovered"]) is True

    updated_manifest = json.loads((results / "stage5a41_manifest.json").read_text(encoding="utf-8"))
    assert updated_manifest["new_usable_evidence_layers"] == ["essentiality", "virulence"]
    assert updated_manifest["new_score_affecting_layers"] == ["essentiality", "virulence"]
    assert updated_manifest["audit_reconciled_after_deg_overlay"] is True
    assert result["new_score_affecting_layers"] == ["essentiality", "virulence"]
