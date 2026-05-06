# Marco de validacion biologica

Este marco ayuda a revisar si los candidatos priorizados por Nodos Funcionales
son biologicamente plausibles. No reemplaza experimentos ni convierte el ranking
en validacion terapeutica.

## Preguntas de validacion

1. ¿El gen o proteina es esencial en el organismo o condicion relevante?
2. ¿Esta conservado entre aislados o cepas de interes?
3. ¿Tiene homologo humano o del hospedero que sugiera riesgo de toxicidad?
4. ¿Esta asociado a virulencia?
5. ¿Esta asociado a resistencia antimicrobiana, tolerancia o persistencia?
6. ¿Participa en una via metabolica critica?
7. ¿Esta en una red funcional central?
8. ¿Es accesible segun localizacion y sitio de infeccion?
9. ¿Tiene soporte bibliografico verificable?
10. ¿Tiene inhibidores conocidos o clases quimicas relacionadas?
11. ¿Presenta riesgo de toxicidad por homologia o funcion compartida?
12. ¿Encaja mejor como antibiotico clasico, antivirulencia, sensibilizador o nodo funcional?

## Plantilla de curacion

Usar:

- `data_templates/biological_validation_targets.csv`

Valores sugeridos para `validation_status`:

- `not_evaluated`
- `computational_support_only`
- `literature_supported`
- `experimentally_supported`
- `deprioritized`
- `requires_manual_review`

Valores sugeridos para `experimental_priority`:

- `high`
- `medium`
- `low`
- `not_ready`

## Criterios de degradacion

Un candidato debe degradarse o pasar a revision manual si:

- depende principalmente de demo o proxy,
- tiene homologia humana o del hospedero no resuelta,
- no esta conservado en aislados relevantes,
- carece de evidencia de accesibilidad,
- tiene soporte bibliografico pendiente,
- su rol terapeutico depende de una capa controlada sin curacion manual.

## Interpretacion

El ranking generado por Nodos Funcionales debe interpretarse como priorizacion
computacional exploratoria. No confirma eficacia terapeutica ni reemplaza
validacion experimental. La plantilla de validacion biologica sirve para decidir
que candidatos merecen curacion adicional, ensayo experimental o descarte.
