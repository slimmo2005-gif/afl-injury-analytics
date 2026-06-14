from pathlib import Path

from data_pipeline.db import connect
from data_pipeline.export.league_unavailability import export_league_unavailability
from data_pipeline.transform.unavailability import build_team_round_value

con = connect()
build_team_round_value(con)
ph = con.execute(
    """
    SELECT p.player_name,
           ROUND(SUM(CASE WHEN a.status IN ('unavailable', 'intermittent') THEN v.pvs ELSE 0 END), 2)
               AS pvs_games_missed
    FROM availability a
    JOIN player_value v ON a.player_id = v.player_id AND a.team = v.team AND a.season = v.season
    JOIN player_profiles p ON v.player_id = p.player_id AND v.team = p.team AND v.season = p.season
    WHERE v.team = 'Hawthorn' AND v.season = 2024 AND p.player_name ILIKE '%Phillips%'
    GROUP BY 1
    """
).df()
print(ph)
haw = con.execute(
    """
    SELECT ROUND(SUM(unavailable_pvs_games_missed), 1) AS team_round_pvs_sum
    FROM team_round_value WHERE team = 'Hawthorn' AND season = 2024
    """
).fetchone()
print("Hawthorn team_round_pvs_sum:", haw[0])
con.close()

out = Path("c:/temp/Temp/shared/output/exports")
try:
    path = export_league_unavailability(2024, out)
except PermissionError:
    path = export_league_unavailability(2024, out / "_refresh")
print("written:", path)
