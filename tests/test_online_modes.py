from __future__ import annotations

import pytest

from src.nodos_funcionales.online.online_utils import describe_online_mode, mode_allows_network, normalize_online_mode
from src.nodos_funcionales.online.provider_modes import accepted_provider_modes, normalize_provider_mode
from src.nodos_funcionales.online.provenance import provider_provenance
from src.nodos_funcionales.string_api import _build_cache_served_manifest as build_string_cache_manifest
from src.nodos_funcionales.uniprot_api import _build_cache_served_manifest as build_uniprot_cache_manifest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("requested", "effective", "network"),
    [
        ("offline_only", "offline_only", False),
        ("local", "offline_only", False),
        ("cache_first", "cache_first", False),
        ("online_optional", "online_optional", True),
        ("auto", "cache_first", False),
        ("api_stub", "offline_only", False),
    ],
)
def test_online_modes_are_explicit(requested: str, effective: str, network: bool) -> None:
    assert normalize_online_mode(requested) == effective
    assert mode_allows_network(requested) is network
    description = describe_online_mode(requested)
    assert description["requested_mode"] == requested
    assert description["effective_mode"] == effective


def test_provider_provenance_caps_incomplete_confidence() -> None:
    provenance = provider_provenance(
        "UniProt",
        "partial_response",
        0.90,
        retrieval_mode="cache_first",
        cache_status="cache_miss",
        incomplete=True,
    )

    assert provenance["confidence"] == 0.50
    assert provenance["source_version"]
    assert "incomplete=True" in provenance["provenance"]


def test_provider_modes_respect_config_and_aliases() -> None:
    config = {"online_sources": {"accepted_modes": {"offline_only": True, "cache_first": True}}}

    assert normalize_provider_mode("local", config) == "offline_only"
    assert normalize_provider_mode("auto", config) == "cache_first"
    assert "api_stub" in accepted_provider_modes(config)


@pytest.mark.parametrize(
    ("builder", "provider"),
    [
        (build_string_cache_manifest, "string_db"),
        (build_uniprot_cache_manifest, "uniprot_rest"),
    ],
)
def test_cache_served_manifests_keep_traceability_fields(builder, provider: str) -> None:
    manifest = builder(
        {
            "provider": provider,
            "generated_at_utc": "2026-05-05T00:00:00+00:00",
            "confidence": 0.91,
        },
        "cache_first",
    )

    for field in ["source_name", "source_version", "retrieval_mode", "cache_status", "provenance", "confidence"]:
        assert field in manifest
    assert manifest["source_name"] == provider
    assert manifest["retrieval_mode"] == "cache_first"
    assert manifest["cache_status"] == "cache_hit"
