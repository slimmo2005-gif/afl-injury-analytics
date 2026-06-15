# Absence reasons and injury episodes

## Goal

Move beyond binary “played / didn’t play” to classify **why** a listed player missed AFL:

| Status | Meaning | Counts as games missed? |
|--------|---------|-------------------------|
| `afl_played` | Selected | — |
| `vfl_only` | Played SANFL/VFL/WAFL instead | No |
| `injured` | On official AFL injury list | Yes |
| `intermittent` | Missed round but played 2+ of prior 4 | Yes |
| `unclear` | Missed AFL, reason unknown (SANFL gap etc.) | Yes |
| `unavailable` | Missed AFL, not yet classified | Yes |

## Data sources

### AFL injury list (live)

- URL: https://www.afl.com.au/matches/injury-list
- Structured tables per club: **Player | Injury | Estimated return**
- Scraped weekly into `injury_list_entries` (`source = afl_injury_list`)
- Injury types normalized to categories: `lower_limb`, `knee`, `concussion`, `suspension`, etc.

### BigFooty news (historical + live)

- Category: https://www.bigfooty.com/category/afl-injuries/
- Round-labelled articles 2018–2019, 2023–2024+ with clean `<h3>` club + table HTML
- Ingest: `ingest/bigfooty_injuries.py` → `source = bigfooty_news`
- **No 2021–2022 articles** in the category index

### BigFooty forum (2024–2026)

- Yearly threads with full 18-club tables (e.g. “Injury List AFL 2024 – updated every few days”)
- Ingest: `ingest/bigfooty_forum.py` → `source = bigfooty_forum`

### Wayback Machine (2021–2022 AFL.com)

- Archived snapshots of `afl.com.au/matches/injury-list`
- Ingest: `ingest/injury_list_wayback.py` → `source = wayback_afl`
- CDX index cached at `data-pipeline/raw/wayback_injury_cdx.json` (requires archive.org access)

### Scripts

```bash
cd data-pipeline

# Historical backfill (BigFooty + optional Wayback) then enrich
python scripts/backfill_injury_lists.py --enrich --export-season 2024

# Weekly live fetch (AFL.com + recent BigFooty news)
python scripts/enrich_absences.py --export-season 2024
```

### Absence episodes (3+ weeks)

`absence_episodes` groups contiguous missed-AFL weeks (excluding `vfl_only`):

1. Detect streaks ≥ 3 weeks from `availability`
2. Match injury list at episode start (when snapshots exist)
3. Label Adelaide/Port 2021–23 & 2025 gaps as `unclear` when still unclassified

## SANFL triage (Adelaide / Port)

For player-weeks where AFL missed and not on injury list:

1. **Injury list** → `injured` + injury type
2. **Club SANFL match reports** (planned) → `vfl_only`
3. Else → `unclear`

australianfootball.com provides fixtures and career totals, not per-round SANFL player logs.

## Reporting

`export/injury_report.py` writes:

- **episodes** — all 3+ week absences with archetype and PVS
- **by_injury_type** — episode count, total weeks, avg weeks per episode
- **by_archetype** — injury weeks rolled up by positional archetype

Run after pipeline:

```bash
cd data-pipeline
python -c "from data_pipeline.db import connect; from data_pipeline.export.injury_report import export_injury_episodes; export_injury_episodes(connect(), season=2024)"
```

## Design notes

- **Episode threshold (3 weeks)** filters noise from single-week omissions and selection calls.
- **Season boundaries** shorten episodes at year end — average weeks by injury type should be interpreted with that caveat.
- **Injury list ≠ complete** — not every absence is listed (rest, personal, SANFL assignment).
- Store weekly injury list snapshots over time to backfill historical injury types on episodes.

## Next steps

1. Club match-report scraper (afc.com.au, portadelaidefc.com.au) for SANFL `vfl_only`
2. Optional manual override CSV: `shared/data/absence_overrides.csv`
