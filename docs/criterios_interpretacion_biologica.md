# Criterios de interpretacion biologica

Este documento explica como leer los candidatos generados por Nodos
Funcionales. El ranking debe interpretarse como una priorizacion computacional
exploratoria, no como confirmacion definitiva de eficacia terapeutica.

## Preguntas biologicas principales

### El gen o la proteina es esencial?

Una senal de esencialidad alta favorece candidatos para una estrategia
antibacteriana clasica. Sin embargo, la esencialidad depende del organismo, la
cepa, el medio, el estado fisiologico y el modelo experimental. Una ausencia de
evidencia de esencialidad no debe leerse automaticamente como no esencialidad.

### Tiene homologo humano?

La presencia de homologos humanos aumenta el riesgo de efectos fuera de blanco.
El pipeline penaliza perfiles con mayor similitud al hospedero, pero esta
lectura no sustituye estudios estructurales, toxicologicos ni de selectividad.

### Esta conservado entre cepas?

Un blanco conservado puede ser mas atractivo si se busca cobertura amplia entre
aislamientos. La conservacion baja puede indicar especificidad de cepa, perdida
funcional, variabilidad biologica o simplemente datos incompletos.

### Esta asociado a virulencia?

Una senal de virulencia alta puede favorecer estrategias antivirulencia. En
estos casos, el objetivo no siempre es matar la bacteria, sino reducir dano al
hospedero, colonizacion, evasion inmune, secrecion de factores o persistencia.

### Donde esta localizado?

La localizacion ayuda a estimar accesibilidad:

- membrana externa, pared celular, periplasma o secretoma suelen ser mas
  accesibles a intervenciones extracelulares o periplasmicas.
- citoplasma puede requerir penetracion celular y concentraciones intracelulares
  suficientes.
- localizacion desconocida reduce la confianza interpretativa.

### Es accesible al antibiotico o intervencion?

La accesibilidad es una hipotesis derivada, no una medicion farmacocinetica. Un
score favorable debe revisarse con permeabilidad, eflujo, estabilidad,
concentracion en sitio de infeccion y forma molecular de la intervencion.

### Participa en una red funcional central?

Un nodo funcional central puede tener impacto sistemico en rutas bacterianas.
Tambien puede ser biologicamente redundante o dificil de modular sin efectos
compensatorios. La centralidad de red debe interpretarse junto con dependencia
funcional y redundancia.

### Hay evidencia experimental directa?

La evidencia experimental directa tiene mayor peso interpretativo que proxies,
datos demo o inferencias. Siempre revisar si la fila proviene de datos reales de
usuario, fuente externa, cache, proxy, demo o calculo indirecto.

## Procedencia de evidencia

- datos reales de usuario: deben considerarse la fuente preferida si fueron
  curados correctamente.
- fuente externa: puede aportar evidencia reproducible, pero requiere revisar
  fecha, cobertura, organismo y metodo.
- cache: reproduce una consulta previa; conviene refrescar cuando se necesite
  evidencia actual.
- proxy o calculo indirecto: util para completar el pipeline, pero no confirma
  biologia.
- demo: sirve para probar el flujo; no debe usarse para conclusiones biologicas
  finales.

## Rol terapeutico sugerido

- `bactericidal_candidate`: perfil compatible con blanco antibacteriano clasico,
  usualmente por esencialidad, seguridad frente al hospedero y accesibilidad.
- `antivirulence_candidate`: perfil compatible con reducir dano, colonizacion o
  virulencia sin necesariamente matar la bacteria.
- `sensitizer_candidate`: nodo que podria potenciar tratamientos o exponer
  vulnerabilidades.
- `mixed_strategy_candidate`: senales relevantes en mas de una estrategia.
- `low_priority_candidate`: evidencia insuficiente, bajo acceso, riesgo al
  hospedero o prioridad terapeutica baja bajo las reglas actuales.

## Advertencia final

El score final no confirma eficacia terapeutica. Es una herramienta para ordenar
hipotesis, detectar faltantes de evidencia y priorizar curacion o experimentos.
Todo candidato requiere validacion experimental y revision bibliografica antes
de cualquier conclusion biologica fuerte.
