"""Ladder rank vs fewest PVS-lost rank by club and season."""

from __future__ import annotations

import duckdb

from ..transform.unavailability import GAMES_MISSED_STATUS_SQL
from .official_ladder import OFFICIAL_LADDER_FROM, OFFICIAL_LADDER_TO, load_official_ladders

WINDOW_YEARS = 5

_COMPUTED_LADDER_SQL = f"""
WITH ha_rounds AS (
    SELECT season, round
    FROM matches
    WHERE round > 0 AND round <= 24
    GROUP BY season, round
    HAVING COUNT(*) > 4
),
team_results AS (
    SELECT m.season, m.home_team AS team,
           CASE WHEN m.winner_team = m.home_team THEN 1 ELSE 0 END AS won,
           CASE WHEN m.home_score = m.away_score THEN 1 ELSE 0 END AS drew,
           m.home_score AS pf, m.away_score AS pa
    FROM matches m
    INNER JOIN ha_rounds r ON m.season = r.season AND m.round = r.round
    UNION ALL
    SELECT m.season, m.away_team,
           CASE WHEN m.winner_team = m.away_team THEN 1 ELSE 0 END,
           CASE WHEN m.home_score = m.away_score THEN 1 ELSE 0 END,
           m.away_score, m.home_score
    FROM matches m
    INNER JOIN ha_rounds r ON m.season = r.season AND m.round = r.round
),
ladder AS (
    SELECT
        team,
        season,
        SUM(won) AS wins,
        SUM(drew) AS draws,
        SUM(won) * 4 + SUM(drew) * 2 AS premiership_points,
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
        draws,
        premiership_points,
        percentage,
        RANK() OVER (
            PARTITION BY season
            ORDER BY premiership_points DESC, percentage DESC, points_for DESC
        ) AS ladder_rank
    FROM ladder
)
SELECT team, season, wins, percentage, ladder_rank
FROM ladder_ranked
ORDER BY team, season
"""

_PVS_LOST_SQL = f"""
SELECT
    a.team,
    a.season,
    ROUND(
        SUM(
            CASE
                WHEN NOT a.afl_played
                     AND a.status IN {GAMES_MISSED_STATUS_SQL}
                THEN COALESCE(v.injury_weight_pvs, v.pvs)
                ELSE 0
            END
        ),
        1
    ) AS pvs_lost
FROM availability a
JOIN player_value v
    ON a.player_id = v.player_id
    AND a.team = v.team
    AND a.season = v.season
GROUP BY a.team, a.season
"""


def _apply_official_ladder(
    computed: dict[tuple[str, int], dict],
    official: dict[int, dict[str, dict[str, int | float]]],
) -> dict[tuple[str, int], dict]:
    """Override computed ladder rows with Squiggle official standings."""
    merged = dict(computed)
    for season, by_team in official.items():
        for team, row in by_team.items():
            key = (team, season)
            base = merged.get(key, {"team": team, "season": season})
            merged[key] = {
                **base,
                "ladder_rank": int(row["ladder_rank"]),
                "wins": int(row["wins"]),
                "draws": int(row["draws"]),
                "percentage": float(row["percentage"]),
            }
    return merged


def build_ladder_pvs_ranks_bundle(con: duckdb.DuckDBPyConnection) -> dict:
    """Per-club season ranks: ladder position vs PVS games-missed rank."""
    computed_rows = con.execute(_COMPUTED_LADDER_SQL).fetchall()
    computed: dict[tuple[str, int], dict] = {}
    for team, season, wins, pct, ladder_rank in computed_rows:
        computed[(team, int(season))] = {
            "team": team,
            "season": int(season),
            "wins": int(wins),
            "percentage": round(float(pct), 1),
            "ladder_rank": int(ladder_rank),
        }

    try:
        official = load_official_ladders(OFFICIAL_LADDER_FROM, OFFICIAL_LADDER_TO)
        ladder_by_key = _apply_official_ladder(computed, official)
    except Exception as exc:
        print(f"[ladder] warning: using computed ladder only: {exc}")
        ladder_by_key = computed

    pvs_rows = con.execute(_PVS_LOST_SQL).fetchall()
    pvs_by_key: dict[tuple[str, int], float] = {
        (team, int(season)): float(pvs_lost) for team, season, pvs_lost in pvs_rows
    }

    seasons = sorted({key[1] for key in ladder_by_key} | {key[1] for key in pvs_by_key})
    pvs_ranks: dict[tuple[str, int], int] = {}
    for season in seasons:
        teams_pvs = [
            (team, pvs_by_key[(team, season)])
            for team in {t for t, s in pvs_by_key if s == season}
        ]
        teams_pvs.sort(key=lambda x: (x[1], x[0]))
        for rank, (team, _) in enumerate(teams_pvs, start=1):
            pvs_ranks[(team, season)] = rank

    by_club: dict[str, list[dict]] = {}
    clubs: set[str] = set()
    for (team, season), ladder in sorted(ladder_by_key.items()):
        if (team, season) not in pvs_by_key:
            continue
        pvs_lost = pvs_by_key[(team, season)]
        pvs_lost_rank = pvs_ranks[(team, season)]
        ladder_rank = ladder["ladder_rank"]
        rank_delta = ladder_rank - pvs_lost_rank
        clubs.add(team)
        by_club.setdefault(team, []).append(
            {
                "season": season,
                "ladderRank": ladder_rank,
                "pvsLostRank": pvs_lost_rank,
                "rankDelta": rank_delta,
                "wins": ladder["wins"],
                "percentage": ladder["percentage"],
                "pvsLost": pvs_lost,
            }
        )

    return {
        "windowYears": WINDOW_YEARS,
        "clubs": sorted(clubs),
        "byClub": by_club,
        "interpretation": (
            "Ladder rank from official end-of-home-and-away standings (Squiggle / AFL) for "
            f"{OFFICIAL_LADDER_FROM}–{OFFICIAL_LADDER_TO}, otherwise premiership points from "
            "match results. PVS-lost rank sorts clubs by season games-missed PVS (rank 1 = fewest lost). "
            "Injury weights use injury_weight_pvs for players with fewer than 14 games played. "
            "Rank delta = ladder rank − PVS-lost rank: negative means the club finished higher on "
            "the ladder than its injury toll would suggest; positive means they finished lower."
        ),
    }
