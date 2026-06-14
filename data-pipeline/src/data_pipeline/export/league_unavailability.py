"""League-wide unavailability summary + per-club player ratings."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import duckdb
import pandas as pd

from ..config import DB_PATH, ROOT

PLAYER_RATINGS_SQL = """
SELECT
    v.player_id,
    p.player_name,
    p.age_est,
    p.draft_pick,
    p.archetype,
    v.games AS games_played_afl,
    ROUND(v.performance_score, 3) AS performance_score,
    ROUND(v.potential_score, 3) AS potential_score,
    ROUND(v.age_perf_weight, 3) AS age_performance_weight,
    ROUND(v.pvs, 3) AS player_value_score,
    COUNT(*) FILTER (WHERE NOT a.afl_played) AS rounds_missed,
    COUNT(*) FILTER (WHERE a.afl_played) AS rounds_played,
    COUNT(*) FILTER (WHERE a.status = 'unavailable') AS rounds_unavailable,
    COUNT(*) FILTER (WHERE a.status = 'vfl_only') AS rounds_vfl_only,
    COUNT(*) FILTER (WHERE a.status = 'intermittent') AS rounds_intermittent,
    ROUND(
        SUM(CASE WHEN a.status IN ('unavailable', 'intermittent') THEN v.pvs ELSE 0 END),
        2
    ) AS pvs_games_missed,
    ROUND(SUM(CASE WHEN NOT a.afl_played THEN v.pvs ELSE 0 END), 2) AS pvs_rounds_lost
FROM player_value v
JOIN player_profiles p
    ON v.player_id = p.player_id AND v.team = p.team AND v.season = p.season
LEFT JOIN availability a
    ON v.player_id = a.player_id AND v.team = a.team AND v.season = a.season
WHERE v.team = ? AND v.season = ?
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
ORDER BY player_value_score DESC
"""

TEAM_SUMMARY_SQL = """
WITH player_absences AS (
    SELECT
        a.team,
        COUNT(*) FILTER (WHERE NOT a.afl_played) AS player_rounds_lost,
        ROUND(SUM(CASE WHEN NOT a.afl_played THEN v.pvs ELSE 0 END), 1) AS total_pvs_lost,
        ROUND(AVG(CASE WHEN NOT a.afl_played THEN v.pvs END), 3) AS avg_pvs_per_lost_round,
        COUNT(*) FILTER (WHERE a.status = 'vfl_only') AS vfl_only_rounds,
        ROUND(SUM(CASE WHEN a.status = 'vfl_only' THEN v.pvs ELSE 0 END), 1) AS pvs_lost_vfl_only,
        COUNT(*) FILTER (WHERE a.status = 'intermittent') AS intermittent_rounds,
        ROUND(SUM(CASE WHEN a.status = 'intermittent' THEN v.pvs ELSE 0 END), 1) AS pvs_lost_intermittent,
        COUNT(*) FILTER (WHERE a.status = 'unavailable') AS unavailable_rounds,
        ROUND(SUM(CASE WHEN a.status = 'unavailable' THEN v.pvs ELSE 0 END), 1) AS pvs_lost_unavailable,
        ROUND(
            SUM(CASE WHEN a.status IN ('unavailable', 'intermittent') THEN v.pvs ELSE 0 END),
            1
        ) AS pvs_lost_games_missed,
        COUNT(DISTINCT a.player_id) FILTER (WHERE NOT a.afl_played) AS players_with_absences
    FROM availability a
    JOIN player_value v
        ON a.player_id = v.player_id AND a.team = v.team AND a.season = v.season
    WHERE a.season = ?
    GROUP BY a.team
),
round_totals AS (
    SELECT team, ROUND(SUM(unavailable_pvs_games_missed), 1) AS team_round_pvs_sum
    FROM team_round_value
    WHERE season = ?
    GROUP BY team
)
SELECT p.*, r.team_round_pvs_sum
FROM player_absences p
LEFT JOIN round_totals r ON p.team = r.team
ORDER BY p.total_pvs_lost DESC
"""


def _sheet_name(team: str, used: set[str]) -> str:
    base = re.sub(r"[^\w\s]", "", team)[:25].strip() or "Team"
    name = base
    n = 2
    while name in used:
        suffix = f"_{n}"
        name = base[: 31 - len(suffix)] + suffix
        n += 1
    used.add(name)
    return name


def export_league_unavailability(season: int, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or ROOT / "shared" / "output" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    team_summary = con.execute(TEAM_SUMMARY_SQL, [season, season]).df()
    teams = team_summary["team"].tolist()

    notes = pd.DataFrame(
        {
            "field": [
                "player_rounds_lost",
                "total_pvs_lost",
                "team_round_pvs_sum",
                "pvs_games_missed (player tab)",
                "pvs_rounds_lost (player tab)",
                "rounds_vfl_only",
            ],
            "description": [
                "Count of player × round absences (squad member did not play AFL).",
                "Sum of PVS for every round a player did not play AFL (includes VFL-only weeks).",
                "Season sum of per-round games-missed PVS (unavailable + intermittent only; excludes VFL-only).",
                "Player-season PVS on rounds with no AFL and status unavailable or intermittent.",
                "Player-season PVS on all rounds without AFL (includes VFL-only reserves weeks).",
                "Missed AFL but played state league for the affiliated side.",
            ],
        }
    )

    path = out_dir / f"league_{season}_pvs_lost_by_team.xlsx"
    used_names: set[str] = {"Team summary", "Notes"}
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        team_summary.to_excel(writer, sheet_name="Team summary", index=False)
        notes.to_excel(writer, sheet_name="Notes", index=False)
        for team in teams:
            ratings = con.execute(PLAYER_RATINGS_SQL, [team, season]).df()
            sheet = _sheet_name(team, used_names)
            ratings.to_excel(writer, sheet_name=sheet, index=False)

    con.close()
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export league PVS lost by team")
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    print(export_league_unavailability(args.season, args.out))


if __name__ == "__main__":
    main()
