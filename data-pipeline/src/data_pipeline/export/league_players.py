"""Export all AFL players for a season with ratings and key position stats."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd
import pyreadr

from ..config import DB_PATH, FRYZIGG_RDS_FILE, ROOT
from ..db import connect as db_connect
from ..ingest.fryzigg import normalize_team
from ..transform.archetypes import ARCHETYPE_LABELS, resolve_archetype
from ..transform.pvs import PERFORMANCE_METRICS, compute_raw_composite, scale_performance_score

EXTRA_STAT_COLS = ("marks_inside_fifty", "intercept_marks")


def _season_stats_from_rds(season: int) -> pd.DataFrame:
    """Per-game averages for stats not yet in DuckDB (or as fallback)."""
    raw = pyreadr.read_r(str(FRYZIGG_RDS_FILE))[None]
    raw["match_date"] = pd.to_datetime(raw["match_date"], errors="coerce")
    raw = raw[raw["match_date"].dt.year == season].copy()
    if raw.empty:
        return pd.DataFrame()

    raw["player_id"] = raw["player_id"].astype(str)
    raw["team"] = raw["player_team"].map(normalize_team)
    raw["player_name"] = (
        raw["player_first_name"].astype(str).str.strip()
        + " "
        + raw["player_last_name"].astype(str).str.strip()
    ).str.strip()
    for col in [
        "disposals",
        "goals",
        "score_involvements",
        "tackles",
        "contested_marks",
        "intercept_marks",
        "marks_inside_fifty",
        "intercepts",
        "clearances",
        "hitouts",
        "hitouts_to_advantage",
        "clangers",
        "metres_gained",
    ]:
        if col in raw.columns:
            raw[col] = pd.to_numeric(raw[col], errors="coerce").fillna(0)
        else:
            raw[col] = 0.0
    raw["metres_per100"] = raw["metres_gained"] / 100.0
    if "disposal_efficiency_percentage" in raw.columns:
        de = pd.to_numeric(raw["disposal_efficiency_percentage"], errors="coerce").fillna(72.0)
    else:
        de = 72.0
    raw["effective_disposals"] = raw["disposals"] * de / 100.0

    def _mode_pos(s: pd.Series) -> str | None:
        m = s.dropna()
        if m.empty:
            return None
        return m.mode().iloc[0]

    agg: dict[str, tuple[str, str]] = {
        "games_rds": ("player_id", "count"),
        "fryzigg_position": ("player_position", _mode_pos),
    }
    for col in [
        "disposals",
        "goals",
        "score_involvements",
        "tackles",
        "contested_marks",
        "intercept_marks",
        "marks_inside_fifty",
        "intercepts",
        "clearances",
        "hitouts",
        "hitouts_to_advantage",
        "clangers",
        "metres_per100",
        "effective_disposals",
    ]:
        agg[f"{col}_pg"] = (col, "mean")

    grouped = (
        raw.groupby(["player_id", "player_name", "team"], as_index=False)
        .agg(**{k: pd.NamedAgg(column=v[0], aggfunc=v[1]) for k, v in agg.items()})
    )
    grouped["season"] = season
    grouped = grouped.rename(columns={"score_involvements_pg": "score_inv_pg", "hitouts_to_advantage_pg": "hota_pg"})
    return grouped


def build_league_players_df(con: duckdb.DuckDBPyConnection, season: int) -> pd.DataFrame:
    ratings = con.execute(
        """
        SELECT
            v.player_id,
            p.player_name,
            v.team,
            p.age_est,
            p.draft_pick,
            p.archetype,
            v.games AS games_played_afl,
            ROUND(v.performance_score, 3) AS performance_score,
            ROUND(v.potential_score, 3) AS potential_score,
            ROUND(v.age_perf_weight, 3) AS age_performance_weight,
            ROUND(v.pvs, 3) AS player_value_score,
            COUNT(*) FILTER (WHERE a.afl_played) AS rounds_played,
            COUNT(*) FILTER (WHERE NOT a.afl_played AND a.status != 'intermittent') AS rounds_missed,
            COUNT(*) FILTER (WHERE a.status = 'vfl_only') AS rounds_vfl_only,
            COUNT(*) FILTER (WHERE a.status = 'unavailable') AS rounds_unavailable,
            ROUND(SUM(CASE WHEN a.status IN ('unavailable', 'intermittent') THEN v.pvs ELSE 0 END), 1)
                AS pvs_games_missed
        FROM player_value v
        JOIN player_profiles p
            ON v.player_id = p.player_id AND v.team = p.team AND v.season = p.season
        LEFT JOIN availability a
            ON v.player_id = a.player_id AND v.team = a.team AND v.season = a.season
        WHERE v.season = ?
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
        ORDER BY player_value_score DESC
        """,
        [season],
    ).df()

    rds_stats = _season_stats_from_rds(season)
    if rds_stats.empty:
        raise ValueError(f"No Fryzigg rows for season {season}")

    df = ratings.merge(rds_stats, on=["player_id", "team"], how="left", suffixes=("", "_rds"))

    pg_cols = {
        c[0]
        for c in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'player_games'"
        ).fetchall()
    }
    if {"intercept_marks", "marks_inside_fifty"}.issubset(pg_cols):
        db_stats = con.execute(
            """
            SELECT
                player_id,
                team,
                AVG(COALESCE(intercept_marks, 0)) AS intercept_marks_pg_db,
                AVG(COALESCE(marks_inside_fifty, 0)) AS marks_inside_fifty_pg_db
            FROM player_games
            WHERE season = ?
            GROUP BY 1, 2
            """,
            [season],
        ).df()
        if not db_stats.empty and db_stats["intercept_marks_pg_db"].sum() > 0:
            df = df.merge(db_stats, on=["player_id", "team"], how="left")
            df["marks_inside_fifty_pg"] = df["marks_inside_fifty_pg_db"].fillna(df["marks_inside_fifty_pg"])
            df["intercept_marks_pg"] = df["intercept_marks_pg_db"].fillna(df["intercept_marks_pg"])

    df["archetype_label"] = df["archetype"].map(lambda a: ARCHETYPE_LABELS.get(a, a))

    stat_rows = []
    for _, row in df.iterrows():
        final, stat_arch, fryzigg_arch = resolve_archetype(
            row.get("fryzigg_position"),
            disposals_pg=float(row.get("disposals_pg") or 0),
            goals_pg=float(row.get("goals_pg") or 0),
            score_inv_pg=float(row.get("score_inv_pg") or 0),
            clearances_pg=float(row.get("clearances_pg") or 0),
            intercepts_pg=float(row.get("intercepts_pg") or 0),
            hitouts_pg=float(row.get("hitouts_pg") or 0),
            tackles_pg=float(row.get("tackles_pg") or 0),
            contested_marks_pg=float(row.get("contested_marks_pg") or 0),
            metres_per100_pg=float(row.get("metres_per100_pg") or 0),
        )
        raw = compute_raw_composite(row)
        stat_rows.append(
            {
                "stat_archetype": stat_arch,
                "fryzigg_archetype": fryzigg_arch,
                "resolved_archetype": final,
                "raw_performance_composite": round(raw, 4),
            }
        )
    stat_df = pd.DataFrame(stat_rows)
    df = pd.concat([df.reset_index(drop=True), stat_df], axis=1)

    league_max = df["raw_performance_composite"].max() or 1.0
    df["implied_performance_score"] = df["raw_performance_composite"].map(
        lambda x: round(scale_performance_score(float(x), league_max), 3)
    )

    col_order = [
        "player_id",
        "player_name",
        "team",
        "age_est",
        "draft_pick",
        "archetype",
        "archetype_label",
        "stat_archetype",
        "fryzigg_archetype",
        "fryzigg_position",
        "games_played_afl",
        "rounds_played",
        "rounds_missed",
        "rounds_vfl_only",
        "rounds_unavailable",
        "player_value_score",
        "performance_score",
        "potential_score",
        "age_performance_weight",
        "implied_performance_score",
        "raw_performance_composite",
        "pvs_games_missed",
        "goals_pg",
        "marks_inside_fifty_pg",
        "contested_marks_pg",
        "intercept_marks_pg",
        "intercepts_pg",
        "score_inv_pg",
        "tackles_pg",
        "clearances_pg",
        "effective_disposals_pg",
        "metres_per100_pg",
        "hitouts_pg",
    ]
    present = [c for c in col_order if c in df.columns]
    df = df[present].round(
        {
            k: 3
            for k in df.columns
            if k.endswith("_pg") or k in ("age_est", "player_value_score", "performance_score", "potential_score")
        }
    )
    return df.sort_values("player_value_score", ascending=False)


def build_archetype_summary(players: pd.DataFrame) -> pd.DataFrame:
    key = players[players["archetype"].isin(["key_forward", "key_defender", "rebound_defender"])]
    rows = []
    for arch, grp in players.groupby("archetype", dropna=False):
        rows.append(
            {
                "archetype": arch,
                "archetype_label": ARCHETYPE_LABELS.get(arch, arch),
                "players": len(grp),
                "avg_pvs": round(grp["player_value_score"].mean(), 3),
                "median_pvs": round(grp["player_value_score"].median(), 3),
                "avg_performance_score": round(grp["performance_score"].mean(), 3),
                "avg_marks_inside_fifty_pg": round(grp["marks_inside_fifty_pg"].mean(), 3),
                "avg_contested_marks_pg": round(grp["contested_marks_pg"].mean(), 3),
                "avg_intercept_marks_pg": round(grp["intercept_marks_pg"].mean(), 3),
                "avg_intercepts_pg": round(grp["intercepts_pg"].mean(), 3),
                "avg_goals_pg": round(grp["goals_pg"].mean(), 3),
            }
        )
    summary = pd.DataFrame(rows).sort_values("avg_pvs", ascending=False)
    if not key.empty:
        summary.attrs["key_position_note"] = (
            f"Key/rebound defenders+forwards (n={len(key)}): "
            f"avg PVS {key['player_value_score'].mean():.2f} vs league {players['player_value_score'].mean():.2f}"
        )
    return summary


def build_notes_df() -> pd.DataFrame:
    weights = pd.DataFrame(
        [{"metric": alias, "pvs_weight": weight} for _col, alias, weight in PERFORMANCE_METRICS]
    )
    notes = pd.DataFrame(
        {
            "topic": [
                "marks_inside_fifty_pg",
                "intercept_marks_pg",
                "intercepts_pg",
                "contested_marks_pg",
                "archetype",
                "pvs_weights",
            ],
            "description": [
                "Average marks inside forward 50 per game (Fryzigg). In PVS at weight 0.28.",
                "Average intercept marks per game (Fryzigg). In PVS at weight 0.09.",
                "Average intercept possessions per game. In PVS at weight 0.06 (trimmed vs intercept marks).",
                "Average contested marks per game. In PVS at weight 0.08; used for key forward/defender rules.",
                "Stored archetype from pipeline. stat_archetype recomputed from season rates for comparison.",
                "See pvs_weights tab. MI50 and intercept marks lift key forwards/defenders toward other roles.",
            ],
        }
    )
    return notes, weights


def export_league_players(season: int, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or ROOT / "shared" / "output" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"league_{season}_all_players.xlsx"

    db_connect().close()  # apply schema migrations before read-only export
    con = duckdb.connect(str(DB_PATH), read_only=True)
    players = build_league_players_df(con, season)
    con.close()

    summary = build_archetype_summary(players)
    notes, weights = build_notes_df()

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        players.to_excel(writer, sheet_name="All players", index=False)
        summary.to_excel(writer, sheet_name="By archetype", index=False)
        notes.to_excel(writer, sheet_name="Notes", index=False)
        weights.to_excel(writer, sheet_name="PVS weights", index=False)

    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export all AFL players for a season")
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    print(export_league_players(args.season, args.out))


if __name__ == "__main__":
    main()
