"""Quick test of state-league ingest for one season."""

from data_pipeline.ingest.sanfl import fetch_sanfl_games
from data_pipeline.ingest.wafl_sportix import fetch_wafl_games

print("WAFL 2024 sample")
wafl = fetch_wafl_games(from_season=2024, to_season=2024, pause=0.05)
print(wafl.head())
print("rows", len(wafl), "peel", (wafl["state_team"] == "Peel Thunder").sum())

print("\nSANFL 2024 sample")
sanfl = fetch_sanfl_games(from_season=2024, to_season=2024, pause=0.05)
print(sanfl.head())
print("rows", len(sanfl))
