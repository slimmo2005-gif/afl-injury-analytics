"""Load full 2024 state-league snapshot and re-apply availability flags."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline.db import connect
from data_pipeline.export.league_unavailability import export_league_unavailability
from data_pipeline.ingest.state_league import fetch_state_league_games, prepare_state_league_games
from data_pipeline.transform.integrate_draft_vfl import (
    IncompleteStateLeagueError,
    apply_vfl_to_availability,
    link_vfl_player_ids,
    load_state_league_games,
)
from data_pipeline.transform.unavailability import build_team_round_value, enrich_availability_status

CACHE_PATH = Path("c:/temp/Temp/shared/data/state_league_2024_raw.parquet")
SEASON = 2024


def load_raw_cache() -> pd.DataFrame:
    if CACHE_PATH.exists():
        raw = pd.read_parquet(CACHE_PATH)
        print("loaded cache", len(raw), raw["competition"].value_counts().to_dict())
        return raw
    print("Fetching 2024 state-league games (VFL+SANFL+WAFL)...")
    raw = fetch_state_league_games(from_season=SEASON, to_season=SEASON, pause=0.05)
    raw.to_parquet(CACHE_PATH, index=False)
    return raw


def apply_state_league(con, raw: pd.DataFrame) -> pd.DataFrame:
    prepared = prepare_state_league_games(raw, con)
    print("prepared rows", len(prepared))
    load_state_league_games(con, prepared, replace_seasons=[SEASON])
    link_vfl_player_ids(con)
    con.execute(
        """
        UPDATE availability
        SET vfl_played = FALSE, status = 'unavailable'
        WHERE season = ? AND NOT afl_played AND status = 'vfl_only'
        """,
        [SEASON],
    )
    apply_vfl_to_availability(con)
    enrich_availability_status(con)
    build_team_round_value(con)
    return prepared


if __name__ == "__main__":
    con = connect()
    apply_state_league(con, load_raw_cache())
    con.close()

    export_path = export_league_unavailability(SEASON)
    print(f"\nExported league unavailability -> {export_path}")

    con = connect()
    print("\n=== state-league rows loaded ===")
    print(con.execute("SELECT competition, COUNT(*) n FROM vfl_games WHERE season=? GROUP BY 1", [SEASON]).df())
