# Real User-Curated Dataset Checklist

## Proposito

Esta checklist operativa ayuda a revisar un dataset real `user_curated` antes
de importarlo o usarlo en una corrida controlada de Nodos Funcionales.

Nodos Funcionales es una plataforma de priorizacion terapeutica. No es un
predictor clinico y debe presentarse como no predictor clinico. La checklist
conserva trazabilidad, separacion de fuentes e interpretacion conservadora antes
de cualquier scoring.

## Alcance

Usar esta checklist con datasets reales `user_curated` preparados en una
carpeta local de staging, antes de:

- importar una capa;
- preparar un workspace temporal o dedicado;
- ejecutar una corrida controlada;
- interpretar scores o reportes.

La revision se aplica al manifest, los archivos en `raw_inputs/`, la curacion
manual cuando exista, la calidad de evidencia cuando aplique, las notas
curatoriales y la documentacion de provenance / procedencia.

## Exclusiones

Completar esta checklist significa que el dataset tiene estructura y
procedencia suficientes para el siguiente paso declarado. No significa:

- no clinical validation / no validacion clinica;
- no experimental validation / no validacion experimental;
- confirmacion de eficacia, seguridad o aplicabilidad terapeutica;
- conversion de evidencia local en evidencia externa;
- inferencia automatica de literatura o evidencia online.

La checklist no sustituye revision experta ni validacion experimental.

## 1. Identidad del dataset

- [ ] `dataset_id` identifica el dataset de forma estable.
- [ ] `organism_name` declara el organismo bacteriano.
- [ ] `taxon_id` esta documentado si existe.
- [ ] El curator / responsable esta identificado.
- [ ] La fecha de preparacion o revision esta registrada.
- [ ] La version del dataset permite distinguir revisiones.
- [ ] La fuente `user_curated` esta declarada de forma explicita.

Detener la revision si no puede confirmarse la identidad del dataset o el
organismo.

## 2. Archivos minimos esperados

- [ ] Existe un `manifest.csv` o manifest equivalente.
- [ ] Existe la carpeta `raw_inputs/` con los archivos declarados.
- [ ] Existe `manual_curation` si aplica al alcance del dataset.
- [ ] Existe `evidence_quality` si aplica al alcance del dataset.
- [ ] Existen notas curatoriales para limites, faltantes o decisiones locales.
- [ ] Existe documentacion de provenance / procedencia y configuracion usada.

Registrar explicitamente los archivos o capas que no apliquen. No llenar
faltantes con datos inventados.

## 3. Procedencia

- [ ] `user_curated` esta claramente declarado para evidencia real aportada o
      revisada por el usuario.
- [ ] No hay mezcla con `demo`.
- [ ] No hay mezcla con `proxy`.
- [ ] No hay mezcla con `cache`.
- [ ] No hay mezcla con `controlled_reference`.
- [ ] No se infiere evidencia `online` automatica como evidencia aceptada.
- [ ] Cada excepcion o fuente auxiliar esta separada y documentada.

`controlled_reference`, `demo`, `proxy`, `cache` y `online` deben conservarse
como categorias distintas de `user_curated`. Si existe una mezcla no resuelta,
detener la revision antes de importacion y scoring.

## 4. Genes y candidatos

Para cada gen o candidato:

- [ ] Existe un identificador estable.
- [ ] El nombre de gen esta declarado si existe.
- [ ] `protein_id` esta declarado si existe.
- [ ] La funcion propuesta esta descrita sin inventar evidencia.
- [ ] El organismo esta identificado.
- [ ] El estado de revision esta declarado.

Detener la revision si los identificadores son ambiguos o no puede vincularse
el candidato con el organismo declarado.

## 5. Evidencia

Revisar y distinguir explicitamente estos estados o campos cuando apliquen:

- [ ] `accepted_for_test`: evidencia revisada y aceptada para el siguiente test
      controlado declarado.
- [ ] `needs_revision`: evidencia que requiere correccion o aclaracion.
- [ ] `insufficient_evidence`: evidencia insuficiente; el riesgo sigue sin
      resolverse.
- [ ] `pending_review`: evidencia todavia pendiente de revision.
- [ ] `local_note`: nota local, no literatura externa.
- [ ] `curator_notes`: contexto curatorial, no aumento automatico de confianza.
- [ ] `include_for_structure_check`: inclusion para control estructural, no
      validacion experimental.

## 6. Interpretacion conservadora

- [ ] `insufficient_evidence` significa riesgo no resuelto; no equivale a
      `low_risk`.
- [ ] `pending_review` no debe entrar como aceptado.
- [ ] `local_note` no debe convertirse en DOI, literatura o evidencia externa.
- [ ] `curator_notes` no elevan `evidence_confidence_score` por si solas.
- [ ] `include_for_structure_check` es control estructural, no validacion
      experimental.
- [ ] `therapeutic_priority_score` se interpreta separado de
      `evidence_confidence_score`.
- [ ] Un score alto no convierte automaticamente evidencia incompleta en
      evidencia fuerte.

## 7. Exclusiones antes de scoring

Marcar `excluded_from_scoring` y detener el avance del candidato cuando exista:

- [ ] evidencia contradictoria no resuelta;
- [ ] identificadores ambiguos;
- [ ] organismo no claro;
- [ ] campos obligatorios ausentes;
- [ ] procedencia mezclada;
- [ ] `insufficient_evidence` marcada incorrectamente como aceptada.

La exclusion debe quedar documentada. No corregirla elevando scores ni
confianza de forma manual.

## 8. Salidas esperadas de revision

Asignar una salida explicita al dataset o candidato revisado:

- `ready_for_import`: estructura y procedencia suficientes para importacion.
- `needs_revision`: faltan correcciones o aclaraciones.
- `insufficient_evidence`: la evidencia no permite avanzar como aceptada.
- `excluded_from_scoring`: no debe entrar a scoring.
- `conditionally_ready_for_controlled_test`: puede pasar a un test controlado
  con condiciones y limites documentados.

Ninguna salida confirma valor clinico ni validacion experimental.

## 9. Comandos sugeridos de PowerShell

Desde la raiz del repositorio, revisar primero el estado de Git:

```powershell
git status --short
```

Crear un paquete local ignorado por Git:

```powershell
.\scripts\new_user_curated_dataset.ps1 -ProjectId <project_id>
```

Verificar la estructura local:

```powershell
Get-ChildItem user_curated_staging\<project_id>
```

Validar el paquete completo:

```powershell
.\scripts\validate_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id>
```

Validar solo el manifest:

```powershell
.\scripts\validate_user_curated_manifest.ps1 -ManifestPath user_curated_staging\<project_id>\manifest.csv
```

Importar una capa revisada en un workspace temporal o dedicado:

```powershell
.\scripts\run_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id> -ImportDataset -Dataset <dataset> -InputFile user_curated_staging\<project_id>\raw_inputs\<archivo.csv> -Workspace <workspace_temporal_o_dedicado> -Organism "<organism_name>" -Strain "<strain_or_isolate>"
```

Ejecutar una corrida offline controlada solo despues del cierre de revision:

```powershell
.\scripts\run_user_curated_dataset.ps1 -ProjectPath user_curated_staging\<project_id> -RunPipeline -Workspace <workspace_temporal_o_dedicado> -Organism "<organism_name>" -Strain "<strain_or_isolate>"
```

## 10. Criterios de cierre

Cerrar la revision solo cuando:

- [ ] identidad, organismo, curator, fecha y version estan documentados;
- [ ] manifest, `raw_inputs/`, notas y procedencia fueron revisados;
- [ ] faltantes y capas no aplicables estan marcados explicitamente;
- [ ] no existe mezcla no resuelta entre `user_curated`,
      `controlled_reference`, `demo`, `proxy`, `cache` y `online`;
- [ ] cada candidato tiene estado de revision y salida esperada;
- [ ] ninguna evidencia `pending_review` entro como `accepted_for_test`;
- [ ] `insufficient_evidence` no fue interpretada como `low_risk`;
- [ ] las exclusiones antes de scoring quedaron documentadas;
- [ ] la persona responsable acepta los limites interpretativos.

## Advertencia final

Esta checklist no sustituye revision experta ni validacion experimental. Solo
prepara una revision reproducible y auditable de datasets reales
`user_curated` antes de importacion o corrida controlada.
