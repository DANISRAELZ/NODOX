from __future__ import annotations

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


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Ensure every test has an explicit operational class marker."""
    for item in items:
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
        if "online" in existing:
            item.add_marker(pytest.mark.slow)
        elif "slow" not in existing and any(keyword in filename for keyword in SLOW_FILE_KEYWORDS):
            item.add_marker(pytest.mark.slow)
