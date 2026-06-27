"""Weekly selection impact: optimal PVS team vs AFL's announced line-up.

Source of truth for "who is playing" is the AFL.com team line-ups feed
(https://www.afl.com.au/matches/team-lineups) via the ``matchRoster`` API.
Teams on a bye have no line-up and are therefore excluded automatically.
Impact for a club = the season injury-weighted PVS of its optimal-23 players
who are *not* named in this week's side (injured, omitted, rested or suspended).
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from ..ingest.team_selections import current_round_with_teams, fetch_round_rosters
from ..transform.archetypes import ARCHETYPE_LABELS

TEAM_SIZE = 23
MIN_GAMES = 1

# Minimum archetype counts in an optimal 23.
# Based on observed 2026 selected-team medians; utility is left flexible because
# AFL.com position data is sparse and inflates that bucket via stats inference.
ROLE_MINIMUMS: dict[str, int] = {
    "ruck": 1,
    "key_defender": 2,
    "rebound_defender": 1,
    "key_forward": 2,
    "pressure_forward": 1,
    "inside_mid": 3,
    "outside_mid": 1,
}


@dataclass
class SquadPlayer:
    player_id: str
    player_name: str
    archetype: str
    injury_pvs: float


def _pick_best_team(pool: list[SquadPlayer], size: int = TEAM_SIZE) -> list[SquadPlayer]:
    if not pool:
        return []
    by_arch: dict[str, list[SquadPlayer]] = {}
    for p in pool:
        by_arch.setdefault(p.archetype, []).append(p)
    for arch in by_arch:
        by_arch[arch].sort(key=lambda x: x.injury_pvs, reverse=True)

    selected: list[SquadPlayer] = []
    selected_ids: set[str] = set()

    for arch, minimum in ROLE_MINIMUMS.items():
        for p in by_arch.get(arch, [])[:minimum]:
            if p.player_id not in selected_ids:
                selected.append(p)
                selected_ids.add(p.player_id)

    for p in sorted(pool, key=lambda x: x.injury_pvs, reverse=True):
        if len(selected) >= size:
            break
        if p.player_id not in selected_ids:
            selected.append(p)
            selected_ids.add(p.player_id)

    return selected[:size]


def _load_squad(con: duckdb.DuckDBPyConnection, season: int, team: str) -> list[SquadPlayer]:
    rows = con.execute(
        """
        SELECT v.player_id,
               MAX(pg.player_name) AS player_name,
               COALESCE(p.archetype, 'utility') AS archetype,
               MAX(COALESCE(v.injury_weight_pvs, v.pvs)) AS injury_pvs,
               COUNT(*)::INT AS games
        FROM player_value v
        JOIN player_profiles p
          ON v.player_id = p.player_id AND v.team = p.team AND v.season = p.season
        JOIN player_games pg
          ON v.player_id = pg.player_id AND v.team = pg.team AND v.season = pg.season
        WHERE v.season = ? AND v.team = ?
        GROUP BY 1, 3
        HAVING games >= ?
        """,
        [season, team, MIN_GAMES],
    ).fetchall()
    return [
        SquadPlayer(
            player_id=str(r[0]),
            player_name=str(r[1]),
            archetype=str(r[2]),
            injury_pvs=float(r[3] or 0),
        )
        for r in rows
    ]


def _unavailable_lookup(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, str]]:
    """Latest AFL injury-list snapshot: team -> {normalized name: reason}.

    ``reason`` is ``"injured"`` or ``"suspended"``. Only these players are
    treated as genuinely unavailable when assessing selection impact; players
    who are merely omitted or rested (and therefore not on the official list)
    are still available and must not be counted as a loss.
    """
    try:
        rows = con.execute(
            """
            WITH latest AS (SELECT MAX(list_date) d FROM injury_list_entries)
            SELECT team,
                   LOWER(REGEXP_REPLACE(player_name, '\\s+', ' ', 'g')) AS norm,
                   CASE WHEN injury_category = 'suspension' THEN 'suspended'
                        ELSE 'injured' END AS reason
            FROM injury_list_entries
            WHERE list_date = (SELECT d FROM latest)
              AND (is_injury OR injury_category = 'suspension')
            """
        ).fetchall()
    except duckdb.Error:
        return {}
    out: dict[str, dict[str, str]] = {}
    for team, norm, reason in rows:
        out.setdefault(str(team), {})[str(norm).strip()] = str(reason)
    return out


def _name_lookup(con: duckdb.DuckDBPyConnection, season: int) -> dict[tuple[str, str], str]:
    rows = con.execute(
        """
        SELECT team, LOWER(REGEXP_REPLACE(player_name, '\\s+', ' ', 'g')) AS norm, player_id
        FROM player_games
        WHERE season = ?
        GROUP BY 1, 2, 3
        """,
        [season],
    ).fetchall()
    return {(str(team), str(norm).strip()): str(pid) for team, norm, pid in rows}


def _resolve_roster_ids(
    rosters: dict[str, dict],
    name_lookup: dict[tuple[str, str], str],
) -> dict[str, list[str]]:
    """Map each announced line-up to player_ids via team + normalized name."""
    out: dict[str, list[str]] = {}
    for team, roster in rosters.items():
        ids: list[str] = []
        for p in roster.get("players", []):
            norm = (p.get("player_name_norm") or "").strip()
            pid = name_lookup.get((team, norm))
            if pid:
                ids.append(pid)
        out[team] = ids
    return out


def _fixtures_for_round(con: duckdb.DuckDBPyConnection, season: int, round_num: int) -> list[dict]:
    rows = con.execute(
        """
        SELECT home_team, away_team
        FROM matches
        WHERE season = ? AND round = ?
        ORDER BY home_team
        """,
        [season, round_num],
    ).fetchall()
    return [{"home": r[0], "away": r[1]} for r in rows]


def _team_impact(
    squad: list[SquadPlayer],
    best: list[SquadPlayer],
    named_ids: list[str],
    unavailable: dict[str, str] | None = None,
) -> dict:
    unavailable = unavailable or {}
    squad_by_id = {p.player_id: p for p in squad}
    named_set = set(named_ids)

    best_total = round(sum(p.injury_pvs for p in best), 1)
    named_total = round(
        sum(squad_by_id[pid].injury_pvs for pid in named_set if pid in squad_by_id),
        1,
    )

    def _norm(name: str) -> str:
        return " ".join(name.lower().split())

    # Only optimal-23 players who are genuinely unavailable (on the AFL injury
    # list, injured or suspended) and not named count as a loss. Available
    # depth that the PVS model rates highly but the coach omitted does NOT.
    out_players: list[tuple[SquadPlayer, str]] = []
    for p in best:
        if p.player_id in named_set:
            continue
        reason = unavailable.get(_norm(p.player_name))
        if reason:
            out_players.append((p, reason))
    out_players.sort(key=lambda t: t[0].injury_pvs, reverse=True)
    impact_pvs = round(sum(p.injury_pvs for p, _ in out_players), 1)

    by_role: dict[str, float] = {}
    for p, _ in out_players:
        by_role[p.archetype] = round(by_role.get(p.archetype, 0) + p.injury_pvs, 1)

    return {
        "bestTeamPvs": best_total,
        "selectedTeamPvs": named_total,
        "impactPvs": impact_pvs,
        "pvsGap": round(best_total - named_total, 1),
        "selectedCount": len(named_set),
        "missingFromOptimal": [
            {
                "player": p.player_name,
                "archetype": p.archetype,
                "archetypeLabel": ARCHETYPE_LABELS.get(p.archetype, p.archetype),
                "pvs": round(p.injury_pvs, 1),
                "reason": reason,
                "injured": reason == "injured",
                "suspended": reason == "suspended",
            }
            for p, reason in out_players[:12]
        ],
        "impactByRole": [
            {
                "roleId": role,
                "role": ARCHETYPE_LABELS.get(role, role),
                "pvs": pvs,
            }
            for role, pvs in sorted(by_role.items(), key=lambda x: -x[1])
        ],
    }


def build_weekly_team_impact_bundle(
    con: duckdb.DuckDBPyConnection,
    season: int,
    *,
    round_num: int | None = None,
) -> dict:
    target_round = round_num if round_num is not None else current_round_with_teams(season)
    if not target_round or target_round <= 0:
        return {
            "round": 0,
            "teamsAnnounced": False,
            "interpretation": "No announced team line-ups available yet.",
            "ladder": [],
            "matchups": [],
            "byClub": {},
        }

    rosters = fetch_round_rosters(season, target_round)
    name_lookup = _name_lookup(con, season)
    roster_ids = _resolve_roster_ids(rosters, name_lookup)
    unavailable = _unavailable_lookup(con)
    playing_teams = sorted(rosters.keys())
    teams_announced = bool(playing_teams)

    # Are these final teams or still provisional?
    statuses = {r.get("team_status") for r in rosters.values()}
    all_final = statuses and statuses <= {"FINAL_TEAM"}
    last_updated = max(
        (r.get("last_updated") or "" for r in rosters.values()),
        default=None,
    )

    ladder_rows: list[dict] = []
    by_club: dict[str, dict] = {}

    for team in playing_teams:
        squad = _load_squad(con, season, team)
        best = _pick_best_team(squad)
        named_ids = roster_ids.get(team, [])
        impact = _team_impact(squad, best, named_ids, unavailable.get(team, {}))
        roster = rosters.get(team, {})
        row = {
            "club": team,
            "round": target_round,
            "teamsAnnounced": True,
            "teamStatus": roster.get("team_status"),
            "lastUpdated": roster.get("last_updated"),
            "namedCount": len(roster.get("players", [])),
            **impact,
        }
        ladder_rows.append(row)
        by_club[team] = row

    # Healthiest (lowest optimal PVS sidelined) first.
    ladder_rows.sort(key=lambda r: (r["impactPvs"], r["club"]))
    for i, row in enumerate(ladder_rows, start=1):
        row["impactRank"] = i

    matchups: list[dict] = []
    for fx in _fixtures_for_round(con, season, target_round):
        home = by_club.get(fx["home"])
        away = by_club.get(fx["away"])
        if not home or not away:
            continue
        home_impact = home["impactPvs"]
        away_impact = away["impactPvs"]
        net = round(home_impact - away_impact, 1)
        matchups.append(
            {
                "home": fx["home"],
                "away": fx["away"],
                "homeImpactPvs": home_impact,
                "awayImpactPvs": away_impact,
                "netAdvantage": net,
                "advantageClub": (
                    fx["home"] if net < 0 else fx["away"] if net > 0 else None
                ),
                "interpretation": (
                    f"{fx['home']} has {abs(net):.1f} PVS less talent sidelined"
                    if net < 0
                    else f"{fx['away']} has {net:.1f} PVS less talent sidelined"
                    if net > 0
                    else "Even selection impact"
                ),
            }
        )

    status_phrase = "final teams" if all_final else "provisional teams (not yet finalised)"
    return {
        "round": target_round,
        "teamsAnnounced": teams_announced,
        "teamSize": TEAM_SIZE,
        "roleMinimums": ROLE_MINIMUMS,
        "selectionSource": "afl.com team line-ups",
        "lastUpdated": last_updated,
        "teamsFinal": bool(all_final),
        "interpretation": (
            f"Round {target_round} {season}, {status_phrase} from AFL.com team line-ups. "
            "Optimal 23 uses season injury-weighted PVS with minimum counts per role. "
            "Impact = combined PVS of a club's optimal-23 players who are unavailable "
            "this week through injury or suspension (per the AFL injury list). Players "
            "who are merely omitted or rested still count as available. Bye teams are "
            "excluded."
        ),
        "ladder": ladder_rows,
        "matchups": matchups,
        "byClub": by_club,
    }
