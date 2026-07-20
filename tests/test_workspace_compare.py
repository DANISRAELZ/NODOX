from __future__ import annotations

import json
from pathlib import Path

from src.nodos_funcionales.workspace_compare import compare_workspaces


def _write_demo_workspace(base_dir: Path, name: str, organism: str) -> None:
    results_dir = base_dir / "data_sessions" / name / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "organism_profile.json").write_text(
        json.dumps(
            {
                "organism_canonical_name": organism,
                "strain_canonical": "demo_strain",
                "completeness_status": "complete",
            }
        ),
        encoding="utf-8",
    )


def test_compare_workspaces_returns_controlled_sessions(tmp_path: Path) -> None:
    _write_demo_workspace(tmp_path, "corynebacterium_pseudotuberculosis_online_demo", "Corynebacterium pseudotuberculosis")
    _write_demo_workspace(tmp_path, "pao1_demo", "Pseudomonas aeruginosa")

    comparison = compare_workspaces(tmp_path)

    for column in [
        "workspace_name",
        "organism_canonical_name",
        "online_source",
        "online_source_used",
        "online_impact_status",
        "online_changed_candidate_count",
        "online_history_count",
        "online_sources_seen",
    ]:
        assert column in comparison.columns

    assert set(comparison["workspace_name"]) == {
        "corynebacterium_pseudotuberculosis_online_demo",
        "pao1_demo",
    }
