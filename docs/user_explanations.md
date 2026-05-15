# User Explanations

## Objetivo

Las explicaciones para usuarios no tecnicos deben traducir el ranking a una
hipotesis biologica prudente. No deben afirmar validacion experimental ni
prometer disponibilidad terapeutica. Tampoco deben presentarse como
recomendacion terapeutica ni sustituir evaluacion medica, microbiologica o
farmacologica.

Cada candidato debe explicar:

1. por que parece nodo funcional;
2. que tipo(s) de nodo funcional representa;
3. que capas apoyan su prioridad;
4. que evidencia existe;
5. que evidencia falta;
6. que confianza tiene;
7. que riesgo evolutivo presenta;
8. que tan restringido parece el escape;
9. que limitaciones aplican;
10. si usa datos reales, snapshot, online, proxy, demo o faltantes.

Las explicaciones simples tambien exponen:

- `therapeutic_priority_components`: resumen de las contribuciones numericas
  que componen `therapeutic_priority_score`;
- `theory_context`: lectura compacta de nodos funcionales, selectividad,
  contexto clinico, robustez evolutiva y modificador de confianza;
- `provenance_context`: procedencia, modo de recuperacion, cache y versionado
  cuando estan disponibles.

## Advertencia fija

El ranking representa hipotesis terapeuticas priorizadas. No es recomendacion
clinica ni validacion experimental. Requiere validacion experimental y clinica
externa antes de cualquier aplicacion.
