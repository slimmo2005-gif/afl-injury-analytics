"""Export aggregated metrics JSON for the static frontend."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np

from ..config import DEFAULT_SEASON, FRONTEND_DATA, HISTORICAL_MAX_SEASON, SHARED_OUTPUT
from ..transform.continuity import continuity_for_season
from ..transform.unavailability import GAMES_MISSED_STATUS_SQL
from .core22_impact import build_core22_impact_bundle
from .ladder_pvs_ranks import build_ladder_pvs_ranks_bundle
from ..transform.availability_adjustments import adjustment_key_injuries_index


def _finalize_player_injury_labels(
    entry: dict,
    *,
    player_id: str | None,
    team: str,
    season: int,
    manual_labels: dict[tuple[str, str, int], list[str]],
    episode_labels: list[str],
) -> None:
    """Merge episode, manual, and default labels for key-injuries display."""
    key: tuple[str, str, int] | None = None
    if player_id:
        key = (str(player_id), str(team), int(season))
    labels = list(manual_labels.get(key, [])) if key else []
    if not labels:
        labels = list(episode_labels)
    if not labels and entry.get("status") == "vfl_only":
        labels = ["VFL / not selected"]
    if labels:
        entry["keyInjuries"] = labels


def _linear_regression(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    if len(x) < 3:
        return 0.0, 0.0, 0.0
    coef = np.polyfit(x, y, 1)
    slope, intercept = float(coef[0]), float(coef[1])
    pred = intercept + slope * x
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 0.0
    return intercept, slope, r2


def _player_status(row, injury_pvs: float | None = None) -> str:
    """Display status for a missed player; avoid VFL label when injury PVS dominates."""
    pvs = injury_pvs if injury_pvs is not None else float(row.get("unavailable_pvs") or 0)
    if pvs > 0:
        if row.get("status") == "intermittent" or row.get("has_intermittent_missed"):
            return "intermittent"
        return "unavailable"
    if row.get("vfl_played") or row.get("any_vfl"):
        return "vfl_only"
    return "unavailable"


def build_season_bundle(
    con: duckdb.DuckDBPyConnection,
    season: int,
    default_club: str = "Collingwood",
    max_round: int | None = None,
) -> dict:
    round_filter_tr = " AND tr.round <= ?" if max_round is not None else ""
    round_filter_a = " AND a.round <= ?" if max_round is not None else ""
    round_filter_m = " AND round <= ?" if max_round is not None else ""
    round_filter_v = " AND round <= ?" if max_round is not None else ""
    base_params: list = [season]
    if max_round is not None:
        base_params.append(max_round)

    club_season = con.execute(
        f"""
        SELECT
            tr.team AS club,
            tr.season,
            SUM(COALESCE(v.unavailable_pvs_games_missed, 0)) AS unavailable_value,
            SUM(COALESCE(v.unavailable_pvs_top5, 0)) AS unavailable_top5,
            SUM(tr.players_unavailable) AS unavailable_slots,
            SUM(CASE WHEN tr.won THEN 1 ELSE 0 END) AS actual_wins,
            COUNT(*) AS rounds_with_data
        FROM team_round_summary tr
        LEFT JOIN team_round_value v
            ON tr.team = v.team AND tr.season = v.season AND tr.round = v.round
        WHERE tr.season = ?{round_filter_tr}
        GROUP BY tr.team, tr.season
        ORDER BY unavailable_value DESC
        """,
        base_params,
    ).df()

    if club_season.empty:
        raise ValueError(f"No data for season {season}")

    x = club_season["unavailable_value"].to_numpy(dtype=float)
    y = club_season["actual_wins"].to_numpy(dtype=float)
    intercept, slope, r2 = _linear_regression(x, y)
    club_season["expected_wins"] = (intercept + slope * x).clip(min=0)
    club_season["delta"] = club_season["actual_wins"] - club_season["expected_wins"]

    avg_unavail = float(club_season["unavailable_value"].mean() / club_season["rounds_with_data"].mean())
    above = int((club_season["delta"] > 0.5).sum())
    below = int((club_season["delta"] < -0.5).sum())
    corr = float(np.corrcoef(x, y)[0, 1]) if len(x) > 1 else 0.0

    clubs = club_season["club"].tolist()
    if default_club not in clubs:
        default_club = str(club_season.iloc[0]["club"])

    def _club_round_df(club: str):
        params = [season, club]
        if max_round is not None:
            params.append(max_round)
        df = con.execute(
            f"""
            SELECT
                tr.round,
                COALESCE(v.unavailable_pvs_games_missed, 0) AS value,
                COALESCE(v.unavailable_pvs_top5, 0) AS top5,
                CASE WHEN tr.won THEN 1 ELSE 0 END AS wins
            FROM team_round_summary tr
            LEFT JOIN team_round_value v
                ON tr.team = v.team AND tr.season = v.season AND tr.round = v.round
            WHERE tr.season = ? AND tr.team = ?{round_filter_tr}
            ORDER BY tr.round
            """,
            params,
        ).df()
        return df

    by_round = _club_round_df(default_club)
    club_series = {}
    for club in clubs:
        cdf = _club_round_df(club)
        club_series[club] = [
            {
                "round": int(r),
                "value": round(float(v), 1),
                "top5": round(float(t5), 1),
                "wins": int(w),
            }
            for r, v, t5, w in zip(cdf["round"], cdf["value"], cdf["top5"], cdf["wins"])
        ]

    top_params = list(base_params)
    top_players = con.execute(
        f"""
        SELECT
            a.player_name AS player,
            a.team AS club,
            MAX(a.status) AS status,
            BOOL_OR(a.status = 'intermittent' AND NOT a.afl_played) AS has_intermittent_missed,
            BOOL_OR(COALESCE(a.vfl_played, FALSE)) AS any_vfl,
            COUNT(*) FILTER (WHERE NOT a.afl_played) AS rounds_missed,
            COUNT(*) FILTER (
                WHERE NOT a.afl_played AND a.status IN {GAMES_MISSED_STATUS_SQL}
            ) AS injury_rounds_missed,
            MAX(COALESCE(v.injury_weight_pvs, v.pvs)) AS pvs,
            SUM(
                CASE
                    WHEN NOT a.afl_played AND a.status IN {GAMES_MISSED_STATUS_SQL}
                    THEN COALESCE(v.injury_weight_pvs, v.pvs)
                    ELSE 0
                END
            ) AS unavailable_pvs
        FROM availability a
        JOIN player_value v
            ON a.player_id = v.player_id AND a.team = v.team AND a.season = v.season
        WHERE a.season = ?{round_filter_a}
            GROUP BY a.player_id, a.player_name, a.team
            HAVING injury_rounds_missed > 0
            ORDER BY unavailable_pvs DESC
            LIMIT 10
        """,
        top_params,
    ).df()

    vfl_params: list = [season]
    if max_round is not None:
        vfl_params.append(max_round)
    vfl_summary = con.execute(
        f"""
        SELECT COALESCE(SUM(unavailable_pvs_vfl_only), 0)
        FROM team_round_value WHERE season = ?{round_filter_v}
        """,
        vfl_params,
    ).fetchone()[0]

    continuity = continuity_for_season(con, season)

    # Margin regression (club-season): unavailable PVS vs avg margin
    margin_params = [season, season, season]
    if max_round is not None:
        margin_params.extend([max_round, max_round, max_round])
    margins = con.execute(
        f"""
        WITH team_margin AS (
            SELECT season, home_team AS team, home_score - away_score AS margin, round
            FROM matches WHERE season = ?{round_filter_m}
            UNION ALL
            SELECT season, away_team, away_score - home_score, round
            FROM matches WHERE season = ?{round_filter_m}
        ),
        club_margin AS (
            SELECT team, AVG(margin) AS avg_margin FROM team_margin GROUP BY team
        ),
        club_unavail AS (
            SELECT team, SUM(unavailable_pvs_total) AS unavail
            FROM team_round_value WHERE season = ?{round_filter_v} GROUP BY team
        )
        SELECT c.team, c.avg_margin, u.unavail
        FROM club_margin c
        JOIN club_unavail u ON c.team = u.team
        """,
        margin_params,
    ).df()

    margin_r2 = 0.0
    margin_slope = 0.0
    if len(margins) >= 3:
        mx = margins["unavail"].to_numpy(dtype=float)
        my = margins["avg_margin"].to_numpy(dtype=float)
        _, margin_slope, margin_r2 = _linear_regression(mx, my)

    player_rows = [
        {
            "player": row["player"],
            "club": row["club"],
            "roundsMissed": int(row["injury_rounds_missed"]),
            "pvs": round(float(row["pvs"]), 1),
            "unavailablePvs": round(float(row["unavailable_pvs"]), 1),
            "status": _player_status(row, float(row["unavailable_pvs"])),
        }
        for _, row in top_players.iterrows()
    ]

    club_top_params = list(base_params) + [season]
    club_top_players = con.execute(
        f"""
        WITH player_agg AS (
            SELECT
                a.player_id,
                a.player_name AS player,
                a.team AS club,
                MAX(a.status) AS status,
                BOOL_OR(COALESCE(a.vfl_played, FALSE)) AS any_vfl,
            BOOL_OR(a.status = 'intermittent' AND NOT a.afl_played) AS has_intermittent_missed,
            COUNT(*) FILTER (WHERE NOT a.afl_played) AS rounds_missed,
            COUNT(*) FILTER (
                WHERE NOT a.afl_played AND a.status IN {GAMES_MISSED_STATUS_SQL}
            ) AS injury_rounds_missed,
            MAX(COALESCE(v.injury_weight_pvs, v.pvs)) AS pvs,
                SUM(
                    CASE
                        WHEN NOT a.afl_played AND a.status IN {GAMES_MISSED_STATUS_SQL}
                        THEN COALESCE(v.injury_weight_pvs, v.pvs)
                        ELSE 0
                    END
                ) AS unavailable_pvs
            FROM availability a
            JOIN player_value v
                ON a.player_id = v.player_id AND a.team = v.team AND a.season = v.season
            WHERE a.season = ?{round_filter_a}
            GROUP BY a.player_id, a.player_name, a.team
            HAVING injury_rounds_missed > 0
        ),
        injury_labels AS (
            SELECT
                e.player_id,
                e.team,
                list(DISTINCT e.injury_type ORDER BY e.injury_type) AS injury_types
            FROM absence_episodes e
            WHERE e.season = ?
              AND e.injury_type IS NOT NULL
              AND TRIM(e.injury_type) != ''
            GROUP BY e.player_id, e.team
        ),
        ranked AS (
            SELECT
                p.player_id,
                p.player,
                p.club,
                p.status,
                p.any_vfl,
                p.rounds_missed,
                p.injury_rounds_missed,
                p.pvs,
                p.unavailable_pvs,
                i.injury_types,
                ROW_NUMBER() OVER (
                    PARTITION BY p.club ORDER BY p.unavailable_pvs DESC, p.injury_rounds_missed DESC
                ) AS rn
            FROM player_agg p
            LEFT JOIN injury_labels i
                ON p.player_id = i.player_id AND p.club = i.team
        )
        SELECT * FROM ranked WHERE rn <= 5
        ORDER BY club, rn
        """,
        club_top_params,
    ).df()

    manual_labels = adjustment_key_injuries_index()
    top_by_club: dict[str, list] = {}
    for _, row in club_top_players.iterrows():
        injury_pvs = float(row["unavailable_pvs"])
        status = _player_status(row, injury_pvs)
        raw_injuries = row["injury_types"]
        episode_labels: list[str] = []
        if raw_injuries is not None:
            try:
                episode_labels = [str(x) for x in list(raw_injuries) if x]
            except TypeError:
                episode_labels = []
        entry = {
            "player": row["player"],
            "club": row["club"],
            "roundsMissed": int(row["injury_rounds_missed"]),
            "pvs": round(float(row["pvs"]), 1),
            "unavailablePvs": round(float(row["unavailable_pvs"]), 1),
            "status": status,
        }
        _finalize_player_injury_labels(
            entry,
            player_id=str(row["player_id"]),
            team=str(row["club"]),
            season=season,
            manual_labels=manual_labels,
            episode_labels=episode_labels,
        )
        top_by_club.setdefault(str(row["club"]), []).append(entry)

    return {
        "leagueOverview": {
            "avgUnavailableValue": round(avg_unavail, 1),
            "totalVflOnlyPvs": round(float(vfl_summary), 1),
            "clubsAboveExpectation": above,
            "clubsBelowExpectation": below,
            "topUnavailableClub": str(club_season.iloc[0]["club"]),
            "correlationUnavailableToWins": round(corr, 2),
        },
        "clubUnavailableByRound": [
            {
                "round": int(r),
                "value": round(float(v), 1),
                "top5": round(float(t5), 1),
                "wins": int(w),
            }
            for r, v, t5, w in zip(by_round["round"], by_round["value"], by_round["top5"], by_round["wins"])
        ],
        "clubRankings": [
            {
                "club": row["club"],
                "unavailableValue": round(float(row["unavailable_value"]), 1),
                "unavailableTop5": round(float(row["unavailable_top5"]), 1),
                "expectedWins": round(float(row["expected_wins"]), 1),
                "actualWins": int(row["actual_wins"]),
                "delta": round(float(row["delta"]), 1),
            }
            for _, row in club_season.sort_values("club").iterrows()
        ],
        "topUnavailablePlayers": player_rows,
        "topUnavailableByClub": top_by_club,
        "continuity": continuity or [{"archetype": "League avg", "changes": 0, "score": 0.0}],
        "regression": {
            "model": "linear",
            "rSquared": round(r2, 2),
            "marginRSquared": round(margin_r2, 2),
            "coefficients": {
                "intercept": round(intercept, 2),
                "unavailablePvs": round(slope, 4),
                "marginPer100Pvs": round(margin_slope * 100, 2),
            },
            "interpretation": (
                f"Each +100 unavailable PVS correlates with ~{abs(slope * 100):.1f} "
                f"{'fewer' if slope < 0 else 'more'} wins (season {season}). "
                f"PVS combines weighted season performance (normalised 0–7, leader = 7) "
                f"with an optional draft-potential top-up for players not yet impacting games."
            ),
        },
        "clubs": clubs,
        "defaultClub": default_club,
        "clubSeries": club_series,
    }


def build_metrics_bundle(
    con: duckdb.DuckDBPyConnection,
    season: int = DEFAULT_SEASON,
    export_all_seasons: bool = True,
    historical_max_season: int | None = HISTORICAL_MAX_SEASON,
) -> dict:
    seasons_df = con.execute(
        "SELECT DISTINCT season FROM team_round_value ORDER BY season"
    ).df()
    seasons = [int(s) for s in seasons_df["season"].tolist()]
    if historical_max_season is not None:
        seasons = [s for s in seasons if s <= historical_max_season]
    if not seasons:
        seasons = [season]

    season_bundles = {}
    for s in seasons:
        try:
            season_bundles[str(s)] = build_season_bundle(con, s)
        except ValueError as exc:
            print(f"[export] skip season {s}: {exc}")

    if not season_bundles:
        raise ValueError("No season bundles exported")

    primary_key = str(season) if str(season) in season_bundles else list(season_bundles.keys())[-1]
    primary = season_bundles[primary_key]

    return {
        "meta": {
            "season": int(primary_key),
            "round": int(
                max((r["round"] for r in primary["clubUnavailableByRound"]), default=0)
            ),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "note": f"Phase 2 — PVS + national draft + VFL ({primary_key})",
            "dataSource": "Squiggle + Fryzigg + Draftguru + VFL",
            "defaultSeason": int(primary_key),
            "seasons": [int(s) for s in season_bundles.keys()],
        },
        "seasons": season_bundles,
        "core22Impact": build_core22_impact_bundle(con),
        "ladderPvsRanks": build_ladder_pvs_ranks_bundle(con),
        **primary,
    }


def write_metrics(
    con: duckdb.DuckDBPyConnection,
    season: int = DEFAULT_SEASON,
    out_dir: Path | None = None,
) -> Path:
    bundle = build_metrics_bundle(con, season=season)
    targets = [out_dir or SHARED_OUTPUT, FRONTEND_DATA]
    written: Path | None = None
    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        path = target / "metrics.json"
        path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        written = path
    assert written is not None
    return written
