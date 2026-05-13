# Theory Software Alignment

```mermaid
flowchart TD
    A["Teoria de Nodos Funcionales"] --> B["Seis postulados"]
    B --> C["Tipologia de nodos funcionales"]
    B --> D["Capas de evidencia"]
    B --> E["Eje evolutivo"]
    D --> F["Procedencia y confianza"]
    C --> G["Scoring modular"]
    D --> G
    E --> G
    F --> G
    G --> H["meta_priority_score"]
    H --> I["Ranking explicable"]
    I --> J["Auditoria"]
    I --> K["Limites de interpretacion"]
```

El diagrama resume la dependencia conceptual: el software no define la teoria;
la teoria define que capas, variables, scores, advertencias y auditorias debe
producir el software.
