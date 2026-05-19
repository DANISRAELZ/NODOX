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

from scripts.create_user_curated_staging import create_staging, validate_project_id
from src.nodos_funcionales.user_curated_validation import validate_user_curated_manifest


APP_TITLE = "Nodos Funcionales - user_curated onboarding"
APP_SUBTITLE = "Onboarding seguro para preparar staging local y prevalidar manifest, antes de cualquier importacion."
SAFETY_NOTICE = (
    "Esta GUI no ejecuta pipeline, no ejecuta scoring, no importa datasets y no "
    "genera outputs cientificos. No versionar datos reales."
)
MANUAL_IMPORT_COMMAND = (
    r".\.venv\Scripts\python.exe import_dataset.py "
    r"--validate-user-curated-manifest <ruta_manifest.csv>"
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


def _render_preparation_checklist() -> None:
    st.header("3. Checklist visual de preparacion")
    st.caption("Use esta lista como control manual antes de pensar en importar.")
    checklist_items = [
        "README.md revisado",
        "manifest.csv llenado y sin placeholders",
        "archivos reales colocados solo en raw_inputs/",
        "procedencia documentada en provenance/",
        "notas de curacion, faltantes y limites registradas en notes/",
        "cada fila real usa source_type=user_curated",
        "sin mezcla demo/proxy/cache como evidencia real",
        "sin pipeline/scoring todavia",
        "git status revisado y sin datos reales visibles",
    ]
    for item in checklist_items:
        st.checkbox(item, value=False)


def _render_interpretation_limits() -> None:
    st.header("Limites interpretativos")
    st.markdown(
        """
        - prevalidar no es validacion biologica;
        - importar no significa evidencia suficiente;
        - score alto no equivale a validacion clinica;
        - el sistema prioriza candidatos, no confirma terapias;
        - requiere revision experta y validacion experimental.
        """
    )


def _render_streamlit_app() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="centered")
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)
    st.warning(SAFETY_NOTICE)

    st.markdown(
        """
        Esta primera interfaz ayuda a crear una carpeta local de staging y a
        prevalidar un `manifest.csv` user_curated. Mantiene el flujo detenido
        antes de importacion, pipeline y scoring.
        """
    )

    st.header("Que hace esta GUI")
    st.markdown(
        """
        - crea `user_curated_staging/<project_id>/` con la logica existente;
        - muestra rutas locales esperadas para `README.md`, `manifest.csv`,
          `raw_inputs/`, `notes/` y `provenance/`;
        - prevalida un manifest con `validate_user_curated_manifest()`;
        - muestra errores de manifest antes de una fase posterior de importacion manual.
        """
    )

    st.header("Que NO hace esta GUI")
    st.markdown(
        """
        - no importa datos;
        - no ejecuta pipeline;
        - no ejecuta scoring;
        - no genera outputs cientificos ni rankings;
        - no valida biologicamente el dataset;
        - no valida clinicamente candidatos;
        - no sustituye revision experta.
        """
    )

    st.header("1. Crear staging local")
    st.caption("Use un identificador corto y multiorganismo. No escriba rutas completas.")
    project_id = st.text_input("project_id", placeholder="<project_id>")
    if st.button("Crear staging local"):
        try:
            safe_project_id = validate_project_id(project_id)
        except ValueError as exc:
            st.error(f"project_id invalido: {exc}")
            st.info("Use un nombre simple de carpeta, sin barras, rutas absolutas, '..' ni separadores de unidad.")
        else:
            try:
                created_path = create_staging(safe_project_id)
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
                st.warning(
                    "La carpeta user_curated_staging/ debe permanecer ignorada por Git. "
                    "Si `git status --short` muestra datos reales, detengase y corrija la ruta."
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
        - revisar notas de faltantes, limites y decisiones pendientes en `notes/`;
        - confirmar con `git status --short` que los datos reales no aparecen.
        """
    )

    _render_preparation_checklist()

    st.header("4. Validar manifest")
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
                st.markdown("Errores encontrados:")
                for error in errors:
                    st.markdown(f"- `{error}`")
                st.warning(
                    "Corrija estos errores antes de importar. Esta GUI no ejecuta importacion; "
                    "la importacion validada queda para una fase posterior/manual."
                )
            else:
                st.success("Manifest valido para revision o una importacion controlada posterior.")
                st.info(
                    "Manifest valido no implica suficiencia cientifica, validacion biologica "
                    "ni validacion clinica. Detenerse antes de pipeline y scoring."
                )

    st.header("5. Proximos pasos manuales")
    st.markdown(
        """
        La importacion validada es una fase posterior y manual. Esta GUI no la
        ejecuta. Cuando el equipo decida avanzar, usar un comando revisado fuera
        de la GUI, por ejemplo:
        """
    )
    st.code(MANUAL_IMPORT_COMMAND, language="powershell")
    st.warning(
        "Incluso despues de importar, no interpretar el dataset ni futuros scores "
        "como validacion terapeutica, biologica o clinica."
    )

    _render_interpretation_limits()

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
