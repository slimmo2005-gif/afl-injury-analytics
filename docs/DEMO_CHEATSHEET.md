# 10-minute demo cheat sheet

## What to say

1. **Vision**: Measure AFL player unavailability (from games played, not injury lists) and correlate missing player value with wins.
2. **This repo**: Wireframe UI + architecture plan; real data comes in Phase 1 ETL.
3. **Stack**: React static site on GitHub Pages; Python/DuckDB pipeline refreshes JSON weekly.

## Live demo flow

| Step | Action |
|------|--------|
| 1 | Show local app: `cd frontend && npm run dev` |
| 2 | Click through 6 tabs (League, Club, Player, Model…) |
| 3 | Create GitHub repo → push code |
| 4 | Settings → Pages → **GitHub Actions** as source |
| 5 | Open `https://<user>.github.io/<repo>/` after workflow completes |

## Talking points on mock data

- **PVS** = Player Value Score (performance + draft potential, age-weighted)
- **Statuses**: unavailable / VFL only / intermittent
- **Regression page**: sample linear model (R² 0.42) — placeholder until Phase 2

## After the meeting

- Phase 1: fitzRoy + AFL Tables ingest → DuckDB → export JSON
- Phase 2: real charts + weekly `data-refresh.yml`
