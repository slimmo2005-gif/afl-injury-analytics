"""Apply draft picks and VFL participation to availability."""

from __future__ import annotations

import duckdb
import pandas as pd


def load_draft_picks(con: duckdb.DuckDBPyConnection, draft_df: pd.DataFrame) -> None:
    con.execute("DELETE FROM draft_picks")
    if draft_df.empty:
        return
    con.register("_draft", draft_df)
    con.execute(
        """
        INSERT INTO draft_picks
        SELECT
            COALESCE(NULLIF(CAST(player_id AS VARCHAR), 'nan'), player_name_norm) AS player_id,
            player_name,
            draft_year,
            draft_pick,
            drafted_club,
            player_name_norm
        FROM _draft
        """
    )
    con.unregister("_draft")

    con.execute(
        """
        UPDATE player_profiles p
        SET draft_pick = d.draft_pick
        FROM draft_picks d
        WHERE p.player_id = d.player_id
           OR (p.player_name = d.player_name AND p.season >= d.draft_year)
        """
    )


def load_vfl_games(con: duckdb.DuckDBPyConnection, vfl_df: pd.DataFrame) -> None:
    con.execute("DELETE FROM vfl_games")
    if vfl_df.empty:
        return
    con.register("_vfl", vfl_df)
    con.execute(
        """
        INSERT INTO vfl_games
        SELECT
            player_name,
            player_name_norm,
            COALESCE(afl_club, vfl_team) AS afl_club,
            vfl_team,
            season,
            round,
            game_slug,
            CAST(NULL AS VARCHAR) AS player_id
        FROM _vfl
        WHERE afl_club IS NOT NULL
        """
    )
    con.unregister("_vfl")


def link_vfl_player_ids(con: duckdb.DuckDBPyConnection) -> None:
    """Match VFL rows to fryzigg player_id by name + AFL club."""
    con.execute(
        """
        UPDATE vfl_games v
        SET player_id = (
            SELECT pg.player_id
            FROM player_games pg
            WHERE LOWER(pg.player_name) = v.player_name_norm
              AND pg.team = v.afl_club
              AND pg.season = v.season
            LIMIT 1
        )
        WHERE v.player_id IS NULL
        """
    )


def apply_vfl_to_availability(con: duckdb.DuckDBPyConnection) -> None:
    """Mark vfl_only: played VFL, not AFL, for squad members."""
    con.execute(
        """
        UPDATE availability a
        SET
            vfl_played = TRUE,
            status = 'vfl_only'
        FROM vfl_games v
        WHERE a.season = v.season
          AND a.round = v.round
          AND NOT a.afl_played
          AND (
              (v.player_id IS NOT NULL AND a.player_id = v.player_id)
              OR (LOWER(a.player_name) = v.player_name_norm AND a.team = v.afl_club)
          )
        """
    )
    con.execute(
        """
        UPDATE availability
        SET status = 'unavailable'
        WHERE NOT afl_played
          AND COALESCE(vfl_played, FALSE) = FALSE
          AND status NOT IN ('intermittent')
        """
    )
