from __future__ import annotations

import atexit
import shutil
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

_ISOLATED_INPUT_DIRS = (
    "config",
    "data_raw",
    "data_curated",
    "data_demo",
    "data_cache",
    "data_external",
    "data_templates",
)
_ISOLATED_OUTPUT_DIRS = ("data_processed", "results")
_TEMP_PROJECTS: list[Path] = []


def _cleanup_temp_projects() -> None:
    for project_dir in reversed(_TEMP_PROJECTS):
        shutil.rmtree(project_dir, ignore_errors=True)
    _TEMP_PROJECTS.clear()


atexit.register(_cleanup_temp_projects)


def make_temp_project() -> Path:
    """Create a disposable project copy for tests that write pipeline outputs."""
    project_dir = Path(tempfile.mkdtemp(prefix="nodox-test-project-"))
    _TEMP_PROJECTS.append(project_dir)
    try:
        for dirname in _ISOLATED_INPUT_DIRS:
            source = PROJECT_ROOT / dirname
            if source.exists():
                shutil.copytree(source, project_dir / dirname)
        for dirname in _ISOLATED_OUTPUT_DIRS:
            (project_dir / dirname).mkdir(parents=True, exist_ok=True)
    except Exception:
        shutil.rmtree(project_dir, ignore_errors=True)
        _TEMP_PROJECTS.remove(project_dir)
        raise
    return project_dir
