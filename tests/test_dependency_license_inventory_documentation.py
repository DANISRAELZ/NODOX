from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = PROJECT_ROOT / "docs" / "dependency_license_inventory.md"
AUDIT_PATH = PROJECT_ROOT / "docs" / "license_and_dependency_audit.md"


def test_dependency_license_inventory_is_contextualized_if_present() -> None:
    assert INVENTORY_PATH.exists()
    audit = AUDIT_PATH.read_text(encoding="utf-8").lower()
    assert "current local virtual environment" in audit
    assert "may include optional workflow/transitive packages" in audit
    assert "not treat the inventory as the minimal core dependency list" in audit
