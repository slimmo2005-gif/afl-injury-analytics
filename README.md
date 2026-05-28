# AFL Unavailability Analytics

Wireframe MVP for an **injury-adjusted team performance** analytics app. Measures how much player value is unavailable each week and correlates it with team results.

**Live demo (after setup):** `https://<your-username>.github.io/<repo-name>/`

## Quick start (local)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Deploy to GitHub Pages (~5 min)

1. Create a new repo on GitHub (e.g. `afl-injury-analytics`).
2. Push this project:
   ```bash
   git init
   git add .
   git commit -m "Initial wireframe MVP"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
3. In the repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. Push to `main` — the **Deploy to GitHub Pages** workflow runs automatically.
5. Your URL appears under **Settings → Pages** (usually within 2–3 minutes).

> The build sets `VITE_BASE_PATH=/<repo-name>/` so assets load correctly on project pages.

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

Sources: [Squiggle API](https://api.squiggle.com.au), [Fryzigg](http://www.fryziggafl.net/) (fitzRoy ecosystem). Availability is inferred from AFL selection — not official injury lists.

## Status

- ✅ Dashboard UI with 6 pages
- ✅ Phase 1 ETL + real metrics JSON (2012–2024 participation)
- ✅ GitHub Actions deploy + weekly data refresh
- ⏳ Phase 2: Player Value Score, VFL data, full regression
