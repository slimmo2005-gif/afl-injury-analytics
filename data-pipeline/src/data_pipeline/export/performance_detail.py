"""Export per-player performance score breakdown (weighted season averages)."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from ..config import DB_PATH, ROOT
from ..transform.archetypes import resolve_archetype
from ..transform.pvs import (
    PERF_TOP_SCORE,
    PERFORMANCE_METRICS,
    compute_raw_composite,
    scale_performance_score,
)

STAT_LABELS = {
    "disposals": "Disposals / game",
    "goals": "Goals / game",
    "score_involvements": "Score involvements / game",
    "tackles": "Tackles / game",
    "contested_marks": "Contested marks / game",
    "intercepts": "Intercepts / game",
    "clearances": "Clearances / game",
    "hitouts": "Hit-outs / game",
    "hitouts_to_advantage": "Hit-outs to advantage / game",
    "clangers": "Clangers / game (penalty)",
    "metres_per100": "Metres gained / 100 per game",
    "effective_disposals": "Effective disposals / game (disp × DE% / 100)",
    "disposal_efficiency_pct": "Disposal efficiency % (reference)",
}


def _load_season_avgs(season: int, team: str | None, con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    base_avgs = ",\n                ".join(
        f"AVG(COALESCE(pg.{col}, 0)) AS {avg_alias}"
        for col, avg_alias, _ in PERFORMANCE_METRICS
    )
    team_clause = f"AND pg.team = '{team.replace(chr(39), chr(39) + chr(39))}'" if team else ""
    return con.execute(
        f"""
        SELECT
            pg.player_id,
            MAX(pg.player_name) AS player_name,
            pg.team,
            pg.season,
            COUNT(*) AS games,
            MODE(pg.player_position) AS fryzigg_mode_position,
            {base_avgs}
        FROM player_games pg
        WHERE pg.season = {int(season)} {team_clause.replace('pg.team', 'pg.team')}
        GROUP BY pg.player_id, pg.team, pg.season
        """
    ).df()


def build_performance_detail(
    team: str,
    season: int,
    con: duckdb.DuckDBPyConnection,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (player_summary, stat_detail_long, weights_context)."""
    club = _load_season_avgs(season, team, con)
    if club.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    league = _load_season_avgs(season, None, con)
    league["raw_composite"] = league.apply(compute_raw_composite, axis=1)
    league_max = float(league["raw_composite"].max())

    scores = con.execute(
        """
        SELECT v.player_id, v.team, ROUND(v.performance_score, 4) AS performance_score,
               ROUND(v.pvs, 3) AS pvs, p.archetype
        FROM player_value v
        JOIN player_profiles p
            ON v.player_id = p.player_id AND v.team = p.team AND v.season = p.season
        WHERE v.season = ? AND v.team = ?
        """,
        [season, team],
    ).df()

    weights_ctx = pd.DataFrame(
        [
            {
                "stat": STAT_LABELS.get(col, col),
                "column": col,
                "weight": weight,
                "contribution_formula": f"weight × raw_season_avg ({weight:+.2f} × stat)",
            }
            for col, _alias, weight in PERFORMANCE_METRICS
        ]
    )

    detail_rows = []
    summary_rows = []

    for _, row in club.iterrows():
        raw_composite = compute_raw_composite(row)
        calc_perf = scale_performance_score(raw_composite, league_max)

        for col, avg_alias, weight in PERFORMANCE_METRICS:
            avg = float(row[avg_alias])
            detail_rows.append(
                {
                    "player_id": row["player_id"],
                    "player_name": row["player_name"],
                    "stat": STAT_LABELS.get(col, col),
                    "weight": weight,
                    "raw_season_avg": round(avg, 4),
                    "weighted_contribution": round(weight * avg, 4),
                }
            )

        final_arch, stat_arch, fryzigg_arch = resolve_archetype(
            row["fryzigg_mode_position"],
            disposals_pg=float(row["disposals_pg"]),
            goals_pg=float(row["goals_pg"]),
            score_inv_pg=float(row["score_inv_pg"]),
            clearances_pg=float(row["clearances_pg"]),
            intercepts_pg=float(row["intercepts_pg"]),
            hitouts_pg=float(row["hitouts_pg"]),
            tackles_pg=float(row["tackles_pg"]),
            contested_marks_pg=float(row["contested_marks_pg"]),
            metres_per100_pg=float(row.get("metres_per100_pg") or 0),
        )

        db_row = scores[(scores["player_id"] == row["player_id"]) & (scores["team"] == row["team"])]
        db_perf = float(db_row["performance_score"].iloc[0]) if len(db_row) else calc_perf

        summary_rows.append(
            {
                "player_id": row["player_id"],
                "player_name": row["player_name"],
                "games": int(row["games"]),
                "fryzigg_mode_position": row["fryzigg_mode_position"],
                "fryzigg_archetype": fryzigg_arch,
                "stat_archetype": stat_arch,
                "archetype_in_db": db_row["archetype"].iloc[0] if len(db_row) else final_arch,
                "raw_composite": round(raw_composite, 4),
                "league_max_composite": round(league_max, 4),
                "calculated_performance": calc_perf,
                "stored_performance": db_perf,
                "stored_pvs": float(db_row["pvs"].iloc[0]) if len(db_row) else None,
            }
        )

    summary = pd.DataFrame(summary_rows).sort_values("stored_performance", ascending=False)
    detail = pd.DataFrame(detail_rows)
    return summary, detail, weights_ctx


def export_performance_detail(
    team: str,
    season: int,
    out_dir: Path | None = None,
) -> tuple[Path, Path]:
    out_dir = out_dir or ROOT / "shared" / "output" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = team.lower().replace(" ", "_")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    summary, detail, weights_ctx = build_performance_detail(team, season, con)
    con.close()

    excel_path = out_dir / f"{slug}_{season}_performance_detail.xlsx"
    csv_path = out_dir / f"{slug}_{season}_performance_detail.csv"

    detail.to_csv(csv_path, index=False)

    notes = pd.DataFrame(
        {
            "topic": [
                "Base formula",
                "Normalisation",
                "Weights",
            ],
            "explanation": [
                "raw_composite = Σ (weight × raw_season_avg per game). "
                "Clangers use a negative weight.",
                f"performance_score = {PERF_TOP_SCORE:.0f} × raw_composite / league_max_composite "
                f"for that season. Best player in the league always scores {PERF_TOP_SCORE:.0f}.",
                "Disposals and goals weighted highest; hit-outs, HOTA and tackles reduced "
                "vs the prior z-score model.",
            ],
        }
    )

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Player summary", index=False)
        detail.to_excel(writer, sheet_name="Stat breakdown", index=False)
        weights_ctx.to_excel(writer, sheet_name="Weights", index=False)
        notes.to_excel(writer, sheet_name="Notes", index=False)

    return excel_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export performance score breakdown")
    parser.add_argument("--team", default="Hawthorn")
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    excel_path, csv_path = export_performance_detail(args.team, args.season, args.out)
    print(f"Excel: {excel_path}")
    print(f"CSV:   {csv_path}")


if __name__ == "__main__":
    main()
