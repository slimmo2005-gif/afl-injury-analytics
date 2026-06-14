import math
import duckdb

con = duckdb.connect("c:/temp/Temp/data-pipeline/processed/afl_analytics.duckdb", read_only=True)

DRAFT_DECAY = 14.0


def draft_potential(pick):
    return 10.0 * math.exp(-pick / DRAFT_DECAY)


def age_weight(age):
    if age <= 18:
        return 0.30
    if age >= 25:
        return 1.00
    return 0.30 + (age - 18) / 7 * 0.70


stats = con.execute(
    """
WITH base AS (
    SELECT player_id, team, season, COUNT(*) games,
        AVG(disposals) disposals_pg, AVG(goals) goals_pg,
        AVG(COALESCE(score_involvements,0)) score_inv_pg
    FROM player_games GROUP BY 1,2,3
),
rolled AS (
    SELECT b.player_id, b.season, b.games,
        (COALESCE((SELECT disposals_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-2), b.disposals_pg)*0.2
         + COALESCE((SELECT disposals_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-1), b.disposals_pg)*0.3
         + b.disposals_pg*0.5) roll_disposals,
        (COALESCE((SELECT goals_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-2), b.goals_pg)*0.2
         + COALESCE((SELECT goals_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-1), b.goals_pg)*0.3
         + b.goals_pg*0.5) roll_goals,
        (COALESCE((SELECT score_inv_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-2), b.score_inv_pg)*0.2
         + COALESCE((SELECT score_inv_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-1), b.score_inv_pg)*0.3
         + b.score_inv_pg*0.5) roll_score_inv
    FROM base b WHERE b.season=2024
)
SELECT AVG(roll_disposals), STDDEV(roll_disposals),
       AVG(roll_goals), STDDEV(roll_goals),
       AVG(roll_score_inv), STDDEV(roll_score_inv),
       AVG(games), STDDEV(games) FROM rolled
"""
).fetchone()

m_rd, s_rd, m_rg, s_rg, m_rs, s_rs, m_g, s_g = stats

for pid, name in [("13103", "Nick Watson"), ("12913", "Jai Newcombe")]:
    row = con.execute(
        """
        WITH base AS (
            SELECT player_id, team, season, COUNT(*) games,
                AVG(disposals) disposals_pg, AVG(goals) goals_pg,
                AVG(COALESCE(score_involvements,0)) score_inv_pg
            FROM player_games WHERE player_id=? GROUP BY 1,2,3
        ),
        rolled AS (
            SELECT b.season, b.games,
                (COALESCE((SELECT disposals_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-2), b.disposals_pg)*0.2
                 + COALESCE((SELECT disposals_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-1), b.disposals_pg)*0.3
                 + b.disposals_pg*0.5) roll_disposals,
                (COALESCE((SELECT goals_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-2), b.goals_pg)*0.2
                 + COALESCE((SELECT goals_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-1), b.goals_pg)*0.3
                 + b.goals_pg*0.5) roll_goals,
                (COALESCE((SELECT score_inv_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-2), b.score_inv_pg)*0.2
                 + COALESCE((SELECT score_inv_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-1), b.score_inv_pg)*0.3
                 + b.score_inv_pg*0.5) roll_score_inv
            FROM base b
        )
        SELECT * FROM rolled WHERE season=2024
        """,
        [pid],
    ).fetchone()

    prof = con.execute(
        "SELECT age_est, draft_pick, debut_season FROM player_profiles WHERE player_id=? AND season=2024",
        [pid],
    ).fetchone()
    age, pick, debut = prof
    rd, rg, rs, g = row[1], row[2], row[3], row[0]

    zd = (rd - m_rd) / s_rd
    zg = (rg - m_rg) / s_rg
    zs = (rs - m_rs) / s_rs
    zgm = (g - m_g) / s_g
    perf = min(10, max(0, 5 + 0.35 * zd + 0.25 * zg + 0.25 * zs + 0.15 * zgm))
    pot = draft_potential(pick)
    w = age_weight(age)
    pvs = w * perf + (1 - w) * pot

    stored = con.execute(
        """
        SELECT performance_score, potential_score, pvs, age_perf_weight
        FROM player_value WHERE player_id=? AND season=2024
        """,
        [pid],
    ).fetchone()

    print("=" * 70)
    print(f"{name} (Hawthorn 2024)")
    print(f"Debut season: {debut} | Estimated age: {age} | Draft pick: {pick}")
    print(f"\nRolling inputs (2024): disposals={rd:.2f}/gm, goals={rg:.2f}/gm, score inv={rs:.2f}/gm, games={g}")
    print(f"2024 league rolling averages: disp={m_rd:.2f}, goals={m_rg:.2f}, SI={m_rs:.2f}, games={m_g:.1f}")
    print(f"\nZ-scores vs 2024 cohort:")
    print(f"  Disposals z={zd:+.2f}  Goals z={zg:+.2f}  Score inv z={zs:+.2f}  Games z={zgm:+.2f}")
    print(f"\nPerformance score:")
    print(f"  5.0 + 0.35({zd:+.2f}) + 0.25({zg:+.2f}) + 0.25({zs:+.2f}) + 0.15({zgm:+.2f})")
    print(f"  = {perf:.3f}  (stored: {stored[0]:.3f})")
    print(f"\nPotential score:")
    print(f"  10 × e^(-{pick}/14) = {pot:.3f}  (stored: {stored[1]:.3f})")
    print(f"\nAge blend: {w:.0%} performance + {1-w:.0%} potential")
    print(f"PVS = {w:.2f}×{perf:.3f} + {1-w:.2f}×{pot:.3f} = {pvs:.3f}  (stored: {stored[2]:.3f})")

    seasons = con.execute(
        """
        SELECT season, COUNT(*) g, ROUND(AVG(disposals),2) d, ROUND(AVG(goals),2) gl,
               ROUND(AVG(COALESCE(score_involvements,0)),2) si
        FROM player_games WHERE player_id=? GROUP BY season ORDER BY season
        """,
        [pid],
    ).df()
    print("\nSeason-by-season raw averages (Fryzigg):")
    print(seasons.to_string(index=False))
    print()

con.close()
