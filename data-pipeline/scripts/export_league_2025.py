"""Export 2025 league player and unavailability workbooks."""

from pathlib import Path

from data_pipeline.export.league_players import export_league_players
from data_pipeline.export.league_unavailability import export_league_unavailability

out = Path("c:/temp/Temp/shared/output/exports")
print("players:", export_league_players(2025, out))
print("unavailability:", export_league_unavailability(2025, out))
