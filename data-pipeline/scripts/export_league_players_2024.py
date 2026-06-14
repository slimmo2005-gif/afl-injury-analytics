"""Export league_2024_all_players.xlsx with MI50 and intercept marks."""

from pathlib import Path

from data_pipeline.export.league_players import export_league_players

out = Path("c:/temp/Temp/shared/output/exports")
try:
    path = export_league_players(2024, out)
except PermissionError:
    path = export_league_players(2024, out / "_refresh")
print("written:", path)
