# Esencialidad Contextual

## Proposito

Este documento describe la diferencia entre esencialidad general y esencialidad contextual para Fase 3. La idea central es que un gen o nodo puede no ser esencial en condiciones de laboratorio estandar, pero volverse critico dentro del hospedero, en un tejido especifico o bajo presion terapeutica.

La implementacion inicial vive en `src/nodos_funcionales/contextual_essentiality.py`. Es un modulo independiente: calcula columnas contextuales sobre una tabla de nodos, pero no cambia todavia el ranking principal del pipeline.

## Esencialidad general

La esencialidad general describe si un gen es necesario para crecimiento o supervivencia bajo una condicion de referencia. Suele venir de ensayos de knockout, Tn-seq, CRISPRi, DEG u otros estudios de perdida de funcion.

Es util, pero incompleta: una condicion de laboratorio no representa todos los nichos de infeccion.

## Esencialidad contextual

La esencialidad contextual pregunta si el nodo es necesario en un contexto especifico:

- sitio anatomico;
- etapa de infeccion;
- disponibilidad de nutrientes;
- presion inmune;
- biofilm;
- ambiente intracelular;
- exposicion a antibioticos;
- estres oxidativo o nitrosativo.

Un nodo puede tener bajo score de esencialidad general y aun asi ser terapeuticamente importante si sostiene supervivencia en el nicho real.

## Importancia del sitio de infeccion

El sitio de infeccion define barreras, nutrientes, oxigeno, pH, presion inmune y concentraciones alcanzables del tratamiento. Por eso la Fase 3 deberia interpretar cada nodo segun el nicho.

Ejemplos de nichos relevantes:

- sangre: presion de complemento, hierro limitado, exposicion inmune sistemica;
- pulmon: moco, oxigeno variable, inflamacion, biofilm, gradientes de antibiotico;
- abscesos: hipoxia, pH bajo, baja penetracion, alta densidad bacteriana;
- ambiente intracelular: estres oxidativo, limitacion nutricional, compartimentos celulares;
- biofilm: matriz extracelular, baja difusion, tolerancia, subpoblaciones persistentes;
- heridas o tejido necrotico: nutrientes heterogeneos, baja perfusion, comunidades mixtas.

## Estres oxidativo

Durante infeccion, fagocitos y tejidos inflamados pueden imponer especies reactivas de oxigeno. Nodos de reparacion, detoxificacion y respuesta a estres pueden volverse esenciales aunque no lo sean en medio rico.

## Limitacion de hierro

El hospedero limita hierro como defensa. Por eso sideroforos, transportadores y reguladores de adquisicion de hierro pueden ser nodos contextualmente esenciales.

## Biofilm

El biofilm cambia la fisiologia bacteriana. Nodos de matriz, adhesion, quorum sensing, metabolismo lento y tolerancia a estres pueden ser mas importantes que blancos bactericidas clasicos.

## Ambiente intracelular

Algunos patogenos sobreviven dentro de celulas del hospedero. En ese contexto pueden ser criticos los nodos de resistencia a acidez, estres oxidativo, adquisicion de nutrientes y evasion de degradacion.

## Abscesos

Los abscesos combinan baja difusion, hipoxia, necrosis, alta carga bacteriana y barreras fisicas. Un nodo accesible en cultivo puede no ser accesible alli, y un nodo de metabolismo anaerobio puede volverse prioritario.

## Relacion con clinical_impact, curated_disease_context y therapy_site_context

Las capas de Fase 2 ya preparan parte de esta lectura:

- `clinical_impact`: aproxima dano al hospedero, severidad o impacto clinico.
- `curated_disease_context`: aproxima relevancia durante enfermedad, etapa o modelo de infeccion.
- `therapy_site_context`: aproxima accesibilidad y contexto del sitio terapeutico.

En Fase 3, estas capas deberian alimentar una variable conceptual de esencialidad contextual, siempre separando evidencia real de proxies.

La implementacion actual puede usar, si existen:

- `clinical_impact_score`
- `host_damage_score`
- `disease_severity_association`
- `infection_context_score`
- `infection_site_access_score`
- `infection_site_access`
- `infection_site`
- `disease_context`
- `infection_stage`
- `syndrome`
- notas o nombres de base asociados a las capas terapeuticas.

No depende obligatoriamente del proveedor controlado. Si detecta que el contexto proviene de una fuente controlada, lo marca en auditoria y no eleva confianza por si solo.

## Implementacion actual

La funcion principal es:

```python
compute_contextual_essentiality_features(df, params) -> df
```

Devuelve una copia de la tabla con estos campos:

- `infection_site_relevance_score`: relevancia del sitio o nicho infeccioso para el nodo.
- `host_stress_relevance_score`: relevancia bajo presion inmune, inflamacion o dano asociado.
- `iron_limitation_relevance_score`: relevancia en limitacion de hierro o inmunidad nutricional.
- `oxidative_stress_relevance_score`: relevancia bajo estres oxidativo o inflamatorio.
- `intracellular_survival_score`: relevancia en ambiente intracelular.
- `biofilm_relevance_score`: relevancia en biofilm, infeccion cronica, dispositivos, abscesos o persistencia.
- `therapy_site_context_score`: senal derivada de accesibilidad o contexto terapeutico del sitio.
- `contextual_essentiality_score`: combinacion final normalizada entre 0 y 1.

## Reglas implementadas

La regla inicial es heuristica e interpretable:

- nodos con palabras asociadas a captacion de hierro, sideroforos, hemo o hierro suben si el contexto menciona limitacion de hierro, sangre, suero, pulmon, absceso o inmunidad nutricional;
- nodos de estres oxidativo suben en contextos inflamatorios, intracelulares, con macrofagos o neutrofilos;
- nodos de biofilm, matriz, adhesion, alginato, quorum sensing o persistencia suben en infecciones cronicas, dispositivos, abscesos, fibrosis quistica o biofilm;
- nodos de supervivencia intracelular suben en contextos intracelulares, fagosoma, macrofago o compartimentos celulares;
- la ausencia de sitio o contexto no rompe el calculo: usa `missing_context_default` y agrega una marca de auditoria.

La formula conceptual es:

```text
contextual_essentiality_score =
  infection_site_relevance_score * infection_site_weight
  + host_stress_relevance_score * host_stress_weight
  + iron_limitation_relevance_score * iron_limitation_weight
  + oxidative_stress_relevance_score * oxidative_stress_weight
  + intracellular_survival_score * intracellular_survival_weight
  + biofilm_relevance_score * biofilm_weight
```

Todos los componentes se limitan al rango 0-1.

## Configuracion

Los pesos se configuran en `config/params.yaml`:

```yaml
phase3:
  contextual_essentiality:
    missing_context_default: 0.5
    infection_site_weight: 0.25
    host_stress_weight: 0.20
    iron_limitation_weight: 0.15
    oxidative_stress_weight: 0.15
    intracellular_survival_weight: 0.15
    biofilm_weight: 0.10
```

## Auditoria

Si no hay contexto de infeccion definido, el modulo agrega:

```text
contextual_essentiality_context_missing
```

Si hay contexto, agrega:

```text
contextual_essentiality_context_present
```

Si detecta que el contexto proviene de una fuente controlada, agrega:

```text
contextual_essentiality_controlled_context_used_no_confidence_boost
```

Esto significa que el contexto puede usarse como senal operativa, pero no debe interpretarse como evidencia experimental ni aumentar la confianza.

## Variables futuras

Posibles columnas futuras:

- `contextual_essentiality_score`
- `infection_niche`
- `infection_stage`
- `niche_evidence_type`
- `niche_evidence_reference`
- `contextual_essentiality_confidence`

## Limitaciones

- La esencialidad contextual requiere evidencia especifica por nicho.
- No debe inferirse automaticamente desde virulencia o centralidad.
- Diferentes enfermedades producidas por el mismo organismo pueden tener contextos distintos.
- Las reglas actuales usan palabras clave y scores existentes; son interpretables, pero no sustituyen curacion biologica.
- El proveedor controlado puede aportar contexto, pero no aumenta confianza por si solo.

## Paso futuro sugerido

Usar las colas de curacion existentes para llenar contexto de enfermedad, sitio y evidencia antes de permitir que `contextual_essentiality_score` afecte scores finales.
