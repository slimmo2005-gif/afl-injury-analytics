"""Weekly selection impact: optimal PVS team vs AFL's announced line-up.

Source of truth for "who is playing" is the AFL.com team line-ups feed
(https://www.afl.com.au/matches/team-lineups) via the ``matchRoster`` API.
Teams on a bye have no line-up and are therefore excluded automatically.
Impact for a club = the season injury-weighted PVS of its optimal-23 players
who are *not* named in this week's side (injured, omitted, rested or suspended).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import duckdb
import requests
from bs4 import BeautifulSoup

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


MIN_ESTABLISHED_GAMES = 10
SUSPENSIONS_TRACKER_URL = "https://aflratings.com.au/afl-suspensions/"
_SUSP_CODE_TO_TEAM: dict[str, str] = {
    "ADE": "Adelaide",
    "BRI": "Brisbane Lions",
    "CAR": "Carlton",
    "COL": "Collingwood",
    "ESS": "Essendon",
    "FRE": "Fremantle",
    "GEE": "Geelong",
    "GC": "Gold Coast",
    "GWS": "Greater Western Sydney",
    "HAW": "Hawthorn",
    "MEL": "Melbourne",
    "NM": "North Melbourne",
    "PA": "Port Adelaide",
    "RIC": "Richmond",
    "STK": "St Kilda",
    "SYD": "Sydney",
    "WC": "West Coast",
    "WB": "Western Bulldogs",
}


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
    squad = [
        SquadPlayer(
            player_id=str(r[0]),
            player_name=str(r[1]),
            archetype=str(r[2]),
            injury_pvs=float(r[3] or 0),
        )
        for r in rows
    ]
    have = {p.player_id for p in squad}
    squad.extend(p for p in _injured_absent_squad(con, season, team) if p.player_id not in have)
    return squad


def _injured_absent_squad(
    con: duckdb.DuckDBPyConnection, season: int, team: str
) -> list[SquadPlayer]:
    """Established players on the current injury list with no games this season.

    A season-ending injury (e.g. an ACL) means the player has no ``season``
    games and therefore never appears in :func:`_load_squad`, which would make
    a genuine best-23 loss invisible. We add them back at their most recent
    established PVS (latest prior season with enough games) so they can earn a
    best-23 spot and be counted as unavailable.
    """
    try:
        rows = con.execute(
            """
            WITH latest AS (SELECT MAX(list_date) d FROM injury_list_entries),
            injured AS (
                SELECT player_id, MAX(player_name) AS player_name
                FROM injury_list_entries
                WHERE list_date = (SELECT d FROM latest)
                  AND team = ?
                  AND player_id IS NOT NULL
                  AND (is_injury OR injury_category = 'suspension')
                GROUP BY player_id
            ),
            recent_val AS (
                SELECT player_id,
                       COALESCE(injury_weight_pvs, pvs) AS pvs,
                       ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY season DESC) AS rn
                FROM player_value
                WHERE season < ? AND games >= ?
            ),
            recent_arch AS (
                SELECT player_id, archetype,
                       ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY season DESC) AS rn
                FROM player_profiles
                WHERE season < ?
            )
            SELECT i.player_id,
                   i.player_name,
                   COALESCE(ra.archetype, 'utility') AS archetype,
                   rv.pvs
            FROM injured i
            JOIN recent_val rv ON rv.player_id = i.player_id AND rv.rn = 1
            LEFT JOIN recent_arch ra ON ra.player_id = i.player_id AND ra.rn = 1
            """,
            [team, season, MIN_ESTABLISHED_GAMES, season],
        ).fetchall()
    except duckdb.Error:
        return []
    return [
        SquadPlayer(
            player_id=str(r[0]),
            player_name=str(r[1]),
            archetype=str(r[2]),
            injury_pvs=float(r[3] or 0),
        )
        for r in rows
    ]


def _parse_suspension_return_round(estimated_return: str | None) -> int | None:
    """Parse ``Round 19`` / ``R19`` style AFL estimated-return strings."""
    if not estimated_return:
        return None
    m = re.search(r"round\s*(\d+)", str(estimated_return).strip(), re.I)
    return int(m.group(1)) if m else None


def _team_matches_before_round(
    con: duckdb.DuckDBPyConnection, season: int, team: str, round_num: int
) -> set[int]:
    rows = con.execute(
        """
        SELECT round
        FROM matches
        WHERE season = ?
          AND round < ?
          AND (home_team = ? OR away_team = ?)
        """,
        [season, round_num, team, team],
    ).fetchall()
    return {int(r[0]) for r in rows}


def _active_suspensions_from_tracker(
    con: duckdb.DuckDBPyConnection, season: int, round_num: int
) -> dict[str, dict[str, str]]:
    """Active suspensions from public tracker using team fixtures (bye-aware).

    Tracker gives offense round + suspension length. We count only the club's
    own matches between offense round and target round (exclusive) so byes are
    naturally handled.
    """
    out: dict[str, dict[str, str]] = {}
    try:
        resp = requests.get(
            SUSPENSIONS_TRACKER_URL,
            timeout=20,
            headers={"User-Agent": "afl-injury-analytics/0.4"},
        )
        if not resp.ok:
            return {}
        soup = BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException:
        return {}

    h2 = None
    for node in soup.find_all("h2"):
        if f"{season} AFL SUSPENSIONS" in node.get_text(" ", strip=True).upper():
            h2 = node
            break
    if h2 is None:
        return {}

    table = h2.find_next("table")
    if table is None:
        return {}

    for tr in table.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["th", "td"])]
        if len(cells) < 4:
            continue
        player, club_code, round_token, suspension = cells[:4]
        if player.upper() == "PLAYER":
            continue
        if re.fullmatch(r"\d{4}", player):
            # Next-season section marker in the same table (e.g. "2025").
            break
        team = _SUSP_CODE_TO_TEAM.get(club_code.upper())
        if not team:
            continue
        m_round = re.search(r"R(\d+)", round_token.upper())
        m_len = re.search(r"(\d+)\s*match", suspension.lower())
        if not m_round or not m_len:
            continue
        offense_round = int(m_round.group(1))
        weeks = int(m_len.group(1))
        prior_team_rounds = _team_matches_before_round(con, season, team, round_num)
        served = sum(1 for rn in prior_team_rounds if rn > offense_round)
        if served < weeks:
            norm = " ".join(player.lower().split())
            out.setdefault(team, {})[norm] = "suspended"
    return out


def _unavailable_lookup(
    con: duckdb.DuckDBPyConnection,
    season: int,
    round_num: int,
) -> dict[str, dict[str, str]]:
    """Unavailable players for a given round: team -> {normalized name: reason}.

    ``reason`` is ``"injured"`` or ``"suspended"``. Injuries come from the latest
    AFL injury-list snapshot. Suspensions also carry forward when the AFL drops
    a player from the list mid-ban but ``estimated_return`` is still in the
    future (e.g. a 3-week ban listed once as ``Round 19``).
    """
    out: dict[str, dict[str, str]] = {}
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
        for team, norm, reason in rows:
            out.setdefault(str(team), {})[str(norm).strip()] = str(reason)
    except duckdb.Error:
        pass

    # Active suspensions removed from the latest list but not yet served out.
    try:
        susp_rows = con.execute(
            """
            WITH ranked AS (
                SELECT team,
                       LOWER(REGEXP_REPLACE(player_name, '\\s+', ' ', 'g')) AS norm,
                       estimated_return,
                       ROW_NUMBER() OVER (
                           PARTITION BY team,
                               LOWER(REGEXP_REPLACE(player_name, '\\s+', ' ', 'g'))
                           ORDER BY list_date DESC
                       ) AS rn
                FROM injury_list_entries
                WHERE injury_category = 'suspension'
            )
            SELECT team, norm, estimated_return
            FROM ranked
            WHERE rn = 1
            """
        ).fetchall()
        for team, norm, est in susp_rows:
            return_round = _parse_suspension_return_round(est)
            if return_round is not None and return_round > round_num:
                out.setdefault(str(team), {})[str(norm).strip()] = "suspended"
    except duckdb.Error:
        pass

    # Independent suspension tracker (offense round + suspension length), with
    # bye-aware carry-forward based on the club's actual fixtures.
    tracker = _active_suspensions_from_tracker(con, season, round_num)
    for team, players in tracker.items():
        out.setdefault(team, {}).update(players)

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
    """Net selection impact of injuries/suspensions.

    Impact = (C) - (B), where:
      * (B) selectedTeamPvs  = PVS of the 23 actually named.
      * (C) cPvs             = PVS of that same side with each injured/suspended
                               best-23 player swapped back in for the cover the
                               coach used in their place. Players the coach simply
                               left out (available, not on the injury list) are
                               kept as picked and never counted as a loss.

    Per missing player we report ``grossPvs`` (their own PVS) and ``netPvs``
    (their PVS minus the PVS of the player who replaced them). Replacements are
    assigned to missing stars best-first: the highest-PVS unused cover player of
    the same role, otherwise the highest-PVS remaining cover player.
    """
    unavailable = unavailable or {}
    squad_by_id = {p.player_id: p for p in squad}
    named_set = set(named_ids)
    best_ids = {p.player_id for p in best}

    best_total = round(sum(p.injury_pvs for p in best), 1)
    named_total = round(
        sum(squad_by_id[pid].injury_pvs for pid in named_set if pid in squad_by_id),
        1,
    )

    def _norm(name: str) -> str:
        return " ".join(name.lower().split())

    # Best-23 players who are genuinely unavailable (on the AFL injury list,
    # injured or suspended) and not named. Available depth the coach omitted
    # is NOT a loss and is excluded.
    out_players: list[tuple[SquadPlayer, str]] = []
    for p in best:
        if p.player_id in named_set:
            continue
        reason = unavailable.get(_norm(p.player_name))
        if reason:
            out_players.append((p, reason))
    out_players.sort(key=lambda t: t[0].injury_pvs, reverse=True)

    # Cover pool = named players who are not part of the optimal best-23, i.e.
    # the depth brought in. Sorted best-first so role matches pick the top option.
    cover_pool = [
        squad_by_id[pid]
        for pid in named_set
        if pid in squad_by_id and pid not in best_ids
    ]
    cover_pool.sort(key=lambda x: x.injury_pvs, reverse=True)

    used_cover: set[str] = set()
    missing: list[dict] = []
    net_total = 0.0
    by_role: dict[str, float] = {}
    for p, reason in out_players:
        same_role = [
            c for c in cover_pool if c.player_id not in used_cover and c.archetype == p.archetype
        ]
        if same_role:
            rep = same_role[0]
        else:
            rest = [c for c in cover_pool if c.player_id not in used_cover]
            rep = rest[0] if rest else None
        rep_pvs = rep.injury_pvs if rep else 0.0
        if rep is not None:
            used_cover.add(rep.player_id)
        # Floor at 0: a like-for-like or better replacement means no net loss.
        # An injury can never make a side stronger, so impact is never negative.
        net = max(0.0, p.injury_pvs - rep_pvs)
        net_total += net
        by_role[p.archetype] = round(by_role.get(p.archetype, 0) + net, 1)
        missing.append(
            {
                "player": p.player_name,
                "archetype": p.archetype,
                "archetypeLabel": ARCHETYPE_LABELS.get(p.archetype, p.archetype),
                "pvs": round(p.injury_pvs, 1),
                "grossPvs": round(p.injury_pvs, 1),
                "netPvs": round(net, 1),
                "replacedBy": rep.player_name if rep is not None else None,
                "replacementPvs": round(rep_pvs, 1),
                "reason": reason,
                "injured": reason == "injured",
                "suspended": reason == "suspended",
            }
        )

    impact_pvs = round(net_total, 1)

    return {
        "bestTeamPvs": best_total,
        "selectedTeamPvs": named_total,
        "cPvs": round(named_total + net_total, 1),
        "impactPvs": impact_pvs,
        "pvsGap": round(best_total - named_total, 1),
        "selectedCount": len(named_set),
        "missingFromOptimal": missing[:12],
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
    unavailable = _unavailable_lookup(con, season, target_round)
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
            "Impact = (C) − (B): the PVS the side would gain if its injured/suspended "
            "best-23 players were fit (C) versus the team actually named (B). Each "
            "missing star is offset by the player who replaced them (best same-role "
            "cover, else best remaining cover), so impact is the net talent lost. "
            "Players the coach simply left out still count as available. Bye teams are "
            "excluded."
        ),
        "ladder": ladder_rows,
        "matchups": matchups,
        "byClub": by_club,
    }


def build_weekly_team_impact_section(
    con: duckdb.DuckDBPyConnection,
    season: int,
) -> dict:
    """Current round plus archived snapshots for prior rounds with line-ups."""
    current_round = current_round_with_teams(season)
    if not current_round or current_round <= 0:
        empty = build_weekly_team_impact_bundle(con, season, round_num=0)
        return {
            "weeklyTeamImpact": empty,
            "weeklyTeamImpactByRound": {},
            "weeklyTeamImpactRounds": [],
        }

    by_round: dict[str, dict] = {}
    for rn in range(1, current_round + 1):
        bundle = build_weekly_team_impact_bundle(con, season, round_num=rn)
        if bundle.get("teamsAnnounced"):
            by_round[str(rn)] = bundle

    current = by_round.get(str(current_round)) or build_weekly_team_impact_bundle(
        con, season, round_num=current_round
    )
    return {
        "weeklyTeamImpact": current,
        "weeklyTeamImpactByRound": by_round,
        "weeklyTeamImpactRounds": sorted(int(k) for k in by_round),
    }
