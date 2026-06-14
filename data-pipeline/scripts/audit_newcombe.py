"""Audit Jai Newcombe 2024 availability vs player_games."""

from data_pipeline.db import connect

con = connect()
pid = con.execute(
    "SELECT player_id FROM player_profiles WHERE season=2024 AND player_name ILIKE '%Newcombe%' LIMIT 1"
).fetchone()[0]
print("player_id", pid)

print("\n=== player_games 2024 (Fryzigg) ===")
pg = con.execute(
    """
    SELECT round, match_date, team, player_name
    FROM player_games
    WHERE player_id = ? AND season = 2024
    ORDER BY round
    """,
    [pid],
).df()
print(pg)
print("games in player_games:", len(pg))

print("\n=== availability 2024 ===")
av = con.execute(
    """
    SELECT round, afl_played, vfl_played, status, team
    FROM availability
    WHERE player_id = ? AND season = 2024
    ORDER BY round
    """,
    [pid],
).df()
print(av)
print("rows:", len(av), "played:", av["afl_played"].sum(), "missed:", (~av["afl_played"]).sum())

missed = av[~av["afl_played"]]
print("\n=== missed rounds detail ===")
print(missed)

print("\n=== Hawthorn squad rounds in availability ===")
print(
    con.execute(
        """
        SELECT MIN(round) min_r, MAX(round) max_r, COUNT(DISTINCT round) n_rounds
        FROM availability WHERE team='Hawthorn' AND season=2024
        """
    ).df()
)

print("\n=== team matches 2024 (squiggle?) ===")
try:
    print(
        con.execute(
            """
            SELECT round, COUNT(DISTINCT player_id) squad_size
            FROM availability
            WHERE team='Hawthorn' AND season=2024
            GROUP BY round ORDER BY round
            """
        ).df()
    )
except Exception as e:
    print(e)

print("\n=== distinct rounds 2024 league-wide ===")
print(con.execute("SELECT DISTINCT round FROM player_games WHERE season=2024 ORDER BY round").df())

print("\n=== round 0 sample ===")
print(con.execute("SELECT round, match_date, team, player_name FROM player_games WHERE season=2024 AND round=0 LIMIT 8").df())

print("\n=== Hawthorn team rounds (from any player) ===")
print(
    con.execute(
        """
        SELECT round, MIN(match_date) AS d, COUNT(DISTINCT player_id) AS players
        FROM player_games
        WHERE season=2024 AND team='Hawthorn'
        GROUP BY round ORDER BY round
        """
    ).df()
)

print("\n=== Hawthorn R15 players count ===")
print(
    con.execute(
        "SELECT COUNT(DISTINCT player_id) FROM player_games WHERE season=2024 AND team='Hawthorn' AND round=15"
    ).fetchone()
)

print("\n=== rounds 25+ in player_games ===")
print(con.execute("SELECT round, COUNT(*) n FROM player_games WHERE season=2024 AND round>=25 GROUP BY 1").df())

print("\n=== matches table rounds 2024 ===")
print(con.execute("SELECT DISTINCT round FROM matches WHERE season=2024 ORDER BY round").df())

print("\n=== Hawthorn matches from matches table ===")
print(
    con.execute(
        """
        SELECT round, home_team, away_team
        FROM matches
        WHERE season=2024 AND (home_team='Hawthorn' OR away_team='Hawthorn')
        ORDER BY round
        """
    ).df()
)

print("\n=== Hawthorn R25 fryzigg count ===")
print(
    con.execute(
        "SELECT COUNT(DISTINCT player_id) FROM player_games WHERE season=2024 AND team = 'Hawthorn' AND round = 25"
    ).fetchone()
)

print("\n=== matches per round 2024 (count) ===")
print(
    con.execute(
        "SELECT round, COUNT(*) n FROM matches WHERE season=2024 GROUP BY round ORDER BY round"
    ).df()
)

print(
    con.execute(
        "SELECT team, COUNT(DISTINCT player_id) n FROM player_games WHERE season=2024 AND round=15 GROUP BY team ORDER BY n DESC LIMIT 10"
    ).df()
)

print(
    con.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE NOT a.afl_played) AS rounds_missed,
            COUNT(*) FILTER (WHERE a.afl_played) AS rounds_played,
            COUNT(*) FILTER (WHERE a.status = 'unavailable') AS unavailable,
            COUNT(*) FILTER (WHERE a.status = 'intermittent') AS intermittent
        FROM availability a
        WHERE player_id = ? AND season = 2024
        """,
        [pid],
    ).df()
)
