"""Map state-league game dates to AFL rounds."""

from __future__ import annotations

from datetime import date, datetime

import duckdb
import pandas as pd


def _as_date(value: date | datetime | str | None) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return pd.to_datetime(value).date()
    except (TypeError, ValueError):
        return None


def build_afl_round_calendar(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Earliest match_date per AFL team/season/round."""
    return con.execute(
        """
        SELECT
            team,
            season,
            round,
            MIN(match_date) AS round_date
        FROM player_games
        WHERE match_date IS NOT NULL
        GROUP BY 1, 2, 3
        """
    ).df()


def map_game_dates_to_afl_rounds(
    games: pd.DataFrame,
    round_calendar: pd.DataFrame,
    *,
    max_days: int = 7,
) -> pd.DataFrame:
    """Attach AFL round numbers using nearest team round date."""
    if games.empty:
        return games

    out = games.copy()
    out["game_date"] = pd.to_datetime(out["game_date"], errors="coerce").dt.date
    out["round"] = pd.NA

    cal = round_calendar.copy()
    cal["round_date"] = pd.to_datetime(cal["round_date"], errors="coerce").dt.date
    cal = cal.dropna(subset=["round_date"])

    mapped: list[pd.DataFrame] = []
    for (team, season), grp in out.groupby(["afl_club", "season"], dropna=False):
        team_cal = cal[(cal["team"] == team) & (cal["season"] == season)] if pd.notna(team) else pd.DataFrame()

        rows: list[dict] = []
        for _, row in grp.iterrows():
            game_date = _as_date(row["game_date"])
            rnd = pd.NA
            if game_date is None and pd.notna(row.get("state_round")):
                rnd = int(row["state_round"])
            elif pd.notna(team) and game_date is not None and not team_cal.empty:
                deltas = team_cal.assign(
                    delta=team_cal["round_date"].apply(
                        lambda rd: abs((rd - game_date).days) if rd else 9999
                    )
                )
                best = deltas[deltas["delta"] <= max_days].sort_values("delta")
                if not best.empty:
                    rnd = int(best.iloc[0]["round"])
            item = row.to_dict()
            item["round"] = rnd
            rows.append(item)
        mapped.append(pd.DataFrame(rows))

    if not mapped:
        return out
    result = pd.concat(mapped, ignore_index=True)
    missing = result["round"].isna().sum()
    if missing:
        print(f"[state_league] warning: {missing} games could not be mapped to an AFL round")
    return result
