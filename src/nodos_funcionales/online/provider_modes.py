from __future__ import annotations

from typing import Any


# Single source of truth for provider/runtime modes. Policy modes remain
# canonical so downstream code can enforce their distinct evidence contracts.
CANONICAL_PROVIDER_MODES = frozenset({
    "offline_only",
    "cache_first",
    "online_optional",
    "online_strict",
    "hybrid_curated",
})

PROVIDER_MODE_ALIASES = {
    "local": "offline_only",
    "offline": "offline_only",
    "auto": "cache_first",
    "api_stub": "offline_only",
    "online_only": "online_strict",
}


def provider_mode_choices() -> tuple[str, ...]:
    """Return stable argparse choices, including backwards-compatible aliases."""
    return tuple(sorted(CANONICAL_PROVIDER_MODES | set(PROVIDER_MODE_ALIASES)))


def accepted_provider_modes(config: dict[str, Any] | None = None) -> set[str]:
    """Return accepted configured modes plus the stable public contract."""
    raw_config = config or {}
    configured = {
        str(key)
        for key, enabled in raw_config.get("online_sources", {}).get("accepted_modes", {}).items()
        if enabled
    }
    return configured | set(provider_mode_choices())


def normalize_provider_mode(mode: str, config: dict[str, Any] | None = None) -> str:
    requested = str(mode).strip()
    if requested not in accepted_provider_modes(config):
        supported = ", ".join(provider_mode_choices())
        raise ValueError(f"online source mode no soportado: {requested!r}. Modos validos: {supported}")
    normalized = PROVIDER_MODE_ALIASES.get(requested, requested)
    if normalized not in CANONICAL_PROVIDER_MODES:
        supported = ", ".join(provider_mode_choices())
        raise ValueError(f"online source mode no soportado: {requested!r}. Modos validos: {supported}")
    return normalized


def mode_allows_network(mode: str, config: dict[str, Any] | None = None) -> bool:
    return normalize_provider_mode(mode, config) in {
        "online_optional",
        "online_strict",
        "hybrid_curated",
    }
