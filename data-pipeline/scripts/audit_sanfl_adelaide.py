"""Audit SANFL coverage for Adelaide players."""

from data_pipeline.db import connect

con = connect()
for name in ["Parnell", "Hamill"]:
    print(f"\n=== {name} ===")
    print(
        con.execute(
            """
            SELECT a.player_name, a.round, a.status, a.afl_played, a.vfl_played, a.team
            FROM availability a
            JOIN player_profiles p ON a.player_id = p.player_id AND a.team = p.team AND a.season = p.season
            WHERE a.season = 2024 AND a.team = 'Adelaide' AND p.player_name ILIKE ?
            ORDER BY round
            """,
            [f"%{name}%"],
        ).df()
    )
    print("vfl_games:")
    print(
        con.execute(
            """
            SELECT * FROM vfl_games
            WHERE season = 2024 AND afl_club = 'Adelaide'
              AND (player_name ILIKE ? OR player_name_norm ILIKE ?)
            ORDER BY round
            """,
            [f"%{name}%", f"%{name.lower()}%"],
        ).df()
    )
    print(
        con.execute(
            """
            SELECT player_id, player_name FROM player_profiles
            WHERE season = 2024 AND team = 'Adelaide' AND player_name ILIKE ?
            """,
            [f"%{name}%"],
        ).df()
    )

print("\n=== SANFL vfl_games Adelaide 2024 sample ===")
print(
    con.execute(
        """
        SELECT player_name, round, player_id, competition
        FROM vfl_games
        WHERE season = 2024 AND competition = 'sanfl' AND afl_club = 'Adelaide'
        ORDER BY player_name, round
        LIMIT 30
        """
    ).df()
)
print("total sanfl rows:", con.execute("SELECT COUNT(*) FROM vfl_games WHERE season=2024 AND competition='sanfl'").fetchone()[0])

print("\n=== SANFL raw names containing parnell/hamill ===")
import pandas as pd

raw = pd.read_parquet("c:/temp/Temp/shared/data/state_league_2024_raw.parquet")
sanfl = raw[(raw.competition == "sanfl") & (raw.afl_club == "Adelaide")]
for pat in ["parnell", "hamill", "Parnell", "Hamill"]:
    hits = sanfl[sanfl.player_name.str.contains(pat, case=False, na=False)]
    if len(hits):
        print(pat, len(hits))
        print(hits[["player_name", "state_round", "game_slug"]].drop_duplicates().head(10))
