from __future__ import annotations
try:
    from nodos_funcionales.user_curated_scoring_approval import (
        summarize_scoring_approval,
        validate_scoring_approval,
    )
except ImportError:
    summarize_scoring_approval = None
    validate_scoring_approval = None

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
from src.nodos_funcionales.user_curated_quality_gate import assess_pre_scoring_readiness
from src.nodos_funcionales.user_curated_validation import validate_user_curated_manifest
from src.nodos_funcionales.publication_gui_readers import (
    PUBLICATION_FIGURES,
    PUBLICATION_TABLES,
    build_candidate_index,
    get_candidate_details,
    get_conservative_gui_warning,
    load_publication_table,
    summarize_publication_package,
)


APP_TITLE = "Nodos Funcionales - user_curated onboarding"
APP_SUBTITLE = (
    "Flujo seguro user_curated: staging local, manifest, evidencia, quality gate, "
    "resumen experto e importacion validada asistida como comando manual."
)
SAFETY_NOTICE = (
    "Esta GUI no ejecuta pipeline, no ejecuta scoring, no importa datasets y no "
    "genera ranking terapeutico ni outputs cientificos. No versionar datos reales."
)
MANUAL_IMPORT_COMMAND = (
    r".\.venv\Scripts\python.exe import_dataset.py "
    r"--validate-user-curated-manifest <ruta_manifest.csv>"
)
EXPERT_REVIEW_REMINDERS = [
    "No es validacion biologica.",
    "No es validacion clinica.",
    "No implica recomendacion terapeutica.",
    "No sustituye revision experta.",
    "Un score alto, en fases futuras, no equivale automaticamente a confianza alta.",
]
PUBLICATION_PACKAGE_DIR = PROJECT_ROOT / "results" / "publication_package"
EXPECTED_PUBLICATION_FIGURES_FOR_REVIEW = [
    "figure_1_top_candidates_meta_priority.png",
    "figure_2_priority_vs_confidence.png",
    "figure_3_score_decomposition.png",
    "figure_4_evolutionary_risk_vs_priority.png",
    "figure_5_ranking_stability.png",
    "figure_6_therapeutic_role_distribution.png",
]
PUBLICATION_RESULTS_WARNINGS = [
    "These results are computationally prioritized hypotheses.",
    "Each candidate is a computationally prioritized hypothesis requiring independent validation.",
    "They do not represent experimental validation.",
    "They do not represent clinical validation.",
    "A high therapeutic_priority_score does not imply high evidence_confidence_score.",
    "demo_only, preliminary, proxy, missing, not_assessed or insufficient_evidence labels must remain visible.",
]
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


def _declared_input_path(manifest_path: Path, input_file: str) -> Path:
    declared_path = Path(input_file)
    if declared_path.is_absolute():
        return declared_path
    return manifest_path.parent / declared_path


def _detected_summary_files(manifest_path: Path, rows: list[dict[str, str]]) -> list[str]:
    detected_files = [
        f"manifest.csv: {'detectado' if manifest_path.is_file() else 'no detectado'} ({manifest_path})"
    ]
    for row_index, row in enumerate(rows, start=2):
        input_file = (row.get("input_file") or "").strip()
        if not input_file:
            detected_files.append(f"fila {row_index}: input_file no declarado")
            continue

        input_path = _declared_input_path(manifest_path, input_file)
        state = "detectado" if input_path.is_file() else "no detectado"
        detected_files.append(f"fila {row_index}: {state} ({input_file})")
    return detected_files


def _summary_dataset_ids(rows: list[dict[str, str]]) -> list[str]:
    dataset_ids = {
        (row.get("dataset_id") or "").strip()
        for row in rows
        if (row.get("dataset_id") or "").strip()
    }
    return sorted(dataset_ids) or ["no declarado"]


def _manual_import_command_for_summary(manifest_path: Path, status: str) -> str | None:
    if status != "conditionally_ready_for_future_controlled_scoring":
        return None
    return MANUAL_IMPORT_COMMAND.replace("<ruta_manifest.csv>", str(manifest_path))


def _build_expert_review_summary(manifest_path: Path) -> dict[str, object]:
    structural_errors = validate_user_curated_manifest(manifest_path)
    rows, read_errors = _load_manifest_rows(manifest_path)
    assessment = assess_pre_scoring_readiness(manifest_path)
    visual_warnings = _review_manifest_rows(rows) if rows else []
    warnings = [*structural_errors, *read_errors, *visual_warnings, *assessment["warnings"]]
    manifest_status = "valido estructuralmente" if not structural_errors and not read_errors else "con errores"
    import_command = _manual_import_command_for_summary(manifest_path, assessment["status"])

    lines = [
        "# Resumen final user_curated para revision experta",
        "",
        "Este resumen se genera antes de cualquier scoring o pipeline.",
        "",
        "## Dataset",
        f"- dataset_id: {', '.join(_summary_dataset_ids(rows))}",
        f"- manifest_path: {manifest_path}",
        f"- estado_manifest_csv: {manifest_status}",
        f"- resultado_quality_gate: {assessment['status']}",
        f"- decision_final: {assessment['status']}",
        "",
        "## Archivos detectados",
    ]
    lines.extend(f"- {item}" for item in _detected_summary_files(manifest_path, rows))
    lines.extend(
        [
            "",
            "## Advertencias principales",
        ]
    )
    if warnings:
        lines.extend(f"- {warning}" for warning in dict.fromkeys(warnings))
    else:
        lines.append("- Sin advertencias tecnicas detectadas por esta vista.")

    lines.extend(
        [
            "",
            "## Limites y separacion de fuentes",
            "- Este resumen conserva source_type=user_curated como alcance esperado.",
            "- No mezclar user_curated con demo, proxy, cache, controlled_reference u online.",
        ]
    )
    lines.extend(f"- {reminder}" for reminder in EXPERT_REVIEW_REMINDERS)
    lines.extend(
        [
            "- No ejecuta scoring, no ejecuta pipeline y no genera rankings.",
            "- No escribe outputs cientificos en results/, data_processed/ ni data_sessions/.",
        ]
    )

    if import_command:
        lines.extend(
            [
                "",
                "## Comando manual sugerido para importacion validada",
                "```powershell",
                import_command,
                "```",
                "",
                "El comando es manual y no se ejecuta desde esta GUI.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Comando manual sugerido para importacion validada",
                "- No se sugiere todavia: primero resolver el estado del quality gate.",
            ]
        )

    return {
        "dataset_ids": _summary_dataset_ids(rows),
        "detected_files": _detected_summary_files(manifest_path, rows),
        "manifest_status": manifest_status,
        "quality_gate": assessment,
        "warnings": list(dict.fromkeys(warnings)),
        "import_command": import_command,
        "markdown": "\n".join(lines),
    }


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
    st.subheader("Checklist visual de archivos locales")
    st.caption("Use esta lista dentro de la revision local antes de validar el manifest.")
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
        - un manifest valido no equivale a validacion biologica;
        - un quality gate favorable no equivale a recomendacion terapeutica;
        - un scoring futuro no sustituye revision experta;
        - un score alto no equivale automaticamente a confianza alta;
        - importar no significa evidencia suficiente ni validacion clinica.
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


def _render_quality_gate_view(manifest_input: str) -> None:
    if not manifest_input.strip():
        st.error("Indique la ruta del manifest.csv antes de evaluar el quality gate.")
        return

    manifest_path = _resolve_manifest_path(manifest_input)
    assessment = assess_pre_scoring_readiness(manifest_path)
    status = assessment["status"]

    if status == "not_ready_for_scoring":
        st.error(status)
    elif status == "requires_expert_review":
        st.warning(status)
    else:
        st.success(status)

    if assessment["errors"]:
        st.markdown("Errores que bloquean avance:")
        for error in assessment["errors"]:
            st.markdown(f"- `{error}`")

    if assessment["warnings"]:
        st.markdown("Advertencias conservadoras:")
        for warning in assessment["warnings"]:
            st.markdown(f"- {warning}")

    st.markdown("Checklist informativa del quality gate:")
    for key, value in assessment["checklist"].items():
        st.markdown(f"- `{key}`: `{value}`")

    st.warning(
        "Este quality gate previo a scoring no ejecuta scoring, no ejecuta pipeline, "
        "no genera ranking, no genera outputs cientificos y requiere revision experta."
    )


def _render_expert_review_summary(manifest_input: str) -> None:
    if not manifest_input.strip():
        st.error("Indique la ruta del manifest.csv antes de generar el resumen final.")
        return

    manifest_path = _resolve_manifest_path(manifest_input)
    summary = _build_expert_review_summary(manifest_path)
    quality_gate = summary["quality_gate"]
    st.subheader("Resumen integral antes de scoring")
    st.markdown(f"- `dataset_id`: `{', '.join(summary['dataset_ids'])}`")
    st.markdown(f"- `estado_manifest.csv`: `{summary['manifest_status']}`")
    st.markdown(f"- `resultado_quality_gate`: `{quality_gate['status']}`")
    st.markdown(f"- `decision_final`: `{quality_gate['status']}`")

    st.markdown("Archivos detectados:")
    for detected_file in summary["detected_files"]:
        st.markdown(f"- {detected_file}")

    st.markdown("Advertencias principales:")
    if summary["warnings"]:
        for warning in summary["warnings"]:
            st.markdown(f"- {warning}")
    else:
        st.markdown("- Sin advertencias tecnicas detectadas por esta vista.")

    st.code(summary["markdown"], language="markdown")
    st.download_button(
        "Descargar resumen Markdown local",
        data=summary["markdown"],
        file_name="user_curated_expert_review_summary.md",
        mime="text/markdown",
    )
    if summary["import_command"]:
        st.markdown("Comando manual sugerido para importacion validada:")
        st.code(summary["import_command"], language="powershell")
    else:
        st.info("El comando manual de importacion solo se sugiere cuando el quality gate aplica.")

    st.warning(
        "No es validacion biologica ni clinica, no implica recomendacion terapeutica "
        "y no sustituye revision experta."
    )


def _render_publication_results_review() -> None:
    st.header("8. Revisar resultados publicables")
    st.markdown(
        """
        Panel de solo lectura para revisar `results/publication_package/`.
        No regenera el paquete, no ejecuta pipeline, no ejecuta scoring, no ejecuta
        Snakemake y no modifica `results/`, `data_processed/` ni `data_sessions/`.
        """
    )
    for warning in PUBLICATION_RESULTS_WARNINGS:
        st.warning(warning)

    package_dir_text = st.text_input(
        "Publication package directory",
        value=str(PUBLICATION_PACKAGE_DIR),
        key="publication_package_dir",
    )
    package_dir = Path(package_dir_text)
    summary = summarize_publication_package(package_dir)
    if not summary["exists"]:
        st.info(f"No publication_package directory found at: {package_dir}")
        return

    st.subheader("Publication package overview")
    st.markdown(f"- `publication_package`: `{package_dir}`")
    st.markdown(f"- tables found: `{summary['tables_found']}` / `{len(PUBLICATION_TABLES)}`")
    st.markdown(f"- figures found: `{summary['figures_found']}` / `{len(PUBLICATION_FIGURES)}`")
    st.markdown(f"- publication_results_manifest.json: `{summary['manifest_exists']}`")
    st.markdown(f"- README_publication_package.md: `{summary['readme_exists']}`")
    if summary["manifest_error"]:
        st.warning(summary["manifest_error"])
    elif summary["manifest"]:
        st.json(summary["manifest"])
    if summary["readme_exists"]:
        st.caption(f"README_publication_package.md: {summary['readme_path']}")

    st.subheader("Tables")
    st.dataframe(summary["tables"], use_container_width=True)
    for table_name in PUBLICATION_TABLES:
        table_path = package_dir / table_name
        table, error = load_publication_table(table_path)
        if error:
            st.warning(error)
            continue
        st.markdown(f"**{table_name}**")
        st.caption(f"Source: {table_path}")
        st.dataframe(table.head(20), use_container_width=True)

    st.subheader("Figures")
    figures_dir = package_dir / "figures"
    st.dataframe(summary["figures"], use_container_width=True)
    for figure_name in EXPECTED_PUBLICATION_FIGURES_FOR_REVIEW:
        figure_path = figures_dir / figure_name
        st.markdown(f"- `{figure_name}`: `{figure_path}`")
        if figure_path.is_file():
            st.image(str(figure_path), caption=figure_name)
        else:
            st.warning(f"Missing expected figure: {figure_name}")

    st.subheader("Candidate explorer")
    candidates = build_candidate_index(package_dir)
    if not candidates:
        st.warning("No candidates found in publication_table_1_top_candidates.csv.")
    else:
        labels = [str(candidate["label"]) for candidate in candidates]
        selected_label = st.selectbox("Select candidate by gene / protein_id", labels)
        selected = candidates[labels.index(selected_label)]
        candidate_id = str(selected["candidate_id"])
        details = get_candidate_details(package_dir, candidate_id)
        for warning in details.get("warnings", []):
            st.warning(warning)
        st.markdown("Identification")
        st.json(details.get("identification", {}))
        st.markdown("Scores")
        st.json(details.get("scores", {}))
        st.markdown("Interpretation")
        st.json(details.get("interpretation", {}))
        st.warning(get_conservative_gui_warning())

    st.subheader("Conservative interpretation")
    st.markdown(
        """
        - `therapeutic_priority_score` and `evidence_confidence_score` are separate.
        - `evolutionary_escape_risk_score` must remain visible during review.
        - `demo_only`, `preliminary`, `proxy`, `missing`, `not_assessed` and
          `insufficient_evidence` labels must remain visible.
        - The GUI only reviews existing publication_package files and does not
          modify `results/`, `data_processed/` or `data_sessions/`.
        """
    )


def _render_manual_approval_review() -> None:
    st.header("Manual approval for future controlled scoring")

    st.warning(
        "This section does not run scoring, does not run the pipeline, and does not "
        "generate rankings. It only reviews whether a manual expert approval record "
        "could allow a future controlled scoring step."
    )

    approval_file = st.file_uploader(
        "Upload manual approval JSON for review only",
        type=["json"],
        key="manual_approval_json",
    )

    if approval_file is not None:
        if validate_scoring_approval is None or summarize_scoring_approval is None:
            st.error("Approval validation module is not available.")
        else:
            import json

            try:
                approval_record = json.load(approval_file)
                approval_validation = validate_scoring_approval(approval_record)

                st.subheader("Approval validation result")
                st.json(approval_validation)

                st.subheader("Conservative approval summary")
                st.text(summarize_scoring_approval(approval_record))

                if approval_validation["allows_controlled_scoring"]:
                    st.success(
                        "This approval record may allow a future controlled scoring step, "
                        "but scoring is not executed from this GUI."
                    )
                else:
                    st.error("This approval record does not allow controlled scoring.")

                st.info(
                    "Even with approval, future scoring would not represent biological "
                    "validation, clinical validation, or a therapeutic recommendation."
                )

            except Exception as exc:
                st.error(f"Could not read approval JSON: {exc}")
    else:
        st.info(
            "No approval file uploaded. Future controlled scoring remains unavailable "
            "without explicit expert approval."
        )


def _render_streamlit_app() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="centered")
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)
    st.warning(SAFETY_NOTICE)

    st.markdown(
        """
        Esta interfaz guia siete pasos conservadores para `user_curated`:
        staging local, revision de archivos, validacion de manifest, revision
        de evidencia, quality gate, resumen para revision experta e importacion
        validada asistida como comando manual. Mantiene el flujo detenido antes
        de cualquier pipeline o scoring.
        """
    )

    st.header("Que hace esta GUI")
    st.markdown(
        """
        - crea `user_curated_staging/<project_id>/` con la logica existente;
        - muestra rutas locales esperadas para `README.md`, `manifest.csv`,
          `raw_inputs/`, `notes/` y `provenance/`;
        - prevalida un manifest con `validate_user_curated_manifest()`;
        - revisa evidencia, quality gate y resumen exportable sin ejecutar scoring;
        - muestra el comando manual de importacion validada sin ejecutarlo.
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

    st.header("4. Revision visual de calidad/evidencia del dataset")
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

    st.header("5. Quality gate previo a scoring")
    st.markdown(
        """
        Esta compuerta conservadora concentra la decision previa a cualquier
        scoring futuro. Evalua el manifest sin ejecutar pipeline, sin generar
        rankings y sin crear outputs cientificos. Un estado favorable no es una
        recomendacion terapeutica.
        """
    )
    st.caption(
        "Estados posibles: not_ready_for_scoring, requires_expert_review, "
        "conditionally_ready_for_future_controlled_scoring."
    )
    quality_gate_manifest_input = st.text_input(
        "Ruta a manifest.csv para quality gate",
        placeholder=r"user_curated_staging\<project_id>\manifest.csv",
        key="quality_gate_manifest_path",
    )
    if st.button("Evaluar quality gate informativo"):
        _render_quality_gate_view(quality_gate_manifest_input)
    st.caption(
        "La plantilla manual esta en docs/templates/user_curated_pre_scoring_approval_template.md."
    )

    st.header("6. Resumen final exportable para revision experta")
    st.markdown(
        """
        Esta vista genera un resumen Markdown copiable o descargable desde
        Streamlit. Resume el manifest y el quality gate sin escribir outputs
        cientificos, sin ejecutar scoring, sin ejecutar pipeline y sin generar
        rankings.
        """
    )
    st.caption(
        "Mantener user_curated separado de demo, proxy, cache, controlled_reference y online."
    )
    summary_manifest_input = st.text_input(
        "Ruta a manifest.csv para resumen final",
        placeholder=r"user_curated_staging\<project_id>\manifest.csv",
        key="expert_review_summary_manifest_path",
    )
    if st.button("Generar resumen final exportable"):
        _render_expert_review_summary(summary_manifest_input)

    st.header("7. Importacion validada asistida como comando manual")
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
        "La GUI no ejecuta este comando. Tampoco ejecuta pipeline, scoring ni rankings, "
        "y no valida biologica ni clinicamente el dataset."
    )

    _render_publication_results_review()
    _render_manual_approval_review()
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
        - cualquier scoring futuro queda fuera de esta GUI.
        """
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

