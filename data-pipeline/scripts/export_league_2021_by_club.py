"""Export league_2021_by_club.xlsx with team summary and per-club player tabs."""

from pathlib import Path

from data_pipeline.export.league_players import export_league_by_club

out = Path("c:/temp/Temp/shared/output/exports")
path = export_league_by_club(2021, out)
print("written:", path)
