"""Fetch SANFL player participation from sanfl.com.au match centre (api3.sanflstats.com)."""

from __future__ import annotations

import time
from datetime import datetime

import pandas as pd
import requests

from ..config import MIN_SEASON
from .sanfl import (
    AFL_CLUBS,
    fetch_sanfl_fixtures,
    load_sanfl_affiliate_map,
    load_sanfl_club_map,
)
from .vfl import normalize_player_name

SANFLSTATS_API = "https://api3.sanflstats.com"
LEAGUE_CODE = "sanfl"
USER_AGENT = "afl-injury-analytics/0.3"
PARSE_TEAMS = AFL_CLUBS | {"Glenelg"}  # Glenelg linked via affiliate map
# api3.sanflstats.com uses longer labels in older seasons (2021–2022).
SQUAD_NAME_ALIASES: dict[str, str] = {
    "Adelaide SANFL": "Adelaide",
    "Port Adelaide Magpies": "Port Adelaide",
}


def _canonical_squad(name: str) -> str:
    return SQUAD_NAME_ALIASES.get(name, name)


def _headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Referer": "https://sanfl.com.au/league/matches/",
    }


def fetch_season_matches(season: int) -> list[dict]:
    resp = requests.get(
        f"{SANFLSTATS_API}/fixtures/{season}/{LEAGUE_CODE}",
        headers=_headers(),
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("matches", [])


def fetch_match_detail(match_id: str) -> dict:
    resp = requests.get(
        f"{SANFLSTATS_API}/fixture/{match_id}",
        headers=_headers(),
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def _is_target_match(match: dict) -> bool:
    home = _canonical_squad(match.get("homeSquadName", ""))
    away = _canonical_squad(match.get("awaySquadName", ""))
    return home in PARSE_TEAMS or away in PARSE_TEAMS


def _squad_name(detail: dict, team_code: str) -> str | None:
    if team_code == detail.get("homeTeamCode"):
        return _canonical_squad(detail.get("homeSquadName", ""))
    if team_code == detail.get("awayTeamCode"):
        return _canonical_squad(detail.get("awaySquadName", ""))
    return None


def _game_date(detail: dict) -> str | None:
    utc = detail.get("utcStartTime") or detail.get("localStartTime") or ""
    return utc[:10] if len(utc) >= 10 else None


def _build_fixture_index(fixtures: list[dict]) -> dict[tuple, str]:
    """Map (round, home, away) -> AFL API game_slug."""
    index: dict[tuple, str] = {}
    for fx in fixtures:
        key = (fx["state_round"], fx["home_team"], fx["away_team"])
        index[key] = fx["game_slug"]
        rev = (fx["state_round"], fx["away_team"], fx["home_team"])
        index[rev] = fx["game_slug"]
    return index


def fetch_sanfl_match_centre_games(
    from_season: int = MIN_SEASON,
    to_season: int | None = None,
    *,
    pause: float = 0.12,
) -> pd.DataFrame:
    to_season = to_season or datetime.now().year
    club_map = load_sanfl_club_map()
    affiliate_map = load_sanfl_affiliate_map()
    rows: list[dict] = []

    for season in range(from_season, to_season + 1):
        try:
            matches = fetch_season_matches(season)
        except requests.RequestException as exc:
            print(f"[sanfl_mc] warning: season {season} fixtures failed: {exc}")
            continue

        targets = [m for m in matches if _is_target_match(m)]
        print(f"[sanfl_mc] season {season}: {len(matches)} fixtures, {len(targets)} AFL-club")

        afl_fixtures: list[dict] = []
        try:
            afl_fixtures = fetch_sanfl_fixtures(season, afl_clubs_only=False)
        except requests.RequestException:
            pass
        slug_index = _build_fixture_index(afl_fixtures)

        for match in targets:
            if match.get("matchStatus") != "complete":
                continue
            match_id = str(match["matchId"])
            try:
                detail = fetch_match_detail(match_id)
            except requests.RequestException as exc:
                print(f"[sanfl_mc] warning: match {match_id}: {exc}")
                time.sleep(pause)
                continue

            state_round = int(detail.get("roundNumber") or match.get("roundNumber") or 0)
            home = _canonical_squad(detail.get("homeSquadName", ""))
            away = _canonical_squad(detail.get("awaySquadName", ""))
            game_date = _game_date(detail)
            game_slug = slug_index.get((state_round, home, away), f"sanfl-mc-{match_id}")

            for player in detail.get("playerStats", []):
                team_code = player.get("teamCode", "")
                state_team = _squad_name(detail, team_code)
                if not state_team or state_team not in PARSE_TEAMS:
                    continue

                if state_team in AFL_CLUBS:
                    afl_club = club_map.get(state_team, state_team)
                elif state_team in affiliate_map:
                    afl_club = None
                else:
                    continue

                first = (player.get("firstname") or "").strip()
                surname = (player.get("surname") or "").strip()
                name = normalize_player_name(f"{first} {surname}".strip())
                if not name:
                    continue

                rows.append(
                    {
                        "competition": "sanfl",
                        "season": season,
                        "state_round": state_round,
                        "state_team": state_team,
                        "afl_club": afl_club,
                        "player_name": name,
                        "player_name_norm": name.lower(),
                        "game_slug": game_slug,
                        "game_date": game_date,
                        "source": "sanfl_match_centre",
                    }
                )
            time.sleep(pause)

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.drop_duplicates(
        subset=[
            "competition",
            "season",
            "game_slug",
            "player_name_norm",
            "state_team",
        ]
    )
