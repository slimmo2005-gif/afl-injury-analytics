from data_pipeline.db import connect

c = connect()
print(c.execute("SELECT round, game_date, game_slug, competition FROM vfl_games WHERE season=2024 AND player_id='12783'").df())
print(c.execute("SELECT round, status FROM availability WHERE player_id='12783' AND season=2024 ORDER BY round").df())
