from pathlib import Path

import duckdb

from .config import DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS matches (
    match_id BIGINT PRIMARY KEY,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    home_team VARCHAR NOT NULL,
    away_team VARCHAR NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    venue VARCHAR,
    winner_team VARCHAR,
    complete INTEGER,
    source VARCHAR DEFAULT 'squiggle'
);

CREATE TABLE IF NOT EXISTS player_games (
    player_id VARCHAR NOT NULL,
    player_name VARCHAR NOT NULL,
    team VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    match_id BIGINT,
    match_date DATE,
    disposals INTEGER,
    goals INTEGER,
    score_involvements DOUBLE,
    player_position VARCHAR,
    source VARCHAR DEFAULT 'fryzigg',
    PRIMARY KEY (player_id, season, round, match_id)
);

CREATE TABLE IF NOT EXISTS squad_players (
    player_id VARCHAR NOT NULL,
    player_name VARCHAR NOT NULL,
    team VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    games_played INTEGER NOT NULL,
    PRIMARY KEY (player_id, team, season)
);

CREATE TABLE IF NOT EXISTS player_profiles (
    player_id VARCHAR NOT NULL,
    player_name VARCHAR NOT NULL,
    team VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    debut_season INTEGER NOT NULL,
    age_est DOUBLE NOT NULL,
    draft_pick INTEGER NOT NULL,
    archetype VARCHAR NOT NULL,
    PRIMARY KEY (player_id, team, season)
);

CREATE TABLE IF NOT EXISTS player_value (
    player_id VARCHAR NOT NULL,
    team VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    games INTEGER NOT NULL,
    performance_score DOUBLE NOT NULL,
    potential_score DOUBLE NOT NULL,
    pvs DOUBLE NOT NULL,
    age_perf_weight DOUBLE NOT NULL,
    PRIMARY KEY (player_id, team, season)
);

CREATE TABLE IF NOT EXISTS availability (
    player_id VARCHAR NOT NULL,
    player_name VARCHAR NOT NULL,
    team VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    status VARCHAR NOT NULL,
    afl_played BOOLEAN NOT NULL,
    vfl_played BOOLEAN,
    PRIMARY KEY (player_id, team, season, round)
);

CREATE TABLE IF NOT EXISTS team_round_summary (
    team VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    squad_size INTEGER NOT NULL,
    players_played INTEGER NOT NULL,
    players_unavailable INTEGER NOT NULL,
    unavailable_rate DOUBLE NOT NULL,
    unavailable_pvs_total DOUBLE DEFAULT 0,
    unavailable_pvs_top5 DOUBLE DEFAULT 0,
    won BOOLEAN,
    PRIMARY KEY (team, season, round)
);

CREATE TABLE IF NOT EXISTS team_round_value (
    team VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    unavailable_pvs_total DOUBLE NOT NULL,
    unavailable_pvs_top5 DOUBLE NOT NULL,
    unavailable_pvs_top10 DOUBLE NOT NULL,
    unavailable_pvs_u22 DOUBLE NOT NULL,
    unavailable_pvs_28plus DOUBLE NOT NULL,
    unavailable_pvs_intermittent DOUBLE NOT NULL,
    unavailable_pvs_vfl_only DOUBLE NOT NULL DEFAULT 0,
    won BOOLEAN,
    PRIMARY KEY (team, season, round)
);

CREATE TABLE IF NOT EXISTS archetype_continuity (
    team VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    archetype VARCHAR NOT NULL,
    avg_changes DOUBLE NOT NULL,
    continuity_score DOUBLE NOT NULL,
    PRIMARY KEY (team, season, archetype)
);

CREATE TABLE IF NOT EXISTS draft_picks (
    player_id VARCHAR NOT NULL,
    player_name VARCHAR NOT NULL,
    draft_year INTEGER NOT NULL,
    draft_pick INTEGER NOT NULL,
    drafted_club VARCHAR NOT NULL,
    player_name_norm VARCHAR,
    PRIMARY KEY (player_id, draft_year)
);

CREATE TABLE IF NOT EXISTS vfl_games (
    player_name VARCHAR NOT NULL,
    player_name_norm VARCHAR NOT NULL,
    afl_club VARCHAR NOT NULL,
    vfl_team VARCHAR,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL,
    game_slug VARCHAR,
    player_id VARCHAR,
    PRIMARY KEY (player_name_norm, afl_club, season, round, game_slug)
);
"""

MIGRATIONS = [
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS score_involvements DOUBLE",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS player_position VARCHAR",
    "ALTER TABLE team_round_summary ADD COLUMN IF NOT EXISTS unavailable_pvs_total DOUBLE DEFAULT 0",
    "ALTER TABLE team_round_summary ADD COLUMN IF NOT EXISTS unavailable_pvs_top5 DOUBLE DEFAULT 0",
    "ALTER TABLE team_round_value ADD COLUMN IF NOT EXISTS unavailable_pvs_vfl_only DOUBLE DEFAULT 0",
]


def connect(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    for stmt in SCHEMA_SQL.strip().split(";"):
        s = stmt.strip()
        if s:
            con.execute(s)
    for stmt in MIGRATIONS:
        try:
            con.execute(stmt)
        except duckdb.Error:
            pass
    return con
