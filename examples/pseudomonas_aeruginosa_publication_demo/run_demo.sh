#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INPUT_DIR="${SCRIPT_DIR}/input"
OUTPUT_DIR="${SCRIPT_DIR}/output"
WORKSPACE_DIR="${OUTPUT_DIR}/workspace"
DATA_USER_DIR="${WORKSPACE_DIR}/data_user"
SOURCE_PACKAGE_DIR="${WORKSPACE_DIR}/source_package"

RUN_DISCOVERY_DRY_RUN="false"
if [[ "${1:-}" == "--run-discovery-dry-run" ]]; then
  RUN_DISCOVERY_DRY_RUN="true"
fi

required_inputs=(
  "gene_list.csv"
  "manual_curation.csv"
  "evidence_quality.csv"
  "manifest.yaml"
  "provenance.yaml"
  "notes.md"
)

for name in "${required_inputs[@]}"; do
  if [[ ! -f "${INPUT_DIR}/${name}" ]]; then
    echo "[ERROR] Missing required demo input: ${INPUT_DIR}/${name}" >&2
    exit 1
  fi
done

mkdir -p "${DATA_USER_DIR}" "${SOURCE_PACKAGE_DIR}" "${OUTPUT_DIR}"

cp "${INPUT_DIR}/gene_list.csv" "${DATA_USER_DIR}/gene_list.csv"
cp "${INPUT_DIR}/manual_curation.csv" "${DATA_USER_DIR}/manual_curation.csv"
cp "${INPUT_DIR}/evidence_quality.csv" "${DATA_USER_DIR}/evidence_quality.csv"
cp "${INPUT_DIR}/manifest.yaml" "${SOURCE_PACKAGE_DIR}/manifest.yaml"
cp "${INPUT_DIR}/provenance.yaml" "${SOURCE_PACKAGE_DIR}/provenance.yaml"
cp "${INPUT_DIR}/notes.md" "${SOURCE_PACKAGE_DIR}/notes.md"

cat > "${OUTPUT_DIR}/DEMO_RUN_NOTES.md" <<EOF
# Pseudomonas aeruginosa publication demo run

Prepared workspace: ${WORKSPACE_DIR}
Input provenance: user_curated
Scope: reproducible publication demo structure only
Clinical validation: no
Experimental validation: no
Clinical efficacy prediction: no

The prepared workspace contains the currently available user-curated layers.
Additional reviewed organism-specific layers are required before interpreting a
full therapeutic ranking.
EOF

echo "[OK] Prepared demo workspace: ${WORKSPACE_DIR}"
echo "[OK] Copied user_curated inputs into data_user/"
echo "[OK] Preserved manifest, provenance, and notes in source_package/"

if [[ "${RUN_DISCOVERY_DRY_RUN}" == "true" ]]; then
  PYTHON_BIN="${PYTHON_EXE:-python}"
  if [[ ! -f "${PROJECT_ROOT}/run_pipeline.py" ]]; then
    echo "[ERROR] Missing pipeline entry point: ${PROJECT_ROOT}/run_pipeline.py" >&2
    exit 1
  fi
  echo "[OK] Running offline discovery dry-run only"
  (
    cd "${PROJECT_ROOT}"
    "${PYTHON_BIN}" run_pipeline.py --organism "Pseudomonas aeruginosa" --strain "not_specified" --workspace "${WORKSPACE_DIR}" --offline-only --dry-run
  )
fi

echo "[OK] Demo preparation completed without writing global result folders."

