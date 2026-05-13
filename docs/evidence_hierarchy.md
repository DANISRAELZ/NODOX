# Evidence Hierarchy

## Jerarquia conceptual

La confianza no depende solo del valor numerico de una variable. Tambien depende
de su procedencia y de si la evidencia es directa, curada, inferida, demo o
faltante.

Orden conceptual:

```text
user_supplied
> curated_snapshot
> real_external_online
> controlled_provider
> inferred_proxy
> demo
> missing_input
```

`insufficient_evidence` no es un punto bajo de la jerarquia. Es una categoria
propia: indica que hay informacion parcial o no concluyente y que no debe
convertirse automaticamente en evidencia negativa.

## Regla obligatoria

La ausencia de evidencia no equivale a evidencia negativa.

Ejemplos:

- Si no hay evidencia de HGT, el sistema no debe concluir que no existe HGT.
- Si no hay datos de paralogia, el sistema no debe concluir que no hay
  paralogos compensatorios.
- Si la localizacion es desconocida, no debe asumirse inaccesibilidad absoluta.

## Uso en el pipeline

- `confidence_modifier` resume confianza operativa por candidato.
- `provenance_status` resume la procedencia dominante cuando puede inferirse.
- `evidence_level` conserva una lectura textual de calidad o tipo de evidencia.
- `interpretation_warning` recuerda limites de interpretacion por candidato.

Los datos demo y los proxies nunca deben elevar la confianza como si fueran
evidencia curada, experimental u online real.
