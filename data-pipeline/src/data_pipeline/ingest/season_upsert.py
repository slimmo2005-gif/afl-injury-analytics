"""Incremental season ingest — append/replace one season without wiping history."""

from __future__ import annotations

import duckdb
import pandas as pd

from ..config import FRYZIGG_RDS_FILE
from .afl_com import latest_fryzigg_season, load_afl_com_player_games
from .fryzigg import load_player_games
from .squiggle import fetch_games


def _register_and_insert(con: duckdb.DuckDBPyConnection, table: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    con.register("_upsert_staging", df)
    cols = ", ".join(df.columns)
    con.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM _upsert_staging")
    con.unregister("_upsert_staging")


def delete_season(con: duckdb.DuckDBPyConnection, table: str, season: int) -> None:
    con.execute(f"DELETE FROM {table} WHERE season = ?", [season])


def upsert_matches(con: duckdb.DuckDBPyConnection, season: int) -> int:
    df = fetch_games(season)
    if df.empty:
        return 0
    df = df.dropna(subset=["home_team", "away_team"])
    delete_season(con, "matches", season)
    _register_and_insert(con, "matches", df)
    return len(df)


def upsert_player_games(con: duckdb.DuckDBPyConnection, season: int, *, refresh: bool = False) -> int:
    fryzigg_max = latest_fryzigg_season(FRYZIGG_RDS_FILE)
    if fryzigg_max is not None and season <= fryzigg_max:
        df = load_player_games(from_season=season, to_season=season)
        source = "fryzigg"
    else:
        df = load_afl_com_player_games(season, cache=not refresh)
        source = "afl.com"
    if df.empty:
        raise RuntimeError(f"No player_games for {season} ({source})")
    delete_season(con, "player_games", season)
    _register_and_insert(con, "player_games", df)
    print(f"[upsert] player_games {season}: {len(df)} rows ({source})")
    return len(df)
