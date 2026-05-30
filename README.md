# AFL Unavailability Analytics

Wireframe MVP for an **injury-adjusted team performance** analytics app. Measures how much player value is unavailable each week and correlates it with team results.

**Live demo:** https://slimmo2005-gif.github.io/afl-injury-analytics/

## Quick start (local)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Deploy to GitHub Pages

Push to `main` — the workflow builds the app and publishes `index.html` + `assets/` to the **repo root** (works when Pages source is `main` / root).

Optional: you can also point Pages at the `gh-pages` branch instead.

**Live URL:** https://slimmo2005-gif.github.io/afl-injury-analytics/

## Project structure

```
├── frontend/          # React + Vite + Tailwind + Recharts (GitHub Pages)
├── data-pipeline/     # Python ETL (Phase 1) — stubs
├── shared/            # JSON schemas & typed contracts
├── notebooks/         # Exploratory analysis
├── docs/              # Architecture & roadmap
└── .github/workflows/ # Deploy + weekly data refresh
```

## Phases

| Phase | Focus |
|-------|--------|
| **1** | Historical availability DB from match participation (2012+) |
| **2** | Player Value Score, unavailability metrics, regression, full viz |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/MVP_ROADMAP.md](docs/MVP_ROADMAP.md).

## Data (planned)

- fitzRoy / AFL Tables / Squiggle — no paid APIs
- DuckDB locally → export Parquet + JSON for static frontend
- Availability inferred: AFL selected / VFL only / neither = unavailable

## Data pipeline (Phase 1)

```bash
pip install -e data-pipeline
python -m data_pipeline run --from-season 2012 --to-season 2024
```

Sources: [Squiggle](https://api.squiggle.com.au), [Fryzigg](http://www.fryziggafl.net/), [Draftguru](https://www.draftguru.com.au) (national draft), [VFL stats](https://vfl.aflmstats.com) (reserves participation 2021+). Availability is inferred from games played — not official injury lists.

## Status

- ✅ Dashboard UI with 6 pages
- ✅ Phase 1 ETL + real metrics JSON (2012–2024 participation)
- ✅ GitHub Actions deploy + weekly data refresh
- ✅ Phase 2: PVS model, PVS-weighted unavailability, archetype continuity, filters
- ✅ National draft (Draftguru) + VFL reserves (2021–2024)
- ⏳ VFL 2012–2020 (not on aflmstats), ladder-adjusted residuals
