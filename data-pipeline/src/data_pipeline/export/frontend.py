"""Export aggregated metrics JSON for the static frontend."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from ..config import DEFAULT_SEASON, FRONTEND_DATA, SHARED_OUTPUT


def _linear_regression(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    if len(x) < 3:
        return 0.0, 0.0, 0.0
    coef = np.polyfit(x, y, 1)
    slope, intercept = float(coef[0]), float(coef[1])
    pred = intercept + slope * x
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 0.0
    return intercept, slope, r2


def build_metrics_bundle(con: duckdb.DuckDBPyConnection, season: int = DEFAULT_SEASON) -> dict:
    club_season = con.execute(
        """
        SELECT
            team AS club,
            season,
            SUM(players_unavailable) AS unavailable_slots,
            SUM(CASE WHEN won THEN 1 ELSE 0 END) AS actual_wins,
            COUNT(*) AS rounds_with_data
        FROM team_round_summary
        WHERE season = ?
        GROUP BY team, season
        ORDER BY unavailable_slots DESC
        """,
        [season],
    ).df()

    if club_season.empty:
        raise ValueError(f"No team_round_summary data for season {season}")

    x = club_season["unavailable_slots"].to_numpy(dtype=float)
    y = club_season["actual_wins"].to_numpy(dtype=float)
    intercept, slope, r2 = _linear_regression(x, y)
    expected = intercept + slope * x
    club_season["expected_wins"] = expected.clip(min=0)
    club_season["delta"] = club_season["actual_wins"] - club_season["expected_wins"]

    avg_unavail = float(club_season["unavailable_slots"].mean() / club_season["rounds_with_data"].mean())
    above = int((club_season["delta"] > 0.5).sum())
    below = int((club_season["delta"] < -0.5).sum())
    corr = float(np.corrcoef(x, y)[0, 1]) if len(x) > 1 else 0.0

    default_club = club_season.iloc[0]["club"]
    if "Collingwood" in club_season["club"].values:
        default_club = "Collingwood"

    by_round = con.execute(
        """
        SELECT
            round,
            SUM(players_unavailable) AS value,
            MAX(CASE WHEN won THEN 1 ELSE 0 END) AS wins
        FROM team_round_summary
        WHERE season = ? AND team = ?
        GROUP BY round
        ORDER BY round
        """,
        [season, default_club],
    ).df()

    top_players = con.execute(
        """
        SELECT
            player_name AS player,
            team AS club,
            COUNT(*) FILTER (WHERE NOT afl_played) AS rounds_missed,
            COUNT(*) FILTER (WHERE afl_played) AS rounds_played
        FROM availability
        WHERE season = ?
        GROUP BY player_id, player_name, team
        HAVING rounds_missed > 0
        ORDER BY rounds_missed DESC
        LIMIT 10
        """,
        [season],
    ).df()

    continuity = con.execute(
        """
        WITH played AS (
            SELECT team, season, round, player_id
            FROM availability
            WHERE afl_played
        ),
        changes AS (
            SELECT
                a.team,
                a.season,
                a.round,
                COUNT(DISTINCT a.player_id) AS current_players,
                COUNT(DISTINCT b.player_id) AS returning_players
            FROM played a
            LEFT JOIN played b
                ON a.team = b.team
                AND a.season = b.season
                AND a.round = b.round + 1
                AND a.player_id = b.player_id
            WHERE a.round > 1
            GROUP BY a.team, a.season, a.round
        )
        SELECT
            team,
            AVG(current_players - returning_players) AS avg_changes,
            AVG(returning_players::DOUBLE / NULLIF(current_players, 0)) AS continuity_score
        FROM changes
        WHERE season = ?
        GROUP BY team
        ORDER BY avg_changes DESC
        LIMIT 5
        """,
        [season],
    ).df()

    continuity_rows = [
        {
            "archetype": row["team"],
            "changes": int(round(row["avg_changes"])),
            "score": round(float(row["continuity_score"]), 2),
        }
        for _, row in continuity.iterrows()
    ] or [
        {"archetype": "League avg", "changes": 0, "score": 0.0},
    ]

    player_rows = []
    for _, row in top_players.iterrows():
        missed = int(row["rounds_missed"])
        played = int(row["rounds_played"])
        if missed >= played and missed >= 3:
            status = "unavailable"
        elif missed >= 2:
            status = "intermittent"
        else:
            status = "vfl_only"
        player_rows.append(
            {
                "player": row["player"],
                "club": row["club"],
                "roundsMissed": missed,
                "pvs": round(min(9.5, 5.0 + missed * 0.4), 1),
                "status": status,
            }
        )

    return {
        "meta": {
            "season": season,
            "round": int(by_round["round"].max()) if not by_round.empty else 0,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "note": f"Phase 1 real data ({season}). PVS is provisional until Phase 2 model.",
            "dataSource": "Squiggle + Fryzigg",
        },
        "leagueOverview": {
            "avgUnavailableValue": round(avg_unavail, 1),
            "clubsAboveExpectation": above,
            "clubsBelowExpectation": below,
            "topUnavailableClub": str(club_season.iloc[0]["club"]),
            "correlationUnavailableToWins": round(corr, 2),
        },
        "clubUnavailableByRound": [
            {"round": int(r), "value": int(v), "wins": int(w)}
            for r, v, w in zip(by_round["round"], by_round["value"], by_round["wins"])
        ],
        "clubRankings": [
            {
                "club": row["club"],
                "unavailableValue": int(row["unavailable_slots"]),
                "expectedWins": round(float(row["expected_wins"]), 1),
                "actualWins": int(row["actual_wins"]),
                "delta": round(float(row["delta"]), 1),
            }
            for _, row in club_season.sort_values("club").iterrows()
        ],
        "topUnavailablePlayers": player_rows,
        "continuity": continuity_rows,
        "regression": {
            "model": "linear",
            "rSquared": round(r2, 2),
            "coefficients": {
                "intercept": round(intercept, 2),
                "unavailableSlots": round(slope, 4),
            },
            "interpretation": (
                f"Each +100 unavailable player-slots correlates with ~{abs(slope * 100):.1f} "
                f"{'fewer' if slope < 0 else 'more'} wins (season {season}, n={len(club_season)} clubs)."
            ),
        },
    }


def write_metrics(
    con: duckdb.DuckDBPyConnection,
    season: int = DEFAULT_SEASON,
    out_dir: Path | None = None,
) -> Path:
    bundle = build_metrics_bundle(con, season=season)
    targets = [out_dir or SHARED_OUTPUT, FRONTEND_DATA]
    written: Path | None = None
    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        path = target / "metrics.json"
        path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        written = path
    assert written is not None
    return written
