# Redundancia y Compensacion

## Proposito

Este documento define como interpretar redundancia funcional y compensacion evolutiva en Fase 3. Un nodo puede ser central y aun asi ser mal blanco terapeutico si el patogeno tiene rutas alternativas para mantener la funcion.

La implementacion inicial vive en `src/nodos_funcionales/redundancy_analysis.py`. Es un modulo independiente: puede calcular columnas de redundancia sobre un `DataFrame`, pero no cambia todavia el ranking principal del pipeline.

## Redundancia funcional

La redundancia funcional ocurre cuando dos o mas genes, proteinas o rutas pueden cumplir funciones similares. Si una intervencion bloquea una ruta, otra puede sostener el fenotipo necesario.

La redundancia puede aparecer como:

- genes paralogos;
- enzimas alternativas;
- transportadores con solapamiento;
- rutas metabolicas de bypass;
- reguladores con funciones compartidas;
- plasticidad fisiologica entre estados bacterianos.

## Paralogos

Los paralogos son genes relacionados por duplicacion dentro del mismo organismo. Si un paralogo puede compensar la perdida del otro, el nodo individual tiene menor valor terapeutico. En cambio, si el paralogo no se expresa en el nicho de infeccion o no cubre la misma funcion, la penalizacion deberia ser menor.

## Bypass metabolico

Un bypass metabolico permite que el flujo biologico continue por una ruta alternativa. Esto puede volver menos efectivo un blanco que parece esencial en una red simple.

Ejemplo conceptual:

```text
Ruta A bloqueada -> metabolito aun se produce por Ruta B -> bajo efecto terapeutico
```

El bypass es especialmente importante en metabolismo central, adquisicion de nutrientes y adaptacion a nichos.

## Compensacion evolutiva

La compensacion evolutiva ocurre cuando una mutacion inicial reduce fitness, pero mutaciones posteriores restauran parte de la aptitud. Esto puede permitir resistencia sostenida aunque el escape inicial sea costoso.

Un nodo robusto deberia tener baja probabilidad de compensacion o compensaciones que generen nuevas vulnerabilidades.

## Por que penalizar un nodo central pero redundante

La centralidad indica conectividad o posicion en una red, no necesariamente vulnerabilidad terapeutica. Un nodo central pero redundante puede producir un score funcional alto, pero permitir escape por rutas alternativas.

Por eso una Fase 3 deberia penalizar:

- alta redundancia;
- paralogia compensatoria;
- bypass metabolico facil;
- baja dificultad de compensacion;
- evidencia de variantes viables que evaden el nodo.

## Relacion con Fase 2

Fase 2 ya incluye `redundancy_penalty` y `low_redundancy_score`. Estas variables son una base util, pero todavia no capturan toda la compensacion evolutiva.

Fase 3 deberia separar:

- redundancia estructural: hay genes o rutas parecidas;
- redundancia funcional: esas rutas realmente sostienen el fenotipo;
- redundancia contextual: esas rutas funcionan en el nicho de infeccion;
- redundancia evolutiva: pueden activarse o seleccionarse durante tratamiento.

## Implementacion actual

La funcion principal es:

```python
compute_redundancy_features(df, params) -> df
```

Recibe una tabla de nodos y devuelve una copia con campos de Fase 3:

- `paralog_count`: numero de genes paralogos conocidos o inferidos.
- `pathway_alternative_count`: numero de rutas alternativas que podrian sostener la funcion.
- `functional_backup_score`: estimacion normalizada de respaldo funcional, entre 0 y 1.
- `metabolic_bypass_score`: evidencia normalizada de bypass metabolico, entre 0 y 1.
- `regulatory_bypass_score`: evidencia normalizada de bypass regulatorio, entre 0 y 1.
- `redundancy_penalty`: penalizacion final normalizada, entre 0 y 1.

La regla inicial combina tres senales principales:

```text
redundancy_penalty =
  paralog_signal * paralog_weight
  + pathway_alternative_signal * pathway_alternative_weight
  + functional_backup_score * functional_backup_weight
```

Luego se aplica un ajuste protector pequeno cuando el nodo parece unico, conservado, esencial y con bajo respaldo funcional. Ese ajuste evita castigar en exceso a nodos con poca evidencia de redundancia.

## Configuracion

Los pesos se configuran en `config/params.yaml`:

```yaml
phase3:
  redundancy:
    missing_data_default: 0.3
    paralog_weight: 0.35
    pathway_alternative_weight: 0.35
    functional_backup_weight: 0.30
```

Tambien existen parametros auxiliares para normalizar conteos y combinar bypass metabolico/regulatorio:

- `max_paralog_count`
- `max_pathway_alternative_count`
- `metabolic_bypass_weight`
- `regulatory_bypass_weight`
- `protective_adjustment_weight`

## Datos faltantes y auditoria

Si faltan columnas de redundancia, el modulo no falla. Usa `missing_data_default` como valor conservador y agrega una marca en `audit_flags`:

```text
redundancy_data_missing=...
```

Esto significa: no hay evidencia suficiente para afirmar baja o alta redundancia. El valor por defecto no debe interpretarse como evidencia experimental.

Si todas las columnas esperadas estan presentes, agrega:

```text
redundancy_data_complete
```

## Variables conceptuales futuras

Posibles columnas:

- `paralog_compensation_score`
- `metabolic_bypass_score`
- `functional_redundancy_score`
- `compensation_difficulty_score`
- `redundancy_evidence_type`
- `redundancy_evidence_reference`

## Limitaciones

- No toda paralogia implica compensacion real.
- No todo bypass teorico funciona en el hospedero.
- La ausencia de rutas anotadas no prueba ausencia de compensacion.
- La compensacion puede depender del nicho y del tratamiento combinado.
- La implementacion actual es heuristica y no reemplaza evidencia experimental.
- `redundancy_penalty` se calcula de forma independiente y aun no modifica el ranking principal.

## Paso futuro sugerido

El siguiente paso natural es conectar fuentes reales o curadas de paralogia y rutas alternativas detras de la arquitectura de resolucion por capa. Despues, una auditoria deberia distinguir datos observados, anotacion de red, inferencia metabolica y proxies antes de permitir que `redundancy_penalty` afecte scores finales.
