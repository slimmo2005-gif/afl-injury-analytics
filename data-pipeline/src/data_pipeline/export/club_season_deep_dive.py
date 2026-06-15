"""Deep-dive Excel for one club-season: injuries, PVS ranks, and league context."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

from ..config import DB_PATH, ROOT
from ..db import connect as db_connect
from ..export.league_players import build_league_injury_summary, build_league_players_df, build_notes_df
from ..transform.archetypes import ARCHETYPE_LABELS
from ..transform.unavailability import GAMES_MISSED_STATUS_SQL


def _league_injury_comparison(con: duckdb.DuckDBPyConnection, season: int) -> pd.DataFrame:
    return build_league_injury_summary(con, season)


def _club_round_pvs(con: duckdb.DuckDBPyConnection, team: str, season: int) -> pd.DataFrame:
    return con.execute(
        """
        SELECT
            tr.round,
            CASE WHEN tr.won THEN 1 ELSE 0 END AS won,
            tr.players_unavailable,
            ROUND(trv.unavailable_pvs_games_missed, 1) AS pvs_games_missed,
            ROUND(trv.unavailable_pvs_total, 1) AS pvs_all_absences,
            ROUND(trv.unavailable_pvs_top5, 1) AS pvs_top5,
            ROUND(trv.unavailable_pvs_vfl_only, 1) AS pvs_vfl_only
        FROM team_round_summary tr
        JOIN team_round_value trv
            ON tr.team = trv.team AND tr.season = trv.season AND tr.round = trv.round
        WHERE tr.team = ? AND tr.season = ?
        ORDER BY tr.round
        """,
        [team, season],
    ).df()


def _club_top_missed(con: duckdb.DuckDBPyConnection, team: str, season: int) -> pd.DataFrame:
    return con.execute(
        f"""
        SELECT
            p.player_name,
            p.archetype,
            ROUND(v.pvs, 3) AS player_value_score,
            ROUND(v.performance_score, 3) AS performance_score,
            ROUND(COALESCE(v.injury_weight_pvs, v.pvs), 3) AS injury_weight_pvs,
            COUNT(*) FILTER (WHERE NOT a.afl_played) AS rounds_missed,
            COUNT(*) FILTER (WHERE a.afl_played) AS rounds_played,
            COUNT(*) FILTER (WHERE a.status = 'unavailable') AS rounds_unavailable,
            COUNT(*) FILTER (WHERE a.status = 'intermittent') AS rounds_intermittent,
            COUNT(*) FILTER (WHERE a.status = 'vfl_only') AS rounds_vfl_only,
            ROUND(
                SUM(
                    CASE
                        WHEN a.status IN {GAMES_MISSED_STATUS_SQL}
                        THEN COALESCE(v.injury_weight_pvs, v.pvs)
                        ELSE 0
                    END
                ),
                1
            ) AS pvs_games_missed,
            ROUND(SUM(CASE WHEN NOT a.afl_played THEN COALESCE(v.injury_weight_pvs, v.pvs) ELSE 0 END), 1) AS pvs_all_absences
        FROM availability a
        JOIN player_value v ON a.player_id = v.player_id AND a.team = v.team AND a.season = v.season
        JOIN player_profiles p ON v.player_id = p.player_id AND v.team = p.team AND v.season = p.season
        WHERE a.team = ? AND a.season = ?
        GROUP BY 1, 2, 3, 4, 5
        HAVING rounds_missed > 0
        ORDER BY pvs_games_missed DESC
        """,
        [team, season],
    ).df()


def _club_archetype_injury(con: duckdb.DuckDBPyConnection, team: str, season: int) -> pd.DataFrame:
    return con.execute(
        f"""
        SELECT
            p.archetype,
            COUNT(DISTINCT a.player_id) AS players,
            COUNT(*) FILTER (WHERE NOT a.afl_played) AS missed_slots,
            ROUND(SUM(CASE WHEN a.status IN {GAMES_MISSED_STATUS_SQL} THEN COALESCE(v.injury_weight_pvs, v.pvs) ELSE 0 END), 1)
                AS pvs_games_missed
        FROM availability a
        JOIN player_value v ON a.player_id = v.player_id AND a.team = v.team AND a.season = v.season
        JOIN player_profiles p ON v.player_id = p.player_id AND v.team = p.team AND v.season = p.season
        WHERE a.team = ? AND a.season = ?
        GROUP BY 1
        ORDER BY pvs_games_missed DESC
        """,
        [team, season],
    ).df()


def _context_notes(team: str, season: int, league: pd.DataFrame) -> pd.DataFrame:
    row = league[league["team"] == team]
    if row.empty:
        return pd.DataFrame({"topic": ["error"], "detail": ["club not found"]})
    r = row.iloc[0]
    league_avg = league["pvs_games_missed"].mean()
    return pd.DataFrame(
        {
            "topic": [
                "club",
                "season",
                "ladder_rank",
                "pvs_games_missed_rank",
                "club_pvs_games_missed",
                "league_avg_pvs_games_missed",
                "vs_league_avg",
                "rank_all_absence_pvs",
                "rank_top5_sum",
                "rank_slots_lost",
                "interpretation",
            ],
            "detail": [
                team,
                season,
                int(r["ladder_rank"]),
                int(r["rank_games_missed_pvs"]),
                float(r["pvs_games_missed"]),
                round(league_avg, 1),
                round(float(r["pvs_games_missed"]) - league_avg, 1),
                int(r["rank_all_absence_pvs"]),
                int(r["rank_top5_sum"]),
                int(r["rank_slots_lost"]),
                (
                    "PVS-lost rank uses games-missed PVS (unavailable, intermittent, injured, and "
                    "unclear; excludes VFL-only). "
                    "Injury weights use injury_weight_pvs when a player played <14 games: max(season PVS, "
                    "last established season with 10+ games). A club can look 'injury cursed' if many squad "
                    "players miss weeks, but rank moves on PVS weight — missing stars hurts more than missing "
                    "fringe players. Compare rank_games_missed_pvs vs rank_all_absence_pvs and rank_slots_lost."
                ),
            ],
        }
    )


def export_club_season_deep_dive(
    team: str,
    season: int,
    out_dir: Path | None = None,
) -> Path:
    out_dir = out_dir or ROOT / "shared" / "output" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = team.lower().replace(" ", "_")
    path = out_dir / f"{slug}_{season}_deep_dive.xlsx"

    db_connect().close()
    con = duckdb.connect(str(DB_PATH), read_only=True)

    league_cmp = _league_injury_comparison(con, season)
    club_players = build_league_players_df(con, season)
    club_players = club_players[club_players["team"] == team].copy()
    club_players["archetype_label"] = club_players["archetype"].map(
        lambda a: ARCHETYPE_LABELS.get(a, a)
    )

    round_pvs = _club_round_pvs(con, team, season)
    top_missed = _club_top_missed(con, team, season)
    arch_inj = _club_archetype_injury(con, team, season)
    arch_inj["archetype_label"] = arch_inj["archetype"].map(lambda a: ARCHETYPE_LABELS.get(a, a))
    context = _context_notes(team, season, league_cmp)
    notes, weights = build_notes_df()

    con.close()

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        context.to_excel(writer, sheet_name="Summary", index=False)
        league_cmp.to_excel(writer, sheet_name="League injury ranks", index=False)
        club_players.to_excel(writer, sheet_name="Club players", index=False)
        top_missed.to_excel(writer, sheet_name="Top missed players", index=False)
        round_pvs.to_excel(writer, sheet_name="PVS by round", index=False)
        arch_inj.to_excel(writer, sheet_name="By archetype injury", index=False)
        notes.to_excel(writer, sheet_name="Notes", index=False)
        weights.to_excel(writer, sheet_name="PVS weights", index=False)

    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export club-season injury deep dive")
    parser.add_argument("--team", default="Collingwood")
    parser.add_argument("--season", type=int, default=2021)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    print(export_club_season_deep_dive(args.team, args.season, args.out))


if __name__ == "__main__":
    main()
