"""Official home-and-away ladder from Squiggle (aligned with AFL.com round-end ladder)."""

from __future__ import annotations

import time

import requests

from ..config import SQUIGGLE_BASE
from ..ingest.squiggle import normalize_team

# End-of-home-and-away round per season (Squiggle standings; 2025 uses 24-round HA).
FINAL_HA_ROUND: dict[int, int] = {
    2021: 23,
    2022: 23,
    2023: 23,
    2024: 24,
    2025: 24,
}

OFFICIAL_LADDER_FROM = 2021
OFFICIAL_LADDER_TO = 2025


def fetch_standings(season: int, round_: int, *, timeout: int = 30) -> list[dict]:
    """Fetch ladder after a given round from Squiggle."""
    url = f"{SQUIGGLE_BASE}/?q=standings;year={season};round={round_}"
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "afl-injury-analytics/0.2"})
    resp.raise_for_status()
    rows = resp.json().get("standings", [])
    if not rows:
        raise ValueError(f"No standings for {season} round {round_}")
    return rows


def official_ladder_by_team(season: int) -> dict[str, dict[str, int | float]] | None:
    """Map normalized team name to official ladder row, or None if not configured."""
    round_ = FINAL_HA_ROUND.get(season)
    if round_ is None:
        return None
    rows = fetch_standings(season, round_)
    return {
        normalize_team(row["name"]): {
            "ladder_rank": int(row["rank"]),
            "wins": int(row["wins"]),
            "draws": int(row.get("draws", 0)),
            "percentage": round(float(row["percentage"]), 1),
        }
        for row in rows
    }


def load_official_ladders(
    from_season: int = OFFICIAL_LADDER_FROM,
    to_season: int = OFFICIAL_LADDER_TO,
    *,
    pause: float = 0.25,
) -> dict[int, dict[str, dict[str, int | float]]]:
    """Load official ladders for a season range (network)."""
    out: dict[int, dict[str, dict[str, int | float]]] = {}
    for season in range(from_season, to_season + 1):
        if season not in FINAL_HA_ROUND:
            continue
        try:
            out[season] = official_ladder_by_team(season)
            print(f"[ladder] official standings loaded: {season} round {FINAL_HA_ROUND[season]}")
        except (requests.RequestException, ValueError) as exc:
            print(f"[ladder] warning: official standings {season} skipped: {exc}")
        time.sleep(pause)
    return out
