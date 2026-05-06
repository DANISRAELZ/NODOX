# Guia de Entrada de Datos del Usuario

Nodos Funcionales puede trabajar con datos parciales. Mientras menos evidencia se cargue, mas preliminar sera el ranking y mas importantes seran las columnas de auditoria, confianza y faltantes.

## Entrada minima

La entrada minima define el analisis y los candidatos:

- organismo bacteriano;
- cepa opcional;
- lista de genes o proteinas candidatas.

En la arquitectura actual, los candidatos se incorporan mediante las capas obligatorias del workspace, especialmente `essentiality.csv`, `virulence.csv`, `human_homologs.csv` y `localization.csv`. Si no hay candidatos ni datos demo habilitados, el sistema debe detenerse con un mensaje claro.

## Entrada intermedia

La entrada intermedia mejora la interpretabilidad:

- organismo;
- cepa;
- candidatos;
- esencialidad;
- virulencia;
- conservacion;
- localizacion subcelular;
- homologia con hospedero.

Estas capas permiten calcular scores antibacterianos, antivirulencia, seguridad del hospedero, accesibilidad y confianza basica.

## Entrada avanzada

La entrada avanzada permite analisis mas robustos:

- pangenoma;
- core genome;
- genes accesorios;
- red funcional;
- resistoma;
- viruloma;
- expresion;
- esencialidad experimental;
- literatura curada;
- contexto clinico;
- sitio de infeccion;
- evidencia terapeutica;
- riesgo evolutivo.

Estas senales alimentan capas como `functional_network`, `strain_conservation`, `literature_support`, `clinical_impact`, `curated_disease_context`, `therapy_site_context`, `redundancy`, `collateral_sensitivity` y `evolutionary_escape_risk`.

## Procedencia

Cada capa debe distinguir:

- datos de usuario;
- fuentes externas;
- catalogos curados;
- cache;
- datos demo;
- proveedores controlados;
- proxies derivadas.

Los datos demo y proxy sirven para ejecutar el flujo o generar hipotesis. No deben presentarse como evidencia fuerte.

## Plantillas

Usa `data_templates/*.csv` para preparar las capas y `data_templates/organism_config_template.yaml` para documentar el organismo, cepa, hospedero, enfermedad, sitio de infeccion y fuentes externas deseadas.
