# Validación PAO1 STRING/UniProt con baseline limpio

Fecha de ejecución: 2026-05-06.

## Alcance

- Organismo: `Pseudomonas aeruginosa`
- Cepa: `PAO1`
- Workspace local: `data_sessions/pao1_online_optional_clean_baseline_validation`

El workspace fue local, ignorado por Git y utilizado únicamente como evidencia de auditoría. PAO1 actúa como caso controlado de validación y no como organismo obligatorio del proyecto.

## Causa de la advertencia previa

La advertencia `baseline_not_clean_non_string_network_preserved` aparece cuando existe una red funcional basal que no parece una salida directa de STRING. El auditor conserva esa evidencia de manera conservadora para evitar reemplazar datos locales sin autorización.

## Preparación portable

```bash
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare --workspace data_sessions/pao1_online_optional_clean_baseline_validation --taxon-resolution-mode offline_only
```

Después se puede ejecutar una auditoría online controlada en el workspace separado:

```bash
python audit_online_sources.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions/pao1_online_optional_clean_baseline_validation --sources string uniprot --mode online_optional --force-refresh --disable-cache-read --compare
```

## Interpretación

- La red demo o local se mantiene separada de una respuesta STRING fresca.
- Los manifiestos deben identificar API, cache, fallback y procedencia.
- Una respuesta vacía o un fallo de proveedor no se interpreta como evidencia biológica negativa.
- Los resultados son de validación técnica, no de confirmación terapéutica.

## Reproducibilidad

Los comandos deben ejecutarse con el intérprete activo del entorno virtual. No se requiere ni se documenta una ruta absoluta de un equipo particular.
