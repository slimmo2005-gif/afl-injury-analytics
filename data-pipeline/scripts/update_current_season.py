"""Ingest and export the in-progress current AFL season (2026+).

Keeps historical metrics.json capped at HISTORICAL_MAX_SEASON (2021–2025 window)
and writes a separate currentSeason.json for the live season page.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_pipeline.config import CURRENT_SEASON, ROOT
from data_pipeline.db import connect
from data_pipeline.export.current_season import write_current_season
from data_pipeline.export.frontend import write_metrics
from data_pipeline.ingest.draftguru import refresh_draft_picks
from data_pipeline.ingest.bigfooty_forum import fetch_bigfooty_forum
from data_pipeline.ingest.injury_sources import ingest_live_injury_lists, load_injury_dataframe
from data_pipeline.ingest.season_upsert import upsert_matches, upsert_player_games
from data_pipeline.ingest.state_league import fetch_state_league_games, prepare_state_league_games
from data_pipeline.pipeline import _apply_vfl_layer
from data_pipeline.transform.absences import enrich_absence_reasons
from data_pipeline.transform.availability import build_availability
from data_pipeline.transform.availability_adjustments import apply_availability_adjustments
from data_pipeline.transform.continuity import build_archetype_continuity
from data_pipeline.transform.integrate_draft_vfl import (
    IncompleteStateLeagueError,
    load_state_league_games,
)
from data_pipeline.transform.pvs import build_player_profiles, build_player_value
from data_pipeline.transform.unavailability import build_team_round_value, enrich_availability_status

VFL_CACHE = ROOT / "shared" / "data" / "state_league_games.parquet"


def _refresh_state_league(con, season: int, *, refresh: bool) -> None:
    if VFL_CACHE.exists() and not refresh:
        raw = pd.read_parquet(VFL_CACHE)
    else:
        raw = pd.DataFrame()
        if VFL_CACHE.exists():
            raw = pd.read_parquet(VFL_CACHE)

    try:
        fetched = fetch_state_league_games(from_season=season, to_season=season)
    except Exception as exc:
        print(f"[current] state-league fetch skipped: {exc}")
        fetched = pd.DataFrame()

    if fetched.empty:
        print(f"[current] no new state-league rows for {season}")
        return

    if not raw.empty:
        raw = raw[raw["season"] != season]
        combined = pd.concat([raw, fetched], ignore_index=True)
    else:
        combined = fetched

    VFL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(VFL_CACHE, index=False)

    prepared = prepare_state_league_games(fetched, con)
    try:
        load_state_league_games(con, prepared, replace_seasons=[season])
        print(f"[current] state-league {season}: {len(prepared)} rows")
    except IncompleteStateLeagueError as exc:
        print(f"[current] state-league load skipped: {exc}")


def _refresh_injury_lists(con, season: int) -> None:
    ingest_live_injury_lists(con)
    try:
        forum = fetch_bigfooty_forum(years=[season])
        if not forum.empty:
            load_injury_dataframe(con, forum)
            print(f"[current] bigfooty forum {season}: {len(forum)} rows")
    except Exception as exc:
        print(f"[current] forum injury scrape skipped: {exc}")


def update_current_season(
    season: int = CURRENT_SEASON,
    *,
    refresh_player_cache: bool = False,
    refresh_vfl: bool = False,
) -> None:
    con = connect()

    print(f"[current] ingesting Squiggle matches {season}")
    n_matches = upsert_matches(con, season)
    print(f"[current] matches {season}: {n_matches} rows")

    upsert_player_games(con, season, refresh=refresh_player_cache)

    refresh_draft_picks(con, to_season=season - 1)

    _refresh_state_league(con, season, refresh=refresh_vfl)

    print("[current] rebuilding availability …")
    build_availability(con)
    _apply_vfl_layer(con)
    apply_availability_adjustments(con)
    enrich_availability_status(con)

    _refresh_injury_lists(con, season)
    enrich_absence_reasons(con)

    build_player_profiles(con)
    build_player_value(con)
    build_team_round_value(con)
    build_archetype_continuity(con)

    write_metrics(con)
    write_current_season(con, season=season)
    print("[current] done")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update current AFL season data")
    parser.add_argument("--season", type=int, default=CURRENT_SEASON)
    parser.add_argument("--refresh-players", action="store_true")
    parser.add_argument("--refresh-vfl", action="store_true")
    args = parser.parse_args()
    update_current_season(
        season=args.season,
        refresh_player_cache=args.refresh_players,
        refresh_vfl=args.refresh_vfl,
    )


if __name__ == "__main__":
    main()
