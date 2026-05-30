# First Real User-Curated Dataset Readiness Index

## 1. Proposito del indice

Este indice maestro consolida la preparacion operativa, documental e
interpretativa para recibir, revisar, importar y eventualmente correr de forma
controlada el primer dataset real `user_curated` en Nodos Funcionales.

Nodos Funcionales es una plataforma de priorizacion terapeutica basada en la
Teoria de Nodos Funcionales. No es un predictor clinico. Esta fase:

- no ejecuta validacion clinica;
- no ejecuta validacion experimental;
- no convierte evidencia local en evidencia externa verificada;
- no convierte curaduria de usuario en `controlled_reference`;
- no autoriza uso clinico;
- no sustituye revision experta;
- no cambia la logica de scoring.

## 2. Alcance

Este indice aplica a datasets reales `user_curated` antes de:

- importacion;
- revision experta;
- prueba controlada;
- scoring futuro;
- interpretacion de candidatos.

El flujo es multi-organismo y no esta acoplado a un organismo especifico. Los
organismos usados en fixtures, ejemplos o referencias historicas no son
defaults cientificos para el primer dataset real.

## 3. Documentos que consolida

Este indice conecta documentos ya presentes en el repositorio:

- `docs/real_user_curated_dataset_validation.md`: protocolo de validacion con
  datos reales antes de aceptar una corrida controlada.
- `docs/real_user_operational_guide.md`: guia operativa para preparar, validar,
  ejecutar e interpretar un dataset real.
- `docs/real_user_curated_dataset_checklist.md`: checklist previa a importacion
  o corrida controlada.
- `docs/user_curated_portable_validation_phase_index.md`: indice de validacion
  portable, offline y multi-organismo.
- `docs/internal_release_readiness_2026_05_27.md`: estado de madurez interna y
  limites antes del uso con datos reales.
- `docs/user_curated_interpretation_phase_closure.md`: cierre de reglas de
  interpretacion conservadora.
- `docs/user_curated_interpretation_release_closure.md`: cierre de release para
  interpretacion `user_curated`.
- `docs/methodology.md`: metodologia general del proyecto.
- `docs/data_model.md`: modelo de datos, variables y contratos interpretables.
- `README.md`: entrada general al repositorio y sus comandos principales.

Los documentos opcionales
`docs/reporting_evidence_strength_interpretation_closure.md` y
`docs/user_curated_evidence_quality_interpretation_closure.md` no estan
presentes actualmente. Si se agregan en el futuro, deben incorporarse a este
mapa sin cambiar la separacion de procedencias ni los limites interpretativos.

## 4. Estado actual de preparacion

El proyecto ya cuenta con:

- guia operativa para usuario real;
- checklist de dataset real;
- protocolo de validacion con datos reales;
- fixture portable minimo `user_curated`;
- pruebas documentales;
- pruebas de interpretacion conservadora;
- suite offline estable;
- separacion de procedencias;
- limites claros de interpretacion.

Esto significa listo para recibir y revisar un primer dataset real. No
significa validado clinicamente ni validado experimentalmente.

## 5. Flujo recomendado para el primer dataset real

1. Crear o recibir el dataset real en una ubicacion local adecuada.
2. Confirmar `dataset_id`.
3. Confirmar organismo y `taxon_id` si esta disponible.
4. Confirmar responsable / curator, fecha y version.
5. Revisar archivos minimos y manifest.
6. Aplicar la checklist operativa.
7. Clasificar genes y candidatos con identificadores estables.
8. Revisar evidencia, notas curatoriales y procedencia.
9. Marcar estados aplicables: `accepted_for_test`, `needs_revision`,
   `insufficient_evidence`, `pending_review`, `excluded_from_scoring`,
   `ready_for_import` o `conditionally_ready_for_controlled_test`.
10. Importar solo si cumple criterios.
11. Ejecutar pruebas controladas en un workspace temporal o dedicado.
12. Interpretar candidatos con lenguaje conservador.
13. Documentar cualquier exclusion o limitacion.

## 6. Reglas de procedencia

- `user_curated` significa evidencia aportada, revisada o seleccionada por el
  usuario.
- `user_curated` no equivale a `controlled_reference`.
- `user_curated` no debe mezclarse con `demo`.
- `user_curated` no debe mezclarse con `proxy`.
- `user_curated` no debe mezclarse con `cache`.
- `user_curated` no debe mezclarse con evidencia `online` no verificada.
- Una `local_note` o nota local no debe convertirse automaticamente en DOI,
  PubMed ID o literatura verificada.
- La evidencia `online`, si se usa en el futuro, debe permanecer separada y
  trazable.

La procedencia debe permitir distinguir evidencia local, literatura externa,
fuentes auxiliares, referencias controladas y enriquecimientos futuros.

## 7. Reglas de interpretacion conservadora

- `insufficient_evidence` significa riesgo no resuelto, no `low_risk`.
- `low_risk` solo puede usarse si hay evidencia suficiente para sostenerlo.
- `pending_review` no debe interpretarse como aceptado.
- `accepted_for_test` no significa validado clinicamente.
- `accepted_for_test` no significa validado experimentalmente.
- `include_for_structure_check` es control estructural, no validacion
  biologica.
- `curator_notes` no elevan `evidence_confidence_score` por si solas.
- `local_note` no equivale a literatura externa.
- `evidence_confidence_score` debe interpretarse por separado de
  `therapeutic_priority_score`.
- Un candidato con alto `therapeutic_priority_score` pero baja confianza debe
  interpretarse como prioritario pero incierto.
- Un candidato con baja evidencia no debe presentarse como blanco seguro.
- Score alto no equivale automaticamente a confianza alta.

## 8. Relacion con la Teoria de Nodos Funcionales

Esta fase sirve a la Teoria de Nodos Funcionales y a la madurez de su
validacion operativa. El software organiza evidencia y preserva trazabilidad;
no reemplaza el eje conceptual de la teoria.

La priorizacion integra dimensiones como:

- importancia funcional;
- selectividad;
- accesibilidad;
- evidencia;
- conservacion;
- contexto evolutivo;
- riesgo de escape evolutivo;
- redundancia;
- tolerancia mutacional;
- paralogia;
- contexto movil;
- HGT;
- recombinacion;
- asociacion con resistencia.

La subcapa evolutiva es moduladora. No reemplaza por si sola la evidencia
funcional ni la validacion experimental.

## 9. Criterios minimos antes de importar un dataset real

- [ ] `dataset_id` definido.
- [ ] Organismo definido.
- [ ] `taxon_id` documentado si esta disponible.
- [ ] Genes y candidatos con identificadores estables.
- [ ] Fuente declarada como `user_curated`.
- [ ] Responsable / curator definido.
- [ ] Fecha o version del dataset.
- [ ] Campos obligatorios presentes.
- [ ] Evidencia clasificada.
- [ ] Notas curatoriales separadas.
- [ ] Procedencia sin mezcla.
- [ ] Candidatos negativos o incompletos marcados como
      `insufficient_evidence` o `needs_revision`.
- [ ] Sin lenguaje de validacion clinica.
- [ ] Sin lenguaje de validacion experimental automatica.
- [ ] Sin conversion de evidencia local a literatura externa.

## 10. Criterios de exclusion o pausa

Pausar o excluir el candidato o dataset antes de importar o hacer scoring si
presenta:

- identificadores ambiguos;
- organismo no claro;
- evidencia contradictoria;
- procedencia mezclada;
- ausencia de campos obligatorios;
- evidencia insuficiente marcada como aceptada;
- `pending_review` tratado como `accepted_for_test`;
- `local_note` tratada como referencia externa;
- candidato presentado como seguro sin evidencia suficiente;
- confusion entre score y confidence.

Documentar `excluded_from_scoring` cuando la exclusion aplique a scoring.

## 11. Estados finales permitidos para la revision

- `ready_for_import`: estructura, evidencia y procedencia suficientes para la
  importacion declarada.
- `needs_revision`: requiere correcciones o aclaraciones antes de avanzar.
- `insufficient_evidence`: el riesgo permanece no resuelto.
- `excluded_from_scoring`: no debe entrar a scoring.
- `conditionally_ready_for_controlled_test`: preparacion limitada para una
  prueba controlada bajo reglas conservadoras.

`conditionally_ready_for_controlled_test` no significa validacion final,
validacion clinica ni validacion experimental.

## 12. Comandos sugeridos de PowerShell

Ejecutar la prueba documental focal:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_first_real_user_curated_dataset_readiness_index.py -q
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

## 13. Criterios de cierre de esta fase

La fase puede cerrarse si:

- [ ] el documento indice existe;
- [ ] la prueba documental pasa;
- [ ] la suite offline completa pasa;
- [ ] no hay cambios no deseados;
- [ ] `config/taxon_resolution_cache.json` fue revertido si solo cambio por
      timestamps o `refresh_count`;
- [ ] el working tree queda limpio despues del commit;
- [ ] se crea commit y tag.

## 14. Advertencia final

- No uso clinico.
- No predictor clinico.
- No validacion clinica.
- No validacion experimental.
- No reemplaza curaduria experta ni revision experta.
- No sustituye ensayos funcionales.
- No convierte priorizacion terapeutica en confirmacion de blanco terapeutico.
