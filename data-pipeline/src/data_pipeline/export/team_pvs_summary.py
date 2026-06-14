"""Export average PVS by team for a season."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from ..config import DB_PATH, ROOT


def export_team_avg_pvs(season: int, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or ROOT / "shared" / "output" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    teams = con.execute(
        """
        SELECT
            v.team,
            COUNT(DISTINCT v.player_id) AS squad_players,
            ROUND(AVG(v.pvs), 3) AS avg_player_value_score,
            ROUND(AVG(v.performance_score), 3) AS avg_performance_score,
            ROUND(AVG(v.potential_score), 3) AS avg_potential_score,
            ROUND(MIN(v.pvs), 3) AS min_pvs,
            ROUND(MAX(v.pvs), 3) AS max_pvs,
            ROUND(STDDEV(v.pvs), 3) AS sd_pvs
        FROM player_value v
        WHERE v.season = ?
        GROUP BY v.team
        ORDER BY avg_player_value_score DESC
        """,
        [season],
    ).df()

    league = con.execute(
        """
        SELECT
            COUNT(DISTINCT v.player_id) AS squad_players,
            ROUND(AVG(v.pvs), 3) AS avg_player_value_score,
            ROUND(AVG(v.performance_score), 3) AS avg_performance_score,
            ROUND(MIN(v.pvs), 3) AS min_pvs,
            ROUND(MAX(v.pvs), 3) AS max_pvs,
            ROUND(STDDEV(v.pvs), 3) AS sd_pvs
        FROM player_value v
        WHERE v.season = ?
        """,
        [season],
    ).df()
    con.close()

    league_row = league.iloc[0].to_dict()
    league_row["team"] = "LEAGUE (all clubs)"
    summary = pd.concat([teams, pd.DataFrame([league_row])], ignore_index=True)

    spread = pd.DataFrame(
        [
            {
                "metric": "Highest club avg PVS",
                "value": teams["avg_player_value_score"].max(),
                "team": teams.loc[teams["avg_player_value_score"].idxmax(), "team"],
            },
            {
                "metric": "Lowest club avg PVS",
                "value": teams["avg_player_value_score"].min(),
                "team": teams.loc[teams["avg_player_value_score"].idxmin(), "team"],
            },
            {
                "metric": "Spread (max − min)",
                "value": round(
                    teams["avg_player_value_score"].max() - teams["avg_player_value_score"].min(),
                    3,
                ),
                "team": "",
            },
            {
                "metric": "League mean of club avgs",
                "value": round(teams["avg_player_value_score"].mean(), 3),
                "team": "",
            },
        ]
    )

    excel_path = out_dir / f"league_{season}_avg_pvs_by_team.xlsx"
    csv_path = out_dir / f"league_{season}_avg_pvs_by_team.csv"
    teams.to_csv(csv_path, index=False)

    notes = pd.DataFrame(
        {
            "topic": ["What this shows", "Why variation is small"],
            "detail": [
                f"Mean player_value_score (PVS) per AFL club for {season}, "
                "across all players with a player_value row that season.",
                "Every club lists ~30–40 players including rookies and depth, "
                "so club averages regress toward the league mean. "
                "Large gaps usually mean more top-tier talent or fewer low-PVS listed players.",
            ],
        }
    )

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        teams.to_excel(writer, sheet_name="By team", index=False)
        spread.to_excel(writer, sheet_name="Spread summary", index=False)
        notes.to_excel(writer, sheet_name="Notes", index=False)

    return excel_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export average PVS by team")
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    path = export_team_avg_pvs(args.season, args.out)
    print(path)


if __name__ == "__main__":
    main()
