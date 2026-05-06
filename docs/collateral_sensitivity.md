# Sensibilidad Colateral

## Proposito

Este documento describe como la sensibilidad colateral se incorpora como capa independiente de Fase 3. La sensibilidad colateral ocurre cuando una adaptacion que protege frente a un tratamiento vuelve al patogeno mas vulnerable a otro.

La implementacion inicial vive en `src/nodos_funcionales/collateral_sensitivity.py`. Es explicable y basada en reglas. No cambia todavia el ranking principal del pipeline.

## Que es sensibilidad colateral

La sensibilidad colateral es una relacion evolutiva entre tratamientos. Una mutacion o estado adaptativo que confiere resistencia a una presion puede aumentar sensibilidad a otra presion.

En teoria de nodos funcionales, esto es importante porque un nodo no solo debe bloquear una funcion actual; tambien puede dirigir el escape del patogeno hacia un estado mas vulnerable.

## Escape que crea vulnerabilidad

Un escape terapeutico puede ser aceptable o incluso explotable si:

- reduce virulencia;
- impone alto costo de crecimiento;
- aumenta permeabilidad;
- debilita biofilm;
- reduce reparacion de dano;
- aumenta sensibilidad a antibioticos existentes;
- limita el nicho donde el patogeno puede sobrevivir.

Por eso Fase 3 deberia distinguir resistencia simple de escape evolutivamente comprometido.

## Diseno de combinaciones terapeuticas

### Nodo metabolico + antibiotico bactericida

Inhibir un nodo metabolico puede reducir energia, precursores o homeostasis. Combinado con un bactericida, puede disminuir la capacidad de reparar dano o sostener crecimiento bajo presion.

Lectura esperada:

- alto costo de escape;
- baja redundancia metabolica;
- posible aumento de sensibilidad a dano celular.

### Nodo de estres + quinolona o aminoglucosido

Quinolonas y aminoglucosidos pueden generar dano que requiere respuestas de reparacion, proteostasis o defensa frente a estres oxidativo. Un nodo de estres puede actuar como sensibilizador.

Lectura esperada:

- menor tolerancia a dano;
- menor supervivencia de subpoblaciones persistentes;
- mayor costo para mutantes resistentes.

### Nodo de biofilm + beta-lactamico

El biofilm reduce penetracion y cambia fisiologia. Un nodo de biofilm puede aumentar exposicion o devolver bacterias a estados mas sensibles a beta-lactamicos.

Lectura esperada:

- menor matriz o adhesion;
- mayor accesibilidad;
- menor tolerancia comunitaria.

### Nodo de virulencia + antibiotico convencional

Un nodo de virulencia puede reducir dano o evasion inmune. Combinado con antibioticos convencionales, puede bajar carga patologica y facilitar control por hospedero.

Lectura esperada:

- menor dano al hospedero;
- menor presion bactericida directa si se busca antivirulencia;
- posible menor seleccion de resistencia clasica.

### Nodo de reparacion de DNA + quinolona

Un nodo de reparacion de DNA puede sostener supervivencia frente a dano genomico. Si se perturba, podria aumentar vulnerabilidad frente a quinolonas u otros tratamientos que generen dano en DNA.

Lectura esperada:

- menor capacidad de reparar dano genomico;
- mayor costo de escape;
- posible reduccion de rutas viables de resistencia.

## Implementacion actual

La funcion principal es:

```python
compute_collateral_sensitivity_features(df, params) -> df
```

Devuelve una copia de la tabla con:

- `collateral_sensitivity_score`: score normalizado de oportunidad por sensibilidad colateral.
- `combination_opportunity_score`: oportunidad combinatoria integrando regla, contexto y calidad de evidencia si existe.
- `recommended_combination_class`: clase de combinacion sugerida por regla.
- `escape_creates_vulnerability`: indica si se encontro una vulnerabilidad secundaria plausible.
- `combination_rationale`: justificacion textual breve.

## Reglas implementadas

La implementacion inicial no afirma evidencia experimental especifica. Solo propone hipotesis mecanisticas:

- nodo de estres oxidativo -> `oxidative_damage_adjuvant`;
- nodo de biofilm -> `antibiofilm_or_beta_lactam_combination`;
- nodo de metabolismo energetico -> `metabolism_dependent_bactericidal_combination`;
- nodo de captacion de hierro -> `nutritional_immunity_or_siderophore_strategy`;
- nodo de virulencia -> `conventional_antibiotic_or_immune_therapy`;
- nodo de reparacion de DNA -> `quinolone_or_genomic_damage_combination`;
- sin regla disponible -> `unknown`.

Cada recomendacion inferida agrega `collateral_sensitivity_rule_based_inference` en `audit_flags`. Si no hay regla, agrega `collateral_sensitivity_no_rule_available`.

## Configuracion

La configuracion vive en `config/params.yaml`:

```yaml
phase3:
  collateral_sensitivity:
    enabled: true
    default_score: 0.0
    rule_based_mode: true
```

`default_score` evita inventar sensibilidad colateral cuando no hay senales. `rule_based_mode` documenta que la primera version opera por reglas transparentes.

## Variables conceptuales futuras

Posibles columnas:

- `collateral_sensitivity_potential`
- `collateral_sensitivity_partner`
- `collateral_sensitivity_evidence_type`
- `collateral_sensitivity_evidence_reference`
- `combination_strategy`
- `combination_confidence_score`

## Relacion con therapeutic_role

La sensibilidad colateral puede ayudar a diferenciar roles:

- `sensitizer_candidate`: nodo que potencia otro tratamiento.
- `mixed_strategy_candidate`: nodo con efecto propio y capacidad de sensibilizacion.
- `antivirulence_candidate`: nodo que reduce dano y puede combinarse con antibioticos.
- `bactericidal_candidate`: nodo cuya inhibicion directa puede ser reforzada por costo evolutivo alto.

## Limitaciones

- La sensibilidad colateral es altamente dependiente del organismo, cepa, dosis y ambiente.
- No debe inferirse solo desde centralidad.
- Requiere evidencia experimental, literatura curada o reglas conservadoras muy claras.
- Las recomendaciones actuales son hipotesis por regla, no evidencia clinica ni experimental.
- Si no hay regla, el modulo devuelve `unknown` y no fuerza una combinacion.

## Paso futuro sugerido

Crear una cola de curacion para combinaciones terapeuticas candidatas, separando hipotesis rule-based, literatura curada y evidencia experimental antes de modificar rankings.
