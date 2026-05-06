from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.workspace_compare import write_workspace_comparison


def main() -> int:
    csv_path, md_path, comparison = write_workspace_comparison(PROJECT_ROOT)
    print(f"[OK] Workspaces comparados: {len(comparison)}")
    print(f"[OK] CSV: {csv_path}")
    print(f"[OK] Markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
