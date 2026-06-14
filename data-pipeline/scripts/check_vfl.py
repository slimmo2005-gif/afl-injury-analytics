import duckdb

con = duckdb.connect("c:/temp/Temp/data-pipeline/processed/afl_analytics.duckdb", read_only=True)
print("availability 2024 by status:")
print(con.execute("SELECT status, COUNT(c) FROM (SELECT status, COUNT(*) c FROM availability WHERE season=2024 GROUP BY status)").df() if False else con.execute("SELECT status, COUNT(*) n FROM availability WHERE season=2024 GROUP BY status ORDER BY n DESC").df())
print("\nHawthorn:")
print(con.execute("SELECT status, COUNT(*) n FROM availability WHERE team='Hawthorn' AND season=2024 GROUP BY status").df())
print("vfl_games:", con.execute("SELECT COUNT(*) FROM vfl_games").fetchone())
print("vfl 2024 hawthorn sample:", con.execute("SELECT COUNT(*) FROM vfl_games WHERE season=2024 AND afl_club='Hawthorn'").fetchone())
print("vfl_played true hawthorn:", con.execute("SELECT COUNT(*) FROM availability WHERE team='Hawthorn' AND season=2024 AND vfl_played=TRUE").fetchone())
