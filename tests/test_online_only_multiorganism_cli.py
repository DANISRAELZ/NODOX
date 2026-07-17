from __future__ import annotations

import json
from pathlib import Path

from scripts.run_online_only_validation import build_parser, resolve_organism_options
from tests.helpers import PROJECT_ROOT


def _resolve(*argv: str) -> dict[str, object]:
    return resolve_organism_options(build_parser().parse_args(list(argv)))


def test_online_only_registry_contains_required_organisms() -> None:
    registry_path = PROJECT_ROOT / "config" / "online_only_organisms.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    assert {"pseudomonas_aeruginosa", "escherichia_coli", "mycobacterium_tuberculosis", "mycobacterium_tuberculosis_h37rv"}.issubset(registry)
    assert registry["pseudomonas_aeruginosa"]["taxon_id"] == 287
    assert registry["escherichia_coli"]["taxon_id"] == 562
    assert registry["mycobacterium_tuberculosis"]["taxon_id"] == 1773


def test_escherichia_coli_key_resolves_without_source_edits() -> None:
    resolved = _resolve("--organism-key", "escherichia_coli")

    assert resolved["organism"] == "Escherichia coli"
    assert resolved["organism_slug"] == "escherichia_coli"
    assert resolved["taxon_id"] == 562


def test_h37rv_key_resolves_strain_and_taxon() -> None:
    resolved = _resolve("--organism-key", "mycobacterium_tuberculosis_h37rv")

    assert resolved["organism"] == "Mycobacterium tuberculosis"
    assert resolved["strain"] == "H37Rv"
    assert resolved["strain_slug"] == "h37rv"
    assert resolved["taxon_id"] == 83332


def test_manual_parameters_override_registry_values() -> None:
    resolved = _resolve(
        "--organism-key", "escherichia_coli", "--organism", "Escherichia coli custom", "--taxon-id", "999"
    )

    assert resolved["organism"] == "Escherichia coli custom"
    assert resolved["taxon_id"] == 999


def test_universal_runner_is_not_pseudomonas_specific() -> None:
    script = (PROJECT_ROOT / "scripts" / "run_online_only_validation.py").read_text(encoding="utf-8")

    assert "run_pseudomonas_online_only_validation" not in script
    assert "--organism-key" in script
    assert "--disable-string" in script


def test_scoring_modules_are_not_imported_or_modified_by_universal_runner() -> None:
    script = (PROJECT_ROOT / "scripts" / "run_online_only_validation.py").read_text(encoding="utf-8")

    assert "scoring" not in script
    assert Path(PROJECT_ROOT / "src" / "nodos_funcionales" / "scoring.py").exists()
