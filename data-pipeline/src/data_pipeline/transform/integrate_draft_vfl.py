"""Apply draft picks and state-league participation to availability."""

from __future__ import annotations

import duckdb
import pandas as pd

# Seasons that must include VFL + SANFL + WAFL before replacing DB rows.
FULL_STATE_LEAGUE_FROM_SEASON = 2024
# Earlier seasons may lack SANFL API data (pre-2022) or VFL site data (pre-2021).
MIN_COMPETITION_ROWS: dict[str, int] = {"vfl": 500, "sanfl": 50, "wafl": 50}
MIN_COMPETITION_ROWS_BY_SEASON: dict[int, dict[str, int]] = {
    2021: {"vfl": 50, "wafl": 50},  # SANFL API has no 2021 fixtures
    2022: {"vfl": 100, "wafl": 50},  # SANFL stats PDFs not on site for 2022
    2023: {"vfl": 100, "wafl": 50},
    2025: {"vfl": 100, "wafl": 50},  # SANFL PDFs sparse until late season
    2026: {"vfl": 100, "sanfl": 25, "wafl": 50},  # club reports until Hostplus PDFs publish
}


class IncompleteStateLeagueError(ValueError):
    """Raised when a load would replace DB rows with a partial competition set."""


def validate_state_league_completeness(
    df: pd.DataFrame,
    seasons: list[int] | None = None,
) -> None:
    """Refuse partial competition loads (e.g. SANFL-only) for recent seasons."""
    if df.empty:
        raise IncompleteStateLeagueError("State-league frame is empty")
    seasons = seasons or sorted(int(s) for s in df["season"].unique())
    for season in seasons:
        if season in MIN_COMPETITION_ROWS_BY_SEASON:
            min_rows = MIN_COMPETITION_ROWS_BY_SEASON[season]
        elif season >= FULL_STATE_LEAGUE_FROM_SEASON:
            min_rows = MIN_COMPETITION_ROWS
        else:
            min_rows = {"vfl": 50, "wafl": 50}
        sub = df[df["season"] == season]
        for comp, min_n in min_rows.items():
            n = int((sub["competition"] == comp).sum())
            if n < min_n:
                raise IncompleteStateLeagueError(
                    f"Refusing state-league load for {season}: "
                    f"{comp} has {n} rows (need >={min_n}). "
                    "Reload from the full state-league cache (VFL+SANFL+WAFL) "
                    "via load_state_league_history.py or the main pipeline."
                )


def load_state_league_games(
    con: duckdb.DuckDBPyConnection,
    prepared: pd.DataFrame,
    *,
    replace_seasons: list[int] | None = None,
) -> None:
    """Merge prepared rows into vfl_games, keeping other seasons from the DB."""
    if prepared.empty:
        return
    replace_seasons = replace_seasons or sorted(int(s) for s in prepared["season"].unique())
    validate_state_league_completeness(prepared, replace_seasons)

    if replace_seasons:
        placeholders = ", ".join("?" * len(replace_seasons))
        existing = con.execute(
            f"SELECT * FROM vfl_games WHERE season NOT IN ({placeholders})",
            replace_seasons,
        ).df()
    else:
        existing = con.execute("SELECT * FROM vfl_games").df()

    combined = pd.concat([existing, prepared], ignore_index=True)
    load_vfl_games(con, combined)


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
    """Low-level replace of vfl_games — prefer load_state_league_games for callers."""
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
            afl_club,
            vfl_team,
            season,
            round,
            game_slug,
            player_id,
            competition,
            game_date
        FROM (
            SELECT
                v.player_name,
                v.player_name_norm,
                COALESCE(
                    v.afl_club,
                    (
                        SELECT pg.team
                        FROM player_games pg
                        WHERE LOWER(pg.player_name) = v.player_name_norm
                          AND pg.season = v.season
                          AND pg.team IN ('Fremantle', 'West Coast')
                        LIMIT 1
                    ),
                    (
                        SELECT 'Adelaide'
                        FROM player_games pg
                        WHERE pg.season = v.season
                          AND pg.team = 'Adelaide'
                          AND v.vfl_team = 'Glenelg'
                          AND LOWER(regexp_extract(pg.player_name, ' ([^ ]+)$', 1)) = LOWER(v.player_name)
                        LIMIT 1
                    ),
                    CASE
                        WHEN v.vfl_team IN ('Peel Thunder', 'Peel') THEN NULL
                        ELSE v.vfl_team
                    END
                ) AS afl_club,
                v.vfl_team,
                v.season,
                v.round,
                v.game_slug,
                CAST(NULL AS VARCHAR) AS player_id,
                COALESCE(v.competition, 'vfl') AS competition,
                TRY_CAST(v.game_date AS DATE) AS game_date,
                ROW_NUMBER() OVER (
                    PARTITION BY v.player_name_norm, v.season, v.round, v.game_slug, COALESCE(v.competition, 'vfl')
                    ORDER BY v.player_name
                ) AS rn
            FROM _vfl v
        ) sub
        WHERE rn = 1
          AND afl_club IS NOT NULL
        """
    )
    con.unregister("_vfl")


def link_vfl_player_ids(con: duckdb.DuckDBPyConnection) -> None:
    """Match state-league rows to fryzigg player_id by name + AFL club."""
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
    con.execute(
        """
        UPDATE vfl_games v
        SET player_id = (
            SELECT pg.player_id
            FROM player_games pg
            WHERE pg.team = v.afl_club
              AND pg.season = v.season
              AND LOWER(regexp_extract(pg.player_name, ' ([^ ]+)$', 1)) = LOWER(v.player_name)
            LIMIT 1
        )
        WHERE v.competition = 'sanfl'
          AND v.player_id IS NULL
          AND v.afl_club IS NOT NULL
        """
    )
    con.execute(
        """
        UPDATE vfl_games v
        SET
            player_id = (
                SELECT pg.player_id
                FROM player_games pg
                WHERE pg.team = 'Adelaide'
                  AND pg.season = v.season
                  AND LOWER(regexp_extract(pg.player_name, ' ([^ ]+)$', 1)) = LOWER(v.player_name)
                LIMIT 1
            ),
            afl_club = 'Adelaide'
        WHERE v.competition = 'sanfl'
          AND v.vfl_team = 'Glenelg'
          AND v.player_id IS NULL
        """
    )


def apply_vfl_to_availability(con: duckdb.DuckDBPyConnection) -> None:
    """Mark vfl_only: played state league, not AFL, for squad members."""
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
              OR (
                  LOWER(a.player_name) = v.player_name_norm
                  AND a.team = v.afl_club
              )
              OR (
                  v.competition = 'sanfl'
                  AND a.team = v.afl_club
                  AND LOWER(regexp_extract(a.player_name, ' ([^ ]+)$', 1)) = LOWER(v.player_name)
              )
              OR (
                  v.competition = 'wafl'
                  AND v.vfl_team ILIKE '%peel%'
                  AND a.team IN ('Fremantle', 'West Coast')
                  AND LOWER(a.player_name) = v.player_name_norm
              )
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
