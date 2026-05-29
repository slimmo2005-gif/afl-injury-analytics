# MVP roadmap

## Now (wireframe) ✅

- [x] React + Vite + Tailwind + Recharts scaffold
- [x] Six dashboard pages with mock JSON
- [x] GitHub Pages deploy workflow
- [x] Folder structure + schema stubs
- [x] Sample regression coefficients in UI

## Phase 1 — Availability database (in progress)

1. **Ingest** ✅ (initial)
   - Squiggle: fixtures/results (`matches`)
   - Fryzigg: player participation (`player_games`, 2012+)
   - VFL: nullable — not populated yet
2. **Normalize** ✅
   - DuckDB: `matches`, `player_games`, `squad_players`, `availability`, `team_round_summary`
3. **Derive** ✅
   - Availability inferred: AFL played vs squad member absent
4. **Export** ✅
   - `shared/output/metrics.json` + `frontend/public/data/metrics.json`
   - Parquet export in weekly GitHub Action
5. **Validate** ⏳
   - Basic checks in `validate.py`; CI schema tests TODO

## Phase 2 — Value & analytics ✅ (initial)

1. PVS hybrid model ✅ — performance z-scores + draft curve + age weighting
2. Team-round unavailability aggregates ✅ — total, top-5, top-10, age cohorts
3. Continuity metrics (archetypes) ✅ — by positional archetype
4. Linear regression ✅ — unavailable PVS vs wins and margin
5. Wire charts + season/club filters ✅
6. Weekly `data-refresh.yml` ✅

**Remaining:** VFL 2012–2020 (source gap), ladder-adjusted residuals, exact archetype from tracking

### Draft + VFL integration ✅

- National draft scraped from Draftguru → `draft_picks` table + `shared/data/draft_picks.csv`
- VFL box scores from vfl.aflmstats.com (2021–2024) → `vfl_only` status on availability
- PVS potential component uses real draft pick when matched (~76% link rate)

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
