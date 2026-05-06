# Acquisition Modes

## Manual

El usuario aporta los archivos al workspace del organismo.

Uso recomendado cuando:

- ya existe una curación previa
- se quiere control total sobre procedencia y contenidos

## Semi-auto

El sistema:

- crea el workspace
- genera plantillas
- genera manifest y report
- deja explícito qué falta

Uso recomendado cuando:

- se inicia un organismo nuevo
- se quiere una ruta reproducible sin fingir automatización inexistente

## Auto

Hoy es una arquitectura preparada, no una adquisición remota completa.

Comportamiento actual:

- se comporta como `semi_auto`
- si existe un demo local compatible y se activa `--allow-demo-data`, puede poblar
  el workspace con ese demo

## Política metodológica

`auto` no simula consultas a bases externas reales si no están implementadas.
La ausencia de conectores queda documentada en `discovery_report.md`.
