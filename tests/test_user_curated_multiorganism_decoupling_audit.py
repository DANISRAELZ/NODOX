from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORTABLE_FLOW_TEST = PROJECT_ROOT / "tests" / "test_user_curated_minimal_functional_validation_flow.py"
AUDIT_DOC = PROJECT_ROOT / "docs" / "user_curated_multiorganism_decoupling_audit.md"
FLOW_CLOSURE_DOC = PROJECT_ROOT / "docs" / "user_curated_minimal_functional_validation_flow_closure.md"
REPORTING_CLOSURE_DOC = PROJECT_ROOT / "docs" / "user_curated_final_reporting_interpretation_closure.md"


def _read(path: Path) -> str:
    assert path.exists(), path
    return path.read_text(encoding="utf-8")


def test_portable_user_curated_fixture_uses_input_organism_without_controlled_defaults() -> None:
    source = _read(PORTABLE_FLOW_TEST)
    lower_source = source.lower()

    organism_match = re.search(r'organism\s*=\s*"([^"]+)"', source)
    assert organism_match is not None
    organism = organism_match.group(1).lower()

    assert "portable user validation isolate" in organism
    assert "pao1" not in organism
    assert "h37rv" not in organism
    assert "corynebacterium pseudotuberculosis" not in organism
    assert "corynebacterium" not in organism

    assert "tmp_path" in source
    assert "source_type\": \"user_curated\"" in source
    assert "source_name=local_review" in source
    assert "as_user_layer=True" in source
    assert "online_source_mode=\"offline_only\"" in source

    for required_boundary in [
        "demo",
        "proxy",
        "cache",
        "online",
        "controlled_reference",
    ]:
        assert required_boundary in lower_source

    for forbidden_dependency in [
        "ranking_snapshots",
        "controlled_reference.csv",
        "controlled_scoring",
        "pao1_demo_reference",
        "h37rv_demo_reference",
        "corynebacterium por defecto",
        "pao1 por defecto",
        "h37rv por defecto",
    ]:
        assert forbidden_dependency not in lower_source


def test_user_curated_multiorganism_decoupling_audit_document_covers_contract() -> None:
    text = _read(AUDIT_DOC)
    lower_text = text.lower()

    for phrase in [
        "multi-organism",
        "user_curated",
        "no organism-specific default",
        "controlled_reference",
        "demo",
        "proxy",
        "cache",
        "online",
        "provenance",
        "arbitrary organism",
        "therapeutic prioritization",
        "no clinical validation",
        "no experimental validation",
    ]:
        assert phrase in lower_text

    for organism_token in [
        "PAO1",
        "H37Rv",
        "Corynebacterium",
    ]:
        assert organism_token in text


def test_recent_user_curated_closures_preserve_multiorganism_interpretation_boundaries() -> None:
    combined = "\n".join([_read(FLOW_CLOSURE_DOC), _read(REPORTING_CLOSURE_DOC), _read(AUDIT_DOC)])
    lower_combined = combined.lower()

    for phrase in [
        "user_curated",
        "provenance",
        "conservative interpretation",
        "no clinical validation",
        "no experimental validation",
        "controlled_reference",
        "demo",
        "proxy",
        "cache",
        "online",
    ]:
        assert phrase in lower_combined

    for organism_token in [
        "PAO1",
        "H37Rv",
        "Corynebacterium",
    ]:
        assert organism_token in combined

    assert "no organism-specific default" in lower_combined
    assert "multi-organism" in lower_combined
