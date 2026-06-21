"""PVS-lost vs ladder correlation: 2022 vs 2026 (post PVS overhaul)."""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_pipeline.config import DB_PATH, SQUIGGLE_BASE
from data_pipeline.export.ladder_pvs_ranks import build_ladder_pvs_ranks_bundle
from data_pipeline.ingest.squiggle import normalize_team
from data_pipeline.transform.unavailability import GAMES_MISSED_STATUS_SQL

GMS = GAMES_MISSED_STATUS_SQL


def corr(a, b) -> float:
    a, b = np.array(a, float), np.array(b, float)
    if len(a) < 3:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def fetch_sq_ladder(year: int, round_: int) -> dict[str, int]:
    url = f"{SQUIGGLE_BASE}/?q=standings;year={year};round={round_}"
    resp = requests.get(url, timeout=30, headers={"User-Agent": "afl-injury-analytics/corr"})
    resp.raise_for_status()
    return {
        normalize_team(r["name"]): int(r["rank"])
        for r in resp.json().get("standings", [])
    }


def pvs_lost_by_team(con: duckdb.DuckDBPyConnection, season: int, max_round: int | None = None) -> dict[str, float]:
    cap = f"AND a.round <= {max_round}" if max_round is not None else ""
    rows = con.execute(
        f"""
        SELECT a.team,
               SUM(
                   CASE
                       WHEN NOT a.afl_played AND a.status IN {GMS} {cap}
                       THEN COALESCE(v.injury_weight_pvs, v.pvs)
                       ELSE 0
                   END
               ) AS pvs_lost
        FROM availability a
        JOIN player_value v
            ON a.player_id = v.player_id AND a.team = v.team AND a.season = v.season
        WHERE a.season = {season}
        GROUP BY a.team
        """
    ).fetchall()
    return {team: float(pvs) for team, pvs in rows}


def wins_by_team(con: duckdb.DuckDBPyConnection, season: int, max_round: int | None = None) -> dict[str, int]:
    cap = f"AND m.round <= {max_round}" if max_round is not None else ""
    rows = con.execute(
        f"""
        WITH ha AS (
            SELECT season, round FROM matches
            WHERE round > 0 AND round <= 24
            GROUP BY season, round HAVING COUNT(*) > 4
        )
        SELECT team, SUM(won) AS wins FROM (
            SELECT m.home_team AS team,
                   CASE WHEN m.winner_team = m.home_team THEN 1 ELSE 0 END AS won
            FROM matches m
            INNER JOIN ha ON m.season = ha.season AND m.round = ha.round
            WHERE m.season = {season} {cap}
            UNION ALL
            SELECT m.away_team,
                   CASE WHEN m.winner_team = m.away_team THEN 1 ELSE 0 END
            FROM matches m
            INNER JOIN ha ON m.season = ha.season AND m.round = ha.round
            WHERE m.season = {season} {cap}
        ) GROUP BY team
        """
    ).fetchall()
    return {team: int(w) for team, w in rows}


def pair_corr(pvs: dict[str, float], ladder: dict[str, int]) -> tuple[float, int]:
    pairs = [(pvs[t], ladder[t]) for t in pvs if t in ladder]
    if len(pairs) < 3:
        return float("nan"), len(pairs)
    return corr([p for p, _ in pairs], [l for _, l in pairs]), len(pairs)


def print_table(rows: list[tuple]) -> None:
    print(f"  {'Scenario':42} {'r':>7} {'n':>3}")
    print(f"  {'-'*42} {'-'*7} {'-'*3}")
    for label, r, n in rows:
        print(f"  {label:42} {r:7.3f} {n:3d}")


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    bundle = build_ladder_pvs_ranks_bundle(con)

    max_r_2026 = con.execute(
        "SELECT MAX(round) FROM matches WHERE season = 2026 AND round > 0 AND complete = 100"
    ).fetchone()[0]
    max_r_2026 = int(max_r_2026 or 14)

    print("=" * 72)
    print(f"PVS-lost vs ladder correlation (updated PVS model) — compare round {max_r_2026}")
    print("=" * 72)

    # Full-season correlations from export bundle
    full_rows = []
    for yr in [2021, 2022, 2023, 2024, 2025]:
        sub = [
            (h["pvsLost"], h["ladderRank"])
            for hist in bundle["byClub"].values()
            for h in hist
            if h["season"] == yr
        ]
        full_rows.append((f"{yr} full HA season", corr([a for a, _ in sub], [b for _, b in sub]), len(sub)))
    print("\n1. Full home-and-away season (official end-of-year ladder)")
    print_table(full_rows)

    # Apples-to-apples at max_r_2026
    sq_ladder_2022 = fetch_sq_ladder(2022, max_r_2026)
    sq_ladder_2026 = fetch_sq_ladder(2026, max_r_2026)

    pvs_2022_mid = pvs_lost_by_team(con, 2022, max_r_2026)
    pvs_2026_mid = pvs_lost_by_team(con, 2026, max_r_2026)

    r22, n22 = pair_corr(pvs_2022_mid, sq_ladder_2022)
    r26, n26 = pair_corr(pvs_2026_mid, sq_ladder_2026)

    print(f"\n2. Mid-season apples-to-apples: R1–{max_r_2026} PVS lost vs R{max_r_2026} Squiggle ladder")
    print_table([
        (f"2022 R1–{max_r_2026} PVS vs R{max_r_2026} ladder", r22, n22),
        (f"2026 R1–{max_r_2026} PVS vs R{max_r_2026} ladder", r26, n26),
    ])

    # Also 2022 full PVS vs mid ladder (mixing horizons)
    pvs_2022_full = pvs_lost_by_team(con, 2022, None)
    r22_mix, _ = pair_corr(pvs_2022_full, sq_ladder_2022)
    print(f"\n3. Mixed horizon (for context)")
    print_table([
        (f"2022 full-season PVS vs R{max_r_2026} ladder", r22_mix, n22),
        (f"2026 R1–{max_r_2026} PVS vs R{max_r_2026} ladder", r26, n26),
    ])

    # PVS lost vs wins (not rank)
    wins_2022 = wins_by_team(con, 2022, max_r_2026)
    wins_2026 = wins_by_team(con, 2026, max_r_2026)

    pairs22 = [(pvs_2022_mid[t], wins_2022[t]) for t in pvs_2022_mid if t in wins_2022]
    pairs26 = [(pvs_2026_mid[t], wins_2026[t]) for t in pvs_2026_mid if t in wins_2026]

    print(f"\n4. PVS lost vs wins through R{max_r_2026}")
    print_table([
        (f"2022 R1–{max_r_2026}", corr([p for p, _ in pairs22], [w for _, w in pairs22]), len(pairs22)),
        (f"2026 R1–{max_r_2026}", corr([p for p, _ in pairs26], [w for _, w in pairs26]), len(pairs26)),
    ])

    # Club-level detail for 2022 vs 2026 at same round
    print(f"\n5. Club table - R1-{max_r_2026} (sorted by 2026 PVS lost, high to low)")
    print(f"  {'Club':22} {'2022 PVS':>9} {'2022 L#':>8} {'2026 PVS':>9} {'2026 L#':>8}")
    clubs = sorted(
        set(pvs_2022_mid) | set(pvs_2026_mid),
        key=lambda c: pvs_2026_mid.get(c, 0),
        reverse=True,
    )
    for club in clubs:
        p22 = pvs_2022_mid.get(club)
        p26 = pvs_2026_mid.get(club)
        l22 = sq_ladder_2022.get(club, "")
        l26 = sq_ladder_2026.get(club, "")
        if p22 is None and p26 is None:
            continue
        print(
            f"  {club:22} "
            f"{p22:9.0f} {str(l22):>8} "
            f"{p26 if p26 is not None else 0:9.0f} {str(l26):>8}"
        )

    print("\n6. Key-defender PVS (2022 full season, 15+ qualifying games)")
    kd = con.execute(
        """
        SELECT p.player_name, v.team, v.pvs, v.games, p.archetype
        FROM player_value v
        JOIN player_profiles p USING (player_id, team, season)
        WHERE v.season = 2022 AND p.archetype = 'key_defender' AND v.games >= 15
        ORDER BY v.pvs DESC
        LIMIT 10
        """
    ).df()
    print(kd.to_string(index=False))

    con.close()


if __name__ == "__main__":
    main()
