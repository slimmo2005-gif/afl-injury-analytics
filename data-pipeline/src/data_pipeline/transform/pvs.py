"""Player Value Score — explainable hybrid of performance and draft potential."""

from __future__ import annotations

import math
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from ..config import ROOT
from .archetypes import map_position

AGE_PERF_FLOOR = 0.30
AGE_PERF_FULL = 1.00
AGE_START = 18
AGE_MATURE = 25
DRAFT_DECAY = 14.0
DEFAULT_DRAFT_PICK = 40
ROOKIE_DRAFT_PICK = 22


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
    games["archetype"] = games["player_position"].map(map_position)

    draft_file = ROOT / "shared" / "data" / "draft_picks.csv"
    if draft_file.exists():
        draft = pd.read_csv(draft_file, dtype={"player_id": str})
        games = games.merge(draft[["player_id", "draft_pick"]], on="player_id", how="left")
    else:
        games["draft_pick"] = np.nan

    is_rookie = games["season"] == games["debut_season"]
    games["draft_pick"] = games["draft_pick"].astype(float)
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
    con.execute(
        """
        INSERT INTO player_value
        WITH base AS (
            SELECT
                pg.player_id,
                pg.team,
                pg.season,
                COUNT(*) AS games,
                AVG(pg.disposals) AS disposals_pg,
                AVG(pg.goals) AS goals_pg,
                AVG(COALESCE(pg.score_involvements, 0)) AS score_inv_pg
            FROM player_games pg
            GROUP BY 1, 2, 3
        ),
        rolled AS (
            SELECT
                b.player_id,
                b.team,
                b.season,
                b.games,
                (
                    COALESCE((SELECT disposals_pg FROM base b2
                        WHERE b2.player_id = b.player_id AND b2.team = b.team AND b2.season = b.season - 2), b.disposals_pg) * 0.2
                    + COALESCE((SELECT disposals_pg FROM base b2
                        WHERE b2.player_id = b.player_id AND b2.team = b.team AND b2.season = b.season - 1), b.disposals_pg) * 0.3
                    + b.disposals_pg * 0.5
                ) AS roll_disposals,
                (
                    COALESCE((SELECT goals_pg FROM base b2
                        WHERE b2.player_id = b.player_id AND b2.team = b.team AND b2.season = b.season - 2), b.goals_pg) * 0.2
                    + COALESCE((SELECT goals_pg FROM base b2
                        WHERE b2.player_id = b.player_id AND b2.team = b.team AND b2.season = b.season - 1), b.goals_pg) * 0.3
                    + b.goals_pg * 0.5
                ) AS roll_goals,
                (
                    COALESCE((SELECT score_inv_pg FROM base b2
                        WHERE b2.player_id = b.player_id AND b2.team = b.team AND b2.season = b.season - 2), b.score_inv_pg) * 0.2
                    + COALESCE((SELECT score_inv_pg FROM base b2
                        WHERE b2.player_id = b.player_id AND b2.team = b.team AND b2.season = b.season - 1), b.score_inv_pg) * 0.3
                    + b.score_inv_pg * 0.5
                ) AS roll_score_inv
            FROM base b
        ),
        z AS (
            SELECT
                r.*,
                (r.roll_disposals - AVG(r.roll_disposals) OVER (PARTITION BY r.season))
                    / NULLIF(STDDEV(r.roll_disposals) OVER (PARTITION BY r.season), 0) AS z_disp,
                (r.roll_goals - AVG(r.roll_goals) OVER (PARTITION BY r.season))
                    / NULLIF(STDDEV(r.roll_goals) OVER (PARTITION BY r.season), 0) AS z_goals,
                (r.roll_score_inv - AVG(r.roll_score_inv) OVER (PARTITION BY r.season))
                    / NULLIF(STDDEV(r.roll_score_inv) OVER (PARTITION BY r.season), 0) AS z_si,
                (r.games - AVG(r.games) OVER (PARTITION BY r.season))
                    / NULLIF(STDDEV(r.games) OVER (PARTITION BY r.season), 0) AS z_games
            FROM rolled r
        )
        SELECT
            z.player_id,
            z.team,
            z.season,
            z.games,
            LEAST(10, GREATEST(0,
                5.0
                + 0.35 * COALESCE(z.z_disp, 0)
                + 0.25 * COALESCE(z.z_goals, 0)
                + 0.25 * COALESCE(z.z_si, 0)
                + 0.15 * COALESCE(z.z_games, 0)
            )) AS performance_score,
            0.0 AS potential_score,
            0.0 AS pvs,
            0.0 AS age_perf_weight
        FROM z
        """
    )

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
    pv["pvs"] = (
        pv["age_perf_weight"] * pv["performance_score"]
        + (1 - pv["age_perf_weight"]) * pv["potential_score"]
    ).round(3)

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
