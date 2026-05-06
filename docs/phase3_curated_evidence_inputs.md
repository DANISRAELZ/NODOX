# Entradas curadas para Fase 3

## Proposito

Esta fase prepara el pipeline para reemplazar datos demo y defaults inferidos
por evidencia curada por organismo, sin volver obligatoria la Fase 3 y sin
inventar evidencia biologica.

El cambio principal es ampliar los contratos CSV que el usuario puede aportar.
Si una tabla curada no existe, el pipeline conserva su comportamiento previo:
usa defaults explicitos, marca `audit_flags` y mantiene Fase 3 como modo
opcional.

## Ortologia reproducible para `human_homologs`

`human_homologs.csv` ahora acepta campos opcionales de ortologia:

- `orthology_method`
- `orthology_tool`
- `orthology_version`
- `orthology_reference`
- `orthology_query_coverage`
- `orthology_subject_coverage`
- `orthology_percent_identity`
- `orthology_bitscore`
- `orthology_confidence_score`
- `orthology_evidence_note`

Uso recomendado:

1. ejecutar una herramienta externa reproducible, por ejemplo BLAST, DIAMOND,
   HMMER u OrthoFinder;
2. conservar version, parametros y fecha de corrida en `orthology_reference`;
3. mapear los resultados al contrato `human_homologs.csv`;
4. mantener `human_homolog=1` solo cuando la evidencia soporte homologia humana;
5. usar `orthology_confidence_score` como confianza interpretativa, no como
   prueba absoluta de toxicidad.

## Redundancia, paralogia y alternativas de via

Se agrega la capa opcional `redundancy.csv`.

Columnas principales:

- `paralog_count`
- `pathway_alternative_count`
- `functional_backup_score`
- `metabolic_bypass_score`
- `regulatory_bypass_score`
- `paralog_evidence_reference`
- `pathway_evidence_reference`
- `redundancy_evidence_type`

Estas columnas alimentan `redundancy_penalty` en Fase 3. Si faltan, el modulo
mantiene defaults conservadores y lo registra en `audit_flags`.

## Escape evolutivo y tolerancia funcional

`evolutionary_escape.csv` ahora acepta senales curadas mas descompuestas:

- `known_escape_mutation_score`
- `inferred_functional_tolerance_score`
- `module_participation_score`
- `paralog_count_score`
- `alternative_pathway_score`
- `mutational_tolerance_score`
- `fitness_cost_score`
- `compensation_difficulty_score`
- `evolutionary_escape_risk_score`
- `evolutionary_space_constraint_score`

Estas columnas pueden venir de literatura, ensayos de evolucion, catalogos de
mutaciones, pangenoma, analisis de red o curacion manual trazable. Ausencia de
mutaciones conocidas no debe interpretarse automaticamente como bajo riesgo.

## Sensibilidad colateral y combinaciones

`collateral_sensitivity.csv` acepta ahora:

- `collateral_sensitivity_score`
- `combination_opportunity_score`
- `recommended_combination_class`
- `combination_partner`
- `combination_evidence_reference`
- `combination_rationale`

La recomendacion de combinacion debe leerse como hipotesis. Si no hay evidencia
experimental o literatura trazable, usar valores bajos o dejar la fila ausente.

## Plantillas

Plantillas nuevas o ampliadas:

- `data_templates/human_homologs_template.csv`
- `data_templates/redundancy_template.csv`
- `data_templates/evolutionary_escape_template.csv`
- `data_templates/collateral_sensitivity_template.csv`

Todas las plantillas quedan vacias salvo encabezados para evitar evidencia
simulada.

## Limitaciones actuales

- El pipeline no ejecuta BLAST, DIAMOND, HMMER ni OrthoFinder internamente.
- La capa `redundancy.csv` no es obligatoria y no bloquea `compare`.
- Fase 3 sigue desactivada como ranking principal; se activa con `--mode phase3`.
- Los defaults inferidos siguen existiendo para mantener reproducibilidad, pero
  quedan auditados.

## Paso futuro sugerido

El siguiente paso cientifico es llenar estas plantillas para un organismo
concreto usando evidencia real, empezando por:

1. ortologia reproducible para homologos humanos;
2. paralogia y alternativas de via desde anotacion/pangenoma;
3. escape evolutivo desde literatura o mutaciones observadas;
4. combinaciones desde evidencia experimental o revisiones curadas.
