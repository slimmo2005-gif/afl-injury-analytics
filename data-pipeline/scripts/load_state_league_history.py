"""Fetch and load state-league participation (VFL/SANFL/WAFL) for all available seasons."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline.config import DEFAULT_SEASON, ROOT
from data_pipeline.db import connect
from data_pipeline.export.frontend import write_metrics
from data_pipeline.ingest.state_league import (
    STATE_LEAGUE_FROM_SEASON,
    fetch_state_league_games,
    prepare_state_league_games,
)
from data_pipeline.transform.integrate_draft_vfl import (
    apply_vfl_to_availability,
    link_vfl_player_ids,
    load_state_league_games,
)
from data_pipeline.transform.unavailability import build_team_round_value, enrich_availability_status

CACHE_PATH = ROOT / "shared" / "data" / "state_league_games.parquet"

# vfl.aflmstats.com has seasons from 2021; SANFL AFL API from ~2022; WAFL Sportix from 2018.
DEFAULT_FROM = 2021


def load_or_fetch(
    from_season: int,
    to_season: int,
    *,
    refresh: bool = False,
    pause: float = 0.12,
) -> pd.DataFrame:
    if CACHE_PATH.exists() and not refresh:
        raw = pd.read_parquet(CACHE_PATH)
        sub = raw[(raw["season"] >= from_season) & (raw["season"] <= to_season)]
        if not sub.empty:
            print(f"[state_league] loaded cache {CACHE_PATH} ({len(sub)} rows in range)")
            return sub

    print(f"[state_league] fetching VFL+SANFL+WAFL {from_season}-{to_season} …")
    raw = fetch_state_league_games(
        from_season=from_season,
        to_season=to_season,
        pause=pause,
    )
    if raw.empty:
        raise RuntimeError("No state-league rows returned from scrapers")

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CACHE_PATH.exists() and not refresh:
        existing = pd.read_parquet(CACHE_PATH)
        keep = existing[
            (existing["season"] < from_season) | (existing["season"] > to_season)
        ]
        raw = pd.concat([keep, raw], ignore_index=True)
    raw.to_parquet(CACHE_PATH, index=False)
    print(f"[state_league] cached {len(raw)} rows -> {CACHE_PATH}")
    return raw[(raw["season"] >= from_season) & (raw["season"] <= to_season)]


def apply_to_db(
    con,
    raw: pd.DataFrame,
    seasons: list[int],
) -> None:
    prepared = prepare_state_league_games(raw, con)
    print(
        "[state_league] prepared rows",
        len(prepared),
        prepared.groupby(["season", "competition"]).size().to_dict(),
    )
    load_state_league_games(con, prepared, replace_seasons=seasons)
    link_vfl_player_ids(con)

    placeholders = ", ".join("?" * len(seasons))
    con.execute(
        f"""
        UPDATE availability
        SET vfl_played = FALSE, status = 'unavailable'
        WHERE season IN ({placeholders})
          AND NOT afl_played
          AND status = 'vfl_only'
        """,
        seasons,
    )
    apply_vfl_to_availability(con)
    enrich_availability_status(con)
    build_team_round_value(con)


def report(con, seasons: list[int]) -> None:
    print("\n=== vfl_games loaded ===")
    print(
        con.execute(
            """
            SELECT season, competition, COUNT(*) n
            FROM vfl_games
            GROUP BY 1, 2
            ORDER BY 1, 2
            """
        ).df()
    )
    print("\n=== vfl_only availability by season ===")
    print(
        con.execute(
            """
            SELECT season, COUNT(*) FILTER (WHERE status = 'vfl_only') vfl_only,
                   COUNT(*) FILTER (WHERE status = 'unavailable') unavailable
            FROM availability
            WHERE season IN (SELECT UNNEST(?))
            GROUP BY 1 ORDER BY 1
            """,
            [seasons],
        ).df()
    )
    for season in seasons:
        print(f"\n--- {season} top vfl_only clubs ---")
        print(
            con.execute(
                """
                SELECT team, COUNT(*) FILTER (WHERE status = 'vfl_only') vfl_only
                FROM availability WHERE season = ?
                GROUP BY 1 ORDER BY 2 DESC LIMIT 6
                """,
                [season],
            ).df()
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load state-league history into DuckDB")
    parser.add_argument("--from-season", type=int, default=DEFAULT_FROM)
    parser.add_argument("--to-season", type=int, default=DEFAULT_SEASON)
    parser.add_argument("--refresh", action="store_true", help="Re-scrape even if cache exists")
    parser.add_argument("--pause", type=float, default=0.12)
    parser.add_argument("--no-metrics", action="store_true")
    args = parser.parse_args()

    seasons = list(range(args.from_season, args.to_season + 1))
    raw = load_or_fetch(args.from_season, args.to_season, refresh=args.refresh, pause=args.pause)

    con = connect()
    apply_to_db(con, raw, seasons)
    report(con, seasons)
    if not args.no_metrics:
        path = write_metrics(con)
        print(f"\n[metrics] {path}")
    con.close()


if __name__ == "__main__":
    main()
