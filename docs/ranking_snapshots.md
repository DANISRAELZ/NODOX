# Snapshots curados de ranking

## Propósito

Los snapshots de ranking detectan regresiones en:

- orden del ranking;
- candidatos agregados o removidos;
- scores principales;
- estrategia preferida;
- rol terapéutico.

## Referencia demo

La referencia demo actual está en:

```text
tests/fixtures/ranking_snapshots/pao1_demo_reference.csv
```

Es un fixture técnico, no evidencia biológica real. No debe contener timestamps, rutas absolutas ni mensajes variables.

## Archivos generados

Cada corrida puede generar:

```text
results/ranking_snapshot.csv
results/ranking_snapshot_comparison.csv
```

La comparación se produce cuando existe `results/ranking_snapshot_reference.csv`.

## Actualizar una referencia

Una referencia solo debe actualizarse cuando el cambio esté justificado y documentado:

```powershell
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
Copy-Item data_sessions/pseudomonas_aeruginosa_pao1/results/ranking_snapshot.csv tests/fixtures/ranking_snapshots/pao1_demo_reference.csv
```

Prueba de snapshot:

```bash
python -m pytest -p no:cacheprovider -m "snapshot and not online" -q
```

## Tolerancia

La comparación acepta ruido de punto flotante hasta `1.0e-6` y debe detectar:

- cambios de rank;
- nodos agregados o removidos;
- cambios en `preferred_strategy`;
- cambios relevantes de score;
- cambios en `therapeutic_role`.

## Snapshots reales controlados

Un snapshot real controlado requiere:

- organismo, cepa y nivel taxonómico declarados;
- fecha y modo de adquisición;
- fuentes y versiones;
- estado de cache;
- commit o versión de NODOX;
- checksums;
- procedencia y limitaciones;
- revisión humana.

Estructura recomendada:

```text
tests/fixtures/ranking_snapshots/
  pao1_demo_reference.csv
  real_controlled/
    <organism_slug>/
      snapshot_manifest.yaml
      source_manifest.csv
      checksums.sha256
      ranking_reference.csv
```

Los snapshots demo y reales no deben mezclarse. No deben versionarse datos privados, clínicos, propietarios, no redistribuibles ni caches volátiles completas.

## Manifest mínimo

```yaml
organism: "Organism name"
strain: "Strain or scope"
taxon_id: "Taxon identifier"
acquisition_date: "YYYY-MM-DD"
acquisition_mode: "curated_snapshot_offline"
evidence_status: "curated_reference"
provenance: "Human-readable provenance summary"
limitations:
  - "Document incomplete or non-comparable evidence."
checksums:
  source_manifest_csv: "sha256:<hash>"
  ranking_reference_csv: "sha256:<hash>"
```

La ausencia de una capa en un snapshot no equivale a ausencia biológica ni a bajo riesgo.
