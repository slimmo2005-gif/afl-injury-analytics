"""Excel breakdown of weekly selection impact for clubs playing this round.

"Who is in" comes from the AFL.com team line-ups feed
(https://www.afl.com.au/matches/team-lineups). Teams on a bye have no line-up
and are excluded. For each playing club:
  - every squad player's injury-weighted PVS and role
  - whether they are NAMED in this week's 23
  - whether they make the full-strength optimal 23
  - whether they are on the latest injury list (context only)
Summary ranks clubs by the PVS of optimal-23 talent not named this week.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from data_pipeline.config import CURRENT_SEASON
from data_pipeline.db import connect
from data_pipeline.export.weekly_team_impact import (
    ROLE_MINIMUMS,
    TEAM_SIZE,
    SquadPlayer,
    _injured_names,
    _load_squad,
    _name_lookup,
    _pick_best_team,
    _resolve_roster_ids,
)
from data_pipeline.ingest.team_selections import (
    current_round_with_teams,
    fetch_round_rosters,
)

OUT = Path(__file__).resolve().parents[2] / "shared" / "output" / "exports"


def main() -> None:
    con = connect()
    season = CURRENT_SEASON
    OUT.mkdir(parents=True, exist_ok=True)

    rnd = current_round_with_teams(season)
    rosters = fetch_round_rosters(season, rnd)
    name_lookup = _name_lookup(con, season)
    roster_ids = _resolve_roster_ids(rosters, name_lookup)
    injured = _injured_names(con)
    snapshot = con.execute("SELECT MAX(list_date) FROM injury_list_entries").fetchone()[0]

    player_rows: list[dict] = []
    summary_rows: list[dict] = []

    for club in sorted(rosters):
        squad = _load_squad(con, season, club)
        if not squad:
            continue

        named_ids = set(roster_ids.get(club, []))
        club_injured = injured.get(club, set())

        def is_injured(p: SquadPlayer) -> bool:
            return " ".join(p.player_name.lower().split()) in club_injured

        best_full = _pick_best_team(squad)
        best_full_ids = {p.player_id for p in best_full}
        best_full_pvs = round(sum(p.injury_pvs for p in best_full), 1)

        named_pvs = round(
            sum(p.injury_pvs for p in squad if p.player_id in named_ids), 1
        )
        missing = [p for p in best_full if p.player_id not in named_ids]
        impact_pvs = round(sum(p.injury_pvs for p in missing), 1)
        injured_missing = [p for p in missing if is_injured(p)]

        summary_rows.append(
            {
                "club": club,
                "team_status": rosters[club].get("team_status"),
                "best23_pvs": best_full_pvs,
                "named_team_pvs": named_pvs,
                "impact_pvs": impact_pvs,
                "pvs_gap": round(best_full_pvs - named_pvs, 1),
                "best23_missing": len(missing),
                "of_which_injured": len(injured_missing),
                "top_missing": ", ".join(
                    f"{p.player_name} ({p.injury_pvs:.1f})" for p in missing[:6]
                ),
            }
        )

        for p in sorted(squad, key=lambda x: x.injury_pvs, reverse=True):
            player_rows.append(
                {
                    "club": club,
                    "player": p.player_name,
                    "role": p.archetype,
                    "injury_weighted_pvs": round(p.injury_pvs, 2),
                    "in_best23": p.player_id in best_full_ids,
                    "named_this_week": p.player_id in named_ids,
                    "on_injury_list": is_injured(p),
                }
            )

    summary = pd.DataFrame(summary_rows).sort_values("impact_pvs").reset_index(drop=True)
    summary.insert(0, "impact_rank", summary.index + 1)
    players = pd.DataFrame(player_rows)

    out_path = OUT / f"weekly_team_impact_{season}.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        players.to_excel(writer, sheet_name="All players", index=False)
        for club in summary["club"]:
            sub = players[players["club"] == club].copy()
            sheet = club[:28].replace("/", "-")
            sub.to_excel(writer, sheet_name=sheet, index=False)
        notes = pd.DataFrame(
            [
                {"field": "round", "value": rnd},
                {"field": "lineups_source", "value": "AFL.com team line-ups (matchRoster API)"},
                {"field": "injury_snapshot", "value": f"Injury list dated {snapshot} (context only; incomplete)"},
                {"field": "team_size", "value": TEAM_SIZE},
                {"field": "role_minimums", "value": str(ROLE_MINIMUMS)},
                {"field": "best23_pvs", "value": "Full-strength optimal 23 by injury-weighted PVS"},
                {"field": "named_team_pvs", "value": "PVS of the 23 named this week"},
                {"field": "impact_pvs", "value": "PVS of optimal-23 players NOT named this week (injured/rested/omitted/suspended)"},
                {"field": "byes", "value": "Clubs on a bye have no line-up and are excluded"},
            ]
        )
        notes.to_excel(writer, sheet_name="Notes", index=False)

    print(f"Wrote {out_path}  (round {rnd}, {len(summary)} clubs)")
    print("\n=== Summary (ranked healthiest -> most impacted) ===")
    print(
        summary[
            ["impact_rank", "club", "best23_pvs", "named_team_pvs", "impact_pvs", "best23_missing", "of_which_injured"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
