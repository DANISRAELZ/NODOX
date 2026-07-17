from __future__ import annotations

from dataclasses import dataclass

from .validation import DATASET_SPECS


@dataclass(frozen=True)
class LayerDefinition:
    table_key: str
    filename: str
    required: bool
    allow_proxy_default: bool
    external_provider: str | None


_DATASET_FILENAMES = {spec.table_key: spec.filename for spec in DATASET_SPECS}
_DATASET_REQUIRED = {spec.table_key: spec.required for spec in DATASET_SPECS}


DEFAULT_EXTERNAL_PROVIDERS = {
    "essentiality": "curated_online_examples",
    "virulence": "curated_online_examples",
    "human_homologs": "human_homology_diamond",
    "localization": "curated_online_examples",
    "host_annotation": "interpro_domain_overlap",
    "strain_conservation": "bvbrc_real",
    "functional_network": "string_real",
    "clinical_impact": "controlled_therapeutic_context_v2",
    "curated_disease_context": "controlled_therapeutic_context_v2",
    "therapy_site_context": "controlled_therapeutic_context_v2",
    "literature_support": "curated_online_examples",
}


LAYER_REGISTRY: dict[str, LayerDefinition] = {
    key: LayerDefinition(
        table_key=key,
        filename=_DATASET_FILENAMES[key],
        required=_DATASET_REQUIRED[key],
        allow_proxy_default=key in {"clinical_impact", "curated_disease_context", "therapy_site_context"},
        external_provider=DEFAULT_EXTERNAL_PROVIDERS.get(key),
    )
    for key in _DATASET_FILENAMES
}


TARGET_LAYER_KEYS = [
    "essentiality",
    "virulence",
    "human_homologs",
    "localization",
    "host_annotation",
    "strain_conservation",
    "functional_network",
    "clinical_impact",
    "curated_disease_context",
    "therapy_site_context",
    "evolutionary_escape",
    "evolutionary_escape_risk",
    "collateral_sensitivity",
    "redundancy",
    "contextual_essentiality",
    "literature_support",
    "evidence_quality",
]


def get_layer_definition(layer_key: str) -> LayerDefinition:
    if layer_key not in LAYER_REGISTRY:
        raise KeyError(f"Capa no registrada: {layer_key}")
    return LAYER_REGISTRY[layer_key]


def list_layer_definitions() -> list[LayerDefinition]:
    return list(LAYER_REGISTRY.values())
