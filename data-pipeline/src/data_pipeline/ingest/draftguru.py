"""Scrape national draft picks from Draftguru (2012+)."""

from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from ..config import MIN_SEASON, ROOT, TEAM_ALIASES

DRAFTGURU_BASE = "https://www.draftguru.com.au"
DRAFT_CACHE = ROOT / "shared" / "data" / "draft_picks.csv"


def normalize_team(name: str) -> str:
    name = name.strip()
    return TEAM_ALIASES.get(name, name)


def normalize_player_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name.replace("\xa0", " ")).strip()
    return name


def fetch_national_draft(season: int, timeout: int = 30) -> pd.DataFrame:
    url = f"{DRAFTGURU_BASE}/years/{season}/national_draft"
    resp = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "afl-injury-analytics/0.3"},
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", class_=re.compile("general"))
    if not table:
        return pd.DataFrame()

    rows: list[dict] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 5:
            continue
        pick_text = cells[1].get_text(strip=True)
        if not pick_text.isdigit():
            continue
        club = normalize_team(cells[2].get_text(strip=True))
        player_cell = cells[4]
        player = normalize_player_name(player_cell.get_text(" ", strip=True))
        if not player:
            continue
        rows.append(
            {
                "draft_year": season,
                "draft_pick": int(pick_text),
                "drafted_club": club,
                "player_name": player,
                "player_name_norm": player.lower(),
            }
        )

    return pd.DataFrame(rows)


def fetch_all_drafts(from_season: int = MIN_SEASON, to_season: int | None = None) -> pd.DataFrame:
    to_season = to_season or pd.Timestamp.now().year
    frames: list[pd.DataFrame] = []
    for year in range(from_season, to_season + 1):
        try:
            df = fetch_national_draft(year)
            if not df.empty:
                frames.append(df)
                print(f"[draftguru] {year}: {len(df)} picks")
        except requests.RequestException as exc:
            print(f"[draftguru] warning: {year} failed: {exc}")
        time.sleep(0.4)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def link_draft_to_players(draft_df: pd.DataFrame, con) -> pd.DataFrame:
    """Attach fryzigg player_id via normalized name (best match on debut season)."""
    if draft_df.empty:
        return draft_df

    players = con.execute(
        """
        SELECT DISTINCT player_id, player_name, LOWER(player_name) AS player_name_norm,
               MIN(season) OVER (PARTITION BY player_id) AS debut_season
        FROM player_games
        """
    ).df()

    merged = draft_df.merge(
        players,
        on="player_name_norm",
        how="left",
        suffixes=("", "_pg"),
    )
    # Prefer match where debut is draft year or year after
    merged["season_ok"] = merged["debut_season"].isna() | merged["debut_season"].between(
        merged["draft_year"], merged["draft_year"] + 2
    )
    merged = merged.sort_values(["season_ok", "debut_season"], ascending=[False, True])
    merged = merged.drop_duplicates(subset=["draft_year", "draft_pick", "player_name"], keep="first")
    merged["player_name_norm"] = merged["player_name"].str.lower()
    return merged[
        [
            "player_id",
            "player_name",
            "player_name_norm",
            "draft_year",
            "draft_pick",
            "drafted_club",
        ]
    ]


def save_draft_cache(df: pd.DataFrame, path: Path = DRAFT_CACHE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.dropna(subset=["draft_pick"]).copy()
    out["player_id"] = out["player_id"].astype(str).where(out["player_id"].notna(), None)
    out.to_csv(path, index=False)
    return path
