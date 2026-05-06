from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def make_temp_project() -> Path:
    return PROJECT_ROOT
