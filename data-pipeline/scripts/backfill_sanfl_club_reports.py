"""Refresh SANFL club-report player rows and reload into DuckDB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline.config import DEFAULT_SEASON
from data_pipeline.db import connect
from data_pipeline.ingest.sanfl import fetch_sanfl_games
from data_pipeline.ingest.state_league import prepare_state_league_games
from data_pipeline.transform.integrate_draft_vfl import (
    apply_vfl_to_availability,
    link_vfl_player_ids,
    load_state_league_games,
)
from data_pipeline.transform.unavailability import build_team_round_value, enrich_availability_status


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill SANFL club match reports")
    parser.add_argument("--from-season", type=int, default=2025)
    parser.add_argument("--to-season", type=int, default=DEFAULT_SEASON)
    parser.add_argument("--refresh-paths", action="store_true", help="Re-scan club news IDs")
    parser.add_argument("--pause", type=float, default=0.08)
    args = parser.parse_args()

    if args.refresh_paths:
        from data_pipeline.ingest.sanfl_club_reports import CLUBS, discover_article_paths

        for club in CLUBS:
            paths = discover_article_paths(club, pause=args.pause, refresh=True)
            print(f"[sanfl_club] {club.key}: {len(paths)} paths cached")

    sanfl = fetch_sanfl_games(
        from_season=args.from_season,
        to_season=args.to_season,
        pause=args.pause,
    )
    print(f"[sanfl] total rows {len(sanfl)}")

    from data_pipeline.ingest.state_league import fetch_state_league_games, prepare_state_league_games

    full = fetch_state_league_games(
        from_season=args.from_season,
        to_season=args.to_season,
        pause=args.pause,
    )
    print(f"[state_league] full fetch {len(full)} rows")

    con = connect()
    seasons = list(range(args.from_season, args.to_season + 1))
    prepared = prepare_state_league_games(full, con)
    load_state_league_games(con, prepared, replace_seasons=seasons)
    link_vfl_player_ids(con)
    apply_vfl_to_availability(con)
    enrich_availability_status(con)
    build_team_round_value(con)

    print(
        con.execute(
            """
            SELECT season, COUNT(*) n
            FROM vfl_games
            WHERE competition = 'sanfl' AND season IN (SELECT UNNEST(?))
            GROUP BY 1 ORDER BY 1
            """,
            [seasons],
        ).df()
    )
    print(
        con.execute(
            """
            SELECT season, COUNT(*) FILTER (WHERE status = 'vfl_only') vfl_only
            FROM availability
            WHERE season IN (SELECT UNNEST(?)) AND team IN ('Adelaide', 'Port Adelaide')
            GROUP BY 1 ORDER BY 1
            """,
            [seasons],
        ).df()
    )
    con.close()


if __name__ == "__main__":
    main()
