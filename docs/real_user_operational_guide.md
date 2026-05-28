# Real user operational guide

## Proposito

Esta guia esta escrita para un real user que quiere preparar, validar e
interpretar un dataset `user_curated` minimo en Nodos Funcionales.

La guia cubre:

- como preparar un dataset `user_curated`;
- como validar el dataset antes de correr analisis;
- como ejecutar el flujo offline cuando el paquete ya fue revisado;
- como interpretar reportes finales con conservative interpretation /
  interpretacion conservadora.

Nodos Funcionales es una plataforma de priorizacion terapeutica. No es un
predictor clinico definitivo / not a clinical predictor.

## Que es user_curated

`user_curated` significa evidencia aportada, revisada o aceptada por el usuario
para un organismo y alcance declarados. No significa evidencia externa
verificada automaticamente.

`user_curated` tampoco equivale por si mismo a no clinical validation /
no validacion clinica ni no experimental validation / no validacion
experimental. Si una fila fue revisada localmente, eso debe leerse como
provenance / procedencia curatorial, no como prueba de eficacia o seguridad.

## Capas minimas esperadas

Para un paquete inicial, preparar o revisar estas capas cuando apliquen al
flujo actual:

- `organism_profile`
- `gene_list`
- `functional_annotations`
- `conservation`
- `evolutionary_escape_risk`
- `manual_curation`
- `evidence_quality`
- `external_sources`, si el flujo necesita declarar fuentes externas revisadas
  por el usuario

Usar las plantillas en `data_templates/` como punto de partida. Si una capa no
esta disponible, marcar el faltante de forma explicita en notas o manifest, en
lugar de llenar valores inventados.

## Recomendaciones para llenar datos

- Usar identificadores consistentes de `gene` y `protein_id` en todas las capas.
- Indicar organismo y cepa como datos de entrada, no como defaults cientificos.
- Declarar procedencia `user_curated`, `user` o `local_review` segun el esquema
  de la capa y el manifest.
- Documentar `curator_notes` y `local_note` como contexto curatorial, sin elevar
  confianza automaticamente.
- Usar `pending_review` o insufficient evidence / evidencia insuficiente cuando
  falte evidencia.
- No usar demo, proxy, cache, online ni `controlled_reference` como si fueran
  evidencia directa del usuario.
- Separar evidencia externa revisada de evidencia externa no verificada.

## Comandos orientativos en PowerShell

Revisar primero que el repositorio no tenga cambios sueltos:

```powershell
git status --short
```

Crear un paquete local ignorado por Git:

```powershell
.\scripts\new_user_curated_dataset.ps1 -ProjectId <project_id>
```

Validar el paquete completo:

```powershell
.\scripts\validate_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id>
```

Validar solo el manifest, si se quiere aislar ese paso:

```powershell
.\scripts\validate_user_curated_manifest.ps1 -ManifestPath user_curated_staging\<project_id>\manifest.csv
```

Importar una capa revisada, si el paquete ya paso validacion:

```powershell
.\scripts\run_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id> -ImportDataset -Dataset <dataset> -InputFile user_curated_staging\<project_id>\raw_inputs\<archivo.csv> -Workspace <workspace_temporal_o_dedicado> -Organism "<organism_name>" -Strain "<strain_or_isolate>"
```

Ejecutar el pipeline offline solo despues de revisar manifest, archivos,
procedencia y faltantes:

```powershell
.\scripts\run_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id> -RunPipeline -Workspace <workspace_temporal_o_dedicado> -Organism "<organism_name>" -Strain "<strain_or_isolate>"
```

Correr la suite offline del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -m "not online" -q
```

Si hay dudas sobre parametros, consultar `README.md`,
`docs/user_friendly_workflow.md`, `docs/user_curated_real_dataset_readiness.md`
y los scripts existentes antes de ejecutar.

## Interpretacion de outputs

Revisar los outputs finales dentro del workspace usado para la corrida:

- `ranking_nodos.csv`: ranking computacional de candidatos. Leer
  `therapeutic_priority_score` separado de `evidence_confidence_score`.
- `report_phase2.md`: resumen interpretativo del analisis.
- `candidate_explanations_simple.csv` y
  `candidate_explanations_simple.md`: explicaciones por candidato.
- `candidate_audit.csv` y `candidate_audit.md`: auditoria de variables,
  procedencia y limites.
- `evidence_strength_audit.csv` y `evidence_strength_audit.md`: lectura de
  fuerza de evidencia, incluyendo insufficient evidence.
- `layer_resolution_summary.csv` y `layer_resolution_summary.md`: resumen de
  resolucion de capas y provenance / procedencia.

## Limites interpretativos

- `therapeutic_priority_score` no es `evidence_confidence_score`.
- Score alto no equivale automaticamente a confianza alta.
- Insufficient evidence / evidencia insuficiente no equivale a bajo riesgo.
- Ausencia de evidencia no equivale a seguridad.
- `pending_review`, `local_note`, `curator_notes` e
  `include_for_structure_check` no elevan confianza por si mismos.
- No usar lenguaje como `safe_target`, `clinically_valid`,
  `validated_clinically` o `validated_experimentally`.
- La plataforma no es un predictor clinico definitivo.

## Checklist final para usuario

- [ ] Dataset tiene organismo y cepa definidos.
- [ ] Genes y proteinas tienen identificadores consistentes.
- [ ] Procedencia declarada en manifest y capas.
- [ ] Evidencia insuficiente marcada de forma explicita.
- [ ] Notas curatoriales separadas de validacion externa.
- [ ] demo, proxy, cache, online y `controlled_reference` no se usan como
      evidencia `user_curated`.
- [ ] Reportes revisados con lectura conservadora.
