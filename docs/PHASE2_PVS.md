# Phase 2 — Player Value Score (PVS)

## Formula

```
blended = w(age) × Performance + (1 − w(age)) × Potential × 0.75
PVS     = max(Performance, blended)
```

Potential only **tops up** players who have not yet shown impact on-field. The **0.75 factor** scales draft potential in the blend so lists heavy with recent top-10 picks (e.g. Essendon 2024) do not inflate club averages excessively.

### Performance (0–7)

Weighted sum of **current-season per-game averages** (no rolling history, no z-scores):

| Stat | Weight |
|------|--------|
| Effective disposals / game (disp × DE% ÷ 100) | +0.22 |
| Goals per game | +0.18 |
| Score involvements per game | +0.11 |
| Metres gained / 100 per game | +0.06 |
| Tackles per game | +0.07 |
| Contested marks per game | +0.08 |
| Marks inside forward 50 per game | +0.28 |
| Intercept marks per game | +0.09 |
| Intercepts per game | +0.06 |
| Clearances per game | +0.11 |
| Hit-outs per game | +0.03 |
| Hit-outs to advantage per game | +0.05 |
| Clangers per game | −0.06 |

Then normalised within each season:

```
performance_score = 7 × raw_composite / league_max_composite
```

The best player in the league each season always scores **7**; everyone else scales proportionally below that.

### Potential (0–10)

Exponential draft curve: `10 × exp(−pick / 14)`

- Pick 1 ≈ 9.5
- Pick 22 (rookie default) ≈ 2.1
- Pick 40 (unknown veteran default) ≈ 0.6

Each player's **best (lowest) draft pick** across all years is used, linked to Fryzigg `player_id` via Draftguru name matching. Override via `shared/data/draft_picks.csv`.

### Age weight w(age)

Linear ramp from 18 → 25 (only applies when potential top-up is used):

| Age | Performance weight |
|-----|-------------------|
| ≤18 | 30% |
| 25+ | 100% |

### Unavailability metrics

Per team-round (players on squad who did not play AFL), sums use **injury_weight_pvs** (not season PVS) when games played &lt; 14 — see below.

- `unavailable_pvs_total` — all non-AFL PVS in a round (includes VFL-only)
- `unavailable_pvs_games_missed` — non-AFL PVS excluding VFL-only (unavailable + intermittent)
- `unavailable_pvs_top5` / `top10`
- `unavailable_pvs_u22` / `unavailable_pvs_28plus`
- Intermittent status: missed round but played 2+ of prior 4

### Injury weight PVS (`injury_weight_pvs`)

Season **PVS** reflects per-game output in fixtures actually played. Injured players often have few games and/or rusty return performances, which **understates** the value lost when they are absent.

For **unavailability counting only** (not player rankings), each player also has:

```
established_pvs = PVS from most recent prior season with 10+ games (if any)
injury_weight_pvs = PVS                         if games >= 14
                  = max(PVS, established_pvs)   if games < 14
```

Player rankings, core-22 selection, and club PVS averages still use season **PVS**. Only injury totals, PVS-lost ranks, and games-missed columns use **injury_weight_pvs**.

### Continuity

Week-to-week returning players grouped by positional archetype (key defender, inside mid, etc.).

Archetypes use **season stats** with separate rule sets:

- **Mids** (unchanged): inside mid from clearances/disposals; outside mid from high disposals + low clearances. Fryzigg `C`/`RR`/`WL` etc. used only when stats are ambiguous.
- **Forwards** (updated): key forward needs contested marks + goals; pressure forward = high tackles, low contested marks.
- **Defenders** (updated): key defender from intercepts + contested marks; rebound defender from metres gained with low contested marks.

Ambiguous profiles → utility (except mid slots fall back to Fryzigg mode).

## Data sources

- [Squiggle](https://api.squiggle.com.au) — results
- [Fryzigg](http://www.fryziggafl.net/) — player stats & positions (fitzRoy ecosystem)
- [Draftguru](https://www.draftguru.com.au) — national draft picks (2012+)
- [VFL AFLM Stats](https://vfl.aflmstats.com) — VFL participation (**2021–2025** on site; earlier seasons unavailable)
- [SANFL](https://sanfl.com.au) — AFL API fixtures (`competitionId=14`) + Hostplus stats PDFs (top scorers / disposal getters; **2024 PDFs on site**; 2022–2023 fixtures exist but stats PDFs not published)
- [WAFL Sportix API](https://wafl.com.au) — full WAFL match stats (**2018–2025**)

### State-league availability (`vfl_only`)

Players on an AFL club squad who did not play AFL but appear in a state-league box score are marked `vfl_only` (label kept for backward compatibility).

**Loading rule:** for 2024+, always load VFL + SANFL + WAFL together (`load_state_league_history.py` or main pipeline). Partial SANFL-only reloads are rejected so VFL/WAFL rows are not wiped from the database.

**Season coverage (as of ingest):**

| Competition | Seasons loaded |
|-------------|----------------|
| VFL | 2021–2025 |
| WAFL | 2018–2025 (loader defaults from 2021) |
| SANFL | 2024 partial (stats PDFs); 2022–2023 fixtures only — no player PDFs on SANFL site yet |

Run `python scripts/load_state_league_history.py --from-season 2021 --to-season 2025` after a fresh scrape (`--refresh`) or from cache.

| Competition | Victorian / other | SA / WA |
|-------------|-------------------|---------|
| Source | VFL AFLM Stats | SANFL PDFs + WAFL Sportix |
| Mapping | `shared/data/vfl_to_afl_club.json` | `sanfl_to_afl_club.json`, `wafl_to_afl_club.json` |

Peel Thunder (WAFL) is shared by Fremantle and West Coast; player rows resolve to the correct AFL club via Fryzigg name lookup at load time. SANFL PDF names are often surname-only — matching uses surname + club.

### National draft

Real draft pick numbers replace the rookie/veteran heuristic when a player is matched to Fryzigg `player_id` via normalized name. Unmatched picks still use defaults.
