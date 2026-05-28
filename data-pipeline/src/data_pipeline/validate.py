"""Data quality checks for Phase 1 pipeline."""

from __future__ import annotations

import duckdb

from .config import MIN_SEASON


def run_checks(con: duckdb.DuckDBPyConnection, season: int) -> list[str]:
    issues: list[str] = []

    match_count = con.execute(
        "SELECT COUNT(*) FROM matches WHERE season = ?", [season]
    ).fetchone()[0]
    if match_count == 0:
        issues.append(f"No matches ingested for season {season}")

    player_count = con.execute(
        "SELECT COUNT(*) FROM player_games WHERE season = ?", [season]
    ).fetchone()[0]
    if player_count == 0:
        issues.append(f"No player_games for season {season}")

    avail_count = con.execute(
        "SELECT COUNT(*) FROM availability WHERE season = ?", [season]
    ).fetchone()[0]
    if avail_count == 0:
        issues.append(f"No availability rows for season {season}")

    seasons = con.execute(
        "SELECT MIN(season), MAX(season), COUNT(DISTINCT season) FROM player_games"
    ).fetchone()
    if seasons[0] and seasons[0] > MIN_SEASON:
        issues.append(f"Earliest player_games season is {seasons[0]} (target {MIN_SEASON}+)")

    dupes = con.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT player_id, team, season, round
            FROM availability
            GROUP BY 1, 2, 3, 4
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]
    if dupes:
        issues.append(f"Duplicate availability keys: {dupes}")

    return issues
