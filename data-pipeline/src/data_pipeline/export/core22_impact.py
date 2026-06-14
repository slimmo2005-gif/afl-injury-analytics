"""Export core-22 missed PVS impact on wins for the frontend."""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from ..transform.archetypes import ARCHETYPE_LABELS

ARCHETYPES = [
    "inside_mid",
    "outside_mid",
    "rebound_defender",
    "key_defender",
    "key_forward",
    "pressure_forward",
    "ruck",
    "utility",
]

FROM_SEASON = 2018
TO_SEASON = 2024
CORE_SIZE = 22
ROLLING_WINDOW = 4
ROLLING_MIN = 2
STAR_PVS = 4.0


def _corr(x: pd.Series, y: pd.Series) -> float:
    mask = x.notna() & y.notna()
    if mask.sum() < 10:
        return 0.0
    xv, yv = x[mask].astype(float), y[mask].astype(float)
    if xv.std() == 0 or yv.std() == 0:
        return 0.0
    return float(np.corrcoef(xv, yv)[0, 1])


def _ols(df: pd.DataFrame, y: str, xs: list[str]) -> tuple[list[dict], float]:
    sub = df[[y, *xs]].dropna()
    if len(sub) < len(xs) + 5:
        return [], 0.0
    yv = sub[y].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(sub)), sub[xs].to_numpy(dtype=float)])
    beta, *_ = np.linalg.lstsq(X, yv, rcond=None)
    ss_res = ((yv - X @ beta) ** 2).sum()
    ss_tot = ((yv - yv.mean()) ** 2).sum()
    r2 = float(1 - ss_res / ss_tot) if ss_tot else 0.0
    rows = [{"term": "intercept", "coef": round(float(beta[0]), 5)}]
    for i, col in enumerate(xs, 1):
        rows.append({"term": col, "coef": round(float(beta[i]), 5)})
    return rows, r2


def _load_base(con: duckdb.DuckDBPyConnection) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ha_rounds = con.execute(
        f"""
        SELECT season, round
        FROM matches
        WHERE season BETWEEN {FROM_SEASON} AND {TO_SEASON} AND round > 0
        GROUP BY 1, 2
        HAVING COUNT(*) > 4
        """
    ).df()

    played = con.execute(
        f"""
        SELECT DISTINCT pg.player_id, pg.team, pg.season, pg.round
        FROM player_games pg
        INNER JOIN ha_rounds r ON pg.season = r.season AND pg.round = r.round
        WHERE pg.season BETWEEN {FROM_SEASON} AND {TO_SEASON}
        """
    ).df()
    played["played"] = 1

    meta = con.execute(
        f"""
        SELECT v.player_id, v.team, v.season, v.pvs, p.archetype
        FROM player_value v
        JOIN player_profiles p
            ON v.player_id = p.player_id AND v.team = p.team AND v.season = p.season
        WHERE v.season BETWEEN {FROM_SEASON} AND {TO_SEASON}
        """
    ).df()

    outcomes = con.execute(
        f"""
        WITH team_margin AS (
            SELECT season, round, home_team AS team, home_score - away_score AS margin
            FROM matches
            WHERE season BETWEEN {FROM_SEASON} AND {TO_SEASON}
            UNION ALL
            SELECT season, round, away_team, away_score - home_score
            FROM matches
            WHERE season BETWEEN {FROM_SEASON} AND {TO_SEASON}
        )
        SELECT trs.team, trs.season, trs.round, CAST(trs.won AS INT) AS won, tm.margin
        FROM team_round_summary trs
        LEFT JOIN team_margin tm
            ON trs.team = tm.team AND trs.season = tm.season AND trs.round = tm.round
        INNER JOIN ha_rounds r ON trs.season = r.season AND trs.round = r.round
        WHERE trs.season BETWEEN {FROM_SEASON} AND {TO_SEASON}
          AND trs.won IS NOT NULL
        """
    ).df()
    return played, meta, outcomes


def _missed_from_expected(
    expected: pd.DataFrame, played: pd.DataFrame, meta: pd.DataFrame
) -> pd.DataFrame:
    exp = expected.merge(meta, on=["player_id", "team", "season"], how="left")
    act = played.rename(columns={"played": "did_play"})
    merged = exp.merge(act, on=["player_id", "team", "season", "round"], how="left")
    merged["did_play"] = merged["did_play"].fillna(0).astype(int)
    missed = merged[merged["did_play"] == 0].copy()
    missed["missed_pvs"] = missed["pvs"].fillna(0)

    by_arch = (
        missed.groupby(["team", "season", "round", "archetype"], as_index=False)
        .agg(missed_pvs=("missed_pvs", "sum"))
    )
    pivot = (
        by_arch.pivot_table(
            index=["team", "season", "round"],
            columns="archetype",
            values="missed_pvs",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reindex(columns=ARCHETYPES, fill_value=0.0)
        .add_prefix("miss_")
        .reset_index()
    )
    pivot["missed_pvs_total"] = pivot[[f"miss_{a}" for a in ARCHETYPES]].sum(axis=1)
    pivot["miss_key_roles"] = pivot["miss_key_forward"] + pivot["miss_key_defender"]
    pivot["miss_mid"] = pivot["miss_inside_mid"] + pivot["miss_outside_mid"]
    pivot["miss_other_roles"] = pivot["missed_pvs_total"] - pivot["miss_key_roles"]
    counts = missed.groupby(["team", "season", "round"], as_index=False).size()
    counts = counts.rename(columns={"size": "core_missed_count"})
    pivot = pivot.merge(counts, on=["team", "season", "round"], how="left")
    pivot["core_missed_count"] = pivot["core_missed_count"].fillna(0).astype(int)
    return pivot


def _prior_round_22(played: pd.DataFrame) -> pd.DataFrame:
    prev = played.copy()
    prev["round"] = prev["round"] + 1
    return prev[["player_id", "team", "season", "round"]].drop_duplicates()


def _rolling_pvs_22(played: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    rounds = played[["team", "season", "round"]].drop_duplicates()
    rows: list[dict] = []
    for (team, season), grp in rounds.groupby(["team", "season"]):
        season_played = played[(played.team == team) & (played.season == season)]
        season_meta = meta[(meta.team == team) & (meta.season == season)]
        for rnd in grp["round"].tolist():
            prior = season_played[
                (season_played["round"] >= rnd - ROLLING_WINDOW) & (season_played["round"] < rnd)
            ]
            if prior.empty:
                continue
            apps = prior.groupby("player_id").size().reset_index(name="apps")
            pool = apps[apps["apps"] >= ROLLING_MIN].merge(
                season_meta[["player_id", "pvs"]], on="player_id", how="inner"
            )
            if pool.empty:
                continue
            for pid in pool.nlargest(min(CORE_SIZE, len(pool)), "pvs")["player_id"]:
                rows.append({"player_id": pid, "team": team, "season": season, "round": rnd})
    return pd.DataFrame(rows)


def _season_pvs_22(meta: pd.DataFrame, played: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    gp = played.groupby(["player_id", "team", "season"]).size().reset_index(name="games")
    for (team, season), m in meta.groupby(["team", "season"]):
        eligible = m.merge(
            gp[(gp.team == team) & (gp.season == season) & (gp.games >= 5)],
            on=["player_id", "team", "season"],
            how="inner",
        )
        if len(eligible) < 10:
            continue
        core = eligible.nlargest(min(CORE_SIZE, len(eligible)), "pvs")
        season_rounds = played[(played.team == team) & (played.season == season)][["round"]].drop_duplicates()
        for rnd in season_rounds["round"]:
            for pid in core["player_id"]:
                rows.append({"player_id": pid, "team": team, "season": season, "round": rnd})
    return pd.DataFrame(rows)


def _summarise_method(df: pd.DataFrame, method_id: str, label: str) -> dict:
    role_metrics = []
    for arch in ARCHETYPES:
        col = f"miss_{arch}"
        role_metrics.append(
            {
                "role": ARCHETYPE_LABELS[arch],
                "roleId": arch,
                "corrWin": round(_corr(df[col], df["won"]), 3),
                "corrMargin": round(_corr(df[col], df["margin"]), 3),
                "avgMissPvs": round(float(df[col].mean()), 2),
                "pctRounds": round(100 * float((df[col] > 0).mean()), 1),
            }
        )
    for col, role, role_id in [
        ("missed_pvs_total", "Total core missed", "total"),
        ("miss_key_roles", "Key FWD + DEF", "key_roles"),
        ("miss_mid", "Inside + outside mid", "mid"),
    ]:
        role_metrics.append(
            {
                "role": role,
                "roleId": role_id,
                "corrWin": round(_corr(df[col], df["won"]), 3),
                "corrMargin": round(_corr(df[col], df["margin"]), 3),
                "avgMissPvs": round(float(df[col].mean()), 2),
                "pctRounds": round(100 * float((df[col] > 0).mean()), 1),
            }
        )

    star_miss = []
    for arch in ARCHETYPES:
        col = f"miss_{arch}"
        star = df[df[col] >= STAR_PVS]
        clean = df[df[col] == 0]
        if star.empty:
            continue
        star_miss.append(
            {
                "role": ARCHETYPE_LABELS[arch],
                "roleId": arch,
                "rounds": int(len(star)),
                "winWhenMiss": round(float(star.won.mean()), 3),
                "winOtherwise": round(float(clean.won.mean()), 3) if len(clean) else 0.5,
                "deltaPp": round(100 * (float(star.won.mean()) - float(clean.won.mean())), 1)
                if len(clean)
                else 0.0,
            }
        )
    star_miss.sort(key=lambda r: r["deltaPp"])

    arch_cols = [f"miss_{a}" for a in ARCHETYPES]
    coef_rows, arch_r2 = _ols(df, "won", arch_cols)
    coefficients = [
        {
            "role": ARCHETYPE_LABELS.get(r["term"].replace("miss_", ""), r["term"]),
            "roleId": r["term"].replace("miss_", ""),
            "coef": r["coef"],
        }
        for r in coef_rows
        if r["term"] != "intercept"
    ]
    split_rows, split_r2 = _ols(df, "won", ["miss_key_roles", "miss_other_roles"])
    key_coef = next((r["coef"] for r in split_rows if r["term"] == "miss_key_roles"), 0.0)
    other_coef = next((r["coef"] for r in split_rows if r["term"] == "miss_other_roles"), 0.0)

    impact = []
    for arch in ARCHETYPES:
        col = f"miss_{arch}"
        sub = df[[col, "won", "margin"]].dropna()
        if sub[col].std() == 0:
            continue
        bw = np.polyfit(sub[col], sub["won"], 1)
        bm = np.polyfit(sub[col], sub["margin"], 1)
        impact.append(
            {
                "role": ARCHETYPE_LABELS[arch],
                "roleId": arch,
                "winPctPer100": round(float(bw[0] * 100), 2),
                "marginPer100": round(float(bm[0] * 100), 2),
            }
        )
    impact.sort(key=lambda r: r["winPctPer100"])

    yearly = []
    for season, g in df.groupby("season"):
        yearly.append(
            {
                "season": int(season),
                "total": round(_corr(g.missed_pvs_total, g.won), 3),
                "keyRoles": round(_corr(g.miss_key_roles, g.won), 3),
                "keyForward": round(_corr(g.miss_key_forward, g.won), 3),
                "keyDefender": round(_corr(g.miss_key_defender, g.won), 3),
                "mid": round(_corr(g.miss_mid, g.won), 3),
            }
        )

    return {
        "id": method_id,
        "label": label,
        "teamRounds": int(len(df)),
        "avgMissedPvs": round(float(df.missed_pvs_total.mean()), 2),
        "avgPlayersMissed": round(float(df.core_missed_count.mean()), 2),
        "winRate": round(float(df.won.mean()), 3),
        "correlations": sorted(role_metrics, key=lambda r: r["corrWin"]),
        "marginalImpact": impact,
        "starMiss": star_miss,
        "coefficients": coefficients,
        "archetypeModelR2": round(arch_r2, 4),
        "keyVsOther": {
            "keyRolesCoef": key_coef,
            "otherRolesCoef": other_coef,
            "r2": round(split_r2, 4),
        },
        "yearly": yearly,
    }


def build_core22_impact_bundle(con: duckdb.DuckDBPyConnection) -> dict:
    played, meta, outcomes = _load_base(con)
    methods = []
    specs = [
        ("priorRound", "Prior round 22 (last week's team)", _prior_round_22(played)),
        (
            "rollingTop22",
            f"Rolling top-{CORE_SIZE} PVS (≥{ROLLING_MIN} of last {ROLLING_WINDOW} rounds)",
            _rolling_pvs_22(played, meta),
        ),
        (
            "seasonTop22",
            f"Season top-{CORE_SIZE} PVS (5+ games)",
            _season_pvs_22(meta, played),
        ),
    ]
    for method_id, label, expected in specs:
        if expected.empty:
            continue
        missed = _missed_from_expected(expected, played, meta)
        df = outcomes.merge(missed, on=["team", "season", "round"], how="inner").fillna(0)
        methods.append(_summarise_method(df, method_id, label))

    return {
        "fromSeason": FROM_SEASON,
        "toSeason": TO_SEASON,
        "starPvsThreshold": STAR_PVS,
        "methods": methods,
        "interpretation": (
            "Core-22 analysis counts misses only from expected selected players, not the full "
            "extended squad. Outside midfield absences correlate most strongly with losses; "
            "key defender star absences show a clearer win-rate drop than key forwards. "
            "Total missed PVS still matters more than role alone."
        ),
    }
