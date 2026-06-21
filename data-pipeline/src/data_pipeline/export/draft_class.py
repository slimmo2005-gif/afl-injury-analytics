"""Export draft-class snapshot for the current-season page."""

from __future__ import annotations

import duckdb

from ..transform.archetypes import ARCHETYPE_LABELS

# 2025 national draft had 25 first-round selections (incl. academy bids).
FIRST_ROUND_MAX_PICK = 25


def build_draft_class_bundle(
    con: duckdb.DuckDBPyConnection,
    *,
    draft_year: int,
    season: int,
    first_round_max_pick: int = FIRST_ROUND_MAX_PICK,
) -> dict:
    """First-round picks from draft_year with season-to-date games and performance score."""
    picks = con.execute(
        """
        SELECT draft_pick, player_name, drafted_club, player_id
        FROM draft_picks
        WHERE draft_year = ? AND draft_pick <= ?
        ORDER BY draft_pick
        """,
        [draft_year, first_round_max_pick],
    ).df()

    if picks.empty:
        return {
            "draftYear": draft_year,
            "season": season,
            "firstRoundMaxPick": first_round_max_pick,
            "players": [],
            "interpretation": f"No {draft_year} first-round picks in draft_picks table.",
        }

    rows: list[dict] = []
    for row in picks.itertuples(index=False):
        pick = int(row.draft_pick)
        name = str(row.player_name)
        club = str(row.drafted_club)
        pid = row.player_id

        games = 0
        perf: float | None = None
        pvs: float | None = None
        archetype = ""
        matched_name = name

        if pid and str(pid) != "nan":
            stat = con.execute(
                """
                SELECT
                    MAX(pg.player_name) AS player_name,
                    COUNT(*) AS games,
                    MAX(v.performance_score) AS performance_score,
                    MAX(v.pvs) AS pvs,
                    MAX(p.archetype) AS archetype
                FROM player_games pg
                LEFT JOIN player_value v
                    ON pg.player_id = v.player_id
                    AND pg.team = v.team
                    AND pg.season = v.season
                LEFT JOIN player_profiles p
                    ON pg.player_id = p.player_id
                    AND pg.team = p.team
                    AND pg.season = p.season
                WHERE pg.season = ? AND pg.player_id = ?
                GROUP BY pg.player_id
                """,
                [season, str(pid)],
            ).fetchone()
            if stat and stat[1]:
                matched_name = stat[0] or name
                games = int(stat[1])
                perf = round(float(stat[2]), 2) if stat[2] is not None else None
                pvs = round(float(stat[3]), 2) if stat[3] is not None else None
                archetype = str(stat[4] or "")
        else:
            # Name + club fallback when draft row is not linked to player_id yet.
            stat = con.execute(
                """
                SELECT
                    pg.player_name,
                    COUNT(*) AS games,
                    MAX(v.performance_score) AS performance_score,
                    MAX(v.pvs) AS pvs,
                    MAX(p.archetype) AS archetype
                FROM player_games pg
                LEFT JOIN player_value v
                    ON pg.player_id = v.player_id
                    AND pg.team = v.team
                    AND pg.season = v.season
                LEFT JOIN player_profiles p
                    ON pg.player_id = p.player_id
                    AND pg.team = p.team
                    AND pg.season = p.season
                WHERE pg.season = ?
                  AND pg.team = ?
                  AND lower(pg.player_name) = lower(?)
                GROUP BY pg.player_name
                LIMIT 1
                """,
                [season, club, name],
            ).fetchone()
            if stat:
                matched_name = stat[0]
                games = int(stat[1])
                perf = round(float(stat[2]), 2) if stat[2] is not None else None
                pvs = round(float(stat[3]), 2) if stat[3] is not None else None
                archetype = str(stat[4] or "")

        rows.append(
            {
                "pick": pick,
                "player": matched_name,
                "club": club,
                "games": games,
                "performanceScore": perf,
                "pvs": pvs,
                "archetype": archetype,
                "archetypeLabel": ARCHETYPE_LABELS.get(archetype, archetype or "—"),
                "hasDebuted": games > 0,
            }
        )

    debuted = sum(1 for r in rows if r["hasDebuted"])
    with_perf = [r for r in rows if r["performanceScore"] is not None]

    return {
        "draftYear": draft_year,
        "season": season,
        "firstRoundMaxPick": first_round_max_pick,
        "totalPicks": len(rows),
        "debuted": debuted,
        "players": rows,
        "interpretation": (
            f"{draft_year} national draft first round (picks 1–{first_round_max_pick}) "
            f"in {season} through the latest completed round. "
            "Performance score is stats-only (0–7); PVS shown for reference includes "
            "draft-potential top-up for young players. "
            f"{debuted} of {len(rows)} have played AFL."
        ),
        "topPerformance": sorted(
            with_perf,
            key=lambda r: r["performanceScore"] or 0,
            reverse=True,
        )[:5],
    }
