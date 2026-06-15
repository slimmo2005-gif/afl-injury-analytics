#!/usr/bin/env python3
"""Weekly injury list fetch (AFL.com + BigFooty) and absence enrichment."""

from __future__ import annotations

import argparse

from data_pipeline.db import connect
from data_pipeline.export.injury_report import export_injury_episodes
from data_pipeline.ingest.injury_sources import ingest_live_injury_lists
from data_pipeline.transform.absences import enrich_absence_reasons


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch live injury lists and enrich absences")
    parser.add_argument("--skip-fetch", action="store_true", help="Use injury_list_entries already in DB")
    parser.add_argument("--export-season", type=int, default=None)
    args = parser.parse_args()

    con = connect()
    if not args.skip_fetch:
        ingest_live_injury_lists(con)

    enrich_absence_reasons(con)
    export_injury_episodes(con, season=args.export_season)


if __name__ == "__main__":
    main()
