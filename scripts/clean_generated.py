from __future__ import annotations

import argparse
import shutil
from pathlib import Path


GENERATED_DIRS = [
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "data_processed",
    "results",
    "dist",
    "build",
    "htmlcov",
]
GENERATED_PATTERNS = ["*.pyc", "*.pyo", "*.log", ".coverage"]
SESSION_GENERATED_DIRS = ["data_processed", "results", "logs", ".cache", "cache"]
PROTECTED_DIRS = {"data_templates", "config", "tests", "data_raw", "data_user", "docs"}


def collect_generated(root: Path) -> list[Path]:
    targets: list[Path] = []
    for name in GENERATED_DIRS:
        path = root / name
        if path.exists() and path.name not in PROTECTED_DIRS:
            targets.append(path)
    for pattern in GENERATED_PATTERNS:
        targets.extend(path for path in root.rglob(pattern) if not _is_protected(path))
    sessions = root / "data_sessions"
    if sessions.exists():
        for session in sessions.iterdir():
            if not session.is_dir():
                continue
            for name in SESSION_GENERATED_DIRS:
                path = session / name
                if path.exists():
                    targets.append(path)
    return sorted(set(targets), key=lambda item: str(item).lower())


def clean_generated(root: Path, apply: bool = False) -> list[Path]:
    targets = collect_generated(root)
    if not apply:
        return targets
    for path in targets:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    return targets


def _is_protected(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & PROTECTED_DIRS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Limpia salidas generadas sin tocar plantillas ni datos fuente.")
    parser.add_argument("--root", default=".", help="Raiz del proyecto.")
    parser.add_argument("--apply", action="store_true", help="Borra los archivos listados. Sin esta bandera solo muestra dry-run.")
    parser.add_argument("--dry-run", action="store_true", help="Lista lo que se borraria. Es el comportamiento por defecto.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    targets = clean_generated(root, apply=bool(args.apply))
    mode = "BORRADO" if args.apply else "DRY-RUN"
    print(f"[{mode}] {len(targets)} rutas generadas encontradas")
    for path in targets:
        print(path)
    if not args.apply:
        print("Ejecuta con --apply para borrar estas rutas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
