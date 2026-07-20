# Revisión final de madurez

Fechas de revisión: 2026-04-26 y 2026-05-15.

Esta nota resume el cierre documental realizado para fortalecer NODOX como herramienta de priorización computacional exploratoria. No modifica fórmulas, pesos ni el contrato público del pipeline.

## Cierre multi-organismo

Se verificó que:

- NODOX se documenta como plataforma multi-organismo;
- los organismos usados en demos y snapshots no definen el alcance del sistema;
- la Teoría de Nodos Funcionales permanece como eje conceptual;
- la capa evolutiva conserva variables explícitas de restricción, tolerancia, redundancia, movilidad, recombinación y asociación con resistencia;
- los datos demo, proxy, cache, controlados, online y `user_curated` se mantienen diferenciados;
- los scores se presentan como priorización exploratoria y no como validación terapéutica.

## Componentes revisados

La revisión incluyó:

- metodología, scoring y modelo de datos;
- explicaciones orientadas al usuario;
- auditoría de procedencia por capa;
- reportes de fuerza de evidencia;
- guías de ejecución en Windows, Linux y WSL;
- marcos de validación biológica;
- plantillas de datos;
- scripts de prueba, demostración y limpieza;
- contratos de snapshots y workspaces.

## Evidencia fuerte y débil

Los reportes clasifican el soporte como `strong`, `moderate`, `weak` o `insufficient` sin modificar el ranking. La ausencia de evidencia no se interpreta como evidencia biológica negativa.

## Validación técnica histórica

Las pruebas principales de validación, integración, scoring, auditoría de fuentes, plantillas multi-organismo, fuerza de evidencia y scripts de plataforma terminaron correctamente en el cierre original.

Los comandos públicos deben usar el intérprete activo del entorno:

```bash
python -m pytest -p no:cacheprovider -m "not online" -q
```

Para el demo controlado:

```bash
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
```

Para un dry-run de otro organismo:

```bash
python run_pipeline.py --organism "Corynebacterium pseudotuberculosis" --acquisition-mode semi_auto --workspace data_sessions/corynebacterium_pseudotuberculosis_demo --dry-run --offline-only
```

## Resultado operativo

Una ejecución histórica encontró un archivo de salida bloqueado por el entorno local. La misma corrida, usando un workspace nuevo y escribible, terminó correctamente. Esto se interpretó como un problema de permisos o sincronización del sistema de archivos, no como un cambio del modelo científico.

## Límites

- Las salidas no constituyen validación clínica ni experimental.
- Los ejemplos no son catálogos biológicos completos.
- Los snapshots controlados no sustituyen evidencia específica del usuario.
- Las fuentes online deben registrar fallos, cache y fallback.
- Los datos privados, clínicos, propietarios o no redistribuibles no deben versionarse.

## Estado

El cierre documental confirmó compatibilidad entre fases, explicabilidad, separación de procedencia, arquitectura multi-organismo y conservación del comportamiento previo. La publicación pública requiere además los controles definidos en `docs/public_release_checklist.md`.
