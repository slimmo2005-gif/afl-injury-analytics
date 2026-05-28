# MVP roadmap

## Now (wireframe) ✅

- [x] React + Vite + Tailwind + Recharts scaffold
- [x] Six dashboard pages with mock JSON
- [x] GitHub Pages deploy workflow
- [x] Folder structure + schema stubs
- [x] Sample regression coefficients in UI

## Phase 1 — Availability database (4–6 weeks)

1. **Ingest**
   - Fixtures, results, lineups via fitzRoy / AFL Tables / Squiggle
   - Player metadata + draft picks where available
2. **Normalize**
   - `players`, `matches`, `selections`, `participation` tables in DuckDB
3. **Derive**
   - Weekly availability status per player
   - VFL flag when data exists (nullable)
4. **Export**
   - `availability_by_round.parquet`
   - `frontend/public/data/metrics.json`
5. **Validate**
   - Coverage report from 2012
   - Schema contract tests in CI

## Phase 2 — Value & analytics (4–8 weeks)

1. PVS hybrid model (performance + draft potential + age curve)
2. Team-round unavailability aggregates
3. Continuity metrics (archetypes)
4. Linear regression → wins, margin, ladder residuals
5. Wire all charts to real exports
6. Enable weekly `data-refresh.yml` to commit outputs

## Suggested first ETL tasks

```bash
# After implementing data-pipeline/src/ingest/squiggle.py etc.
python -m data_pipeline.run --season 2024 --dry-run
python -m data_pipeline.export --format json --out shared/output/
```

## Risk register

| Risk | Mitigation |
|------|------------|
| VFL data incomplete | Nullable `vfl_played`; partial population |
| Source API changes | Pin versions; schema drift check in CI |
| GitHub Pages base path | `VITE_BASE_PATH` in deploy workflow |
