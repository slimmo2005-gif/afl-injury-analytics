"""Ingest fixtures and results from Squiggle API."""

from __future__ import annotations

import time

import pandas as pd
import requests

from ..config import SQUIGGLE_BASE, TEAM_ALIASES


def normalize_team(name: str) -> str:
    return TEAM_ALIASES.get(name, name)


def fetch_games(season: int, timeout: int = 30) -> pd.DataFrame:
    url = f"{SQUIGGLE_BASE}/?q=games;year={season}"
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "afl-injury-analytics/0.2"})
    resp.raise_for_status()
    games = resp.json().get("games", [])
    if not games:
        return pd.DataFrame()

    df = pd.DataFrame(games)
    df = df.rename(
        columns={
            "id": "match_id",
            "round": "round",
            "hteam": "home_team",
            "ateam": "away_team",
            "hscore": "home_score",
            "ascore": "away_score",
            "winner": "winner_team",
            "complete": "complete",
        }
    )
    df["season"] = season
    df["home_team"] = df["home_team"].map(normalize_team)
    df["away_team"] = df["away_team"].map(normalize_team)
    df["winner_team"] = df["winner_team"].map(normalize_team)
    df["venue"] = df.get("venue", "")
    return df[
        [
            "match_id",
            "season",
            "round",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "venue",
            "winner_team",
            "complete",
        ]
    ]


def fetch_all_seasons(from_season: int, to_season: int, pause: float = 0.3) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for year in range(from_season, to_season + 1):
        try:
            df = fetch_games(year)
            if not df.empty:
                frames.append(df)
        except requests.RequestException as exc:
            print(f"[squiggle] warning: season {year} failed: {exc}")
        time.sleep(pause)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
