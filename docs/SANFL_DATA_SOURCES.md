# SANFL player participation — data source investigation

**Goal:** mark `vfl_only` when an AFL-listed player missed AFL but played SANFL (Adelaide, Port Adelaide, Glenelg affiliate).

**Current pipeline:** [SANFL match centre](https://sanfl.com.au/league/matches/) via `api3.sanflstats.com` (full box scores, 2021+). Hostplus PDFs and club reports are legacy fallbacks only.

---

## What each source provides

| Source | Fixtures | Per-round player lists | Seasons tested | Auth |
|--------|----------|------------------------|----------------|------|
| **SANFL match centre** (`api3.sanflstats.com`) | Yes | **Full box scores** | **2021+** (`/fixtures/{season}/sanfl`) | Public (Referer header) |
| **SANFL Hostplus PDFs** (legacy fallback) | — | Partial (leaders only) | 2024 (~19 PDFs) | Public |
| **AFL API v2** (`aflapi.afl.com.au`) | Yes | **No** (score/venue only) | 2022–2025 in `compSeason` name; **2021 not listed** | Public |
| **Champion Data API** (`api.afl.championdata.io`) | Yes | **Full box scores** | SANFL on roadmap (official docs); match `providerId` e.g. `CD_M20220160101` | **API key** (401 without) |
| **WheelO** (`wheeloratings.com`) | — | **Season totals only** | 2022–2025 `player_stats/sanfl/{year}.json` (~400 players); **2021: 404** | Public |
| **WheelO `match_stats/table_data`** | — | Per-match (AFL) | IDs like `202401` are **AFL** rounds; **no SANFL round IDs found** after brute-force | Public |
| **WAFL Sportix** pattern on sanfl.com.au | — | — | **No Sportix embed** on SANFL site (unlike WAFL) | — |
| **FootyWire / stats.sanfl.com.au** | — | — | **404 / DNS dead** | — |
| **Club match reports** (afc.com.au, portadelaidefc.com.au) | — | Named players in prose | 2022+ articles exist | Public scrape |

Probe scripts: `scripts/probe_sanfl_alternatives.py`, `scripts/probe_wheelo_sanfl.py`.

---

## Why 2021–2023 are empty today

1. **PDFs** — SANFL only publishes round stats PDFs on their resources hub from **2024** (and 2025 finals). Older seasons are not linked there.
2. **AFL API** — No `"2021 SANFL Premiership Season"` fixtures; earliest season name in API is **2022**.
3. **WheelO** — No `sanfl/2021.json`; 2022+ files are **season aggregates** (`Matches` count per player), not game-by-game logs.
4. **Champion Data** — Endpoints exist (`GET /v1/matches/{matchId}/statistics/players`) but require credentials.

---

## Recommended options (best → fallback)

### 1. Champion Data AFL API (recommended if you can get access)

- Map AFL API match `id` / `providerId` → Champion Data match ID.
- Pull full player lists per SANFL game for Adelaide & Port (and Glenelg via surname matching, as today).
- Covers **2022+** reliably; 2021 only if CD holds historical SANFL.
- Docs: https://docs.api.afl.championdata.com/

**Effort:** Medium — new ingest module + API key in env; same `vfl_games` / `apply_vfl_to_availability` path.

### 2. SANFL match centre API (implemented — primary source)

- Module: `ingest/sanfl_match_centre.py` — `https://api3.sanflstats.com/fixtures/{season}/sanfl` + `/fixture/{matchId}`.
- Powers [sanfl.com.au/league/matches](https://sanfl.com.au/league/matches/?league=sanfl&season=2026&round=10); full `playerStats` (44 players/game).
- Covers **2021+**; Adelaide, Port Adelaide, Glenelg (affiliate).
- Wired as primary path in `fetch_sanfl_games()`; PDFs/club reports are fallback only.

### 3. Keep PDFs (legacy fallback)

- Continue PDF parse for 2024+.
- Add imgix/CDN crawl, Internet Archive, and alternate resource search paths.
- Still **partial** (top scorers/disposals, not every player) and **no 2021–2023** unless PDFs surface elsewhere.

**Effort:** Low — extend `_discover_pdf_urls()` in `ingest/sanfl.py`.

### 3. Club SANFL match-report scraper (Adelaide + Port) — **implemented**

- Module: `ingest/sanfl_club_reports.py` — scrapes `afc.com.au/teams/sanfl/news` and Port `teams/sanfl` match reports.
- Parses team-selection lists (AFL-listed players) and stat lines (`finished with N disposals`, Goals/Best).
- Merged into `fetch_sanfl_games()`; discovered article paths cached at `shared/data/sanfl_club_article_paths.json`.
- **Coverage:** current-season articles on club sites (~10 AFC, ~3 Port per season); ID-neighbour scan finds nearby team-selection posts. Not a full historical archive (2021–2023 still sparse).
- **Cons:** Partial player lists; first catalog scrape slow (~5 min); maintenance if HTML changes.

**Run:** `python scripts/load_state_league_history.py --from-season 2025 --to-season 2026 --refresh`

### 4. WheelO season file (not sufficient alone)

- `player_stats/sanfl/{year}.json` confirms a player played **N** SANFL games in a season but **not which rounds**.
- Cannot drive round-level `vfl_only` without guessing.
- Useful as **validation** or to prioritise name matching after another source fills rounds.

---

## 2021 specifically

No automated public source found for per-round SANFL player lists in 2021:

- No AFL API SANFL season
- No WheelO file
- No PDFs
- WAFL/VFL already cover Victorian & WA clubs

**Practical options for 2021 Adelaide/Port:** Champion Data (if historical), manual/club archives, or accept `unavailable` for those weeks.

---

## Suggested next step

If you have (or can request) a **Champion Data API key**, implementing `ingest/sanfl_championdata.py` is the cleanest path for 2022–2025 and would replace most PDF dependency.

Without a key, the best incremental win is a **club match-report scraper** for Adelaide and Port alongside existing 2024 PDFs.
