"""Diagnose club-average PVS — performance vs potential top-ups."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from ..config import DB_PATH, ROOT
from ..transform.pvs import POTENTIAL_BLEND_FACTOR, compute_pvs


def export_club_pvs_diagnosis(team: str, season: int, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or ROOT / "shared" / "output" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = team.lower().replace(" ", "_")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    players = con.execute(
        """
        SELECT
            g.player_name,
            p.age_est,
            p.draft_pick,
            ROUND(v.performance_score, 3) AS performance_score,
            ROUND(v.potential_score, 3) AS potential_score,
            ROUND(v.age_perf_weight, 3) AS age_weight,
            ROUND(v.pvs, 3) AS player_value_score,
            ROUND(v.pvs - v.performance_score, 3) AS potential_boost
        FROM player_value v
        JOIN player_profiles p USING (player_id, team, season)
        JOIN (
            SELECT player_id, MAX(player_name) AS player_name
            FROM player_games GROUP BY 1
        ) g ON v.player_id = g.player_id
        WHERE v.team = ? AND v.season = ?
        ORDER BY player_value_score DESC
        """,
        [team, season],
    ).df()

    club_compare = con.execute(
        """
        SELECT
            v.team,
            ROUND(AVG(v.performance_score), 3) AS avg_performance,
            ROUND(AVG(v.potential_score), 3) AS avg_potential,
            ROUND(AVG(v.pvs), 3) AS avg_pvs,
            ROUND(AVG(v.pvs - v.performance_score), 3) AS avg_boost,
            SUM(CASE WHEN v.pvs > v.performance_score + 0.001 THEN 1 ELSE 0 END) AS players_topped_up
        FROM player_value v
        WHERE v.season = ?
        GROUP BY v.team
        ORDER BY avg_pvs DESC
        """,
        [season],
    ).df()
    con.close()

    summary = pd.DataFrame(
        [
            {
                "metric": "Avg performance (perf-only ranking driver)",
                "value": club_compare.loc[club_compare["team"] == team, "avg_performance"].iloc[0],
            },
            {
                "metric": "Avg PVS (with potential top-up)",
                "value": club_compare.loc[club_compare["team"] == team, "avg_pvs"].iloc[0],
            },
            {
                "metric": "Avg boost from potential",
                "value": club_compare.loc[club_compare["team"] == team, "avg_boost"].iloc[0],
            },
            {
                "metric": "Players receiving top-up",
                "value": int(
                    club_compare.loc[club_compare["team"] == team, "players_topped_up"].iloc[0]
                ),
            },
            {
                "metric": "Club rank by avg performance",
                "value": int(club_compare["avg_performance"].rank(ascending=False)[
                    club_compare["team"] == team
                ].iloc[0]),
            },
            {
                "metric": "Club rank by avg PVS",
                "value": int(club_compare["avg_pvs"].rank(ascending=False)[
                    club_compare["team"] == team
                ].iloc[0]),
            },
        ]
    )

    notes = pd.DataFrame(
        {
            "topic": [
                "Why a club can rank high",
                "Potential top-up",
                f"POTENTIAL_BLEND_FACTOR ({POTENTIAL_BLEND_FACTOR})",
            ],
            "detail": [
                "Club average PVS is driven mainly by avg performance_score across the "
                "listed squad. Veterans with strong stats (e.g. elite mids) raise the "
                "average even without draft top-up.",
                "Young high draft picks with low performance can raise PVS above "
                "performance via max(perf, age_blend). Does not apply at age 25+.",
                "Potential in the blend is scaled by this factor (0–1) to limit "
                "inflation from lists with many recent top-10 picks.",
            ],
        }
    )

    path = out_dir / f"{slug}_{season}_pvs_diagnosis.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        players.to_excel(writer, sheet_name="Players", index=False)
        club_compare.to_excel(writer, sheet_name="All clubs", index=False)
        notes.to_excel(writer, sheet_name="Notes", index=False)
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team", default="Essendon")
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    print(export_club_pvs_diagnosis(args.team, args.season, args.out))


if __name__ == "__main__":
    main()
