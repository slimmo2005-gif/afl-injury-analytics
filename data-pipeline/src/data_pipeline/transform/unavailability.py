"""PVS-weighted team-round unavailability metrics."""

from __future__ import annotations

import duckdb


def enrich_availability_status(con: duckdb.DuckDBPyConnection) -> None:
    """Classify intermittent absences (played recently but not this round)."""
    con.execute(
        """
        UPDATE availability a
        SET status = 'intermittent'
        WHERE NOT a.afl_played
          AND COALESCE(a.vfl_played, FALSE) = FALSE
          AND (
              SELECT COUNT(*)
              FROM availability a2
              WHERE a2.player_id = a.player_id
                AND a2.team = a.team
                AND a2.season = a.season
                AND a2.round BETWEEN a.round - 4 AND a.round - 1
                AND a2.afl_played
          ) >= 2
        """
    )
    con.execute(
        """
        UPDATE availability
        SET status = 'unavailable'
        WHERE NOT afl_played
          AND COALESCE(status, 'unavailable') NOT IN ('intermittent', 'vfl_only')
        """
    )


def build_team_round_value(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DELETE FROM team_round_value")
    con.execute(
        """
        INSERT INTO team_round_value
        WITH unavail AS (
            SELECT
                a.team,
                a.season,
                a.round,
                a.player_id,
                a.status,
                v.pvs,
                p.age_est,
                p.archetype
            FROM availability a
            JOIN player_value v
                ON a.player_id = v.player_id
                AND a.team = v.team
                AND a.season = v.season
            JOIN player_profiles p
                ON a.player_id = p.player_id
                AND a.team = p.team
                AND a.season = p.season
            WHERE NOT a.afl_played
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY team, season, round
                    ORDER BY pvs DESC
                ) AS pvs_rank
            FROM unavail
        ),
        agg AS (
            SELECT
                team,
                season,
                round,
                SUM(pvs) AS unavailable_pvs_total,
                SUM(CASE WHEN pvs_rank <= 5 THEN pvs ELSE 0 END) AS unavailable_pvs_top5,
                SUM(CASE WHEN pvs_rank <= 10 THEN pvs ELSE 0 END) AS unavailable_pvs_top10,
                SUM(CASE WHEN age_est < 22 THEN pvs ELSE 0 END) AS unavailable_pvs_u22,
                SUM(CASE WHEN age_est >= 28 THEN pvs ELSE 0 END) AS unavailable_pvs_28plus,
                SUM(CASE WHEN status = 'intermittent' THEN pvs ELSE 0 END) AS unavailable_pvs_intermittent,
                SUM(CASE WHEN status = 'vfl_only' THEN pvs ELSE 0 END) AS unavailable_pvs_vfl_only,
                SUM(
                    CASE WHEN status IN ('unavailable', 'intermittent') THEN pvs ELSE 0 END
                ) AS unavailable_pvs_games_missed
            FROM ranked
            GROUP BY 1, 2, 3
        )
        SELECT
            tr.team,
            tr.season,
            tr.round,
            COALESCE(a.unavailable_pvs_total, 0) AS unavailable_pvs_total,
            COALESCE(a.unavailable_pvs_top5, 0) AS unavailable_pvs_top5,
            COALESCE(a.unavailable_pvs_top10, 0) AS unavailable_pvs_top10,
            COALESCE(a.unavailable_pvs_u22, 0) AS unavailable_pvs_u22,
            COALESCE(a.unavailable_pvs_28plus, 0) AS unavailable_pvs_28plus,
            COALESCE(a.unavailable_pvs_intermittent, 0) AS unavailable_pvs_intermittent,
            COALESCE(a.unavailable_pvs_vfl_only, 0) AS unavailable_pvs_vfl_only,
            COALESCE(a.unavailable_pvs_games_missed, 0) AS unavailable_pvs_games_missed,
            tr.won
        FROM team_round_summary tr
        LEFT JOIN agg a
            ON tr.team = a.team
            AND tr.season = a.season
            AND tr.round = a.round
        """
    )

    # Mirror PVS totals into team_round_summary for legacy queries
    con.execute(
        """
        UPDATE team_round_summary tr
        SET
            unavailable_pvs_total = v.unavailable_pvs_total,
            unavailable_pvs_top5 = v.unavailable_pvs_top5
        FROM team_round_value v
        WHERE tr.team = v.team
            AND tr.season = v.season
            AND tr.round = v.round
        """
    )
