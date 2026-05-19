from __future__ import annotations

import csv
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
APP_SUBTITLE = (
    "Onboarding seguro user_curated: staging local, prevalidacion de manifest "
    "e importacion validada asistida sin ejecutar pipeline ni scoring."
)
SAFETY_NOTICE = (
    "Esta GUI no ejecuta pipeline, no ejecuta scoring, no importa datasets y no "
    "genera ranking terapeutico ni outputs cientificos. No versionar datos reales."
)
MANUAL_IMPORT_COMMAND = (
    r".\.venv\Scripts\python.exe import_dataset.py "
    r"--validate-user-curated-manifest <ruta_manifest.csv>"
)
MANIFEST_REVIEW_FIELDS = [
    "organism",
    "strain",
    "dataset_id",
    "dataset_version",
    "source_type",
    "evidence_status",
    "evidence_kind",
    "provenance",
    "input_file",
    "input_schema",
    "required_for_scoring",
    "notes",
]
CRITICAL_REVIEW_FIELDS = {
    "organism",
    "dataset_id",
    "source_type",
    "provenance",
    "input_file",
    "required_for_scoring",
}
WEAK_PROVENANCE_VALUES = {"", "na", "n/a", "none", "unknown", "pending", "placeholder", "tbd"}


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


def _has_placeholder(value: object) -> bool:
    text = "" if value is None else str(value).strip()
    return "<" in text and ">" in text


def _load_manifest_rows(manifest_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not manifest_path.exists():
        return [], [f"Manifest file does not exist: {manifest_path}"]
    if not manifest_path.is_file():
        return [], [f"Manifest path is not a file: {manifest_path}"]
    try:
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle)), []
    except (csv.Error, OSError, UnicodeDecodeError) as exc:
        return [], [f"Manifest could not be read for visual review: {exc}"]


def _review_manifest_rows(rows: list[dict[str, str]]) -> list[str]:
    warnings: list[str] = []
    manifest_text = " ".join(str(value) for row in rows for value in row.values()).lower()
    if any(marker in manifest_text for marker in ("demo", "proxy", "cache")):
        warnings.append("Posible mezcla con demo/proxy/cache en el texto del manifest.")

    for row_index, row in enumerate(rows, start=2):
        for field in MANIFEST_REVIEW_FIELDS:
            value = (row.get(field) or "").strip()
            if not value and field in CRITICAL_REVIEW_FIELDS:
                warnings.append(f"Fila {row_index}: campo critico vacio: {field}.")
            if _has_placeholder(value):
                warnings.append(f"Fila {row_index}: {field} conserva placeholder: {value}.")

        source_type = (row.get("source_type") or "").strip()
        evidence_status = (row.get("evidence_status") or "").strip().lower()
        evidence_kind = (row.get("evidence_kind") or "").strip()
        provenance = (row.get("provenance") or "").strip()
        input_file = (row.get("input_file") or "").strip()
        required_for_scoring = (row.get("required_for_scoring") or "").strip()

        if source_type != "user_curated":
            warnings.append(f"Fila {row_index}: source_type no es user_curated.")
        if "pending" in evidence_status:
            warnings.append(f"Fila {row_index}: evidence_status esta pending.")
        if not evidence_kind:
            warnings.append(f"Fila {row_index}: evidence_kind esta vacio.")
        if provenance.lower() in WEAK_PROVENANCE_VALUES or _has_placeholder(provenance):
            warnings.append(f"Fila {row_index}: provenance esta vacio, debil o conserva placeholder.")
        if not input_file or _has_placeholder(input_file):
            warnings.append(f"Fila {row_index}: input_file esta vacio o conserva placeholder.")
        if not required_for_scoring:
            warnings.append(f"Fila {row_index}: required_for_scoring esta vacio.")

    return warnings


def _render_manifest_visual_review(manifest_input: str) -> None:
    if not manifest_input.strip():
        st.error("Indique la ruta del manifest.csv antes de revisar evidencia.")
        return

    manifest_path = _resolve_manifest_path(manifest_input)
    structural_errors = validate_user_curated_manifest(manifest_path)
    rows, read_errors = _load_manifest_rows(manifest_path)

    if read_errors:
        st.error("No se pudo leer el manifest para revision visual.")
        for error in read_errors:
            st.markdown(f"- `{error}`")
        return

    if not rows:
        st.warning("El manifest no contiene filas para revisar.")
        return

    st.subheader("Resumen de campos principales del manifest")
    st.dataframe(
        [{field: row.get(field, "") for field in MANIFEST_REVIEW_FIELDS} for row in rows],
        use_container_width=True,
    )

    review_warnings = _review_manifest_rows(rows)
    if structural_errors:
        st.warning("Errores estructurales detectados por validate_user_curated_manifest():")
        for error in structural_errors:
            st.markdown(f"- `{error}`")
    if review_warnings:
        st.warning("Advertencias de revision visual de evidencia:")
        for warning in review_warnings:
            st.markdown(f"- {warning}")

    if structural_errors or review_warnings:
        st.error("Conclusion conservadora: Requiere correccion antes de avanzar.")
    else:
        st.success("Conclusion conservadora: Listo para revision/importacion.")

    st.info("No interpretar como validacion biologica o clinica.")


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
        "usuario entiende que no hay scoring/pipeline",
    ]
    for item in checklist_items:
        st.checkbox(item, value=False)


def _render_import_checklist() -> None:
    st.subheader("Checklist antes de importacion validada")
    import_checklist_items = [
        "manifest validado sin errores",
        "README.md revisado",
        "raw_inputs/ contiene archivos reales",
        "provenance/ contiene procedencia",
        "notes/ contiene notas de curacion",
        "source_type=user_curated",
        "no hay mezcla demo/proxy/cache",
        "git status revisado",
        "usuario entiende que no hay scoring/pipeline",
    ]
    for item in import_checklist_items:
        st.checkbox(item, value=False, key=f"import_check_{item}")


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


def _render_evidence_review_checklist() -> None:
    st.subheader("Checklist visual de revision de evidencia")
    review_items = [
        "source_type=user_curated",
        "procedencia documentada",
        "evidencia revisada o claramente pendiente",
        "archivos reales identificados",
        "raw_inputs/ revisado",
        "provenance/ revisado",
        "notes/ revisado",
        "ausencia de demo/proxy/cache usados como datos reales",
        "revision experta pendiente o completada",
        "no scoring todavia",
        "no pipeline todavia",
    ]
    for item in review_items:
        st.checkbox(item, value=False, key=f"evidence_review_{item}")


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
        - no ejecuta Snakemake;
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

    st.header("5. Revision visual de calidad/evidencia del dataset")
    st.markdown(
        """
        Esta revision visual es orientativa y de solo lectura. Ayuda a revisar
        procedencia, completitud y consistencia del manifest antes de importar.
        No calcula `confidence_score`, no calcula `therapeutic_priority_score`,
        no ejecuta scoring y no ejecuta pipeline.
        """
    )
    review_manifest_input = st.text_input(
        "Ruta a manifest.csv para revision visual",
        placeholder=r"user_curated_staging\<project_id>\manifest.csv",
        key="manifest_visual_review_path",
    )
    if st.button("Revisar calidad/evidencia del manifest"):
        _render_manifest_visual_review(review_manifest_input)
    _render_evidence_review_checklist()

    st.header("6. Importacion validada asistida")
    st.markdown(
        """
        La importacion validada ocurre despues de que el manifest valida sin
        errores. En esta fase la GUI solo prepara el comando manual y no ejecuta
        `import_dataset.py`.
        """
    )
    _render_import_checklist()
    st.markdown("Comando manual sugerido para una fase posterior:")
    st.code(MANUAL_IMPORT_COMMAND, language="powershell")
    st.warning(
        "Este comando no ejecuta pipeline, no ejecuta scoring, no genera ranking "
        "terapeutico y no valida biologica ni clinicamente el dataset."
    )

    _render_interpretation_limits()

    st.header("La GUI se detiene aqui")
    st.markdown(
        """
        - no pipeline;
        - no scoring;
        - no ranking;
        - no outputs cientificos;
        - no validacion clinica;
        - no validacion biologica;
        - siguiente fase futura: revision de calidad/evidencia antes de cualquier scoring.
        """
    )

    st.header("Siguiente fase futura")
    st.button("Importar dataset (deshabilitado en esta version)", disabled=True)
    st.caption(
        "La importacion con import_dataset.py queda documentada como siguiente fase; "
        "esta GUI solo prepara staging, valida manifest y muestra el comando manual."
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
