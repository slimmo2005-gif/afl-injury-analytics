import duckdb

c = duckdb.connect("c:/temp/Temp/data-pipeline/processed/afl_analytics.duckdb", read_only=True)
print(c.execute("SELECT status, COUNT(*) FROM availability WHERE season=2024 GROUP BY 1").df())
print(c.execute("SELECT COUNT(*) FROM vfl_games WHERE season=2024").fetchone())
