"""Export club player PVS and round-by-round availability for analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from ..config import DB_PATH, ROOT


def export_club_season(
    team: str,
    season: int,
    out_dir: Path | None = None,
    excel_filename: str | None = None,
) -> tuple[Path, Path, Path | None]:
    out_dir = out_dir or ROOT / "shared" / "output" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = team.lower().replace(" ", "_")
    con = duckdb.connect(str(DB_PATH), read_only=True)

    player_summary = con.execute(
        """
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
            COUNT(*) FILTER (WHERE NOT a.afl_played AND a.status != 'intermittent') AS rounds_missed,
            COUNT(*) FILTER (WHERE a.afl_played) AS rounds_played,
            COUNT(*) FILTER (WHERE a.status = 'unavailable') AS rounds_unavailable,
            COUNT(*) FILTER (WHERE a.status = 'vfl_only') AS rounds_vfl_only,
            COUNT(*) FILTER (WHERE a.status = 'intermittent') AS rounds_intermittent
        FROM player_value v
        JOIN player_profiles p
            ON v.player_id = p.player_id AND v.team = p.team AND v.season = p.season
        LEFT JOIN availability a
            ON v.player_id = a.player_id AND v.team = a.team AND v.season = a.season
        WHERE v.team = ? AND v.season = ?
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
        ORDER BY player_value_score DESC
        """,
        [team, season],
    ).df()

    round_detail = con.execute(
        """
        SELECT
            a.player_id,
            a.player_name,
            a.round,
            a.status,
            a.afl_played,
            a.vfl_played,
            ROUND(v.pvs, 3) AS player_value_score,
            ROUND(v.performance_score, 3) AS performance_score,
            ROUND(v.potential_score, 3) AS potential_score,
            CASE WHEN a.afl_played THEN 'played' ELSE 'missing' END AS availability_label
        FROM availability a
        JOIN player_value v
            ON a.player_id = v.player_id AND a.team = v.team AND a.season = v.season
        WHERE a.team = ? AND a.season = ?
        ORDER BY a.player_name, a.round
        """,
        [team, season],
    ).df()

    # Wide matrix: one row per player, column per round with status
    if not round_detail.empty:
        matrix = round_detail.pivot_table(
            index=["player_id", "player_name", "player_value_score"],
            columns="round",
            values="status",
            aggfunc="first",
        ).reset_index()
        matrix.columns = [
            str(c) if isinstance(c, (int, float)) else c for c in matrix.columns
        ]
    else:
        matrix = pd.DataFrame()

    summary_path = out_dir / f"{slug}_{season}_player_ratings.csv"
    rounds_path = out_dir / f"{slug}_{season}_availability_by_round.csv"
    matrix_path = out_dir / f"{slug}_{season}_availability_matrix.csv"

    player_summary.to_csv(summary_path, index=False)
    round_detail.to_csv(rounds_path, index=False)
    if not matrix.empty:
        matrix.to_csv(matrix_path, index=False)

    excel_path: Path | None = None
    try:
        excel_path = out_dir / (excel_filename or f"{slug}_{season}_analysis.xlsx")
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            player_summary.to_excel(writer, sheet_name="Player ratings", index=False)
            round_detail.to_excel(writer, sheet_name="By round (long)", index=False)
            if not matrix.empty:
                matrix.to_excel(writer, sheet_name="By round (wide)", index=False)
            meta = pd.DataFrame(
                {
                    "field": [
                        "club",
                        "season",
                        "player_value_score",
                        "performance_score",
                        "potential_score",
                    ],
                    "description": [
                        team,
                        season,
                        "PVS = max(performance, age_weight * performance + (1-age_weight) * potential)",
                        "Weighted sum of season per-game stats (disp, goals, tackles, etc.); "
                        "normalised so league leader = 7",
                        "Exponential draft-pick curve; real pick from Draftguru when linked",
                    ],
                }
            )
            meta.to_excel(writer, sheet_name="Notes", index=False)
    except ImportError:
        excel_path = None

    con.close()
    return summary_path, rounds_path, excel_path if excel_path and excel_path.exists() else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Export club PVS and availability CSV/Excel")
    parser.add_argument("--team", default="Hawthorn")
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    summary, rounds, excel = export_club_season(args.team, args.season, args.out)
    print(f"Player ratings: {summary}")
    print(f"By round:       {rounds}")
    if excel:
        print(f"Excel:          {excel}")


if __name__ == "__main__":
    main()
