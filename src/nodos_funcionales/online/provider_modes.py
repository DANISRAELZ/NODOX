from __future__ import annotations

from typing import Any

from .online_utils import normalize_online_mode


def accepted_provider_modes(config: dict[str, Any]) -> set[str]:
    configured = {
        str(key)
        for key, enabled in config.get("online_sources", {}).get("accepted_modes", {}).items()
        if enabled
    }
    configured.update({"offline_only", "local", "cache_first", "online_optional", "auto", "api_stub"})
    return configured


def normalize_provider_mode(mode: str, config: dict[str, Any]) -> str:
    if mode not in accepted_provider_modes(config):
        raise ValueError(f"online source mode no soportado: {mode}")
    return normalize_online_mode(mode)
