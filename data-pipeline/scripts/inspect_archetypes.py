import duckdb

con = duckdb.connect("c:/temp/Temp/data-pipeline/processed/afl_analytics.duckdb", read_only=True)

for name in ["Will Day", "Jack Gunston"]:
    print("===", name, "===")
    print(
        con.execute(
            """
            SELECT season, player_position, COUNT(*) n
            FROM player_games WHERE player_name=? GROUP BY 1,2 ORDER BY season, n DESC
            """,
            [name],
        ).df()
    )
    print(
        con.execute(
            """
            SELECT pp.archetype, pp.player_position
            FROM player_profiles pp
            JOIN player_games pg ON pp.player_id=pg.player_id AND pp.season=pg.season
            WHERE pg.player_name=? AND pp.season=2024 LIMIT 1
            """,
            [name],
        ).fetchone()
    )

print("\nHawthorn 2024 perf:", con.execute(
    "SELECT MIN(performance_score), MAX(performance_score), AVG(performance_score), STDDEV(performance_score) FROM player_value WHERE team='Hawthorn' AND season=2024"
).fetchone())
print("League 2024 perf:", con.execute(
    "SELECT MIN(performance_score), MAX(performance_score), AVG(performance_score), STDDEV(performance_score) FROM player_value WHERE season=2024"
).fetchone())

print("\nTop positions 2024:")
print(con.execute(
    "SELECT player_position, COUNT(*) n FROM player_games WHERE season=2024 GROUP BY 1 ORDER BY 2 DESC LIMIT 25"
).df())

print("\nUnmapped positions:")
print(con.execute(
    """
    SELECT DISTINCT player_position FROM player_games
    WHERE season=2024 AND player_position NOT IN ('FB','CHB','HBFL','HBFR','BPL','BPR','FF','CHF','FPL','FPR','C','RR','WR','R','WL','W','RK','HFFL','HFFR','HF','INT','SUB','I/C')
    ORDER BY 1
    """
).df())

con.close()
