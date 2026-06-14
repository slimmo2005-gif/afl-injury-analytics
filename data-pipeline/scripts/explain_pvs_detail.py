import math
import duckdb

DB = "c:/temp/Temp/data-pipeline/processed/afl_analytics.duckdb"
con = duckdb.connect(DB, read_only=True)

DRAFT_DECAY = 14.0

def draft_potential(pick):
    return 10.0 * math.exp(-pick / DRAFT_DECAY)

def age_weight(age):
    if age <= 18: return 0.30
    if age >= 25: return 1.00
    t = (age - 18) / 7
    return 0.30 + t * 0.70

for pid, label in [("13103", "Nick Watson"), ("12913", "Jai Newcombe")]:
    print("\n" + "=" * 70)
    print(label, f"(player_id={pid})")
    
    seasons = con.execute(
        """
        SELECT season, COUNT(*) games, AVG(disposals) d, AVG(goals) g,
               AVG(COALESCE(score_involvements,0)) si
        FROM player_games WHERE player_id=? GROUP BY season ORDER BY season
        """, [pid]).df()
    print("\nPer-season raw averages:")
    print(seasons.to_string(index=False))

    s2024 = seasons[seasons.season==2024].iloc[0]
    s2022 = seasons[seasons.season==2022] if 2022 in seasons.season.values else None
    s2023 = seasons[seasons.season==2023] if 2023 in seasons.season.values else None

    def roll(metric):
        cur = s2024[metric]
        y1 = seasons[seasons.season==2023][metric].iloc[0] if 2023 in seasons.season.values else cur
        y2 = seasons[seasons.season==2022][metric].iloc[0] if 2022 in seasons.season.values else cur
        return 0.2*y2 + 0.3*y1 + 0.5*cur, y2, y1, cur

    for m, name in [("d","disposals"), ("g","goals"), ("si","score involvements")]:
        rolled, y2, y1, cur = roll(m)
        print(f"\nRolling {name}: 0.2*{y2:.3f} + 0.3*{y1:.3f} + 0.5*{cur:.3f} = {rolled:.3f}")

    detail = con.execute(
        """
        WITH base AS (
            SELECT player_id, team, season, COUNT(*) games,
                AVG(disposals) disposals_pg, AVG(goals) goals_pg,
                AVG(COALESCE(score_involvements,0)) score_inv_pg
            FROM player_games GROUP BY 1,2,3
        ),
        rolled AS (
            SELECT b.player_id, b.team, b.season, b.games,
                (COALESCE((SELECT disposals_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-2), b.disposals_pg)*0.2
                 + COALESCE((SELECT disposals_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-1), b.disposals_pg)*0.3
                 + b.disposals_pg*0.5) roll_disposals,
                (COALESCE((SELECT goals_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-2), b.goals_pg)*0.2
                 + COALESCE((SELECT goals_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-1), b.goals_pg)*0.3
                 + b.goals_pg*0.5) roll_goals,
                (COALESCE((SELECT score_inv_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-2), b.score_inv_pg)*0.2
                 + COALESCE((SELECT score_inv_pg FROM base b2 WHERE b2.player_id=b.player_id AND b2.team=b.team AND b2.season=b.season-1), b.score_inv_pg)*0.3
                 + b.score_inv_pg*0.5) roll_score_inv
            FROM base b WHERE b.player_id=?
        ),
        z AS (
            SELECT r.*,
                (r.roll_disposals - AVG(r.roll_disposals) OVER (PARTITION BY r.season)) / NULLIF(STDDEV(r.roll_disposals) OVER (PARTITION BY r.season),0) z_disp,
                (r.roll_goals - AVG(r.roll_goals) OVER (PARTITION BY r.season)) / NULLIF(STDDEV(r.roll_goals) OVER (PARTITION BY r.season),0) z_goals,
                (r.roll_score_inv - AVG(r.roll_score_inv) OVER (PARTITION BY r.season)) / NULLIF(STDDEV(r.roll_score_inv) OVER (PARTITION BY r.season),0) z_si,
                (r.games - AVG(r.games) OVER (PARTITION BY r.season)) / NULLIF(STDDEV(r.games) OVER (PARTITION BY r.season),0) z_games
            FROM rolled r
        )
        SELECT * FROM z WHERE season=2024
        """, [pid]).df()
    print("\nDB rolled + z-scores (2024):")
    print(detail.to_string(index=False))

    z = detail.iloc[0]
    perf = min(10, max(0, 5.0 + 0.35*z.z_disp + 0.25*z.z_goals + 0.25*z.z_si + 0.15*z.z_games))
    print(f"\nPerformance = 5.0 + 0.35*{z.z_disp:.3f} + 0.25*{z.z_goals:.3f} + 0.25*{z.z_si:.3f} + 0.15*{z.z_games:.3f}")
    print(f"            = {perf:.3f} (stored: {con.execute('SELECT performance_score FROM player_value WHERE player_id=? AND season=2024',[pid]).fetchone()[0]:.3f})")

    prof = con.execute("SELECT age_est, draft_pick FROM player_profiles WHERE player_id=? AND season=2024", [pid]).fetchone()
    age, pick = prof
    pot = draft_potential(pick)
    w = age_weight(age)
    pvs = w*perf + (1-w)*pot
    print(f"\nAge est: {age}, draft pick: {pick}")
    print(f"Potential = 10 * exp(-{pick}/{DRAFT_DECAY}) = {pot:.3f}")
    print(f"Age weight (perf): {w:.1f}  (potential weight: {1-w:.1f})")
    print(f"PVS = {w:.1f}*{perf:.3f} + {1-w:.1f}*{pot:.3f} = {pvs:.3f}")

con.close()
