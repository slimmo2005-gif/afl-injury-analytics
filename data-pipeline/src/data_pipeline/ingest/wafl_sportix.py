"""Fetch WAFL player participation via WAFL Sportix API (wafl.com.au)."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime

import pandas as pd
import requests

from ..config import MIN_SEASON, ROOT, TEAM_ALIASES
from .vfl import normalize_player_name

WAFL_CLUB_MAP_PATH = ROOT / "shared" / "data" / "wafl_to_afl_club.json"
SPORTIX_BASE = "https://api.sportix.cloud/public"
WAFL_HOME = "https://wafl.com.au/"
USER_AGENT = "afl-injury-analytics/0.3"


def load_wafl_club_map() -> dict[str, str | list[str] | None]:
    if WAFL_CLUB_MAP_PATH.exists():
        return json.loads(WAFL_CLUB_MAP_PATH.read_text(encoding="utf-8"))
    return {}


def normalize_team(name: str) -> str:
    return TEAM_ALIASES.get(name.strip(), name.strip())


def _fetch_wafl_credentials() -> tuple[str, str]:
    resp = requests.get(WAFL_HOME, timeout=30, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    key_match = re.search(r'apiKey:"([^"]+)"', resp.text)
    tenant_match = re.search(r'tenantId:"([^"]+)"', resp.text)
    if not key_match or not tenant_match:
        raise RuntimeError("Could not parse WAFL Sportix credentials from wafl.com.au")
    return key_match.group(1), tenant_match.group(1)


def _sportix_headers() -> dict[str, str]:
    api_key, tenant_id = _fetch_wafl_credentials()
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
        "tenant-id": tenant_id,
    }


def _resolve_afl_clubs(state_team: str, club_map: dict) -> list[str | None]:
    mapped = club_map.get(state_team)
    if mapped is None:
        mapped = club_map.get(normalize_team(state_team))
    if mapped is None:
        return [None]
    if isinstance(mapped, list):
        return mapped
    return [mapped]


def _players_from_match(match: dict, side: str) -> list[dict]:
    stats = match.get("statistics") or {}
    side_stats = stats.get(side)
    if isinstance(side_stats, list):
        return side_stats
    if isinstance(side_stats, dict):
        players = side_stats.get("players")
        if isinstance(players, list):
            return players
    return []


def _player_display_name(entry: dict) -> str:
    if entry.get("player"):
        p = entry["player"]
        first = p.get("first") or entry.get("first") or ""
        last = p.get("last") or entry.get("last") or ""
        return normalize_player_name(f"{first} {last}".strip())
    first = entry.get("first") or ""
    last = entry.get("last") or ""
    return normalize_player_name(f"{first} {last}".strip())


def fetch_wafl_match_slugs(season: int, headers: dict[str, str]) -> list[str]:
    resp = requests.get(
        f"{SPORTIX_BASE}/matches",
        headers=headers,
        params={"season_slug": str(season), "round_slug": "all"},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    slugs: list[str] = []
    for comp in data.get("competitions", []):
        if comp.get("slug") != "league":
            continue
        for m in comp.get("matches", []):
            if m.get("completed") and m.get("slug"):
                slugs.append(m["slug"])
    return sorted(set(slugs))


def fetch_wafl_games(
    from_season: int = MIN_SEASON,
    to_season: int | None = None,
    pause: float = 0.15,
) -> pd.DataFrame:
    to_season = to_season or datetime.now().year
    club_map = load_wafl_club_map()
    headers = _sportix_headers()
    rows: list[dict] = []

    for season in range(from_season, to_season + 1):
        try:
            slugs = fetch_wafl_match_slugs(season, headers)
        except requests.RequestException as exc:
            print(f"[wafl] warning: season {season} fixture failed: {exc}")
            continue
        print(f"[wafl] season {season}: {len(slugs)} completed league games")
        for slug in slugs:
            try:
                resp = requests.get(
                    f"{SPORTIX_BASE}/matches/{slug}",
                    headers=headers,
                    timeout=60,
                )
                resp.raise_for_status()
                match = resp.json()
            except requests.RequestException as exc:
                print(f"[wafl] warning: {slug}: {exc}")
                continue

            if not match.get("completed"):
                continue

            state_round_num = 0
            rnd_slug = (match.get("round") or {}).get("slug", "")
            rnd_m = re.search(r"round-(\d+)", rnd_slug or "")
            if rnd_m:
                state_round_num = int(rnd_m.group(1))
            game_date = (match.get("start_datetime") or "")[:10] or None
            home_team = (match.get("home") or {}).get("name")
            away_team = (match.get("away") or {}).get("name")

            for side, state_team in (("home", home_team), ("away", away_team)):
                if not state_team:
                    continue
                afl_clubs = _resolve_afl_clubs(state_team, club_map)
                if afl_clubs == [None]:
                    continue
                multi_affiliate = len(afl_clubs) > 1
                for entry in _players_from_match(match, side):
                    player = _player_display_name(entry)
                    if not player:
                        continue
                    if multi_affiliate:
                        rows.append(
                            {
                                "competition": "wafl",
                                "season": season,
                                "state_round": state_round_num,
                                "state_team": state_team,
                                "afl_club": None,
                                "player_name": player,
                                "player_name_norm": player.lower(),
                                "game_slug": slug,
                                "game_date": game_date,
                            }
                        )
                    else:
                        rows.append(
                            {
                                "competition": "wafl",
                                "season": season,
                                "state_round": state_round_num,
                                "state_team": state_team,
                                "afl_club": afl_clubs[0],
                                "player_name": player,
                                "player_name_norm": player.lower(),
                                "game_slug": slug,
                                "game_date": game_date,
                            }
                        )
            time.sleep(pause)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).drop_duplicates(
        subset=[
            "competition",
            "season",
            "game_slug",
            "player_name_norm",
            "state_team",
        ]
    )
