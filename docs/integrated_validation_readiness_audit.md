# Auditoría de preparación de la validación integrada

Este documento define la auditoría que debe ejecutarse antes de modificar la Teoría de Nodos Funcionales, el riesgo de escape evolutivo o el ranking principal.

## Baseline esperado

- Rama: `main`.
- Commit de referencia al preparar Stage 1: `b7b86769d5cf9a69d01959cab328332d1f0aff84`.
- El auditor debe registrar el SHA efectivo; una diferencia no es un error por sí misma, pero debe quedar documentada.
- El árbol inicial debe estar limpio antes de aplicar el parche.

## Preguntas que debe responder

1. ¿Qué corridas existen y cuáles contienen manifiestos, rankings y auditorías completas?
2. ¿Cuál es la corrida reproducible principal de *Helicobacter pylori*?
3. ¿Qué proveedores fueron intentados, respondieron, mapearon candidatos, produjeron evidencia utilizable y afectaron scoring?
4. ¿Qué fuentes son online reales, snapshots, curadas, cache, proxy, fixtures, demo o no resueltas?
5. ¿Qué postulados están operacionalizados y cuáles sólo están documentados o parcialmente cubiertos?
6. ¿Qué variables de escape evolutivo son explícitas y cuáles se derivan de proxies?
7. ¿Qué afirmaciones pueden sostenerse en el manuscrito?
8. ¿Qué afirmaciones continúan sin respaldo?

## Interpretación

El auditor inspecciona código, configuraciones, manifiestos y encabezados de tablas. No recalcula resultados biológicos ni valida experimentalmente la teoría. Sus conclusiones describen disponibilidad, trazabilidad y cobertura, no eficacia terapéutica.
