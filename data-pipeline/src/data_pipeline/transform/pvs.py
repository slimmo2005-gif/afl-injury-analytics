"""Player Value Score — explainable hybrid of performance and draft potential."""

from __future__ import annotations

import math
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from ..config import ROOT
from .archetypes import resolve_archetype

AGE_PERF_FLOOR = 0.30
AGE_PERF_FULL = 1.00
AGE_START = 18
AGE_MATURE = 25
DRAFT_DECAY = 14.0
DEFAULT_DRAFT_PICK = 40
ROOKIE_DRAFT_PICK = 22
PERF_TOP_SCORE = 7.0
# Scales draft potential in the age blend only (top-up path). Lower = less list inflation
# from young high picks who have not yet performed.
POTENTIAL_BLEND_FACTOR = 0.75

# (player_games column, season-avg alias, weight)
# effective_disposals = disposals × DE% / 100 (quality-adjusted ball use)
PERFORMANCE_METRICS: list[tuple[str, str, float]] = [
    ("effective_disposals", "effective_disposals_pg", 0.22),
    ("goals", "goals_pg", 0.18),
    ("score_involvements", "score_inv_pg", 0.11),
    ("metres_per100", "metres_per100_pg", 0.06),
    ("tackles", "tackles_pg", 0.07),
    ("contested_marks", "contested_marks_pg", 0.08),
    ("marks_inside_fifty", "marks_inside_fifty_pg", 0.28),
    ("intercept_marks", "intercept_marks_pg", 0.09),
    ("intercepts", "intercepts_pg", 0.06),
    ("clearances", "clearances_pg", 0.11),
    ("hitouts", "hitouts_pg", 0.03),
    ("hitouts_to_advantage", "hota_pg", 0.05),
    ("clangers", "clangers_pg", -0.06),
]


def raw_composite_expr(prefix: str = "") -> str:
    """SQL expression for weighted sum of season per-game averages."""
    p = f"{prefix}." if prefix else ""
    terms = [f"{weight:+.4f} * {p}{alias}" for _, alias, weight in PERFORMANCE_METRICS]
    return " ".join(terms)


def age_performance_weight(age: float) -> float:
    if age <= AGE_START:
        return AGE_PERF_FLOOR
    if age >= AGE_MATURE:
        return AGE_PERF_FULL
    t = (age - AGE_START) / (AGE_MATURE - AGE_START)
    return AGE_PERF_FLOOR + t * (AGE_PERF_FULL - AGE_PERF_FLOOR)


def draft_potential_score(pick: int) -> float:
    pick = max(1, min(int(pick), 120))
    return float(10.0 * math.exp(-pick / DRAFT_DECAY))


def compute_pvs(performance_score: float, potential_score: float, age_perf_weight: float) -> float:
    """Potential tops up young/high-pick players but never reduces a proven score."""
    blended = age_perf_weight * performance_score + (
        (1 - age_perf_weight) * potential_score * POTENTIAL_BLEND_FACTOR
    )
    return round(max(performance_score, blended), 3)


def compute_raw_composite(row: pd.Series) -> float:
    total = 0.0
    for _col, alias, weight in PERFORMANCE_METRICS:
        total += weight * float(row.get(alias) or 0)
    return total


def scale_performance_score(raw_composite: float, league_max: float) -> float:
    if league_max <= 0:
        return 0.0
    return round(PERF_TOP_SCORE * raw_composite / league_max, 4)


def _build_player_value_sql() -> str:
    base_avgs = ",\n                ".join(
        f"AVG(COALESCE(pg.{col}, 0)) AS {avg_alias}"
        for col, avg_alias, _ in PERFORMANCE_METRICS
    )
    composite = raw_composite_expr("b")

    return f"""
        INSERT INTO player_value
        WITH base AS (
            SELECT
                pg.player_id,
                pg.team,
                pg.season,
                COUNT(*) AS games,
                {base_avgs}
            FROM player_games pg
            GROUP BY 1, 2, 3
        ),
        composite AS (
            SELECT
                b.*,
                ({composite}) AS raw_composite
            FROM base b
        )
        SELECT
            c.player_id,
            c.team,
            c.season,
            c.games,
            LEAST({PERF_TOP_SCORE}, GREATEST(0,
                {PERF_TOP_SCORE} * c.raw_composite
                / NULLIF(MAX(c.raw_composite) OVER (PARTITION BY c.season), 0)
            )) AS performance_score,
            0.0 AS potential_score,
            0.0 AS pvs,
            0.0 AS age_perf_weight
        FROM composite c
    """


def _load_draft_picks(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    try:
        draft_db = con.execute(
            """
            SELECT player_id, MIN(draft_pick) AS draft_pick
            FROM draft_picks
            GROUP BY 1
            """
        ).df()
        if not draft_db.empty:
            return draft_db
    except duckdb.CatalogException:
        pass

    draft_file = ROOT / "shared" / "data" / "draft_picks.csv"
    if draft_file.exists():
        draft = pd.read_csv(draft_file, dtype={"player_id": str})
        if not draft.empty:
            return draft.groupby("player_id", as_index=False)["draft_pick"].min()

    return pd.DataFrame(columns=["player_id", "draft_pick"])


def build_player_profiles(con: duckdb.DuckDBPyConnection) -> None:
    games = con.execute(
        """
        SELECT
            player_id,
            MAX(player_name) AS player_name,
            team,
            season,
            MIN(season) OVER (PARTITION BY player_id) AS debut_season,
            MODE(player_position) AS player_position
        FROM player_games
        GROUP BY player_id, team, season
        """
    ).df()

    if games.empty:
        return

    games["age_est"] = (games["season"] - games["debut_season"] + 18).clip(17, 40)

    season_stats = con.execute(
        """
        SELECT
            player_id,
            team,
            season,
            AVG(COALESCE(disposals, 0)) AS disposals_pg,
            AVG(COALESCE(goals, 0)) AS goals_pg,
            AVG(COALESCE(score_involvements, 0)) AS score_inv_pg,
            AVG(COALESCE(clearances, 0)) AS clearances_pg,
            AVG(COALESCE(intercepts, 0)) AS intercepts_pg,
            AVG(COALESCE(hitouts, 0)) AS hitouts_pg,
            AVG(COALESCE(tackles, 0)) AS tackles_pg,
            AVG(COALESCE(contested_marks, 0)) AS contested_marks_pg,
            AVG(COALESCE(metres_per100, 0)) AS metres_per100_pg
        FROM player_games
        GROUP BY 1, 2, 3
        """
    ).df()
    games = games.merge(season_stats, on=["player_id", "team", "season"], how="left")
    games["archetype"] = games.apply(
        lambda r: resolve_archetype(
            r["player_position"],
            disposals_pg=float(r.get("disposals_pg") or 0),
            goals_pg=float(r.get("goals_pg") or 0),
            score_inv_pg=float(r.get("score_inv_pg") or 0),
            clearances_pg=float(r.get("clearances_pg") or 0),
            intercepts_pg=float(r.get("intercepts_pg") or 0),
            hitouts_pg=float(r.get("hitouts_pg") or 0),
            tackles_pg=float(r.get("tackles_pg") or 0),
            contested_marks_pg=float(r.get("contested_marks_pg") or 0),
            metres_per100_pg=float(r.get("metres_per100_pg") or 0),
        )[0],
        axis=1,
    )

    draft = _load_draft_picks(con)
    if not draft.empty:
        games = games.merge(draft, on="player_id", how="left")
    elif "draft_pick" not in games.columns:
        games["draft_pick"] = np.nan

    is_rookie = games["season"] == games["debut_season"]
    games["draft_pick"] = pd.to_numeric(games.get("draft_pick"), errors="coerce")
    games.loc[games["draft_pick"].isna() & is_rookie, "draft_pick"] = ROOKIE_DRAFT_PICK
    games.loc[games["draft_pick"].isna(), "draft_pick"] = DEFAULT_DRAFT_PICK
    games["draft_pick"] = games["draft_pick"].astype(int)

    profiles = games[
        [
            "player_id",
            "player_name",
            "team",
            "season",
            "debut_season",
            "age_est",
            "draft_pick",
            "archetype",
        ]
    ].drop_duplicates(subset=["player_id", "team", "season"])

    con.execute("DELETE FROM player_profiles")
    con.register("_profiles", profiles)
    con.execute("INSERT INTO player_profiles SELECT * FROM _profiles")
    con.unregister("_profiles")


def build_player_value(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DELETE FROM player_value")
    con.execute(_build_player_value_sql())

    pv = con.execute(
        """
        SELECT
            v.player_id,
            v.team,
            v.season,
            v.games,
            v.performance_score,
            p.age_est,
            p.draft_pick
        FROM player_value v
        JOIN player_profiles p
            ON v.player_id = p.player_id
            AND v.team = p.team
            AND v.season = p.season
        """
    ).df()

    pv["potential_score"] = pv["draft_pick"].map(draft_potential_score)
    pv["age_perf_weight"] = pv["age_est"].map(age_performance_weight)
    pv["pvs"] = pv.apply(
        lambda row: compute_pvs(row["performance_score"], row["potential_score"], row["age_perf_weight"]),
        axis=1,
    )

    con.execute("DELETE FROM player_value")
    con.register("_pv", pv)
    con.execute(
        """
        INSERT INTO player_value
        SELECT player_id, team, season, games, performance_score,
               potential_score, pvs, age_perf_weight
        FROM _pv
        """
    )
    con.unregister("_pv")
