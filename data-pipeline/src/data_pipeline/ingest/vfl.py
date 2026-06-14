"""Scrape VFL player participation from vfl.aflmstats.com."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

from ..config import MIN_SEASON, ROOT, TEAM_ALIASES

VFL_BASE = "https://vfl.aflmstats.com"
VFL_CLUB_MAP_PATH = ROOT / "shared" / "data" / "vfl_to_afl_club.json"


def normalize_team(name: str) -> str:
    return TEAM_ALIASES.get(name.strip(), name.strip())


def load_vfl_club_map() -> dict[str, str | None]:
    if VFL_CLUB_MAP_PATH.exists():
        raw = json.loads(VFL_CLUB_MAP_PATH.read_text(encoding="utf-8"))
        return {k: (normalize_team(v) if v else None) for k, v in raw.items()}
    return {}


def normalize_player_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace("\xa0", " ")).strip()


def parse_team_from_h2(text: str) -> str:
    text = text.strip()
    m = re.match(r"^([A-Za-z][A-Za-z\s&']*?)(?:\d|$)", text)
    if m:
        return m.group(1).strip()
    return text


def fetch_season_game_slugs(season: int) -> list[tuple[int, str]]:
    url = f"{VFL_BASE}/season/{season}"
    resp = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "afl-injury-analytics/0.3"},
    )
    resp.raise_for_status()
    slugs = sorted(
        set(re.findall(rf"/game/{season}-\d+-[a-z0-9-]+", resp.text))
    )
    out: list[tuple[int, str]] = []
    for path in slugs:
        slug = path.replace("/game/", "")
        m = re.search(rf"^{season}-(\d+)-", slug)
        rnd = int(m.group(1)) if m else 0
        out.append((rnd, slug))
    return out


def fetch_game_players(season: int, round_num: int, slug: str) -> pd.DataFrame:
    url = f"{VFL_BASE}/game/{slug}"
    resp = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "afl-injury-analytics/0.3"},
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    vfl_map = load_vfl_club_map()
    team_headers = [
        parse_team_from_h2(h.get_text(strip=True))
        for h in soup.find_all("h2")
        if h.get_text(strip=True) and "VFL Stats" not in h.get_text()
    ]
    stat_tables = [
        t
        for t in soup.find_all("table")
        if t.find("th") and "player" in t.find("th").get_text(strip=True).lower()
    ]

    rows: list[dict] = []
    for idx, table in enumerate(stat_tables):
        vfl_team = team_headers[idx] if idx < len(team_headers) else None
        afl_club = vfl_map.get(vfl_team or "", None) if vfl_team else None
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if "player" not in headers:
            continue
        player_idx = headers.index("player")

        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all("td")
            if len(cells) <= player_idx:
                continue
            player = normalize_player_name(cells[player_idx].get_text(" ", strip=True))
            if not player:
                continue
            rows.append(
                {
                    "competition": "vfl",
                    "season": season,
                    "state_round": round_num,
                    "state_team": vfl_team,
                    "afl_club": afl_club,
                    "player_name": player,
                    "player_name_norm": player.lower(),
                    "game_slug": slug,
                    "game_date": None,
                }
            )

    return pd.DataFrame(rows)


def fetch_vfl_games(
    from_season: int = MIN_SEASON,
    to_season: int | None = None,
    pause: float = 0.2,
) -> pd.DataFrame:
    to_season = to_season or datetime.now().year
    all_rows: list[pd.DataFrame] = []

    for season in range(from_season, to_season + 1):
        try:
            slugs = fetch_season_game_slugs(season)
        except requests.RequestException as exc:
            print(f"[vfl] warning: season {season} fixture failed: {exc}")
            continue
        print(f"[vfl] season {season}: {len(slugs)} games")
        for rnd, slug in slugs:
            try:
                df = fetch_game_players(season, rnd, slug)
                if not df.empty:
                    all_rows.append(df)
            except requests.RequestException as exc:
                print(f"[vfl] warning: {slug}: {exc}")
            time.sleep(pause)

    if not all_rows:
        return pd.DataFrame()
    return pd.concat(all_rows, ignore_index=True).drop_duplicates(
        subset=["competition", "season", "game_slug", "player_name_norm", "state_team"]
    )
