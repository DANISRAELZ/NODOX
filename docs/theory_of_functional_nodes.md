# Teoria de Nodos Funcionales y Robustez Evolutiva

## Proposito

Este documento define la base conceptual de una Fase 3 opcional para Nodos Funcionales. La Fase 3 no reemplaza la Fase 1 ni la Fase 2. Su objetivo es ampliar la interpretacion cientifica de los candidatos para preguntar no solo si un nodo parece importante, sino si intervenirlo podria restringir las rutas evolutivas viables del patogeno.

En esta fase documental no se modifica el pipeline ni se cambian resultados.

## Que es un nodo funcional

Un nodo funcional es una unidad biologica cuya perturbacion afecta de manera relevante la capacidad del patogeno para sobrevivir, causar enfermedad, adaptarse al nicho de infeccion o tolerar tratamiento. El nodo puede ser una proteina, gen, complejo, modulo funcional, ruta metabolica, regulador o proceso biologico integrado.

Un nodo funcional fuerte no se define solo por estar conectado en una red. Tambien debe evaluarse por:

- cuanto depende el patogeno de el;
- cuantas rutas alternativas existen;
- que costo tendria escapar por mutacion;
- si el escape deja nuevas vulnerabilidades;
- si la evidencia viene de datos reales, curados, controlados o proxy.

## functional_node_score vs functional_node_theory_score

`functional_node_score` es el score de Fase 2 ya implementado. Resume senales funcionales practicas como centralidad de red, cuello de botella, dependencia funcional, baja redundancia y confianza de evidencia.

`functional_node_theory_score` es el score integrador inicial de Fase 3 implementado en `src/nodos_funcionales/functional_node_theory.py`. El modulo es independiente y no reemplaza todavia rankings de Fase 1/Fase 2. Amplia `functional_node_score` con variables evolutivas, contextuales y de evidencia:

- esencialidad contextual;
- costo de escape;
- tolerancia mutacional;
- dificultad de compensacion;
- sensibilidad colateral;
- restriccion del espacio evolutivo.

La diferencia central es que `functional_node_score` pregunta "que tan funcionalmente importante parece este nodo ahora", mientras que `functional_node_theory_score` preguntaria "que tan dificil seria para el patogeno escapar de una intervencion contra este nodo sin perder aptitud".

Formula implementada:

```text
functional_node_theory_score =
  w_functional_node * functional_node_score
  + w_contextual_essentiality * contextual_essentiality_score
  + w_pleiotropy * pleiotropy_score
  + w_conservation * conservation_score
  + w_evolutionary_constraint * evolutionary_space_constraint_score
  + w_evidence_quality * evidence_quality_score
  - p_redundancy * redundancy_penalty
  - p_escape * evolutionary_escape_risk_score
  - p_biofilm * biofilm_escape_penalty
  - p_hgt * horizontal_transfer_penalty
  - p_host_similarity * host_similarity_penalty
```

El modulo tambien genera:

- `functional_node_theory_confidence`: confianza reportada limitada por `confidence_ceiling`;
- `functional_node_theory_label`: interpretacion cualitativa;
- `audit_flags`: penalizaciones aplicadas, faltantes, limite de confianza, alto riesgo evolutivo o alta redundancia.

## Tipos de nodos funcionales

### Hub

Nodo con muchas conexiones directas en una red funcional o fisica. Puede ser importante porque coordina multiples procesos, pero debe revisarse si esas conexiones son biologicamente relevantes para el nicho de infeccion.

### Bottleneck

Nodo que conecta modulos o rutas. Su bloqueo puede separar procesos que el patogeno necesita combinar, por ejemplo metabolismo central y respuesta a estres.

### Regulador global

Regulador transcripcional, postranscripcional o de senalizacion que controla muchos genes o estados fisiologicos. Puede ser terapeuticamente atractivo si su perturbacion reduce adaptacion, virulencia o tolerancia.

### Nodo metabolico

Enzima, transportador o paso metabolico. Es fuerte cuando controla un flujo esencial, tiene pocas rutas alternativas y su perdida impone alto costo de crecimiento o supervivencia.

### Nodo de virulencia

Factor o regulador que contribuye al dano, invasion, evasion inmune, secrecion, adhesion o toxicidad. Puede ser candidato antivirulencia si reduce enfermedad sin requerir necesariamente letalidad directa.

En Fase 3, la virulencia se separa en subcapas para evitar mezclar mecanismos biologicos distintos:

- dano directo al hospedero: toxinas, proteasas, hemolisinas o enzimas de dano tisular;
- colonizacion: adhesinas, pili, fimbriae, proteinas de superficie o invasion inicial;
- evasion inmune: capsula, resistencia a complemento, antigenicidad o evasion de fagocitosis;
- persistencia y biofilm: matriz, alginato, quorum sensing, adhesion persistente o tolerancia comunitaria;
- escape a inmunidad nutricional: sideroforos, captacion de hierro o uso de hemo;
- regulacion de quorum sensing: reguladores `las`, `rhl`, `pqs`, `lux`, `agr` o equivalentes.

La implementacion inicial esta en `src/nodos_funcionales/virulence_layers.py`. Produce sub-scores trazables y un `virulence_severity_score`, pero no elimina ni reemplaza `antivirulence_target_score`.

### Nodo de biofilm

Componente que sostiene matriz, adhesion, comunicacion, tolerancia o arquitectura del biofilm. Puede ser prioritario para hacer al patogeno mas vulnerable a antibioticos convencionales.

### Nodo de respuesta al estres

Sistema que permite tolerar estres oxidativo, dano de ADN, estres de membrana, limitacion nutricional, presion inmune o antibioticos. Puede ser un sensibilizador si su inhibicion aumenta la eficacia de otros tratamientos.

## Criterios de un nodo terapeutico fuerte

Un nodo terapeutico fuerte en Fase 3 deberia combinar:

- centralidad: participa en procesos conectados o coordinadores;
- esencialidad: su perdida reduce supervivencia o crecimiento;
- conservacion: esta presente en cepas relevantes o linajes clinicos;
- baja redundancia: no hay alternativas equivalentes faciles;
- pleiotropia: afecta multiples fenotipos importantes;
- esencialidad contextual: importa en el sitio o estado de infeccion;
- bajo riesgo de escape evolutivo: pocas mutaciones viables generan resistencia;
- alto costo de escape: escapar reduce fitness, virulencia o transmision;
- sensibilidad colateral favorable: el escape aumenta vulnerabilidad a otro tratamiento;
- evidencia de calidad: datos experimentales, curados o externos trazables pesan mas que proxies.

## Relacion con fases existentes

La Fase 1 conserva un baseline simple e interpretable.

La Fase 2 separa estrategias terapeuticas, procedencia, confianza, contexto de hospedero, red funcional y reportes.

La Fase 3 propuesta se apoyaria sobre esas salidas, pero agregaria una capa conceptual de robustez evolutiva. No debe implementarse hasta que existan reglas transparentes, columnas documentadas y tests que garanticen compatibilidad.

## Limitaciones actuales

- `functional_node_theory_score` existe como modulo independiente, pero aun no modifica el ranking principal.
- No hay medicion directa de tasa de escape evolutivo.
- Muchas senales necesarias pueden requerir curacion manual o evidencia externa.
- La centralidad no debe confundirse con robustez terapeutica.

## Paso futuro sugerido

Antes de implementar scoring Fase 3, conviene crear plantillas o columnas opcionales para evidencia evolutiva, manteniendo valores faltantes explicitos y sin alterar rankings actuales.
