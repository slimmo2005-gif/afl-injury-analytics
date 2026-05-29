"""Orchestrate ingest → transform → export."""

from __future__ import annotations

import duckdb
import pandas as pd

from .config import DEFAULT_SEASON, MIN_SEASON, ROOT
from .db import connect
from .export.frontend import write_metrics
from .ingest.draftguru import fetch_all_drafts, link_draft_to_players, save_draft_cache
from .ingest.fryzigg import load_player_games
from .ingest.squiggle import fetch_all_seasons
from .ingest.vfl import fetch_vfl_games
from .transform.availability import build_availability
from .transform.continuity import build_archetype_continuity
from .transform.integrate_draft_vfl import (
    apply_vfl_to_availability,
    link_vfl_player_ids,
    load_draft_picks,
    load_vfl_games,
)
from .transform.pvs import build_player_profiles, build_player_value
from .transform.unavailability import build_team_round_value, enrich_availability_status
from .validate import run_checks

VFL_CACHE = ROOT / "shared" / "data" / "vfl_games.parquet"
VFL_FROM_SEASON = 2018  # full 2012+ available; 2018+ balances coverage vs runtime


def _load_df(con: duckdb.DuckDBPyConnection, table: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    con.register("_staging", df)
    con.execute(f"DELETE FROM {table}")
    cols = ", ".join(df.columns)
    con.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM _staging")
    con.unregister("_staging")


def run_pipeline(
    from_season: int = MIN_SEASON,
    to_season: int = DEFAULT_SEASON,
    export_season: int | None = None,
    skip_squiggle: bool = False,
    skip_fryzigg: bool = False,
    skip_draft: bool = False,
    skip_vfl: bool = False,
    vfl_from_season: int = VFL_FROM_SEASON,
    refresh_vfl_cache: bool = False,
) -> duckdb.DuckDBPyConnection:
    con = connect()
    export_season = export_season or to_season

    if not skip_squiggle:
        print(f"[pipeline] ingesting Squiggle matches {from_season}-{to_season}")
        matches = fetch_all_seasons(from_season, to_season)
        _load_df(con, "matches", matches)
        print(f"[pipeline] matches rows: {len(matches)}")

    if not skip_fryzigg:
        print(f"[pipeline] ingesting Fryzigg player games {from_season}-{to_season}")
        players = load_player_games(from_season=from_season, to_season=to_season)
        _load_df(con, "player_games", players)
        print(f"[pipeline] player_games rows: {len(players)}")

    print("[pipeline] building availability …")
    build_availability(con)
    enrich_availability_status(con)

    if not skip_draft:
        print(f"[pipeline] ingesting national draft {from_season}-{to_season}")
        draft_raw = fetch_all_drafts(from_season=from_season, to_season=to_season)
        if not draft_raw.empty:
            draft_linked = link_draft_to_players(draft_raw, con)
            load_draft_picks(con, draft_linked)
            save_draft_cache(draft_linked)
            matched = draft_linked["player_id"].notna().sum()
            print(f"[pipeline] draft picks: {len(draft_linked)} ({matched} linked to player_id)")

    print("[pipeline] building player profiles and PVS …")
    build_player_profiles(con)
    build_player_value(con)

    if not skip_vfl:
        vfl_df: pd.DataFrame
        if VFL_CACHE.exists() and not refresh_vfl_cache:
            print(f"[pipeline] loading VFL cache {VFL_CACHE}")
            vfl_df = pd.read_parquet(VFL_CACHE)
        else:
            print(f"[pipeline] scraping VFL participation {vfl_from_season}-{to_season}")
            vfl_df = fetch_vfl_games(from_season=vfl_from_season, to_season=to_season)
            if not vfl_df.empty:
                VFL_CACHE.parent.mkdir(parents=True, exist_ok=True)
                vfl_df.to_parquet(VFL_CACHE, index=False)
        if not vfl_df.empty:
            load_vfl_games(con, vfl_df)
            link_vfl_player_ids(con)
            apply_vfl_to_availability(con)
            print(f"[pipeline] VFL player-rows: {len(vfl_df)}")
            enrich_availability_status(con)

    print("[pipeline] building PVS-weighted unavailability …")
    build_team_round_value(con)

    print("[pipeline] building archetype continuity …")
    build_archetype_continuity(con)

    issues = run_checks(con, export_season)
    for issue in issues:
        print(f"[validate] WARNING: {issue}")
    if any("No " in i for i in issues):
        raise RuntimeError("Pipeline validation failed — see warnings above")

    path = write_metrics(con, season=export_season)
    print(f"[pipeline] exported metrics -> {path}")
    return con
