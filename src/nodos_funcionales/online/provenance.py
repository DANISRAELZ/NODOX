from __future__ import annotations

from datetime import datetime, timezone


def provider_provenance(
    provider: str,
    status: str,
    confidence: float,
    retrieval_mode: str = "not_reported",
    cache_status: str = "not_reported",
    source_version: str | None = None,
    incomplete: bool = False,
) -> dict[str, object]:
    capped_confidence = max(0.0, min(float(confidence), 1.0))
    if incomplete:
        capped_confidence = min(capped_confidence, 0.50)
    return {
        "source_name": provider,
        "source_version": source_version or datetime.now(timezone.utc).date().isoformat(),
        "retrieval_mode": retrieval_mode,
        "cache_status": cache_status,
        "retrieval_status": status,
        "confidence": capped_confidence,
        "provenance": (
            f"source={provider}; status={status}; mode={retrieval_mode}; "
            f"cache={cache_status}; incomplete={bool(incomplete)}"
        ),
    }
