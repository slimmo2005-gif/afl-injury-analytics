"""Incremental season ingest — append/replace one season without wiping history."""

from __future__ import annotations

import duckdb
import pandas as pd

from ..config import FRYZIGG_RDS_FILE
from .afl_com import latest_fryzigg_season, load_afl_com_player_games, _provider_match_id
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


def _coerce_match_ids(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "match_id" not in df.columns:
        return df
    out = df.copy()

    def _to_int(value):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return _provider_match_id(str(value))

    out["match_id"] = out["match_id"].map(_to_int)
    return out.dropna(subset=["match_id"])


def remap_to_canonical_player_ids(
    df: pd.DataFrame,
    con: duckdb.DuckDBPyConnection,
    season: int,
) -> pd.DataFrame:
    """Map AFL.com player ids onto existing Fryzigg ids when names match."""
    if df.empty:
        return df
    mapping = con.execute(
        """
        SELECT LOWER(player_name) AS pn, team, player_id AS canonical_id
        FROM (
            SELECT
                player_name,
                team,
                player_id,
                ROW_NUMBER() OVER (
                    PARTITION BY LOWER(player_name), team
                    ORDER BY COUNT(*) DESC
                ) AS rn
            FROM player_games
            WHERE season < ?
            GROUP BY player_name, team, player_id
        )
        WHERE rn = 1
        """,
        [season],
    ).df()
    if mapping.empty:
        return df
    out = df.copy()
    out["_pn"] = out["player_name"].str.lower()
    merged = out.merge(mapping, left_on=["_pn", "team"], right_on=["pn", "team"], how="left")
    out["player_id"] = merged["canonical_id"].fillna(out["player_id"]).astype(str)
    return out.drop(columns=["_pn"], errors="ignore")


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
    df = remap_to_canonical_player_ids(df, con, season)
    df = _coerce_match_ids(df)
    delete_season(con, "player_games", season)
    _register_and_insert(con, "player_games", df)
    print(f"[upsert] player_games {season}: {len(df)} rows ({source})")
    return len(df)
