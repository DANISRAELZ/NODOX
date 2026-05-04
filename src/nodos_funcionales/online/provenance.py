from __future__ import annotations


def provider_provenance(provider: str, status: str, confidence: float) -> dict[str, object]:
    return {
        "source_name": provider,
        "retrieval_status": status,
        "confidence": max(0.0, min(float(confidence), 1.0)),
    }
