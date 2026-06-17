"""Export in-progress current season metrics for a separate frontend page."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from ..config import CURRENT_SEASON, FRONTEND_DATA, SHARED_OUTPUT
from ..transform.unavailability import GAMES_MISSED_STATUS_SQL
from .frontend import build_season_bundle
from .official_ladder import current_ladder_by_team, latest_completed_round


def _current_ladder_pvs_snapshot(
    con: duckdb.DuckDBPyConnection,
    season: int,
    ladder_round: int,
    official: dict[str, dict[str, int | float]],
) -> dict:
    pvs_rows = con.execute(
        f"""
        SELECT a.team,
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
        WHERE a.season = ?
          AND a.round <= ?
        GROUP BY a.team
        """,
        [season, ladder_round],
    ).fetchall()
    pvs_by_team = {team: float(pvs) for team, pvs in pvs_rows}
    teams_pvs = sorted(pvs_by_team.items(), key=lambda x: (x[1], x[0]))
    pvs_rank = {team: rank for rank, (team, _) in enumerate(teams_pvs, start=1)}

    clubs = []
    by_club: dict[str, list[dict]] = {}
    for team, ladder in sorted(official.items()):
        pvs_lost = pvs_by_team.get(team, 0.0)
        pvs_lost_rank = pvs_rank.get(team, 18)
        ladder_rank = int(ladder["ladder_rank"])
        entry = {
            "season": season,
            "ladderRank": ladder_rank,
            "pvsLostRank": pvs_lost_rank,
            "rankDelta": ladder_rank - pvs_lost_rank,
            "wins": int(ladder["wins"]),
            "percentage": float(ladder["percentage"]),
            "pvsLost": pvs_lost,
        }
        clubs.append({"club": team, **entry})
        by_club.setdefault(team, []).append(entry)

    clubs.sort(key=lambda x: x["ladderRank"])
    return {
        "ladderRound": ladder_round,
        "clubs": clubs,
        "byClub": by_club,
        "interpretation": (
            f"Through round {ladder_round} of {season}. Ladder from Squiggle; "
            "PVS-lost rank uses season-to-date injury-counted games-missed PVS."
        ),
    }


def build_current_season_bundle(
    con: duckdb.DuckDBPyConnection,
    season: int = CURRENT_SEASON,
) -> dict:
    ladder_round, official = current_ladder_by_team(season, con=con)
    season_data = build_season_bundle(con, season, max_round=ladder_round)

    # Override club rankings wins with official ladder through current round.
    for row in season_data["clubRankings"]:
        club = row["club"]
        if club in official:
            row["actualWins"] = int(official[club]["wins"])

    snapshot = _current_ladder_pvs_snapshot(con, season, ladder_round, official)

    return {
        "meta": {
            "season": season,
            "round": ladder_round,
            "ladderRound": ladder_round,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "note": f"{season} season to date — in progress",
            "dataSource": "Squiggle + AFL.com API + VFL + injury lists",
            "isPartialSeason": True,
            "historicalWindow": "2021–2025",
        },
        **season_data,
        "currentLadderPvs": snapshot,
    }


def write_current_season(
    con: duckdb.DuckDBPyConnection,
    season: int = CURRENT_SEASON,
    out_dir: Path | None = None,
) -> Path:
    bundle = build_current_season_bundle(con, season=season)
    targets = [out_dir or SHARED_OUTPUT, FRONTEND_DATA]
    written: Path | None = None
    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        path = target / "currentSeason.json"
        path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        written = path
    assert written is not None
    max_round = latest_completed_round(con, season)
    print(f"[export] current season {season} through R{max_round} -> {written}")
    return written
