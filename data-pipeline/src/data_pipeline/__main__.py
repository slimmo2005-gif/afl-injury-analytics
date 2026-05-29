"""CLI: python -m data_pipeline run --from-season 2012 --to-season 2024"""

from __future__ import annotations

import argparse

from .config import DEFAULT_SEASON, MIN_SEASON
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="AFL availability ETL pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Ingest, transform, and export metrics")
    run_p.add_argument("--from-season", type=int, default=MIN_SEASON)
    run_p.add_argument("--to-season", type=int, default=DEFAULT_SEASON)
    run_p.add_argument("--export-season", type=int, default=None)
    run_p.add_argument("--skip-squiggle", action="store_true")
    run_p.add_argument("--skip-fryzigg", action="store_true")
    run_p.add_argument("--skip-draft", action="store_true")
    run_p.add_argument("--skip-vfl", action="store_true")
    run_p.add_argument("--vfl-from-season", type=int, default=2018)
    run_p.add_argument("--refresh-vfl-cache", action="store_true")

    args = parser.parse_args()
    if args.command == "run":
        run_pipeline(
            from_season=args.from_season,
            to_season=args.to_season,
            export_season=args.export_season,
            skip_squiggle=args.skip_squiggle,
            skip_fryzigg=args.skip_fryzigg,
            skip_draft=args.skip_draft,
            skip_vfl=args.skip_vfl,
            vfl_from_season=args.vfl_from_season,
            refresh_vfl_cache=args.refresh_vfl_cache,
        )


if __name__ == "__main__":
    main()
