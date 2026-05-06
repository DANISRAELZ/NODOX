from __future__ import annotations

import argparse
from typing import Iterable


VALID_PIPELINE_MODES = {"default", "legacy", "phase2", "compare", "phase3"}
PIPELINE_MODE_ALIASES = {"default": "compare"}


def build_argument_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--mode",
        choices=sorted(VALID_PIPELINE_MODES),
        help="Modo de salida del pipeline: default, legacy, phase2, compare o phase3.",
    )
    return parser


def resolve_pipeline_mode(config: dict, cli_mode: str | None = None) -> str:
    mode = cli_mode or config.get("runtime", {}).get("pipeline_mode", "compare")
    if mode not in VALID_PIPELINE_MODES:
        raise ValueError(f"Modo de pipeline no soportado: {mode}")
    return PIPELINE_MODE_ALIASES.get(mode, mode)
