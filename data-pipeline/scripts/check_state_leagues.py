import duckdb

con = duckdb.connect("c:/temp/Temp/data-pipeline/processed/afl_analytics.duckdb", read_only=True)
teams = ["Adelaide", "Port Adelaide", "Fremantle", "West Coast", "Hawthorn", "Melbourne"]
print("vfl_only by team 2024:")
print(
    con.execute(
        """
        SELECT team,
               COUNT(*) FILTER (WHERE status = 'vfl_only') AS vfl_only,
               COUNT(*) FILTER (WHERE status = 'unavailable') AS unavailable,
               COUNT(*) FILTER (WHERE status = 'intermittent') AS intermittent
        FROM availability WHERE season = 2024
        GROUP BY team ORDER BY vfl_only DESC
        """
    ).df()
)
print("\nVFL games linked to SA/WA clubs:")
print(
    con.execute(
        """
        SELECT afl_club, COUNT(*) n
        FROM vfl_games WHERE season = 2024
        AND afl_club IN ('Adelaide','Port Adelaide','Fremantle','West Coast')
        GROUP BY 1
        """
    ).df()
)
