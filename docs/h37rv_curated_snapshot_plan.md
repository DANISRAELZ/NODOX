# Plan de snapshot curado H37Rv

## 1. Proposito

Este documento define como preparar, en una fase posterior, un snapshot curado
para `Mycobacterium tuberculosis` H37Rv. El objetivo es crear una referencia
pequena, trazable y auditable para validar el contrato multi-organismo de Nodos
Funcionales sin convertir H37Rv en default universal del proyecto.

Este plan no contiene datos biologicos curados, no descarga fuentes externas y
no modifica reglas de scoring. Solo establece criterios para decidir que debe
llenarse antes de congelar un snapshot.

## 2. Por que H37Rv es util

H37Rv es una cepa de referencia ampliamente usada para `Mycobacterium
tuberculosis`. Por su cobertura publica esperada, puede servir como validacion
cruzada multi-organismo despues del demo controlado PAO1 y sin depender de
organismos no relacionados con este bloque de trabajo.

Su valor dentro del proyecto es tecnico y metodologico:

- comprobar que el pipeline acepta otro organismo bacteriano con cepa definida;
- validar resolucion taxonomica local/cache-first sin asumir PAO1;
- preparar evidencia curada que pueda auditar procedencia, confianza y
  limitaciones;
- probar que la Teoria de Nodos Funcionales se operacionaliza por capas de
  evidencia, no por identidad de organismo.

## 3. Tres rutas distintas

| Ruta | Que valida | Que no valida |
| --- | --- | --- |
| Dry-run H37Rv | Resolucion taxonomica, creacion de workspace, manifest inicial y compatibilidad de comandos. | No produce ranking biologico interpretable. |
| Snapshot curado H37Rv | Contrato de capas, procedencia, fuentes, checksums y evidencia congelada revisada. | No sustituye una corrida completa ni valida eficacia terapeutica. |
| Corrida biologica real interpretable | Integracion de capas curadas suficientes, ranking, reportes y auditoria de candidatos. | No confirma eficacia experimental ni recomendacion clinica. |

## 4. Capas minimas requeridas

Antes de considerar listo un snapshot H37Rv, deben prepararse archivos pequenos
y revisados para estas capas, usando las plantillas existentes cuando aplique:

- `organism_profile`: identidad del organismo, cepa, taxon id, alcance de cepa o
  especie y notas de limitacion.
- `essentiality`: evidencia de esencialidad, con fuente, metodo y contexto.
- `virulence`: evidencia de virulencia o patogenicidad, con procedencia clara.
- `localization`: localizacion celular/subcelular o accesibilidad biologica
  estimada desde fuentes trazables.
- `human_homologs`: evidencia de homologos humanos, ausencia documentada o
  estado no evaluado; nunca asumir ausencia por falta de datos.
- `strain_conservation`: conservacion en cepas o linajes relevantes, declarando
  si el alcance es H37Rv, especie o un conjunto definido.
- `functional_network`: red funcional, interacciones o asociaciones, con fuente
  y estado de recuperacion.
- `evolutionary_escape_risk`: subcapa evolutiva con variables explicitas o
  faltantes controlados.

Para la subcapa evolutiva, el snapshot debe preservar al menos:

- `evolutionary_escape_risk`
- `evolutionary_constraint`
- `mutation_tolerance`
- `pathway_redundancy`
- `paralog_count`
- `mobile_context`
- `hgt_context`
- `recombination_context`
- `resistance_association`

## 5. Capas opcionales recomendadas

Estas capas no deben bloquear el primer snapshot si se declaran como faltantes,
pero aumentan la interpretabilidad si se curan correctamente:

- `clinical_impact`
- `curated_disease_context`
- `therapy_site_context`
- `literature_support`
- `biological_validation_targets`

## 6. Reglas de procedencia

Cada fila o fuente debe conservar una categoria de procedencia clara:

- `user_data`: datos aportados o curados manualmente por el usuario.
- `curated_literature`: evidencia revisada desde articulos, revisiones o
  literatura primaria con identificador trazable.
- `curated_database`: base curada estable consultada y registrada.
- `external_provider`: proveedor externo usado por el resolvedor o por una fase
  de adquisicion documentada.
- `cache`: resultado previamente resuelto, reutilizado con fecha y estado.
- `demo` o `proxy`: permitido solo si esta claramente marcado, no se mezcla con
  evidencia real y no eleva confianza.

Reglas adicionales:

- No interpretar ausencia de datos como evidencia negativa.
- No mezclar evidencia a nivel especie con evidencia a nivel H37Rv sin
  explicarlo en `limitations`.
- No usar datos demo para sostener conclusiones biologicas.
- No elevar confianza si una capa proviene solo de proxy, cache viejo o faltante
  controlado.

## 7. Fuentes candidatas para consulta posterior

Estas fuentes pueden evaluarse en una fase futura. Este plan no descarga ni
consulta ninguna de ellas:

- Mycobrowser.
- TBDB, si sigue aplicando y se define su estado de mantenimiento.
- UniProt.
- STRING.
- Literatura de essentiality o DEG, si se decide posteriormente una estrategia
  reproducible de curacion.
- VFDB u otras fuentes de virulencia, si la cobertura para H37Rv resulta
  pertinente.

Cada fuente candidata debe registrarse con fecha de consulta, identificadores,
licencia o restriccion de uso, alcance taxonomico, metodo de recuperacion y
estado de confianza.

## 8. Criterios minimos de listo

El snapshot H37Rv puede considerarse listo para versionarse solo si cumple:

- identidad taxonomica documentada, indicando si se usa taxon id de cepa o de
  especie;
- todos los archivos minimos presentes o declarados como faltantes controlados;
- fuentes y procedencia separadas por capa;
- limitaciones explicitas para evidencia parcial, inferida, cacheada o a nivel
  especie;
- checksums calculados despues de congelar los archivos;
- ausencia de datos demo no marcados;
- ningun campo biologico inventado para completar una tabla;
- validacion local del contrato de snapshot sin modificar el validador por
  reglas especificas de H37Rv.

## 9. Limites de interpretacion

Un snapshot H37Rv no equivale a validacion terapeutica. Sirve para reproducir y
auditar evidencia curada en el marco de la Teoria de Nodos Funcionales. Un
ranking derivado de ese snapshot seguiria siendo una priorizacion computacional
exploratoria, no una confirmacion de eficacia, seguridad, actividad clinica ni
recomendacion terapeutica.

Las capas incompletas, proxies, caches o evidencia a nivel especie deben
reducir confianza interpretativa. Ningun candidato debe promocionarse solo por
ausencia de evidencia negativa.

## 10. Checklist antes de correr el pipeline

- [ ] Confirmar que el objetivo es H37Rv y que no se mezclan datos de otros
  organismos.
- [ ] Crear un workspace o snapshot separado para H37Rv.
- [ ] Llenar `organism_profile` con taxonomia, cepa y limitaciones.
- [ ] Preparar las capas minimas requeridas o marcar faltantes controlados.
- [ ] Registrar procedencia, fuente, confianza y estado de recuperacion por capa.
- [ ] Separar evidencia a nivel H37Rv de evidencia a nivel especie.
- [ ] Revisar que `demo` y `proxy` esten marcados y no eleven confianza.
- [ ] Revisar que la subcapa evolutiva conserve todas sus variables clave.
- [ ] Calcular checksums si se va a versionar el snapshot.
- [ ] Ejecutar primero un dry-run offline/cache-first.
- [ ] Ejecutar pruebas offline antes de interpretar resultados.
- [ ] Revisar reportes de procedencia, faltantes, confianza y limites antes del
  ranking terapeutico.
