from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest


INTEGRATION_FILE_KEYWORDS = {
    "e2e",
    "export",
    "layer_resolver",
    "layer_source_audit",
    "multiorganism_orientation",
    "packaging_templates_literature",
    "phase3_scoring",
    "run_pipeline",
}

ONLINE_FILE_KEYWORDS = {
    "api",
    "online",
    "string_api",
    "uniprot_api",
    "taxonomy_api",
    "vfdb_api",
    "deg_api",
    "bvbrc_api",
}

SLOW_FILE_KEYWORDS = {
    "e2e",
    "export",
    "layer_resolver",
    "layer_source_audit",
    "multiorganism_orientation",
    "packaging_templates_literature",
    "phase3_scoring",
    "run_pipeline",
}

SNAPSHOT_FILE_KEYWORDS = {
    "ranking_snapshots",
}

# These tests preserve behavior tied to the former PAO1 demonstration fixture.
# They remain useful as historical diagnostics, but they are not part of the
# organism-agnostic contract of NODOX and must not gate the standard or online
# provider-contract suites.
ORGANISM_REGRESSION_NODEIDS = {
    "tests/test_e2e.py::EndToEndTests::test_full_phase2_pipeline_runs_on_example_data",
    "tests/test_ranking_snapshots.py::test_pao1_demo_pipeline_matches_curated_snapshot",
    "tests/test_scoring.py::ScoringTests::test_scores_are_generated_in_expected_range",
    "tests/test_scoring.py::ScoringTests::test_specific_therapeutic_rules_take_priority_over_mixed_fallback",
    "tests/test_layer_external_sources.py::LayerExternalSourceTests::test_controlled_therapeutic_provider_materializes_clinical_impact",
    "tests/test_layer_external_sources.py::LayerExternalSourceTests::test_literature_support_uses_curated_online_examples_catalog",
    "tests/test_layer_external_sources.py::LayerExternalSourceTests::test_required_layers_can_use_curated_online_examples_catalog",
}


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest) -> Path:
    """Workspace-local tmp path to avoid locked Windows/OneDrive temp roots."""
    project_root = Path(__file__).resolve().parents[1]
    safe_name = "".join(char if char.isalnum() else "_" for char in request.node.name)[:80]
    path = project_root / ".tmp_tests" / f"{safe_name}_{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Ensure every test has an explicit operational class marker."""
    for item in items:
        if item.nodeid in ORGANISM_REGRESSION_NODEIDS:
            item.add_marker(pytest.mark.organism_regression)

        existing = {marker.name for marker in item.iter_markers()}
        filename = Path(str(item.fspath)).name.lower()

        if not existing & {"unit", "integration", "online"}:
            if any(keyword in filename for keyword in ONLINE_FILE_KEYWORDS):
                item.add_marker(pytest.mark.online)
            elif any(keyword in filename for keyword in INTEGRATION_FILE_KEYWORDS):
                item.add_marker(pytest.mark.integration)
            else:
                item.add_marker(pytest.mark.unit)

        existing = {marker.name for marker in item.iter_markers()}
        if "snapshot" not in existing and any(keyword in filename for keyword in SNAPSHOT_FILE_KEYWORDS):
            item.add_marker(pytest.mark.snapshot)
            existing = {marker.name for marker in item.iter_markers()}
        if "online" in existing:
            item.add_marker(pytest.mark.slow)
        elif "slow" not in existing and any(keyword in filename for keyword in SLOW_FILE_KEYWORDS):
            item.add_marker(pytest.mark.slow)
