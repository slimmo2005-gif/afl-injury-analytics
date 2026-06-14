from data_pipeline.db import connect
c=connect()
print("vfl 2024 total", c.execute("SELECT competition, COUNT(*) FROM vfl_games WHERE season=2024 GROUP BY 1").df())
print("watson vfl", c.execute("SELECT COUNT(*) FROM vfl_games WHERE season=2024 AND player_name ILIKE '%nick watson%'").fetchone())
