"""Export Collingwood 2021 injury deep dive (or any club/season)."""

from pathlib import Path

from data_pipeline.export.club_season_deep_dive import export_club_season_deep_dive

out = Path("c:/temp/Temp/shared/output/exports")
path = export_club_season_deep_dive("Collingwood", 2021, out)
print("written:", path)
