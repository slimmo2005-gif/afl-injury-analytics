"""Export injury episodes and absence-reason reporting."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from ..config import SHARED_OUTPUT


def export_injury_episodes(
    con: duckdb.DuckDBPyConnection,
    *,
    season: int | None = None,
    out_dir: Path | None = None,
) -> Path:
    out = out_dir or (SHARED_OUTPUT / "exports")
    out.mkdir(parents=True, exist_ok=True)

    season_filter = f"AND e.season = {season}" if season else ""

    episodes = con.execute(
        f"""
        SELECT
            e.player_id,
            e.player_name,
            e.team,
            e.season,
            e.start_round,
            e.end_round,
            e.weeks,
            e.absence_reason,
            e.injury_type,
            e.injury_category,
            e.source,
            e.confidence,
            p.archetype,
            p.age_est,
            COALESCE(v.injury_weight_pvs, v.pvs) AS pvs
        FROM absence_episodes e
        LEFT JOIN player_profiles p
            ON e.player_id = p.player_id
            AND e.team = p.team
            AND e.season = p.season
        LEFT JOIN player_value v
            ON e.player_id = v.player_id
            AND e.team = v.team
            AND e.season = v.season
        WHERE 1=1 {season_filter}
        ORDER BY e.season DESC, e.weeks DESC, pvs DESC NULLS LAST
        """
    ).df()

    by_injury = con.execute(
        f"""
        SELECT
            e.season,
            COALESCE(e.injury_category, 'unknown') AS injury_category,
            COALESCE(e.injury_type, 'unknown') AS injury_type,
            COUNT(*) AS episodes,
            SUM(e.weeks) AS total_weeks,
            ROUND(AVG(e.weeks), 1) AS avg_weeks_per_episode,
            ROUND(SUM(COALESCE(v.injury_weight_pvs, v.pvs) * e.weeks), 1) AS pvs_weeks_lost
        FROM absence_episodes e
        LEFT JOIN player_value v
            ON e.player_id = v.player_id
            AND e.team = v.team
            AND e.season = v.season
        WHERE e.absence_reason = 'injury' {season_filter.replace('e.', 'e.')}
        GROUP BY 1, 2, 3
        ORDER BY total_weeks DESC
        """
    ).df()

    by_archetype = con.execute(
        f"""
        SELECT
            e.season,
            COALESCE(p.archetype, 'unknown') AS archetype,
            COALESCE(e.injury_category, 'unknown') AS injury_category,
            COUNT(*) AS episodes,
            SUM(e.weeks) AS total_weeks,
            ROUND(AVG(e.weeks), 1) AS avg_weeks
        FROM absence_episodes e
        LEFT JOIN player_profiles p
            ON e.player_id = p.player_id
            AND e.team = p.team
            AND e.season = p.season
        WHERE e.absence_reason = 'injury' {season_filter}
        GROUP BY 1, 2, 3
        ORDER BY total_weeks DESC
        """
    ).df()

    suffix = f"_{season}" if season else "_all"
    xlsx = out / f"injury_episodes{suffix}.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        episodes.to_excel(writer, sheet_name="episodes", index=False)
        by_injury.to_excel(writer, sheet_name="by_injury_type", index=False)
        by_archetype.to_excel(writer, sheet_name="by_archetype", index=False)

    print(f"[export] injury episodes -> {xlsx}")
    return xlsx
