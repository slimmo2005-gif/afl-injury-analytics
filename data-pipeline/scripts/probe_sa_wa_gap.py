import duckdb

con = duckdb.connect("c:/temp/Temp/data-pipeline/processed/afl_analytics.duckdb", read_only=True)

print("=== vfl_only by SA/WA teams 2024 ===")
print(
    con.execute(
        """
        SELECT team,
               COUNT(*) FILTER (WHERE status = 'vfl_only') AS vfl_only,
               COUNT(*) FILTER (WHERE status = 'unavailable') AS unavailable
        FROM availability
        WHERE season = 2024 AND team IN ('Adelaide','Port Adelaide','Fremantle','West Coast')
        GROUP BY team
        """
    ).df()
)

print("\n=== Port Adelaide VFL rows (Port Melbourne mapping) ===")
print(
    con.execute(
        """
        SELECT vfl_team, COUNT(*) n
        FROM vfl_games
        WHERE afl_club = 'Port Adelaide' AND season = 2024
        GROUP BY vfl_team
        """
    ).df()
)

print("\n=== Adelaide unavailable sample (would benefit from SANFL) ===")
print(
    con.execute(
        """
        SELECT player_name, COUNT(*) AS rounds
        FROM availability
        WHERE season = 2024 AND team = 'Adelaide' AND status = 'unavailable'
        GROUP BY player_name
        ORDER BY rounds DESC
        LIMIT 10
        """
    ).df()
)
