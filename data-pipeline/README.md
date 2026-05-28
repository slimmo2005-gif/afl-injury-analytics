# Data pipeline (Phase 1)

Planned modules:

- `ingest/` — AFL Tables, Squiggle, fitzRoy exports
- `transform/` — availability derivation, participation joins
- `models/` — PVS, unavailability aggregates (Phase 2)
- `export/` — Parquet + JSON for frontend

Entry point (TODO):

```bash
python -m data_pipeline.run --season 2024
```
