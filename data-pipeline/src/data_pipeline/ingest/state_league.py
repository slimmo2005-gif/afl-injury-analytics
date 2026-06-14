"""Unified state-league participation ingest (VFL, SANFL, WAFL)."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from ..config import MIN_SEASON
from .sanfl import fetch_sanfl_games, load_sanfl_affiliate_map
from .state_league_rounds import build_afl_round_calendar, map_game_dates_to_afl_rounds
from .vfl import fetch_vfl_games
from .wafl_sportix import fetch_wafl_games

STATE_LEAGUE_FROM_SEASON = 2018


def fetch_state_league_games(
    from_season: int = STATE_LEAGUE_FROM_SEASON,
    to_season: int | None = None,
    *,
    include_vfl: bool = True,
    include_sanfl: bool = True,
    include_wafl: bool = True,
    pause: float = 0.15,
) -> pd.DataFrame:
    to_season = to_season or datetime.now().year
    parts: list[pd.DataFrame] = []

    if include_vfl:
        vfl_df = fetch_vfl_games(from_season=from_season, to_season=to_season, pause=pause)
        if not vfl_df.empty:
            parts.append(vfl_df)
    if include_sanfl:
        sanfl_df = fetch_sanfl_games(from_season=from_season, to_season=to_season, pause=pause)
        if not sanfl_df.empty:
            parts.append(sanfl_df)
    if include_wafl:
        wafl_df = fetch_wafl_games(from_season=from_season, to_season=to_season, pause=pause)
        if not wafl_df.empty:
            parts.append(wafl_df)

    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def align_state_league_rounds(
    games: pd.DataFrame,
    round_calendar: pd.DataFrame,
) -> pd.DataFrame:
    if games.empty:
        return games

    mapped = map_game_dates_to_afl_rounds(games, round_calendar)
    still_missing = mapped["round"].isna()
    if still_missing.any():
        fallback = mapped[still_missing].copy()
        fallback["round"] = fallback["state_round"]
        mapped.loc[still_missing, "round"] = fallback["state_round"].values
    return mapped


def prepare_state_league_games(
    games: pd.DataFrame,
    con,
) -> pd.DataFrame:
    if games.empty:
        return games
    games = games.copy()
    affiliate = load_sanfl_affiliate_map()
    if affiliate and "state_team" in games.columns:
        games["afl_club"] = games["afl_club"].fillna(games["state_team"].map(affiliate))
    calendar = build_afl_round_calendar(con)
    aligned = align_state_league_rounds(games, calendar)
    return aligned.rename(columns={"state_team": "vfl_team"})
