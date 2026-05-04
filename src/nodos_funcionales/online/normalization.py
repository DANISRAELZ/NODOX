from __future__ import annotations


def normalize_identifier(value: object) -> str:
    return str(value or "").strip().upper()
