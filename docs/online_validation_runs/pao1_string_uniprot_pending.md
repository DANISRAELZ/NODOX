# Validacion online controlada pendiente: PAO1 STRING/UniProt

## Estado

Pendiente. En esta consolidacion no se ejecuto red real. Se validaron comportamientos offline/cache con pruebas unitarias y se documento el comando manual.

## Razon

La suite obligatoria debe permanecer offline y reproducible. La validacion real de APIs externas debe ejecutarse solo en un entorno con red autorizada y estable, usando un workspace separado para no contaminar el demo principal.

## Workspace recomendado

```text
data_sessions\pao1_online_validation
```

## Comando recomendado

```powershell
C:\Users\danis\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe audit_online_sources.py --organism "Pseudomonas aeruginosa" --strain PAO1 --workspace data_sessions\pao1_online_validation --sources string uniprot --mode online_optional --force-refresh --disable-cache-read --compare
```

## Informacion a registrar al ejecutar

- Fecha/hora.
- Modo.
- Fuentes.
- Numero de consultas.
- Numero de aciertos.
- Numero de faltantes.
- Numero de fallos.
- Uso de fallback.
- Archivos generados.
- Diferencias de ranking si se comparo.
- Advertencias.

## Regla de interpretacion

No convertir resultados online no curados en snapshot de referencia. Solo congelar snapshot online si las fuentes, fecha, cache, fallos y degradaciones quedan revisadas y documentadas.
