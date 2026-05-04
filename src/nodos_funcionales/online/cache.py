from __future__ import annotations

from pathlib import Path


def cache_status(path: str | Path) -> str:
    target = Path(path)
    if target.exists() and target.stat().st_size > 0:
        return "cache_available"
    return "cache_missing"
