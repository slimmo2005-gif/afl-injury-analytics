"""Rebuild availability metrics and regenerate 2024 Excel exports."""

from data_pipeline.db import connect
from data_pipeline.export.club_export import export_club_season
from data_pipeline.export.league_unavailability import export_league_unavailability
from data_pipeline.export.performance_detail import export_performance_detail
from data_pipeline.transform.availability import build_availability
from data_pipeline.transform.integrate_draft_vfl import apply_vfl_to_availability
from data_pipeline.transform.unavailability import (
    build_team_round_value,
    enrich_availability_status,
)

con = connect()
print("[1/4] Rebuilding availability …")
build_availability(con)
apply_vfl_to_availability(con)
enrich_availability_status(con)
build_team_round_value(con)
con.close()

print("[2/4] League unavailability …")
print(export_league_unavailability(2024))

print("[3/4] Hawthorn club season …")
print(export_club_season("Hawthorn", 2024))

print("[4/4] Hawthorn performance detail …")
print(export_performance_detail("Hawthorn", 2024))
