"""Audit Ethan Phillips 2024 pvs_rounds_lost."""

from data_pipeline.db import connect

con = connect()
row = con.execute(
    """
    SELECT v.player_id, p.player_name, v.pvs, v.games,
           COUNT(*) FILTER (WHERE NOT a.afl_played) AS not_played,
           COUNT(*) FILTER (WHERE a.afl_played) AS played,
           COUNT(*) FILTER (WHERE a.status = 'unavailable') AS unavailable,
           COUNT(*) FILTER (WHERE a.status = 'vfl_only') AS vfl_only,
           COUNT(*) FILTER (WHERE a.status = 'intermittent') AS intermittent,
           ROUND(SUM(CASE WHEN NOT a.afl_played THEN v.pvs ELSE 0 END), 2) AS pvs_rounds_lost
    FROM player_value v
    JOIN player_profiles p ON v.player_id = p.player_id AND v.team = p.team AND v.season = p.season
    LEFT JOIN availability a ON v.player_id = a.player_id AND v.team = a.team AND v.season = a.season
    WHERE v.season = 2024 AND v.team = 'Hawthorn' AND p.player_name ILIKE '%Phillips%'
    GROUP BY 1, 2, 3, 4
    """
).df()
print(row)

pid = row["player_id"].iloc[0]
print("\n=== by status ===")
print(
    con.execute(
        """
        SELECT status, COUNT(*) n, ROUND(SUM(v.pvs), 2) pvs_sum
        FROM availability a
        JOIN player_value v ON a.player_id = v.player_id AND a.team = v.team AND a.season = v.season
        WHERE a.player_id = ? AND a.season = 2024
        GROUP BY status ORDER BY n DESC
        """,
        [pid],
    ).df()
)

print("\n=== scheduled rounds (availability rows) ===")
print(
    con.execute(
        "SELECT COUNT(*) FROM availability WHERE player_id=? AND season=2024",
        [pid],
    ).fetchone()
)

print("\n=== NOT afl_played rounds ===")
print(
    con.execute(
        """
        SELECT round, status, afl_played, vfl_played
        FROM availability a
        WHERE player_id=? AND season=2024 AND NOT afl_played
        ORDER BY round
        """,
        [pid],
    ).df()
)
