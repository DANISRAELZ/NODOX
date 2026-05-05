from __future__ import annotations

import pytest

from src.nodos_funcionales.online.online_utils import describe_online_mode, mode_allows_network, normalize_online_mode
from src.nodos_funcionales.online.provenance import provider_provenance

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
