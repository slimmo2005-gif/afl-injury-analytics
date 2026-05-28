"""Derive player availability from AFL participation (Phase 1)."""

from __future__ import annotations

import duckdb


def build_availability(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DELETE FROM squad_players")
    con.execute(
        """
        INSERT INTO squad_players
        SELECT
            player_id,
            MAX(player_name) AS player_name,
            team,
            season,
            COUNT(DISTINCT round) AS games_played
        FROM player_games
        GROUP BY 1, 3, 4
        """
    )

    con.execute("DELETE FROM availability")
    con.execute(
        """
        INSERT INTO availability
        WITH rounds AS (
            SELECT DISTINCT season, round FROM player_games
        ),
        squad_rounds AS (
            SELECT s.player_id, s.player_name, s.team, s.season, r.round
            FROM squad_players s
            JOIN rounds r ON s.season = r.season
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
            CAST(NULL AS BOOLEAN) AS vfl_played
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
            SELECT season, round, home_team AS team, winner_team
            FROM matches
            UNION ALL
            SELECT season, round, away_team AS team, winner_team
            FROM matches
        )
        SELECT
            a.team,
            a.season,
            a.round,
            a.squad_size,
            a.players_played,
            a.players_unavailable,
            a.players_unavailable::DOUBLE / NULLIF(a.squad_size, 0) AS unavailable_rate,
            mr.winner_team = a.team AS won
        FROM avail a
        LEFT JOIN match_results mr
            ON a.team = mr.team
            AND a.season = mr.season
            AND a.round = mr.round
        """
    )
