from __future__ import annotations


ONLINE_MODE_ALIASES = {
    "local": "offline_only",
    "offline": "offline_only",
    "offline_only": "offline_only",
    "cache_first": "cache_first",
    "online_optional": "online_optional",
    "auto": "cache_first",
    "api_stub": "offline_only",
}


def normalize_online_mode(mode: str) -> str:
    normalized = ONLINE_MODE_ALIASES.get(str(mode).strip(), "")
    if not normalized:
        raise ValueError(f"online source mode no soportado: {mode}")
    return normalized


def describe_online_mode(mode: str) -> dict[str, object]:
    normalized = normalize_online_mode(mode)
    return {
        "requested_mode": str(mode),
        "effective_mode": normalized,
        "network_allowed": mode_allows_network(str(mode)),
        "retrieval_mode": normalized,
        "provenance": f"requested={mode}; effective={normalized}",
    }


def mode_allows_network(mode: str) -> bool:
    normalized = normalize_online_mode(mode)
    return normalized == "online_optional"
