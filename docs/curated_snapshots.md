# Curated Snapshots

## Propósito

Un snapshot curado es una referencia pequeña, versionada y auditable que describe evidencias y procedencia de forma estable. No es una corrida activa, no es un cache vivo y no reemplaza datos de usuario.

Los snapshots sirven para validar contratos, procedencia y reproducibilidad. No representan verdad biológica completa ni limitan a NODOX a los organismos incluidos como ejemplo.

## Principio multi-organismo

NODOX puede trabajar con cualquier bacteria cuyas capas de evidencia puedan resolverse de forma trazable. Un snapshot debe admitir:

- organismo con o sin cepa;
- taxón resuelto o limitación explícita;
- evidencia aportada por el usuario;
- evidencia externa, local, cacheada o controlada;
- capas parciales y faltantes declarados.

La falta de evidencia se registra como `missing`, `not_queried`, `cache_miss`, `stub` o `fallback`; nunca se interpreta automáticamente como evidencia biológica negativa.

## Snapshots de referencia

```text
data_external/curated_snapshots/pseudomonas_aeruginosa_pao1/
data_external/curated_snapshots/corynebacterium_pseudotuberculosis_biovar_ovis/
data_external/curated_snapshots/mycobacterium_tuberculosis_h37rv/
```

Son fixtures controlados para pruebas de estructura y procedencia. No son catálogos completos ni validación terapéutica.

## Estructura recomendada

```text
data_external/curated_snapshots/<snapshot_slug>/
  snapshot_metadata.json
  taxonomy.json
  sources_manifest.json
  functional_annotations.json
  provenance.json
  README.md
```

## Contrato de metadata

`snapshot_metadata.json` debe incluir, como mínimo:

- versión del esquema;
- organismo y cepa o alcance;
- nombre canónico y `taxon_id`;
- identificador y etiqueta del snapshot;
- fecha de creación;
- modo de adquisición y política de red;
- fuentes permitidas y versiones;
- política de cache, procedencia y confianza;
- limitaciones;
- herramienta o proceso generador;
- notas de reproducibilidad.

## Contrato de fuentes

Cada fuente debe registrar:

- nombre y tipo;
- estado de recuperación;
- modo de adquisición;
- cache;
- confianza;
- clase de evidencia;
- indicadores `is_stub`, `is_controlled` e `is_real_external`;
- fecha de acceso;
- URL, referencia y notas.

Reglas:

- una fuente controlada debe indicar `is_controlled=true` y `is_real_external=false`;
- un stub nunca se presenta como evidencia real;
- un fallback conserva motivo y procedencia;
- una respuesta cacheada no se confunde con una consulta fresca;
- un snapshot offline no debe afirmar `fresh_api_run`.

## Validación

```bash
python -m pytest tests/test_curated_snapshots.py -q
```

La validación revisa campos obligatorios, consistencia taxonómica, procedencia, contradicciones de estado y uso indebido de fuentes frescas en snapshots offline.

## Qué no se versiona

- bases completas descargadas de proveedores;
- caches volátiles;
- carpetas completas de ejecución;
- rankings no revisados;
- datos privados, clínicos, propietarios o no redistribuibles.

## Extensión futura

Nuevos snapshots deben agregarse sin modificar el contrato general. La evidencia externa real debe congelarse únicamente después de revisión humana, atribución, comprobación de derechos de redistribución y cálculo de checksums.
