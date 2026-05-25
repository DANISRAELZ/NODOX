# User-curated Interpretation Phase Closure

## Alcance

Este documento cierra formalmente la fase de interpretacion
`user_curated`/reporting/`evidence_quality`/`evidence_strength`. La fase se
limito a estabilizar como se explican procedencia, confianza, evidencia
insuficiente y limites de uso en documentacion, reportes, exportaciones y
explicaciones para usuarios.

No se agregaron nuevos scores, no se cambio `scoring.py`, no se modifico la
logica cientifica central y no se crearon nuevas capacidades funcionales.

## Cambios consolidados

- `manual_curation -> evidence_quality` queda documentado y probado como una
  transformacion conservadora de procedencia y nivel de evidencia.
- `pending_review` conserva un techo bajo de confianza y no eleva confianza por
  si mismo.
- `local_note`, `curator_notes` e `include_for_structure_check` preservan
  trazabilidad, pero no equivalen a DOI, literatura verificada ni validacion
  experimental.
- `evidence_strength`, `evidence_quality` y la etiqueta `strong` son lecturas
  interpretativas de soporte relativo; no son evidencia externa verificada
  automaticamente ni validacion experimental.
- Los reportes y exportaciones incluyen notas de alcance interpretativo para
  evitar confundir fuerza de evidencia, calidad de evidencia, procedencia y
  prioridad terapeutica.

## Limites interpretativos fijados

- `therapeutic_priority_score` y `evidence_confidence_score` se leen por
  separado: prioridad terapeutica dentro del modelo frente a soporte trazable de
  evidencia.
- `user_curated` significa informacion aportada o revisada por el usuario; no
  equivale automaticamente a evidencia externa verificada.
- Ausencia, insuficiencia, proxy o evidencia incompleta no equivalen a bajo
  riesgo ni a evidencia negativa.
- Nodos Funcionales es una plataforma de priorizacion terapeutica, no un
  predictor clinico definitivo, herramienta clinica ni recomendacion
  terapeutica.
- La subcapa evolutiva modula la interpretacion de robustez y escape, pero no
  reemplaza funcionalidad, selectividad, accesibilidad ni evidencia trazable.
- Se mantiene la separacion entre `user_curated`, `controlled_reference`,
  `demo`, `proxy`, `cache` y `online`.

## Validaciones ejecutadas

Durante el cierre de esta fase se ejecutaron pruebas especificas de:

- `user_explanations`;
- exportacion y reportes;
- `evidence_strength`;
- `evidence_quality`;
- transformacion/importacion interpretativa de `manual_curation -> evidence_quality`;
- guardas de interpretacion `user_curated`.

Tambien se ejecuto la suite offline estable:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -m "not online" -q
```

Las validaciones pasaron al 100%.

## Estado final esperado

Despues del commit y tag de cierre:

- `git diff --name-only` no debe mostrar cambios no versionados;
- `git status --short` debe quedar limpio;
- `config/taxon_resolution_cache.json` debe revertirse si solo cambia por
  `updated_at_utc`, `saved_at_utc` o `refresh_count` durante pruebas;
- no deben quedar cambios en snapshots, `results/`, `data_processed/` ni
  `data_sessions/`.

## Siguiente fase sugerida

La siguiente fase logica es preparar una validacion con datasets
`user_curated` reales o, en una rama/protocolo separado, una evaluacion externa
controlada. Esa fase deberia mantener la arquitectura de capas existente,
preservar procedencia por fuente y evitar convertir datos de usuario, cache,
demo, proxy u online en evidencia experimental sin revision explicita.
