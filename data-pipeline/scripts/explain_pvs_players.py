"""Explain PVS components for specific players."""
import duckdb
import pandas as pd

DB = "c:/temp/Temp/data-pipeline/processed/afl_analytics.duckdb"
con = duckdb.connect(DB, read_only=True)

for name in ["Nick Watson", "Jai Newcombe"]:
    print("=" * 60, name)
    prof = con.execute(
        """
        SELECT p.*, v.performance_score, v.potential_score, v.pvs, v.age_perf_weight, v.games
        FROM player_profiles p
        JOIN player_value v ON p.player_id=v.player_id AND p.team=v.team AND p.season=v.season
        WHERE p.season=2024 AND LOWER(p.player_name) LIKE ?
        """,
        [f"%{name.split()[-1].lower()}%"],
    ).df()
    print(prof.to_string())

    stats = con.execute(
        """
        SELECT season, COUNT(*) games, AVG(disposals) disp, AVG(goals) goals,
               AVG(COALESCE(score_involvements,0)) si
        FROM player_games
        WHERE season=2024 AND LOWER(player_name) LIKE ?
        GROUP BY season
        """,
        [f"%{name.split()[-1].lower()}%"],
    ).df()
    print("\n2024 raw averages:", stats.to_string())

    rolled = con.execute(
        """
        WITH base AS (
            SELECT player_id, team, season,
                COUNT(*) games, AVG(disposals) disposals_pg, AVG(goals) goals_pg,
                AVG(COALESCE(score_involvements,0)) score_inv_pg
            FROM player_games
            WHERE LOWER(player_name) LIKE ?
            GROUP BY 1,2,3
        ),
        b AS (SELECT * FROM base WHERE player_id IN (SELECT player_id FROM base WHERE season=2024))
        SELECT * FROM b ORDER BY season
        """,
        [f"%{name.split()[-1].lower()}%"],
    ).df()
    print("\nSeason stats:", rolled.to_string())

    draft = con.execute(
        """
        SELECT * FROM draft_picks WHERE LOWER(player_name) LIKE ? AND draft_year <= 2024
        ORDER BY draft_year DESC LIMIT 3
        """,
        [f"%{name.split()[-1].lower()}%"],
    ).df()
    print("\nDraft:", draft.to_string())

    # season z-score context for 2024
    zctx = con.execute(
        """
        WITH base AS (
            SELECT player_id, team, season,
                AVG(disposals) disposals_pg, AVG(goals) goals_pg,
                AVG(COALESCE(score_involvements,0)) score_inv_pg, COUNT(*) games
            FROM player_games WHERE season=2024 GROUP BY 1,2,3
        )
        SELECT
            AVG(disposals_pg) avg_disp, STDDEV(disposals_pg) sd_disp,
            AVG(goals_pg) avg_goals, STDDEV(goals_pg) sd_goals,
            AVG(score_inv_pg) avg_si, STDDEV(score_inv_pg) sd_si,
            AVG(games) avg_games, STDDEV(games) sd_games
        FROM base
        """
    ).df()
    print("\n2024 league averages (for z-scores):", zctx.to_string())

con.close()
