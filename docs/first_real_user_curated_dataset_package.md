# First Real User-Curated Dataset Package

## 1. Proposito del paquete

Este documento define los archivos minimos, campos esperados, estados
permitidos y limites interpretativos para recibir el primer dataset real
`user_curated` en Nodos Funcionales.

Nodos Funcionales es una plataforma de priorizacion terapeutica basada en la
Teoria de Nodos Funcionales. No es un predictor clinico. Preparar este paquete:

- no ejecuta scoring;
- no modifica priorizacion;
- no valida clinicamente;
- no valida experimentalmente;
- no sustituye revision experta;
- no convierte evidencia local en evidencia externa;
- no convierte `user_curated` en `controlled_reference`;
- no autoriza uso clinico.

## 2. Alcance

El paquete aplica antes de:

- importacion;
- revision experta;
- prueba controlada;
- scoring futuro;
- interpretacion de candidatos.

El formato es multi-organismo y no esta acoplado a un organismo especifico.
Los nombres usados en los ejemplos son placeholders estructurales seguros. No
son datos reales, evidencia cientifica ni defaults biologicos.

## 3. Relacion con documentos previos

Este documento traduce la preparacion existente en un paquete de entrada
practico. Debe leerse junto con:

- `docs/real_user_curated_dataset_validation.md`;
- `docs/real_user_operational_guide.md`;
- `docs/real_user_curated_dataset_checklist.md`;
- `docs/first_real_user_curated_dataset_readiness_index.md`;
- `docs/user_curated_portable_validation_phase_index.md`;
- `docs/internal_release_readiness_2026_05_27.md`;
- `docs/methodology.md`;
- `docs/data_model.md`;
- `README.md`.

## 4. Estructura recomendada del paquete

```text
first_real_user_curated_dataset/
|-- manifest.yaml
|-- provenance.yaml
|-- raw_inputs/
|   |-- gene_list.csv
|   |-- functional_annotations.csv
|   |-- essentiality.csv
|   |-- virulence.csv
|   |-- conservation.csv
|   |-- localization.csv
|   |-- human_homologs.csv
|   |-- manual_curation.csv
|   `-- evidence_quality.csv
|-- curator_notes/
|   `-- notes.md
`-- README_dataset.md
```

No todos los archivos son obligatorios en todos los casos. Cada archivo ausente
debe declararse explicitamente, junto con el motivo y el impacto esperado.

## 5. Archivo `manifest.yaml`

Campos minimos esperados:

- `dataset_id`
- `dataset_name`
- `organism_name`
- `taxon_id`
- `strain_or_isolate`, si aplica
- `dataset_version`
- `created_by`
- `curator`
- `created_at`
- `updated_at`
- `provenance_type: user_curated`
- `intended_use`
- `not_for_clinical_use`
- `not_clinically_validated`
- `not_experimentally_validated`
- `notes`

Ejemplo minimo seguro con placeholders:

```yaml
dataset_id: "<dataset_id>"
dataset_name: "<dataset_name>"
organism_name: "<organism_name>"
taxon_id: "<taxon_id_if_available>"
strain_or_isolate: "<strain_or_isolate_if_applicable>"
dataset_version: "0.1-review"
created_by: "<responsible_person>"
curator: "<curator_name>"
created_at: "<YYYY-MM-DD>"
updated_at: "<YYYY-MM-DD>"
provenance_type: user_curated
intended_use: "controlled preparation and review"
not_for_clinical_use: true
not_clinically_validated: true
not_experimentally_validated: true
notes: "Structural example only. Replace placeholders with reviewed data."
```

## 6. Archivo `provenance.yaml`

Campos minimos esperados:

- `provenance_type`
- `source_scope`
- `curation_method`
- `external_literature_used`
- `online_lookup_used`
- `controlled_reference_used`
- `demo_data_used`
- `proxy_data_used`
- `cache_data_used`
- `review_status`
- `limitations`

Ejemplo conservador para un paquete local:

```yaml
provenance_type: user_curated
source_scope: "local reviewed inputs"
curation_method: "manual review documented by curator"
external_literature_used: false
online_lookup_used: false
controlled_reference_used: false
demo_data_used: false
proxy_data_used: false
cache_data_used: false
review_status: pending_review
limitations: "No external verification performed."
```

Cualquier uso futuro de evidencia externa, `online`, `controlled_reference`,
`demo`, `proxy` o `cache` debe declararse y mantenerse separado de
`user_curated`.

## 7. Archivo `raw_inputs/gene_list.csv`

Columnas minimas sugeridas:

- `gene`
- `protein_id`
- `locus_tag`
- `organism_name`
- `taxon_id`
- `product`
- `candidate_label`
- `review_status`
- `curator`
- `curator_notes`

Estados permitidos en `review_status`:

- `accepted_for_test`
- `needs_revision`
- `insufficient_evidence`
- `pending_review`
- `excluded_from_scoring`

Ejemplos estructurales seguros:

```csv
gene,protein_id,locus_tag,organism_name,taxon_id,product,candidate_label,review_status,curator,curator_notes
<gene_reviewed>,<protein_id_reviewed>,<locus_tag_reviewed>,<organism_name>,<taxon_id>,<reviewed_product>,<candidate_label>,accepted_for_test,<curator_name>,Reviewed for controlled test only
<gene_incomplete>,<protein_id_incomplete>,<locus_tag_incomplete>,<organism_name>,<taxon_id>,<product_if_known>,<candidate_label>,insufficient_evidence,<curator_name>,Risk remains unresolved
```

Los ejemplos describen forma, no evidencia biologica.

## 8. Archivo `raw_inputs/functional_annotations.csv`

Columnas sugeridas:

- `gene`
- `protein_id`
- `function`
- `pathway`
- `annotation_source`
- `annotation_confidence`
- `review_status`
- `curator_notes`

Una anotacion funcional no equivale a validacion experimental.

## 9. Archivo `raw_inputs/essentiality.csv`

Columnas sugeridas:

- `gene`
- `protein_id`
- `essentiality_label`
- `essentiality_score`
- `evidence_source`
- `evidence_type`
- `review_status`
- `curator_notes`

La esencialidad inferida o curada localmente debe mantenerse como
`user_curated`, salvo que exista una fuente controlada explicita y separada.

## 10. Archivo `raw_inputs/virulence.csv`

Columnas sugeridas:

- `gene`
- `protein_id`
- `virulence_label`
- `virulence_score`
- `evidence_source`
- `evidence_type`
- `review_status`
- `curator_notes`

La asociacion con virulencia no significa blanco terapeutico validado.

## 11. Archivo `raw_inputs/conservation.csv`

Columnas sugeridas:

- `gene`
- `protein_id`
- `conservation_score`
- `conservation_scope`
- `organisms_compared`
- `method`
- `review_status`
- `curator_notes`

La conservacion debe interpretarse junto con selectividad, accesibilidad,
evidencia y riesgo evolutivo.

## 12. Archivo `raw_inputs/localization.csv`

Columnas sugeridas:

- `gene`
- `protein_id`
- `predicted_localization`
- `localization_confidence`
- `method`
- `review_status`
- `curator_notes`

La localizacion predicha no equivale a accesibilidad experimental confirmada.

## 13. Archivo `raw_inputs/human_homologs.csv`

Columnas sugeridas:

- `gene`
- `protein_id`
- `human_homolog_status`
- `similarity_score`
- `method`
- `review_status`
- `curator_notes`

La ausencia de homologo humano no autoriza seguridad clinica.

## 14. Archivo `raw_inputs/manual_curation.csv`

Columnas sugeridas:

- `gene`
- `protein_id`
- `curation_decision`
- `curation_summary`
- `curator`
- `curation_date`
- `review_status`
- `local_note`
- `curator_notes`
- `include_for_structure_check`

Reglas:

- `local_note` no equivale a literatura externa.
- `curator_notes` no elevan confianza por si solas.
- `include_for_structure_check` no equivale a validacion experimental.
- `accepted_for_test` no equivale a blanco validado.

## 15. Archivo `raw_inputs/evidence_quality.csv`

Columnas sugeridas:

- `gene`
- `protein_id`
- `evidence_strength`
- `evidence_quality`
- `evidence_confidence_score`
- `evidence_source`
- `review_status`
- `limitations`
- `curator_notes`

Reglas:

- `evidence_confidence_score` es diferente de `therapeutic_priority_score`.
- Evidencia fuerte no equivale a validacion clinica.
- Baja evidencia no equivale automaticamente a bajo riesgo o `low_risk`.
- `insufficient_evidence` significa riesgo no resuelto.
- Score alto no equivale automaticamente a confianza alta.

## 16. Carpeta `curator_notes/`

Las notas curatoriales pueden registrar:

- dudas;
- decisiones;
- exclusiones;
- limitaciones;
- fuentes locales;
- conflictos de evidencia;
- razones de pausa.

Las notas curatoriales no son evidencia externa verificada por si mismas.

## 17. Archivo `README_dataset.md`

Cada dataset debe incluir un README propio con:

- descripcion breve;
- organismo;
- responsable;
- fecha;
- archivos incluidos;
- archivos faltantes;
- limitaciones;
- advertencia de no uso clinico;
- advertencia de no validacion experimental;
- contacto o responsable interno.

## 18. Estados permitidos

- `accepted_for_test`: revisado para el siguiente test controlado declarado.
- `needs_revision`: requiere correccion o aclaracion.
- `insufficient_evidence`: la evidencia es insuficiente y el riesgo permanece
  no resuelto.
- `pending_review`: todavia no aceptado.
- `excluded_from_scoring`: no debe entrar a scoring.
- `ready_for_import`: paquete listo para la importacion declarada.
- `conditionally_ready_for_controlled_test`: preparacion limitada para una
  prueba controlada bajo reglas conservadoras.

`conditionally_ready_for_controlled_test` no significa validacion final.

## 19. Criterios minimos para aceptar el paquete

- [ ] `dataset_id` presente.
- [ ] Organismo definido.
- [ ] Procedencia `user_curated`.
- [ ] Curator o responsable definido.
- [ ] Archivos presentes o faltantes justificados.
- [ ] Identificadores estables.
- [ ] Evidencia clasificada.
- [ ] Notas separadas de evidencia externa.
- [ ] Estados permitidos usados de forma consistente.
- [ ] Sin mezcla con `demo`, `proxy`, `cache`, `online` o
      `controlled_reference`.
- [ ] Sin lenguaje de validacion clinica o experimental automatica.

## 20. Criterios de pausa o rechazo

Pausar o rechazar el paquete si:

- falta organismo;
- falta `dataset_id`;
- los identificadores son ambiguos;
- hay procedencia mezclada;
- se usa evidencia `online` sin declararla;
- se marca evidencia insuficiente como aceptada;
- se usa `pending_review` como `accepted_for_test`;
- se presenta un candidato como seguro sin evidencia suficiente;
- se confunde `therapeutic_priority_score` con `evidence_confidence_score`;
- se usa lenguaje de validacion clinica;
- se usa lenguaje de validacion experimental automatica.

## 21. Relacion con la Teoria de Nodos Funcionales

El paquete permite capturar datos para alimentar la priorizacion basada en la
Teoria de Nodos Funcionales. Las capas pueden aportar:

- importancia funcional;
- selectividad;
- accesibilidad;
- evidencia;
- conservacion;
- contexto evolutivo;
- riesgo de escape evolutivo;
- redundancia de via;
- tolerancia mutacional;
- paralogia;
- contexto movil;
- HGT;
- recombinacion;
- asociacion con resistencia.

Estas capas sirven para priorizacion, no para confirmacion automatica de blanco
terapeutico. La subcapa evolutiva modula la interpretacion; no reemplaza la
evidencia funcional ni la validacion experimental.

## 22. Comandos sugeridos de PowerShell

Ejecutar la prueba documental focal:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_first_real_user_curated_dataset_package_doc.py -q
```

Ejecutar la suite offline completa:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -m "not online" -q
```

Revisar cambios:

```powershell
git status --short
git diff --name-only
```

Si `config/taxon_resolution_cache.json` cambia solo por timestamps,
`saved_at_utc`, `updated_at_utc` o `refresh_count`, revertirlo:

```powershell
git checkout -- config/taxon_resolution_cache.json
```

## 23. Criterios de cierre

La fase puede cerrarse si:

- [ ] el documento existe;
- [ ] la prueba documental pasa;
- [ ] la suite offline completa pasa;
- [ ] no hay cambios no deseados;
- [ ] `config/taxon_resolution_cache.json` fue revertido si solo cambio por
      timestamps o `refresh_count`;
- [ ] el working tree queda limpio despues del commit;
- [ ] se crea commit y tag.

## 24. Advertencia final

- No uso clinico.
- No predictor clinico.
- No validacion clinica.
- No validacion experimental.
- No reemplaza revision experta.
- No sustituye ensayos funcionales.
- No convierte priorizacion terapeutica en confirmacion de blanco terapeutico.
