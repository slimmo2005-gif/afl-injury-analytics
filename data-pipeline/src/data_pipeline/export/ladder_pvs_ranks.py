"""Ladder rank vs fewest PVS-lost rank by club and season."""

from __future__ import annotations

import duckdb

WINDOW_YEARS = 5


def build_ladder_pvs_ranks_bundle(con: duckdb.DuckDBPyConnection) -> dict:
    """Per-club season ranks: ladder position vs PVS games-missed rank."""
    rows = con.execute(
        """
        WITH ha_rounds AS (
            SELECT season, round
            FROM matches
            WHERE round > 0
            GROUP BY season, round
            HAVING COUNT(*) > 4
        ),
        team_results AS (
            SELECT m.season, m.home_team AS team,
                   CASE WHEN m.winner_team = m.home_team THEN 1 ELSE 0 END AS won,
                   m.home_score AS pf, m.away_score AS pa
            FROM matches m
            INNER JOIN ha_rounds r ON m.season = r.season AND m.round = r.round
            UNION ALL
            SELECT m.season, m.away_team,
                   CASE WHEN m.winner_team = m.away_team THEN 1 ELSE 0 END,
                   m.away_score, m.home_score
            FROM matches m
            INNER JOIN ha_rounds r ON m.season = r.season AND m.round = r.round
        ),
        ladder AS (
            SELECT
                team,
                season,
                SUM(won) AS wins,
                SUM(pf) AS points_for,
                SUM(pa) AS points_against,
                CASE WHEN SUM(pa) > 0 THEN 100.0 * SUM(pf) / SUM(pa) ELSE 0 END AS percentage
            FROM team_results
            GROUP BY team, season
        ),
        ladder_ranked AS (
            SELECT
                team,
                season,
                wins,
                points_for,
                points_against,
                percentage,
                RANK() OVER (
                    PARTITION BY season
                    ORDER BY wins DESC, percentage DESC, points_for DESC
                ) AS ladder_rank
            FROM ladder
        ),
        pvs_lost AS (
            SELECT
                team,
                season,
                ROUND(SUM(unavailable_pvs_games_missed), 1) AS pvs_lost
            FROM team_round_value
            GROUP BY team, season
        ),
        pvs_ranked AS (
            SELECT
                team,
                season,
                pvs_lost,
                RANK() OVER (
                    PARTITION BY season
                    ORDER BY pvs_lost ASC, team ASC
                ) AS pvs_lost_rank
            FROM pvs_lost
        )
        SELECT
            l.team,
            l.season,
            l.wins,
            l.percentage,
            l.ladder_rank,
            p.pvs_lost,
            p.pvs_lost_rank,
            l.ladder_rank - p.pvs_lost_rank AS rank_delta
        FROM ladder_ranked l
        JOIN pvs_ranked p ON l.team = p.team AND l.season = p.season
        ORDER BY l.team, l.season
        """
    ).fetchall()

    by_club: dict[str, list[dict]] = {}
    clubs: set[str] = set()
    for team, season, wins, pct, ladder_rank, pvs_lost, pvs_lost_rank, rank_delta in rows:
        clubs.add(team)
        by_club.setdefault(team, []).append(
            {
                "season": int(season),
                "ladderRank": int(ladder_rank),
                "pvsLostRank": int(pvs_lost_rank),
                "rankDelta": int(rank_delta),
                "wins": int(wins),
                "percentage": round(float(pct), 1),
                "pvsLost": float(pvs_lost),
            }
        )

    return {
        "windowYears": WINDOW_YEARS,
        "clubs": sorted(clubs),
        "byClub": by_club,
        "interpretation": (
            "Ladder rank from home-and-away wins and percentage. PVS-lost rank sorts clubs "
            "by season games-missed PVS (rank 1 = fewest lost). Rank delta = ladder rank − "
            "PVS-lost rank: negative means the club finished higher on the ladder than its "
            "injury toll would suggest; positive means they finished lower."
        ),
    }
