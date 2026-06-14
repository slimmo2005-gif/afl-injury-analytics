"""Simulate PVS archetype balance when adding MI50 / intercept marks weights."""

from __future__ import annotations

import itertools

import duckdb
import pandas as pd
import pyreadr

from data_pipeline.config import DB_PATH, FRYZIGG_RDS_FILE
from data_pipeline.db import connect
from data_pipeline.ingest.fryzigg import normalize_team
from data_pipeline.transform.archetypes import ARCHETYPE_LABELS, resolve_archetype
from data_pipeline.transform.pvs import (
    PERFORMANCE_METRICS,
    age_performance_weight,
    compute_pvs,
    draft_potential_score,
)

BASE_WEIGHTS = dict((alias, w) for _c, alias, w in PERFORMANCE_METRICS)


def load_2024_stats() -> pd.DataFrame:
    connect().close()
    con = duckdb.connect(str(DB_PATH), read_only=True)
    ratings = con.execute(
        """
        SELECT v.player_id, p.player_name, v.team, p.archetype, p.age_est, p.draft_pick,
               v.performance_score AS old_perf, v.pvs AS old_pvs
        FROM player_value v
        JOIN player_profiles p
          ON v.player_id = p.player_id AND v.team = p.team AND v.season = p.season
        WHERE v.season = 2024
        """
    ).df()
    con.close()

    raw = pyreadr.read_r(str(FRYZIGG_RDS_FILE))[None]
    raw["match_date"] = pd.to_datetime(raw["match_date"], errors="coerce")
    raw = raw[raw["match_date"].dt.year == 2024].copy()
    raw["player_id"] = raw["player_id"].astype(str)
    raw["team"] = raw["player_team"].map(normalize_team)
    num_cols = [
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
    ]
    for col in num_cols:
        raw[col] = pd.to_numeric(raw.get(col, 0), errors="coerce").fillna(0)
    if "disposal_efficiency_percentage" in raw.columns:
        de = pd.to_numeric(raw["disposal_efficiency_percentage"], errors="coerce").fillna(72.0)
    else:
        de = 72.0
    raw["metres_per100"] = raw["metres_gained"] / 100.0
    raw["effective_disposals"] = raw["disposals"] * de / 100.0

    agg = {f"{c}_pg": (c, "mean") for c in num_cols + ["metres_per100", "effective_disposals"]}
    agg["fryzigg_position"] = ("player_position", lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else None)
    stats = raw.groupby(["player_id", "team"], as_index=False).agg(
        **{k: pd.NamedAgg(column=v[0], aggfunc=v[1]) for k, v in agg.items()}
    )
    stats = stats.rename(
        columns={
            "score_involvements_pg": "score_inv_pg",
            "hitouts_to_advantage_pg": "hota_pg",
            "metres_per100_pg": "metres_per100_pg",
        }
    )
    return ratings.merge(stats, on=["player_id", "team"], how="left")


def score_with_weights(df: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    out = df.copy()
    raw = 0.0
    for alias, w in weights.items():
        if alias in out.columns:
            raw = raw + w * out[alias].fillna(0)
    out["raw_composite"] = raw
    league_max = out["raw_composite"].max() or 1.0
    out["performance_score"] = 7.0 * out["raw_composite"] / league_max
    out["potential_score"] = out["draft_pick"].map(draft_potential_score)
    out["age_perf_weight"] = out["age_est"].map(age_performance_weight)
    out["pvs"] = out.apply(
        lambda r: compute_pvs(r["performance_score"], r["potential_score"], r["age_perf_weight"]),
        axis=1,
    )
    return out


def archetype_summary(df: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    league = df["pvs"].mean()
    for arch, g in df.groupby("archetype"):
        rows.append(
            {
                "label": label,
                "archetype": arch,
                "n": len(g),
                "avg_pvs": g["pvs"].mean(),
                "vs_league": g["pvs"].mean() - league,
                "avg_perf": g["performance_score"].mean(),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    df = load_2024_stats()
    league_avg = df["old_pvs"].mean()
    print(f"OLD league avg PVS: {league_avg:.3f}")
    old = archetype_summary(
        df.assign(pvs=df["old_pvs"], performance_score=df["old_perf"]),
        "old",
    ).sort_values("avg_pvs", ascending=False)
    print(old.to_string(index=False))

    # grid search
    best = None
    for mi50_w, im_w, cm_adj, int_adj in itertools.product(
        [0.08, 0.10, 0.12, 0.14, 0.16],
        [0.04, 0.06, 0.08, 0.10],
        [-0.02, -0.03, -0.04],
        [-0.01, -0.02, -0.03],
    ):
        w = dict(BASE_WEIGHTS)
        w["marks_inside_fifty_pg"] = mi50_w
        w["intercept_marks_pg"] = im_w
        w["contested_marks_pg"] = w.get("contested_marks_pg", 0.09) + cm_adj
        w["intercepts_pg"] = w.get("intercepts_pg", 0.09) + int_adj
        if w["contested_marks_pg"] < 0.04 or w["intercepts_pg"] < 0.04:
            continue

        scored = score_with_weights(df, w)
        summ = scored.groupby("archetype").agg(avg_pvs=("pvs", "mean"), avg_perf=("performance_score", "mean"))
        im_avg = summ.loc["inside_mid", "avg_pvs"] if "inside_mid" in summ.index else 0
        kf_avg = summ.loc["key_forward", "avg_pvs"] if "key_forward" in summ.index else 0
        kd_avg = summ.loc["key_defender", "avg_pvs"] if "key_defender" in summ.index else 0
        om_avg = summ.loc["outside_mid", "avg_pvs"] if "outside_mid" in summ.index else 0
        league = scored["pvs"].mean()

        # objectives: mids highest, kf/kd near league (~0), im still above kf/kd
        kf_gap = abs(kf_avg - league)
        kd_gap = abs(kd_avg - league)
        mid_lead = im_avg - max(kf_avg, kd_avg, om_avg)
        if mid_lead < 0.8:
            continue
        if kf_avg < league - 0.15 or kf_avg > league + 0.25:
            continue
        if kd_avg < league - 0.25 or kd_avg > league + 0.25:
            continue

        obj = kf_gap + kd_gap - mid_lead * 0.1
        if best is None or obj < best[0]:
            best = (obj, mi50_w, im_w, cm_adj, int_adj, summ, im_avg, kf_avg, kd_avg, league)

    if best:
        _, mi50_w, im_w, cm_adj, int_adj, summ, im_avg, kf_avg, kd_avg, league = best
        print(f"\nBEST mi50={mi50_w} im={im_w} cm_adj={cm_adj} int_adj={int_adj}")
        print(f"league={league:.3f} inside_mid={im_avg:.3f} key_forward={kf_avg:.3f} key_defender={kd_avg:.3f}")
        print(summ.sort_values("avg_pvs", ascending=False))
    else:
        print("No config met constraints; relaxing...")
        for mi50_w, im_w in [(0.12, 0.07), (0.14, 0.06), (0.10, 0.08)]:
            w = dict(BASE_WEIGHTS)
            w["marks_inside_fifty_pg"] = mi50_w
            w["intercept_marks_pg"] = im_w
            w["contested_marks_pg"] = 0.06
            w["intercepts_pg"] = 0.07
            scored = score_with_weights(df, w)
            summ = scored.groupby("archetype")["pvs"].mean().sort_values(ascending=False)
            print(f"\nmi50={mi50_w} im={im_w} cm=0.06 int=0.07 league={scored.pvs.mean():.3f}")
            print(summ)


if __name__ == "__main__":
    main()
