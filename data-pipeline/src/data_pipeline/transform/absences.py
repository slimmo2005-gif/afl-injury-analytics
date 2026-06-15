"""Derive absence episodes and enrich availability with reasons."""

from __future__ import annotations

import duckdb

SANFL_CLUBS = ("Adelaide", "Port Adelaide")
MIN_EPISODE_WEEKS = 3


def _reset_absence_columns(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        UPDATE availability
        SET
            absence_reason = NULL,
            injury_type = NULL,
            injury_category = NULL
        WHERE NOT afl_played
        """
    )


def build_absence_episodes(con: duckdb.DuckDBPyConnection, *, min_weeks: int = MIN_EPISODE_WEEKS) -> None:
    """Contiguous AFL absences (excluding vfl_only) of min_weeks+."""
    con.execute("DELETE FROM absence_episodes")
    con.execute(
        f"""
        INSERT INTO absence_episodes
        WITH missed AS (
            SELECT
                a.player_id,
                a.player_name,
                a.team,
                a.season,
                a.round,
                a.status,
                a.round - ROW_NUMBER() OVER (
                    PARTITION BY a.player_id, a.team, a.season
                    ORDER BY a.round
                ) AS streak_grp
            FROM availability a
            WHERE NOT a.afl_played
              AND COALESCE(a.vfl_played, FALSE) = FALSE
              AND a.status NOT IN ('vfl_only')
        ),
        grouped AS (
            SELECT
                player_id,
                MAX(player_name) AS player_name,
                team,
                season,
                MIN(round) AS start_round,
                MAX(round) AS end_round,
                COUNT(*) AS weeks,
                streak_grp
            FROM missed
            GROUP BY player_id, team, season, streak_grp
            HAVING COUNT(*) >= {min_weeks}
        )
        SELECT
            g.player_id,
            g.player_name,
            g.team,
            g.season,
            g.start_round,
            g.end_round,
            g.weeks,
            'unclear' AS absence_reason,
            CAST(NULL AS VARCHAR) AS injury_type,
            CAST(NULL AS VARCHAR) AS injury_category,
            'inferred_from_games' AS source,
            'low' AS confidence
        FROM grouped g
        """
    )
    n = con.execute("SELECT COUNT(*) FROM absence_episodes").fetchone()[0]
    print(f"[absences] {n} episodes (>={min_weeks} weeks)")


def _apply_injury_list_to_availability(con: duckdb.DuckDBPyConnection) -> None:
    """Players on official injury list who missed AFL → injured (current snapshots)."""
    con.execute(
        """
        WITH round_dates AS (
            SELECT season, round, MIN(match_date) AS round_date
            FROM player_games
            WHERE round > 0
            GROUP BY 1, 2
        ),
        injury_rounds AS (
            SELECT
                i.*,
                rd.round AS target_round,
                ROW_NUMBER() OVER (
                    PARTITION BY i.list_date, i.team, i.player_name_norm
                    ORDER BY ABS(rd.round_date - i.list_date)
                ) AS rn
            FROM injury_list_entries i
            JOIN round_dates rd
                ON rd.season = EXTRACT(YEAR FROM i.list_date)
               AND rd.round_date BETWEEN i.list_date - INTERVAL 3 DAY
                                     AND i.list_date + INTERVAL 10 DAY
        )
        UPDATE availability a
        SET
            status = CASE
                WHEN ir.is_injury THEN 'injured'
                ELSE a.status
            END,
            absence_reason = CASE
                WHEN ir.is_injury THEN 'injury'
                WHEN LOWER(ir.injury_type) LIKE '%suspension%' THEN 'suspension'
                ELSE 'listed'
            END,
            injury_type = ir.injury_type,
            injury_category = ir.injury_category
        FROM injury_rounds ir
        WHERE ir.rn = 1
          AND NOT a.afl_played
          AND a.team = ir.team
          AND a.season = EXTRACT(YEAR FROM ir.list_date)
          AND a.round = ir.target_round
          AND (
              (ir.player_id IS NOT NULL AND a.player_id = ir.player_id)
              OR LOWER(a.player_name) = ir.player_name_norm
              OR LOWER(regexp_extract(a.player_name, ' ([^ ]+)$', 1))
                  = LOWER(regexp_extract(ir.player_name, ' ([^ ]+)$', 1))
          )
          AND a.status NOT IN ('vfl_only', 'intermittent')
        """
    )


def _label_episodes_from_injury_list(con: duckdb.DuckDBPyConnection) -> None:
    """Best-effort injury type on episodes when list entry overlaps episode start."""
    con.execute(
        """
        UPDATE absence_episodes e
        SET
            absence_reason = CASE WHEN i.is_injury THEN 'injury' ELSE e.absence_reason END,
            injury_type = COALESCE(e.injury_type, i.injury_type),
            injury_category = COALESCE(e.injury_category, i.injury_category),
            source = 'injury_list_match',
            confidence = 'medium'
        FROM injury_list_entries i
        INNER JOIN (
            SELECT season, round, MIN(match_date) AS round_date
            FROM player_games
            WHERE round > 0
            GROUP BY 1, 2
        ) rd
            ON rd.season = EXTRACT(YEAR FROM i.list_date)
        WHERE e.team = i.team
          AND e.season = rd.season
          AND e.start_round = rd.round
          AND (
              (i.player_id IS NOT NULL AND e.player_id = i.player_id)
              OR LOWER(e.player_name) = i.player_name_norm
          )
          AND i.list_date BETWEEN rd.round_date - INTERVAL 14 DAY
                              AND rd.round_date + INTERVAL 14 DAY
          AND e.absence_reason = 'unclear'
        """
    )


def _propagate_episode_labels_to_rounds(con: duckdb.DuckDBPyConnection) -> None:
    """Copy episode-level injury labels onto member rounds (where still unclear)."""
    con.execute(
        """
        UPDATE availability a
        SET
            status = CASE
                WHEN e.absence_reason = 'injury' THEN 'injured'
                ELSE a.status
            END,
            absence_reason = e.absence_reason,
            injury_type = e.injury_type,
            injury_category = e.injury_category
        FROM absence_episodes e
        WHERE a.player_id = e.player_id
          AND a.team = e.team
          AND a.season = e.season
          AND a.round BETWEEN e.start_round AND e.end_round
          AND NOT a.afl_played
          AND a.status NOT IN ('vfl_only', 'intermittent')
          AND COALESCE(a.absence_reason, 'unclear') IN ('unclear', 'listed')
          AND e.absence_reason = 'injury'
          AND e.injury_type IS NOT NULL
        """
    )


def _mark_sanfl_gaps_unclear(con: duckdb.DuckDBPyConnection) -> None:
    """Adelaide/Port unavailable weeks with no reason → unclear (SANFL gap years)."""
    con.execute(
        """
        UPDATE availability a
        SET
            status = 'unclear',
            absence_reason = 'unclear'
        WHERE a.team IN ('Adelaide', 'Port Adelaide')
          AND a.season IN (2021, 2022, 2023, 2025)
          AND NOT a.afl_played
          AND COALESCE(a.vfl_played, FALSE) = FALSE
          AND a.status IN ('unavailable')
          AND a.absence_reason IS NULL
        """
    )


def enrich_absence_reasons(con: duckdb.DuckDBPyConnection) -> None:
    """Full absence enrichment pass (run after vfl + intermittent)."""
    _reset_absence_columns(con)
    build_absence_episodes(con)
    injury_count = con.execute("SELECT COUNT(*) FROM injury_list_entries").fetchone()[0]
    if injury_count:
        _apply_injury_list_to_availability(con)
        _label_episodes_from_injury_list(con)
        _propagate_episode_labels_to_rounds(con)
    _mark_sanfl_gaps_unclear(con)

    summary = con.execute(
        """
        SELECT status, absence_reason, COUNT(*) AS n
        FROM availability
        WHERE NOT afl_played
        GROUP BY 1, 2
        ORDER BY n DESC
        """
    ).df()
    print("[absences] availability breakdown (missed AFL):")
    for _, row in summary.iterrows():
        print(f"  {row['status']}/{row['absence_reason']}: {row['n']}")
