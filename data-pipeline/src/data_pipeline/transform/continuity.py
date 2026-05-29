"""Lineup continuity by positional archetype."""

from __future__ import annotations

import duckdb

from .archetypes import ARCHETYPE_LABELS


def build_archetype_continuity(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DELETE FROM archetype_continuity")
    con.execute(
        """
        INSERT INTO archetype_continuity
        WITH played AS (
            SELECT
                a.team,
                a.season,
                a.round,
                p.archetype,
                a.player_id
            FROM availability a
            JOIN player_profiles p
                ON a.player_id = p.player_id
                AND a.team = p.team
                AND a.season = p.season
            WHERE a.afl_played
        ),
        round_pairs AS (
            SELECT
                cur.team,
                cur.season,
                cur.round,
                cur.archetype,
                COUNT(DISTINCT cur.player_id) AS current_players,
                COUNT(DISTINCT prev.player_id) AS returning_players
            FROM played cur
            LEFT JOIN played prev
                ON cur.team = prev.team
                AND cur.season = prev.season
                AND cur.round = prev.round + 1
                AND cur.archetype = prev.archetype
                AND cur.player_id = prev.player_id
            WHERE cur.round > 0
            GROUP BY 1, 2, 3, 4
        )
        SELECT
            team,
            season,
            archetype,
            AVG(current_players - returning_players) AS avg_changes,
            AVG(returning_players::DOUBLE / NULLIF(current_players, 0)) AS continuity_score
        FROM round_pairs
        GROUP BY 1, 2, 3
        """
    )


def continuity_for_season(
    con: duckdb.DuckDBPyConnection, season: int, team: str | None = None
) -> list[dict]:
    query = """
        SELECT archetype, AVG(avg_changes) AS changes, AVG(continuity_score) AS score
        FROM archetype_continuity
        WHERE season = ?
    """
    params: list = [season]
    if team:
        query += " AND team = ?"
        params.append(team)
    query += " GROUP BY archetype ORDER BY score DESC"

    rows = con.execute(query, params).df()
    return [
        {
            "archetype": ARCHETYPE_LABELS.get(row["archetype"], row["archetype"]),
            "changes": int(round(row["changes"])),
            "score": round(float(row["score"]), 2),
        }
        for _, row in rows.iterrows()
    ]
