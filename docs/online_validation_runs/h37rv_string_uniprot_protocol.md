# Protocolo futuro H37Rv STRING/UniProt

## Objetivo

Este documento define un protocolo futuro para validar, de forma controlada, una
corrida `online_optional` con STRING y UniProt para `Mycobacterium tuberculosis`
H37Rv.

El objetivo no es convertir H37Rv en organismo central del proyecto. H37Rv se
usa como caso multiorganismo controlado para probar que Nodos Funcionales puede
separar evidencia externa real, evidencia controlada, cache, proxy, demo y datos
del usuario sin cambiar la Teoria de Nodos Funcionales ni los contratos de
salida.

## Estado actual

Existe un snapshot controlado en:

```text
data_external/curated_snapshots/mycobacterium_tuberculosis_h37rv/
```

Ese snapshot es `controlled_reference_snapshot`. No es evidencia online fresca,
no es dato demo, no es proxy y no depende de cache mutable. Sus anotaciones son
entradas controladas para validar estructura y procedencia.

La ausencia de genes, capas o variables en ese snapshot no equivale a ausencia
biologica, bajo riesgo ni irrelevancia terapeutica.

## Fuentes previstas

Fuentes a evaluar en una corrida futura:

- STRING: red funcional e identificadores de red.
- UniProt: contexto de identificadores, anotacion y localizacion cuando aplique.

Las fuentes deben registrarse como evidencia externa real solo si la corrida
futura efectivamente consulta el proveedor, conserva manifiestos, declara estado
de recuperacion y deja trazabilidad suficiente para auditoria.

## Workspace recomendado

Usar un workspace separado y no versionado, por ejemplo:

```text
data_sessions/h37rv_string_uniprot_online_validation/
```

Ese workspace debe permanecer fuera de Git. No se deben versionar sus outputs,
caches locales, reportes generados ni tablas intermedias.

## Criterios para una corrida online_optional futura

Antes de ejecutar cualquier consulta online:

1. Confirmar que `git status --short` esta limpio o que solo hay cambios
   documentales intencionales.
2. Crear o reutilizar un workspace separado para H37Rv.
3. Confirmar que el snapshot controlado actual no sera modificado.
4. Definir si la corrida usara `online_optional` fresco, cache controlado o una
   comparacion fresh/cache.
5. Registrar el comando exacto antes de ejecutarlo.
6. Confirmar que STRING y UniProt quedan separados en manifiestos, historiales y
   reportes.

La corrida futura debe poder distinguir al menos estos escenarios:

- `baseline_no_online`
- `string_only_fresh`
- `uniprot_only_fresh`
- `combined_online_fresh`
- `string_only_cache`
- `uniprot_only_cache`
- `combined_online_cache`

## Archivos que no deben versionarse

No versionar:

- `data_sessions/h37rv_string_uniprot_online_validation/`
- `results/` generados por la corrida
- `data_processed/` generado
- caches volatiles de proveedores
- manifiestos generados dentro del workspace
- rankings o auditorias generados por la corrida online

Solo debe versionarse un resumen documental revisado, como este archivo o un
cierre futuro dentro de `docs/online_validation_runs/`.

## Comparacion contra snapshot controlado

La comparacion esperada debe separar:

- snapshot controlado H37Rv: referencia offline, limitada y auditable;
- STRING fresh/cache: evidencia externa real o cacheada, si se ejecuta;
- UniProt fresh/cache: evidencia externa real o cacheada, si se ejecuta;
- datos del usuario: evidencia curada cargada explicitamente por el usuario;
- demo/proxy/controlado: soporte exploratorio o de contrato, nunca evidencia
  externa real.

La validacion debe responder:

1. Que cambia al incorporar STRING?
2. Que cambia al incorporar UniProt?
3. Que cambia al combinar STRING y UniProt?
4. Fresh y cache reproducen el mismo efecto?
5. Los cambios son de ranking, scores, features o solo procedencia?
6. La evidencia externa real contradice, complementa o no afecta el snapshot
   controlado?

## Reglas de interpretacion

- Un resultado online fresco no se convierte automaticamente en snapshot curado.
- Cache reproduce una corrida previa, pero no equivale a evidencia nueva.
- Demo, proxy y proveedor controlado no sustituyen evidencia externa real ni
  datos del usuario.
- Ausencia de respuesta de proveedor, ausencia de mapping o ausencia de una capa
  no equivale a ausencia biologica.
- Ausencia o insuficiencia de evidencia no equivale a bajo riesgo ni
  irrelevancia terapeutica.
- Evidencia negativa real solo debe declararse cuando una fuente trazable busco
  explicitamente una senal y el metodo permite interpretar una no deteccion
  acotada.
- Cualquier lectura terapeutica sigue siendo hipotesis computacional y requiere
  validacion experimental externa.

## Criterios de cierre

La validacion futura puede cerrarse cuando exista:

- workspace separado documentado;
- comandos exactos registrados;
- manifiestos por fuente;
- comparacion fresh/cache si aplica;
- reporte de impacto por ranking, scores, features y procedencia;
- separacion explicita entre evidencia externa real, snapshot controlado, cache,
  proxy, demo y datos de usuario;
- pruebas offline `not online` pasando al 100% despues de la documentacion;
- `git status --short` limpio despues de restaurar cualquier cache mutable.

Si alguno de esos puntos falta, la corrida debe quedar como auditoria pendiente,
no como validacion cerrada ni como snapshot curado.
