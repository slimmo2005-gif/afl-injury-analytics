# Phase 2 — Player Value Score (PVS)

## Formula

```
PVS = w(age) × Performance + (1 − w(age)) × Potential
```

### Performance (0–10)

Rolling weighted blend of prior two seasons + current (20% / 30% / 50%), then z-scored within season:

- Disposals per game (35%)
- Goals per game (25%)
- Score involvements per game (25%)
- Games played (15%)

Mapped to 0–10 via `5 + weighted z-sum`.

### Potential (0–10)

Exponential draft curve: `10 × exp(−pick / 14)`

- Pick 1 ≈ 9.5
- Pick 22 (rookie default) ≈ 2.1
- Pick 40 (unknown veteran default) ≈ 0.6

Override picks via `shared/data/draft_picks.csv` (`player_id`, `draft_pick`).

### Age weight w(age)

Linear ramp from 18 → 25:

| Age | Performance weight |
|-----|-------------------|
| ≤18 | 30% |
| 25+ | 100% |

### Unavailability metrics

Per team-round (players on squad who did not play AFL):

- `unavailable_pvs_total`
- `unavailable_pvs_top5` / `top10`
- `unavailable_pvs_u22` / `unavailable_pvs_28plus`
- Intermittent status: missed round but played 2+ of prior 4

### Continuity

Week-to-week returning players grouped by Fryzigg position → archetype (key defender, inside mid, etc.).

## Data sources

- [Squiggle](https://api.squiggle.com.au) — results
- [Fryzigg](http://www.fryziggafl.net/) — player stats & positions (fitzRoy ecosystem)
- [Draftguru](https://www.draftguru.com.au) — national draft picks (2012+)
- [VFL AFLM Stats](https://vfl.aflmstats.com) — VFL participation (2021–2024 on site; earlier seasons unavailable)

### VFL availability

Players on an AFL club squad who did not play AFL but appear in a VFL box score for the affiliated reserves side are marked `vfl_only`. VFL franchise → AFL club mapping is in `shared/data/vfl_to_afl_club.json`.

### National draft

Real draft pick numbers replace the rookie/veteran heuristic when a player is matched to Fryzigg `player_id` via normalized name. Unmatched picks still use defaults.
