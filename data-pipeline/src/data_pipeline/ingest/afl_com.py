"""Fetch current-season AFL player stats from the public AFL.com API (Champion Data)."""

from __future__ import annotations

import time

import pandas as pd
import requests

from ..config import RAW_DIR
from .fryzigg import normalize_team

AFL_API = "https://aflapi.afl.com.au/afl/v2"
CFS_API = "https://api.afl.com.au/cfs/afl"
_HEADERS = {
    "User-Agent": "afl-injury-analytics/0.2",
    "Accept": "application/json",
    "Referer": "https://www.afl.com.au/",
}
_PREMIERSHIP_COMP_ID = 1
_REQUEST_PAUSE_SEC = 0.15


def get_afl_token() -> str:
    resp = requests.post(f"{CFS_API}/WMCTok", headers=_HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()["token"]


def find_comp_season_id(season: int) -> int | None:
    resp = requests.get(
        f"{AFL_API}/competitions/{_PREMIERSHIP_COMP_ID}/compseasons",
        headers=_HEADERS,
        params={"pageSize": 100},
        timeout=30,
    )
    resp.raise_for_status()
    for comp_season in resp.json().get("compSeasons", []):
        name = comp_season.get("name", "")
        if str(season) in name and "Premiership" in name:
            return int(comp_season["id"])
    return None


def fetch_season_matches(season: int) -> list[dict]:
    comp_season_id = find_comp_season_id(season)
    if comp_season_id is None:
        return []

    matches: list[dict] = []
    for page in range(50):
        resp = requests.get(
            f"{AFL_API}/matches",
            headers=_HEADERS,
            params={"compSeasonId": comp_season_id, "page": page, "pageSize": 50},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json().get("matches", [])
        if not batch:
            break
        matches.extend(batch)
    return [m for m in matches if m.get("status") == "CONCLUDED"]


def _team_lookup() -> dict[str, str]:
    resp = requests.get(
        f"{AFL_API}/teams",
        headers=_HEADERS,
        params={"pageSize": 1000},
        timeout=30,
    )
    resp.raise_for_status()
    lookup: dict[str, str] = {}
    for team in resp.json().get("teams", []):
        if team.get("teamType") != "MEN":
            continue
        name = normalize_team(team.get("club", {}).get("name") or team.get("name", ""))
        lookup[str(team["id"])] = name
        provider = team.get("providerId")
        if provider:
            lookup[str(provider)] = name
    return lookup


def _parse_player_rows(
    payload: dict,
    match: dict,
    team_lookup: dict[str, str],
) -> list[dict]:
    season_name = match.get("compSeason", {}).get("name", "")
    season = int(season_name[:4]) if season_name[:4].isdigit() else None
    round_no = match.get("round", {}).get("roundNumber")
    match_date = match.get("utcStartTime", "")[:10] or None
    rows: list[dict] = []

    for side, team_key in (("home", "homeTeamPlayerStats"), ("away", "awayTeamPlayerStats")):
        default_team = normalize_team(
            match.get(side, {}).get("team", {}).get("club", {}).get("name")
            or match.get(side, {}).get("team", {}).get("name", "")
        )
        for entry in payload.get(team_key, []):
            ps = entry.get("playerStats", {})
            stats = ps.get("stats", {})
            player = ps.get("player", {})
            pname = player.get("playerName", {})
            player_name = f"{pname.get('givenName', '')} {pname.get('surname', '')}".strip()
            team_id = str(ps.get("teamId", ""))
            team = team_lookup.get(team_id, default_team)
            shots = stats.get("shotsAtGoal") or 0
            goals = stats.get("goals") or 0
            behinds = stats.get("behinds") or 0
            if shots <= 0 and goals <= 0 and behinds <= 0:
                continue
            rows.append(
                {
                    "player_id": str(player.get("playerId", player_name)),
                    "player_name": player_name,
                    "team": team,
                    "season": season,
                    "round": round_no,
                    "match_id": match.get("providerId"),
                    "match_date": match_date,
                    "goals": float(goals),
                    "behinds": float(behinds),
                    "shots_at_goal": float(shots if shots > 0 else goals + behinds),
                    "source": "afl.com",
                }
            )
    return rows


def fetch_match_goal_kicking(
    match: dict,
    token: str,
    team_lookup: dict[str, str],
) -> list[dict]:
    provider_id = match.get("providerId")
    if not provider_id:
        return []
    resp = requests.get(
        f"{CFS_API}/playerStats/match/{provider_id}",
        headers={**_HEADERS, "x-media-mis-token": token},
        timeout=30,
    )
    if resp.status_code != 200:
        return []
    return _parse_player_rows(resp.json(), match, team_lookup)


def load_goal_kicking_player_games(
    season: int,
    cache: bool = True,
) -> pd.DataFrame:
    """Per-player-match goal kicking rows for seasons not yet in Fryzigg."""
    cache_path = RAW_DIR / f"afl_com_goal_kicking_{season}.parquet"
    if cache and cache_path.exists():
        cached = pd.read_parquet(cache_path)
        if not cached.empty:
            return cached

    matches = fetch_season_matches(season)
    if not matches:
        return pd.DataFrame()

    token = get_afl_token()
    team_lookup = _team_lookup()
    rows: list[dict] = []
    for match in matches:
        rows.extend(fetch_match_goal_kicking(match, token, team_lookup))
        time.sleep(_REQUEST_PAUSE_SEC)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce").dt.date
    if cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path, index=False)
    return df


def latest_fryzigg_season(rds_path) -> int | None:
    import pyreadr

    raw = pyreadr.read_r(str(rds_path))[None]
    raw["match_date"] = pd.to_datetime(raw["match_date"], errors="coerce")
    if raw["match_date"].isna().all():
        return None
    return int(raw["match_date"].dt.year.max())
