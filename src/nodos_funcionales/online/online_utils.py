from __future__ import annotations


def mode_allows_network(mode: str) -> bool:
    return str(mode) in {"online_optional", "auto"}
