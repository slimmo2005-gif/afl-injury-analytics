"""Fetch official AFL selected teams from AFL.com playerStats API."""

from __future__ import annotations

import time
from collections import defaultdict

import pandas as pd
import requests

from .afl_com import (
    CFS_API,
    _HEADERS,
    _team_lookup,
    fetch_all_season_matches,
    get_afl_token,
    normalize_team,
)
from .injury_list import normalize_player_name

_REQUEST_PAUSE_SEC = 0.15


def _player_name(entry: dict) -> str:
    player = entry.get("player", {})
    nested = player.get("player", player)
    if isinstance(nested, dict) and "playerName" in nested:
        pname = nested["playerName"]
        return f"{pname.get('givenName', '')} {pname.get('surname', '')}".strip()
    pname = player.get("playerName", {})
    if pname:
        return f"{pname.get('givenName', '')} {pname.get('surname', '')}".strip()
    return ""


def _player_provider_id(entry: dict) -> str | None:
    player = entry.get("player", {})
    nested = player.get("player", player)
    if isinstance(nested, dict):
        pid = nested.get("playerId")
        return str(pid) if pid else None
    return None


def _position(entry: dict) -> str | None:
    player = entry.get("player", {})
    pos = player.get("position")
    if pos:
        return str(pos)
    nested = player.get("player", {})
    if isinstance(nested, dict):
        return nested.get("position")
    return None


def _roster_player(pos_entry: dict) -> dict | None:
    player = pos_entry.get("player") or {}
    pname = player.get("playerName") or {}
    name = f"{pname.get('givenName', '')} {pname.get('surname', '')}".strip()
    if not name:
        return None
    return {
        "player_name": name,
        "player_name_norm": normalize_player_name(name),
        "provider_player_id": str(player.get("playerId")) if player.get("playerId") else None,
        "position": pos_entry.get("position"),
        "jumper": player.get("playerJumperNumber"),
        "captain": bool(player.get("captain")),
    }


def fetch_round_rosters(season: int, round_num: int) -> dict[str, dict]:
    """Return announced team line-ups for a round from AFL.com matchRoster feed.

    Mirrors https://www.afl.com.au/matches/team-lineups. Maps normalized team
    name -> {players, ins, outs, late_changes, team_status, last_updated}.
    The named 23 excludes emergencies (position code ``EMERG``). Teams on a bye
    in the round simply have no roster and are therefore absent from the result.
    """
    matches = fetch_all_season_matches(season)
    round_matches = [
        m
        for m in matches
        if (m.get("round") or {}).get("roundNumber") == round_num
        and m.get("status") not in ("CANCELLED", "POSTPONED", "PLACEHOLDER", "TBC")
    ]
    if not round_matches:
        return {}

    token = get_afl_token()
    headers = {**_HEADERS, "x-media-mis-token": token}
    rosters: dict[str, dict] = {}

    for match in round_matches:
        provider_id = match.get("providerId")
        if not provider_id:
            continue
        resp = requests.get(
            f"{CFS_API}/matchRoster/{provider_id}",
            headers=headers,
            timeout=30,
        )
        time.sleep(_REQUEST_PAUSE_SEC)
        if not resp.ok:
            continue
        payload = resp.json() or {}
        last_updated = payload.get("lastUpdated")
        for side in ("homeTeam", "awayTeam"):
            team = payload.get(side) or {}
            team_name_obj = team.get("teamName") or {}
            team_name = normalize_team(team_name_obj.get("teamName", ""))
            if not team_name:
                continue
            positions = team.get("positions") or []
            named = [
                rp
                for p in positions
                if p.get("position") != "EMERG"
                and (rp := _roster_player(p)) is not None
            ]
            emergencies = [
                rp
                for p in positions
                if p.get("position") == "EMERG"
                and (rp := _roster_player(p)) is not None
            ]
            if not named:
                continue
            rosters[team_name] = {
                "players": named,
                "emergencies": emergencies,
                "ins": [
                    (i.get("playerName") or {})
                    for i in (team.get("ins") or [])
                ],
                "outs": team.get("outs") or [],
                "late_changes": team.get("lateChanges") or [],
                "team_status": team.get("teamStatus"),
                "last_updated": last_updated,
                "match_status": match.get("status"),
            }
    return rosters


def current_round_with_teams(season: int) -> int | None:
    """Pick the round whose teams are announced (line-ups available).

    Returns the lowest round that still has a non-concluded match and at least
    one announced side; falls back to the latest round with announced teams.
    """
    matches = fetch_all_season_matches(season)
    by_round: dict[int, list[dict]] = defaultdict(list)
    for m in matches:
        rn = (m.get("round") or {}).get("roundNumber")
        if rn is not None:
            by_round[rn].append(m)

    announced_statuses = {"CONFIRMED_TEAMS", "UNCONFIRMED_TEAMS", "CONCLUDED"}
    candidates: list[int] = []
    for rn in sorted(by_round):
        statuses = {m.get("status") for m in by_round[rn]}
        has_announced = statuses & announced_statuses
        not_all_concluded = statuses - {"CONCLUDED", "CANCELLED", "POSTPONED"}
        if has_announced and not_all_concluded:
            candidates.append(rn)
    if candidates:
        return candidates[0]
    # all announced rounds fully concluded -> use the most recent concluded round
    concluded = [
        rn
        for rn in sorted(by_round)
        if any(m.get("status") == "CONCLUDED" for m in by_round[rn])
    ]
    return concluded[-1] if concluded else None


def fetch_round_team_selections(season: int, round_num: int) -> dict[str, list[dict]]:
    """Return normalized team name -> selected player rows for a round."""
    matches = fetch_all_season_matches(season)
    round_matches = [
        m
        for m in matches
        if (m.get("round") or {}).get("roundNumber") == round_num
        and m.get("status") not in ("CANCELLED", "POSTPONED", "PLACEHOLDER", "TBC")
    ]
    if not round_matches:
        return {}

    token = get_afl_token()
    headers = {**_HEADERS, "x-media-mis-token": token}
    team_lookup = _team_lookup()
    selections: dict[str, list[dict]] = defaultdict(list)

    for match in round_matches:
        provider_id = match.get("providerId")
        if not provider_id:
            continue
        resp = requests.get(
            f"{CFS_API}/playerStats/match/{provider_id}",
            headers=headers,
            timeout=30,
        )
        time.sleep(_REQUEST_PAUSE_SEC)
        if resp.status_code != 200:
            continue
        payload = resp.json() if resp.ok else {}
        for side, key in (("home", "homeTeamPlayerStats"), ("away", "awayTeamPlayerStats")):
            default_team = normalize_team(
                match.get(side, {})
                .get("team", {})
                .get("club", {})
                .get("name", "")
                or match.get(side, {}).get("team", {}).get("name", "")
            )
            for entry in payload.get(key) or []:
                name = _player_name(entry)
                if not name:
                    continue
                team_id = str(entry.get("teamId", ""))
                team = team_lookup.get(team_id, default_team)
                selections[team].append(
                    {
                        "player_name": name,
                        "player_name_norm": normalize_player_name(name),
                        "provider_player_id": _player_provider_id(entry),
                        "position": _position(entry),
                        "jumper": entry.get("player", {}).get("jumperNumber"),
                    }
                )
    return dict(selections)


def selections_to_dataframe(selections: dict[str, list[dict]], season: int, round_num: int) -> pd.DataFrame:
    rows: list[dict] = []
    for team, players in selections.items():
        for p in players:
            rows.append(
                {
                    "season": season,
                    "round": round_num,
                    "team": team,
                    **p,
                }
            )
    return pd.DataFrame(rows)
