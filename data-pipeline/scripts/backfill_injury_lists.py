#!/usr/bin/env python3
"""Backfill historical injury list snapshots from BigFooty + Wayback."""

from __future__ import annotations

import argparse

from data_pipeline.db import connect
from data_pipeline.export.injury_report import export_injury_episodes
from data_pipeline.ingest.injury_sources import backfill_injury_lists, ingest_live_injury_lists
from data_pipeline.transform.absences import enrich_absence_reasons


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill injury list entries from multiple sources")
    parser.add_argument("--live", action="store_true", help="Also fetch current AFL.com + recent BigFooty")
    parser.add_argument("--no-wayback", action="store_true", help="Skip Wayback AFL.com snapshots")
    parser.add_argument("--no-forum", action="store_true", help="Skip BigFooty forum threads")
    parser.add_argument("--no-news", action="store_true", help="Skip BigFooty news category")
    parser.add_argument("--wayback-from", type=int, default=2021)
    parser.add_argument("--wayback-to", type=int, default=2022)
    parser.add_argument("--years", type=str, default="2018,2019,2023,2024,2025")
    parser.add_argument("--enrich", action="store_true", help="Re-run absence enrichment after load")
    parser.add_argument("--export-season", type=int, default=None)
    args = parser.parse_args()

    years = tuple(int(y.strip()) for y in args.years.split(",") if y.strip())
    con = connect()

    counts = backfill_injury_lists(
        con,
        years=years,
        include_wayback=not args.no_wayback,
        include_forum=not args.no_forum,
        include_news=not args.no_news,
        wayback_from=args.wayback_from,
        wayback_to=args.wayback_to,
    )
    print("[backfill] loaded:", counts)

    if args.live:
        ingest_live_injury_lists(con)

    total = con.execute("SELECT COUNT(*) FROM injury_list_entries").fetchone()[0]
    by_source = con.execute(
        "SELECT source, COUNT(*) AS n FROM injury_list_entries GROUP BY 1 ORDER BY n DESC"
    ).df()
    print(f"[backfill] injury_list_entries total: {total}")
    print(by_source.to_string(index=False))

    if args.enrich:
        enrich_absence_reasons(con)
        if args.export_season:
            export_injury_episodes(con, season=args.export_season)


if __name__ == "__main__":
    main()
