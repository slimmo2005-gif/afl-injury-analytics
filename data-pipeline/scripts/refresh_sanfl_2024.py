"""Refresh SANFL in the raw cache only, then reload the full 2024 state-league snapshot."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline.db import connect
from data_pipeline.export.league_unavailability import export_league_unavailability
from data_pipeline.ingest.sanfl import fetch_sanfl_games

CACHE_PATH = Path("c:/temp/Temp/shared/data/state_league_2024_raw.parquet")
SEASON = 2024

if __name__ == "__main__":
    raw = pd.read_parquet(CACHE_PATH)
    non_sanfl = raw[raw.competition != "sanfl"]
    print("Refreshing SANFL in cache only …")
    sanfl = fetch_sanfl_games(from_season=SEASON, to_season=SEASON, pause=0.05)
    sanfl = sanfl[sanfl["player_name"].str.len() >= 2]
    updated = pd.concat([non_sanfl, sanfl], ignore_index=True)
    updated.to_parquet(CACHE_PATH, index=False)
    print("cache updated", updated["competition"].value_counts().to_dict())

    from apply_state_league_2024 import apply_state_league

    con = connect()
    apply_state_league(con, updated)
    con.close()

    print(export_league_unavailability(SEASON))
