"""Fetch SANFL player participation via AFL API fixtures and Hostplus stats PDFs."""

from __future__ import annotations

import io
import json
import re
import time
from datetime import datetime

import pandas as pd
import pdfplumber
import requests

from ..config import MIN_SEASON, ROOT
from .vfl import normalize_player_name

SANFL_CLUB_MAP_PATH = ROOT / "shared" / "data" / "sanfl_to_afl_club.json"
SANFL_AFFILIATE_PATH = ROOT / "shared" / "data" / "sanfl_affiliate_to_afl_club.json"
AFL_API = "https://aflapi.afl.com.au/afl/v2"
SANFL_COMPETITION_ID = 14
USER_AGENT = "afl-injury-analytics/0.3"
AFL_CLUBS = {"Adelaide", "Port Adelaide"}

# Hostplus stats PDFs use short labels (e.g. "Port" not "Port Adelaide").
PDF_TEAM_ALIASES: dict[str, list[str]] = {
    "Adelaide": ["Adelaide"],
    "Port Adelaide": ["Port"],
    "Glenelg": ["Glenelg"],
}


def load_sanfl_club_map() -> dict[str, str]:
    if SANFL_CLUB_MAP_PATH.exists():
        return json.loads(SANFL_CLUB_MAP_PATH.read_text(encoding="utf-8"))
    return {}


def _afl_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": "application/json"}


def load_sanfl_affiliate_map() -> dict[str, str]:
    if SANFL_AFFILIATE_PATH.exists():
        return json.loads(SANFL_AFFILIATE_PATH.read_text(encoding="utf-8"))
    return {}


def fetch_sanfl_fixtures(season: int, *, afl_clubs_only: bool = True) -> list[dict]:
    matches: list[dict] = []
    for page in range(100):
        resp = requests.get(
            f"{AFL_API}/matches",
            headers=_afl_headers(),
            params={"competitionId": SANFL_COMPETITION_ID, "year": season, "page": page},
            timeout=60,
        )
        resp.raise_for_status()
        batch = resp.json().get("matches", [])
        if not batch:
            break
        for m in batch:
            if f"{season} SANFL" not in m.get("compSeason", {}).get("name", ""):
                continue
            home = m.get("home", {}).get("team", {}).get("name")
            away = m.get("away", {}).get("team", {}).get("name")
            if home not in AFL_CLUBS and away not in AFL_CLUBS:
                if afl_clubs_only:
                    continue
            matches.append(
                {
                    "match_id": m["id"],
                    "season": season,
                    "state_round": m.get("round", {}).get("roundNumber", 0),
                    "home_team": home,
                    "away_team": away,
                    "game_date": (m.get("utcStartTime") or "")[:10] or None,
                    "game_slug": f"sanfl-{m['id']}",
                }
            )
    return matches


def _discover_pdf_urls(season: int) -> dict[int, str]:
    """Map SANFL round number -> stats PDF URL from sanfl.com.au resources."""
    round_urls: dict[int, str] = {}
    for page in range(1, 15):
        resp = requests.get(
            f"https://sanfl.com.au/inside-sanfl/resources/page/{page}/?s=stats",
            timeout=30,
            headers={"User-Agent": USER_AGENT},
        )
        if resp.status_code != 200:
            break
        for url in re.findall(r'href="(https://sanfl-content[^"]+\.pdf)"', resp.text):
            if f"SANFL-{season}-Rd-" not in url and f"SANFL-{season}-RD-" not in url.upper():
                continue
            m = re.search(rf"SANFL-{season}-Rd-(\d+)", url, re.I)
            if m:
                round_urls[int(m.group(1))] = url
    return round_urls


def _parse_player_tokens(chunk: str) -> list[str]:
    """Extract player name tokens from 'Welsh 5, Burgess 4, Cook' style lists."""
    names: list[str] = []
    for part in re.split(r",\s*", chunk.strip()):
        part = part.strip().strip(".")
        if not part:
            continue
        m = re.match(r"^([A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*)?)\s*(?:\d|$)", part)
        if m:
            token = m.group(1).strip()
            if len(token) < 2:
                continue
            if token.lower() not in {"d", "l", "by", "pm", "am"}:
                names.append(normalize_player_name(token))
    return names


def _parse_pdf_players(pdf_bytes: bytes, state_round: int, teams: set[str]) -> dict[str, set[str]]:
    """Return {state_team: {player name tokens}} for one round PDF."""
    out: dict[str, set[str]] = {}
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    for team in teams:
        players: set[str] = set()
        aliases = PDF_TEAM_ALIASES.get(team, [team])
        for alias in aliases:
            for label in ("Goals", "Most Disposals", "Best"):
                for sep in (r"-", r"–"):
                    pat = rf"{label}\s*{sep}\s*{re.escape(alias)}:\s*([^\n]+)"
                    for m in re.finditer(pat, text):
                        players.update(_parse_player_tokens(m.group(1)))
            for m in re.finditer(
                rf"(?<!Goals [-–])(?<!Best [-–]){re.escape(alias)}:\s*([^.\n]+)",
                text,
            ):
                players.update(_parse_player_tokens(m.group(1)))
            if alias in ("Port", "Adelaide"):
                for m in re.finditer(
                    rf"(?<!Goals [-–]){re.escape(alias)}:\s*([^.\n]+\d[^.\n]*)\.",
                    text,
                ):
                    players.update(_parse_player_tokens(m.group(1)))
        if players:
            out[team] = players
    return out


def fetch_sanfl_games(
    from_season: int = MIN_SEASON,
    to_season: int | None = None,
    pause: float = 0.2,
) -> pd.DataFrame:
    to_season = to_season or datetime.now().year
    club_map = load_sanfl_club_map()
    affiliate_map = load_sanfl_affiliate_map()
    parse_teams = set(AFL_CLUBS) | set(affiliate_map.keys())
    rows: list[dict] = []

    for season in range(from_season, to_season + 1):
        fixtures = fetch_sanfl_fixtures(season, afl_clubs_only=False)
        afl_fixtures = [f for f in fixtures if f["home_team"] in AFL_CLUBS or f["away_team"] in AFL_CLUBS]
        print(f"[sanfl] season {season}: {len(fixtures)} fixtures ({len(afl_fixtures)} AFL-club)")
        pdf_urls = _discover_pdf_urls(season)
        print(f"[sanfl] season {season}: {len(pdf_urls)} stats PDFs discovered")

        pdf_players: dict[int, dict[str, set[str]]] = {}
        for rnd, url in sorted(pdf_urls.items()):
            try:
                resp = requests.get(url, timeout=90, headers={"User-Agent": USER_AGENT})
                resp.raise_for_status()
                pdf_players[rnd] = _parse_pdf_players(resp.content, rnd, parse_teams)
            except (requests.RequestException, OSError) as exc:
                print(f"[sanfl] warning: round {rnd} PDF failed: {exc}")
            time.sleep(pause)

        for fx in fixtures:
            round_players = pdf_players.get(fx["state_round"], {})
            for state_team in (fx["home_team"], fx["away_team"]):
                if state_team not in round_players:
                    continue
                if state_team in AFL_CLUBS:
                    afl_club = club_map.get(state_team, state_team)
                elif state_team in affiliate_map:
                    # Affiliate side (e.g. Glenelg): link to AFL club via surname in link_vfl_player_ids
                    afl_club = None
                else:
                    continue
                players = round_players[state_team]
                for player in players:
                    rows.append(
                        {
                            "competition": "sanfl",
                            "season": season,
                            "state_round": fx["state_round"],
                            "state_team": state_team,
                            "afl_club": afl_club,
                            "player_name": player,
                            "player_name_norm": player.lower(),
                            "game_slug": fx["game_slug"],
                            "game_date": fx["game_date"],
                        }
                    )

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
