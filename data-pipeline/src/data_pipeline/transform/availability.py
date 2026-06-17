"""Derive player availability from AFL participation (Phase 1)."""

from __future__ import annotations

import duckdb


def build_availability(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DELETE FROM squad_players")
    con.execute(
        """
        INSERT INTO squad_players
        WITH from_games AS (
            SELECT
                player_id,
                MAX(player_name) AS player_name,
                team,
                season,
                COUNT(DISTINCT round) AS games_played
            FROM player_games
            GROUP BY 1, 3, 4
        ),
        carry_forward AS (
            SELECT
                pg.player_id,
                MAX(pg.player_name) AS player_name,
                pg.team,
                pg.season + 1 AS season,
                0 AS games_played
            FROM player_games pg
            WHERE EXISTS (
                SELECT 1 FROM matches m WHERE m.season = pg.season + 1
            )
            GROUP BY pg.player_id, pg.team, pg.season
            HAVING COUNT(DISTINCT pg.round) >= 5
        ),
        combined AS (
            SELECT player_id, player_name, team, season, games_played FROM from_games
            UNION ALL
            SELECT cf.player_id, cf.player_name, cf.team, cf.season, cf.games_played
            FROM carry_forward cf
            WHERE NOT EXISTS (
                SELECT 1 FROM from_games g
                WHERE LOWER(g.player_name) = LOWER(cf.player_name)
                  AND g.team = cf.team
                  AND g.season = cf.season
            )
        )
        SELECT
            COALESCE(
                MAX(CASE WHEN games_played > 0 THEN player_id END),
                MAX(player_id)
            ) AS player_id,
            MAX(player_name) AS player_name,
            team,
            season,
            MAX(games_played) AS games_played
        FROM combined
        GROUP BY LOWER(player_name), team, season
        """
    )

    con.execute("DELETE FROM availability")
    con.execute(
        """
        INSERT INTO availability
        WITH home_away_rounds AS (
            -- Home-and-away weeks only (exclude Opening Round 0 and finals blocks).
            SELECT season, round
            FROM matches
            WHERE round > 0
            GROUP BY season, round
            HAVING COUNT(*) > 4
        ),
        team_rounds AS (
            SELECT m.season, m.round, m.home_team AS team
            FROM matches m
            INNER JOIN home_away_rounds r
                ON m.season = r.season AND m.round = r.round
            UNION
            SELECT m.season, m.round, m.away_team AS team
            FROM matches m
            INNER JOIN home_away_rounds r
                ON m.season = r.season AND m.round = r.round
        ),
        carried_forward AS (
            SELECT DISTINCT s.player_id, s.team, s.season
            FROM squad_players s
            WHERE EXISTS (
                SELECT 1
                FROM player_games pg
                WHERE LOWER(pg.player_name) = LOWER(s.player_name)
                  AND pg.team = s.team
                  AND pg.season = s.season - 1
                GROUP BY pg.player_id
                HAVING COUNT(DISTINCT pg.round) >= 5
            )
        ),
        debut AS (
            SELECT player_id, team, season, MIN(round) AS debut_round
            FROM player_games
            GROUP BY 1, 2, 3
        ),
        squad_rounds AS (
            SELECT s.player_id, s.player_name, s.team, s.season, tr.round
            FROM squad_players s
            INNER JOIN team_rounds tr
                ON s.team = tr.team AND s.season = tr.season
            LEFT JOIN debut d
                ON s.player_id = d.player_id
                AND s.team = d.team
                AND s.season = d.season
            LEFT JOIN carried_forward cf
                ON s.player_id = cf.player_id
                AND s.team = cf.team
                AND s.season = cf.season
            WHERE tr.round >= CASE
                WHEN cf.player_id IS NOT NULL THEN 1
                ELSE COALESCE(d.debut_round, 1)
            END
        ),
        played AS (
            SELECT DISTINCT player_id, team, season, round
            FROM player_games
        )
        SELECT
            sr.player_id,
            sr.player_name,
            sr.team,
            sr.season,
            sr.round,
            CASE
                WHEN p.player_id IS NOT NULL THEN 'afl_played'
                ELSE 'unavailable'
            END AS status,
            p.player_id IS NOT NULL AS afl_played,
            CAST(NULL AS BOOLEAN) AS vfl_played,
            CAST(NULL AS VARCHAR) AS absence_reason,
            CAST(NULL AS VARCHAR) AS injury_type,
            CAST(NULL AS VARCHAR) AS injury_category
        FROM squad_rounds sr
        LEFT JOIN played p
            ON sr.player_id = p.player_id
            AND sr.team = p.team
            AND sr.season = p.season
            AND sr.round = p.round
        """
    )

    con.execute("DELETE FROM team_round_summary")
    con.execute(
        """
        INSERT INTO team_round_summary
        WITH avail AS (
            SELECT
                team,
                season,
                round,
                COUNT(*) AS squad_size,
                SUM(CASE WHEN afl_played THEN 1 ELSE 0 END) AS players_played,
                SUM(CASE WHEN NOT afl_played THEN 1 ELSE 0 END) AS players_unavailable
            FROM availability
            GROUP BY 1, 2, 3
        ),
        match_results AS (
            SELECT
                season,
                round,
                team,
                MAX(CASE WHEN winner_team = team THEN 1 ELSE 0 END) = 1 AS won
            FROM (
                SELECT season, round, home_team AS team, winner_team
                FROM matches
                UNION ALL
                SELECT season, round, away_team AS team, winner_team
                FROM matches
            ) mr
            GROUP BY 1, 2, 3
        )
        SELECT
            a.team,
            a.season,
            a.round,
            a.squad_size,
            a.players_played,
            a.players_unavailable,
            a.players_unavailable::DOUBLE / NULLIF(a.squad_size, 0) AS unavailable_rate,
            0.0 AS unavailable_pvs_total,
            0.0 AS unavailable_pvs_top5,
            mr.won
        FROM avail a
        LEFT JOIN match_results mr
            ON a.team = mr.team
            AND a.season = mr.season
            AND a.round = mr.round
        """
    )
