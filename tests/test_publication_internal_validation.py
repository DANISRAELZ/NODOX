from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.nodos_funcionales.functional_node_model import FunctionalNodeModel
from src.nodos_funcionales.publication_validation import build_internal_validation_summary


def test_publication_internal_validation_outputs_and_conservative_language(tmp_path: Path) -> None:
    output_dir = tmp_path / "publication_package"
    candidates = pd.DataFrame(
        [
            {
                "protein_id": "P1",
                "gene": "a",
                "antibiotic_target_score": 0.8,
                "antivirulence_target_score": 0.3,
                "functional_node_score": 0.7,
                "selectivity_score": 0.9,
                "clinical_context_score": 0.5,
                "evidence_confidence_score": 0.8,
                "evolutionary_escape_risk_score": 0.1,
                "therapeutic_role": "bactericidal_candidate",
                "provenance_status": "demo_only; proxy; missing; not_assessed",
            }
        ]
    )
    scored = FunctionalNodeModel().score_candidates(candidates)
    baseline = pd.DataFrame([{"protein_id": "P1", "baseline_rank": 1}])
    sensitivity = pd.DataFrame([{"score_name": "meta_priority", "scenario": "baseline"}])

    summary = build_internal_validation_summary(scored, output_dir, sensitivity=sensitivity, baseline_comparison=baseline)

    assert (output_dir / "publication_internal_validation.md").exists()
    assert (output_dir / "publication_internal_validation_summary.csv").exists()
    assert set(summary["status"]) == {"pass"}
    markdown = (output_dir / "publication_internal_validation.md").read_text(encoding="utf-8").lower()
    assert "prioritized hypothesis" in markdown
    assert "not clinical recommendation" in markdown
    for phrase in [
        "clinically" + " validated",
        "experimentally" + " validated",
        "safe" + " target",
        "confirmed" + " therapeutic target",
    ]:
        assert phrase not in markdown
