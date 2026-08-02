from __future__ import annotations

from .provider_modes import mode_allows_network, normalize_provider_mode


def normalize_online_mode(mode: str) -> str:
    """Backward-compatible wrapper around the centralized mode contract."""
    return normalize_provider_mode(mode)


def describe_online_mode(mode: str) -> dict[str, object]:
    normalized = normalize_online_mode(mode)
    return {
        "requested_mode": str(mode),
        "effective_mode": normalized,
        "network_allowed": mode_allows_network(str(mode)),
        "retrieval_mode": normalized,
        "provenance": f"requested={mode}; effective={normalized}",
    }
