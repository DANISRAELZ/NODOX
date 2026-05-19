from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - optional GUI dependency
    st = None

from scripts.create_user_curated_staging import create_staging
from src.nodos_funcionales.user_curated_validation import validate_user_curated_manifest


APP_TITLE = "Nodos Funcionales - user_curated onboarding"
SAFETY_NOTICE = (
    "Esta GUI no ejecuta pipeline, no ejecuta scoring, no importa datasets y no "
    "genera outputs cientificos. No versionar datos reales."
)


def _resolve_manifest_path(raw_path: str) -> Path:
    manifest_path = Path(raw_path.strip())
    if not manifest_path.is_absolute():
        manifest_path = PROJECT_ROOT / manifest_path
    return manifest_path


def _format_staging_paths(staging_path: Path) -> str:
    paths = {
        "README.md": staging_path / "README.md",
        "manifest.csv": staging_path / "manifest.csv",
        "raw_inputs/": staging_path / "raw_inputs",
        "notes/": staging_path / "notes",
        "provenance/": staging_path / "provenance",
    }
    return "\n".join(f"{label}: {path}" for label, path in paths.items())


def _render_streamlit_app() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="centered")
    st.title(APP_TITLE)
    st.warning(SAFETY_NOTICE)

    st.markdown(
        """
        Esta primera interfaz ayuda a crear una carpeta local de staging y a
        prevalidar un `manifest.csv` user_curated. Mantiene el flujo detenido
        antes de importacion, pipeline y scoring.
        """
    )

    st.header("1. Crear staging local")
    st.caption("Use un identificador corto y multiorganismo. No escriba rutas completas.")
    project_id = st.text_input("project_id", placeholder="<project_id>")
    if st.button("Crear staging local"):
        try:
            created_path = create_staging(project_id)
        except (FileExistsError, FileNotFoundError, OSError, ValueError) as exc:
            st.error(str(exc))
        else:
            st.success("Staging local creado.")
            st.code(str(created_path), language="text")
            st.code(_format_staging_paths(created_path), language="text")
            st.info(
                "Revise README.md, complete manifest.csv, coloque archivos reales "
                "solo en raw_inputs/ y documente procedencia en provenance/."
            )

    st.header("2. Revisar archivos locales")
    st.markdown(
        """
        Despues de crear el staging:

        - completar `README.md`;
        - reemplazar placeholders en `manifest.csv`;
        - colocar archivos reales solo en `raw_inputs/`;
        - registrar decisiones de curacion en `notes/`;
        - documentar procedencia en `provenance/`;
        - confirmar con `git status --short` que los datos reales no aparecen.
        """
    )

    st.header("3. Validar manifest")
    manifest_input = st.text_input(
        "Ruta a manifest.csv",
        placeholder=r"user_curated_staging\<project_id>\manifest.csv",
    )
    if st.button("Validar manifest"):
        if not manifest_input.strip():
            st.error("Indique la ruta del manifest.csv antes de validar.")
        else:
            manifest_path = _resolve_manifest_path(manifest_input)
            errors = validate_user_curated_manifest(manifest_path)
            if errors:
                st.error("El manifest no valida. Corrija estos puntos antes de avanzar:")
                for error in errors:
                    st.write(f"- {error}")
            else:
                st.success("Manifest valido para revision/importacion controlada.")
                st.info(
                    "Esta prevalidacion no es validacion biologica. Detenerse "
                    "antes de pipeline y scoring."
                )

    st.header("Siguiente fase")
    st.button("Importar dataset (deshabilitado en esta version)", disabled=True)
    st.caption(
        "La importacion con import_dataset.py queda documentada como siguiente fase; "
        "esta GUI solo prepara staging y valida manifest."
    )


def main() -> int:
    if st is None:
        print(
            "Streamlit no esta instalado. Instalar manualmente con `python -m pip install streamlit` "
            "y ejecutar: streamlit run apps/user_curated_onboarding_app.py",
            file=sys.stderr,
        )
        return 1
    _render_streamlit_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
