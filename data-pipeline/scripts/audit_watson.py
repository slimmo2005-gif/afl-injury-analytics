"""Detailed audit: Nick Watson 2024 availability vs sources."""

from data_pipeline.db import connect

con = connect()
pid = con.execute(
    """
    SELECT player_id FROM player_profiles
    WHERE season = 2024 AND team = 'Hawthorn' AND player_name ILIKE '%Watson%'
    LIMIT 1
    """
).fetchone()[0]
print("player_id", pid)

pg = con.execute(
    """
    SELECT round, match_date, team, player_name
    FROM player_games
    WHERE player_id = ? AND season = 2024
    ORDER BY round
    """,
    [pid],
).df()
print("\n=== Fryzigg player_games (AFL) ===")
print(pg)
print("count:", len(pg))

av = con.execute(
    """
    SELECT round, afl_played, vfl_played, status
    FROM availability
    WHERE player_id = ? AND season = 2024
    ORDER BY round
    """,
    [pid],
).df()
print("\n=== availability ===")
print(av)
print(
    av.groupby("status").size(),
    "\nplayed:", av["afl_played"].sum(),
    "not played:", (~av["afl_played"]).sum(),
)

missed = av[~av["afl_played"]]
print("\n=== missed rounds ===")
print(missed)

vfl = con.execute(
    """
    SELECT player_name, round, vfl_team, competition, game_date, game_slug, player_id
    FROM vfl_games
    WHERE season = 2024
      AND (player_id = ? OR player_name ILIKE '%watson%')
      AND afl_club = 'Hawthorn'
    ORDER BY round
    """,
    [pid],
).df()
print("\n=== vfl_games Hawthorn ===")
print(vfl)

print("\n=== Hawthorn scheduled rounds 2024 ===")
print(
    con.execute(
        """
        SELECT round, home_team, away_team
        FROM matches
        WHERE season = 2024 AND (home_team = 'Hawthorn' OR away_team = 'Hawthorn')
        ORDER BY round
        """
    ).df()
)

print("\n=== vfl_games + availability join ===")
print(
    con.execute(
        """
        SELECT a.round, a.status, a.afl_played, v.game_slug, v.round AS vfl_mapped_round
        FROM availability a
        LEFT JOIN vfl_games v
            ON v.player_id = a.player_id AND v.season = a.season AND v.round = a.round AND v.afl_club = a.team
        WHERE a.player_id = ? AND a.season = 2024
        ORDER BY a.round
        """,
        [pid],
    ).df()
)
print(
    con.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE a.afl_played) AS rounds_played,
            COUNT(*) FILTER (WHERE NOT a.afl_played AND a.status != 'intermittent') AS rounds_missed,
            COUNT(*) FILTER (WHERE a.status = 'vfl_only') AS vfl_only,
            COUNT(*) FILTER (WHERE a.status = 'unavailable') AS unavailable,
            COUNT(*) FILTER (WHERE a.status = 'intermittent') AS intermittent
        FROM availability a
        WHERE player_id = ? AND season = 2024
        """,
        [pid],
    ).df()
)

print("\n=== player_value.games ===")
print(con.execute("SELECT games FROM player_value WHERE player_id=? AND season=2024", [pid]).fetchone())
