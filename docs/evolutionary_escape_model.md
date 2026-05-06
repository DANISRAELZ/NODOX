# Modelo de Escape Evolutivo

## Proposito

Este documento define conceptos para evaluar si un patogeno podria escapar de una intervencion terapeutica contra un nodo funcional. La idea central es que una mutacion posible no siempre produce resistencia exitosa. Para ser exitosa, la variante debe sobrevivir, competir, mantener virulencia suficiente y sostenerse en el nicho de infeccion.

Este documento es conceptual. No modifica el pipeline.

## Espacio evolutivo

El espacio evolutivo es el conjunto de estados geneticos y fenotipicos que una poblacion bacteriana puede explorar por mutacion, recombinacion, perdida de genes, ganancia de genes, cambios regulatorios o compensacion metabolica.

Un tratamiento robusto intenta reducir ese espacio. Un nodo terapeutico ideal deja al patogeno con pocas rutas viables de escape o con rutas que tienen alto costo biologico.

## Tasa elevada de mutacion

Una tasa elevada de mutacion puede aumentar la probabilidad de generar variantes resistentes. Esto es especialmente relevante en infecciones cronicas, biofilm, poblaciones grandes, exposicion prolongada a antibioticos o ambientes de estres.

Sin embargo, mas mutaciones no significan automaticamente mas resistencia clinicamente exitosa. Muchas mutaciones:

- rompen funciones esenciales;
- reducen fitness;
- disminuyen virulencia;
- generan dependencia de condiciones especificas;
- aumentan sensibilidad a otros tratamientos.

## Mutacion posible vs resistencia exitosa

Una mutacion posible es cualquier cambio genetico que puede ocurrir.

Una resistencia evolutivamente exitosa requiere que ese cambio:

- reduzca el efecto terapeutico;
- conserve viabilidad;
- mantenga aptitud en el nicho de infeccion;
- no imponga un costo demasiado alto;
- pueda expandirse dentro de la poblacion;
- no genere una sensibilidad colateral explotable.

Por eso la Fase 3 debe distinguir tolerancia mutacional de escape viable.

## Variables conceptuales

### mutational_tolerance_score

Mide que tan tolerante es el nodo a cambios sin perder funcion. Un valor alto indicaria que muchas mutaciones pueden ocurrir sin destruir la aptitud del patogeno. Esto aumenta riesgo de escape.

Fuentes futuras posibles:

- conservacion de residuos;
- dominios funcionales;
- datos de mutagenesis;
- variacion natural en aislamientos;
- tolerancia observada en familias homologas.

### redundancy_penalty

Ya existe como concepto de Fase 2. En Fase 3 seguiria penalizando nodos con rutas alternativas o funciones compensables. Un nodo con alta redundancia puede parecer central, pero ser terapeuticamente debil si el patogeno puede activar un bypass.

### fitness_cost_score

Representa el costo para el patogeno de escapar al tratamiento. Alto `fitness_cost_score` es favorable: significa que una ruta de escape probablemente reduce crecimiento, supervivencia, virulencia o transmision.

### compensation_difficulty_score

Mide que tan dificil seria compensar la perdida o inhibicion del nodo. Un valor alto indica pocas rutas alternativas, poca plasticidad y alto acoplamiento funcional.

### evolutionary_escape_risk_score

Score conceptual de riesgo. Seria alto cuando el nodo tiene:

- alta tolerancia mutacional;
- baja dificultad de compensacion;
- bajo costo de fitness;
- alta redundancia;
- evidencia de variantes resistentes viables.

### evolutionary_space_constraint_score

Score conceptual favorable. Seria alto cuando intervenir el nodo restringe el espacio evolutivo viable del patogeno. Puede entenderse como la contraparte terapeutica del riesgo de escape:

```text
evolutionary_space_constraint_score aumenta cuando:
- mutational_tolerance_score es bajo
- redundancy_penalty es bajo
- fitness_cost_score es alto
- compensation_difficulty_score es alto
- evidencia de sensibilidad colateral es favorable
```

## Relacion conceptual entre variables

Formula conceptual, no implementada:

```text
evolutionary_escape_risk_score =
  + mutational_tolerance_score
  + redundancy_penalty
  - fitness_cost_score
  - compensation_difficulty_score
  - collateral_sensitivity_potential
```

```text
evolutionary_space_constraint_score =
  1 - evolutionary_escape_risk_score
```

En una implementacion real, los pesos deberian ser configurables, trazables y auditables.

## Limitaciones

- No debe inferirse escape evolutivo sin evidencia.
- La ausencia de mutaciones conocidas no prueba bajo riesgo.
- El modelo debe separar datos experimentales, literatura curada, proxies y desconocidos.
- Diferentes nichos de infeccion pueden cambiar el costo de escape.

## Paso futuro sugerido

Crear una plantilla opcional para evidencia evolutiva con columnas como `mutational_tolerance_score`, `fitness_cost_score`, `compensation_difficulty_score`, `collateral_sensitivity_potential` y referencias trazables.
## Unknown vs Low Risk

Fase 3 distingue riesgo de escape desconocido de riesgo bajo.

- `unknown_missing_evidence`: no hay variables explicitas suficientes; no debe
  interpretarse como bajo riesgo.
- riesgo bajo: existe evidencia real de baja redundancia, alto costo de escape
  o restriccion evolutiva.
- riesgo moderado: hay senales parciales de redundancia, tolerancia o
  compensacion.
- riesgo alto: hay paralogos, rutas alternativas, mecanismos compensatorios o
  mutaciones de escape conocidas.

El score `evolutionary_escape_risk_score` se separa de la calidad de evidencia.
Un riesgo alto basado solo en proxy se penaliza menos que un riesgo alto con
literatura, curacion o base externa real.

La plantilla actualizada es `data_templates/evolutionary_escape_template.csv`.
