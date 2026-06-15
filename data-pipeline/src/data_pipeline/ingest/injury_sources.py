"""Orchestrate injury list ingest from all sources."""

from __future__ import annotations

import pandas as pd

from .bigfooty_forum import fetch_bigfooty_forum
from .bigfooty_injuries import fetch_bigfooty_news, fetch_recent_bigfooty_news
from .injury_list import fetch_injury_list, link_injury_list_players, load_injury_list_entries
from .injury_list_wayback import fetch_wayback_injury_lists


def _tag_source(df: pd.DataFrame, source: str) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["source"] = source
    return out


def load_injury_dataframe(con, df: pd.DataFrame) -> None:
    if df.empty:
        return
    if "source" not in df.columns:
        df = _tag_source(df, "afl_injury_list")
    linked = link_injury_list_players(df, con)
    load_injury_list_entries(con, linked)


def fetch_live_injury_lists() -> pd.DataFrame:
    """Current-week snapshots for pipeline / weekly cron."""
    frames: list[pd.DataFrame] = []

    afl_df = fetch_injury_list()
    if not afl_df.empty:
        frames.append(_tag_source(afl_df, "afl_injury_list"))

    try:
        bf_df = fetch_recent_bigfooty_news(pages=1)
        if not bf_df.empty:
            frames.append(bf_df)
    except Exception as exc:
        print(f"[injury_sources] bigfooty news skipped: {exc}")

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates(
        subset=["list_date", "team", "player_name_norm"], keep="last"
    )


def backfill_injury_lists(
    con,
    *,
    years: tuple[int, ...] = (2018, 2019, 2023, 2024, 2025),
    include_wayback: bool = True,
    include_forum: bool = True,
    include_news: bool = True,
    wayback_from: int = 2021,
    wayback_to: int = 2022,
) -> dict[str, int]:
    """Load historical injury snapshots; returns row counts per source."""
    counts: dict[str, int] = {}

    if include_wayback:
        wb = fetch_wayback_injury_lists(from_year=wayback_from, to_year=wayback_to)
        if not wb.empty:
            load_injury_dataframe(con, wb)
            src = wb["source"].iloc[0] if "source" in wb.columns else "wayback_afl"
            counts[src] = len(wb)

    if include_news:
        news = fetch_bigfooty_news(min_year=min(years), max_year=max(years))
        if not news.empty:
            load_injury_dataframe(con, news)
            counts["bigfooty_news"] = len(news)

    if include_forum:
        forum_years = [y for y in years if y in (2024, 2025, 2026)]
        forum = fetch_bigfooty_forum(years=forum_years)
        if not forum.empty:
            load_injury_dataframe(con, forum)
            counts["bigfooty_forum"] = len(forum)

    return counts


def ingest_live_injury_lists(con) -> None:
    df = fetch_live_injury_lists()
    load_injury_dataframe(con, df)
