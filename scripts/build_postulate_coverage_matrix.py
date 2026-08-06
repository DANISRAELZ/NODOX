#!/usr/bin/env python3
"""Build only the Functional Node Theory postulate coverage matrix."""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Sequence


def _load_auditor(script_path: Path):
    spec = importlib.util.spec_from_file_location("nodox_integrated_validation_auditor", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/integrated_validation_stage1/functional_node_postulates_matrix.csv"),
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    auditor = _load_auditor(repo_root / "scripts" / "audit_integrated_validation.py")
    rows = auditor.build_postulate_coverage(repo_root)
    output = args.output if args.output.is_absolute() else repo_root / args.output
    auditor.write_csv(output, rows)
    print(f"Matriz escrita en: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
