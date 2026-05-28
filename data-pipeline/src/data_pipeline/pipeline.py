"""Orchestrate ingest → transform → export."""

from __future__ import annotations

import duckdb
import pandas as pd

from .config import DEFAULT_SEASON, MIN_SEASON
from .db import connect
from .export.frontend import write_metrics
from .ingest.fryzigg import load_player_games
from .ingest.squiggle import fetch_all_seasons
from .transform.availability import build_availability
from .validate import run_checks


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
) -> duckdb.DuckDBPyConnection:
    con = connect()
    export_season = export_season or to_season

    if not skip_squiggle:
        print(f"[pipeline] ingesting Squiggle matches {from_season}–{to_season}")
        matches = fetch_all_seasons(from_season, to_season)
        _load_df(con, "matches", matches)
        print(f"[pipeline] matches rows: {len(matches)}")

    if not skip_fryzigg:
        print(f"[pipeline] ingesting Fryzigg player games {from_season}–{to_season}")
        players = load_player_games(from_season=from_season, to_season=to_season)
        _load_df(con, "player_games", players)
        print(f"[pipeline] player_games rows: {len(players)}")

    print("[pipeline] building availability …")
    build_availability(con)

    issues = run_checks(con, export_season)
    for issue in issues:
        print(f"[validate] WARNING: {issue}")
    if any("No " in i for i in issues):
        raise RuntimeError("Pipeline validation failed — see warnings above")

    path = write_metrics(con, season=export_season)
    print(f"[pipeline] exported metrics -> {path}")
    return con
