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
    tackles DOUBLE DEFAULT 0,
    contested_marks DOUBLE DEFAULT 0,
    intercept_marks DOUBLE DEFAULT 0,
    marks_inside_fifty DOUBLE DEFAULT 0,
    intercepts DOUBLE DEFAULT 0,
    clearances DOUBLE DEFAULT 0,
    hitouts DOUBLE DEFAULT 0,
    hitouts_to_advantage DOUBLE DEFAULT 0,
    clangers DOUBLE DEFAULT 0,
    one_percenters DOUBLE DEFAULT 0,
    spoils DOUBLE DEFAULT 0,
    time_on_ground_pct DOUBLE,
    metres_gained DOUBLE DEFAULT 0,
    metres_per100 DOUBLE DEFAULT 0,
    disposal_efficiency_pct DOUBLE DEFAULT 0,
    effective_disposals DOUBLE DEFAULT 0,
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
    established_pvs DOUBLE,
    injury_weight_pvs DOUBLE,
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
    unavailable_pvs_games_missed DOUBLE NOT NULL DEFAULT 0,
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
    competition VARCHAR NOT NULL DEFAULT 'vfl',
    game_date DATE,
    PRIMARY KEY (player_name_norm, afl_club, season, round, game_slug, competition)
);

CREATE TABLE IF NOT EXISTS injury_list_entries (
    list_date DATE NOT NULL,
    team VARCHAR NOT NULL,
    player_name VARCHAR NOT NULL,
    player_name_norm VARCHAR NOT NULL,
    injury_type VARCHAR NOT NULL,
    injury_category VARCHAR,
    estimated_return VARCHAR,
    is_injury BOOLEAN NOT NULL DEFAULT TRUE,
    player_id VARCHAR,
    source VARCHAR DEFAULT 'afl_injury_list',
    PRIMARY KEY (list_date, team, player_name_norm)
);

CREATE TABLE IF NOT EXISTS absence_episodes (
    player_id VARCHAR NOT NULL,
    player_name VARCHAR NOT NULL,
    team VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    start_round INTEGER NOT NULL,
    end_round INTEGER NOT NULL,
    weeks INTEGER NOT NULL,
    absence_reason VARCHAR NOT NULL,
    injury_type VARCHAR,
    injury_category VARCHAR,
    source VARCHAR,
    confidence VARCHAR DEFAULT 'inferred',
    PRIMARY KEY (player_id, team, season, start_round)
);
"""

MIGRATIONS = [
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS score_involvements DOUBLE",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS player_position VARCHAR",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS tackles DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS contested_marks DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS intercept_marks DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS marks_inside_fifty DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS intercepts DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS clearances DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS hitouts DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS hitouts_to_advantage DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS clangers DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS metres_gained DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS metres_per100 DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS disposal_efficiency_pct DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS effective_disposals DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS spoils DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS one_percenters DOUBLE DEFAULT 0",
    "ALTER TABLE player_games ADD COLUMN IF NOT EXISTS time_on_ground_pct DOUBLE",
    "ALTER TABLE team_round_summary ADD COLUMN IF NOT EXISTS unavailable_pvs_total DOUBLE DEFAULT 0",
    "ALTER TABLE team_round_summary ADD COLUMN IF NOT EXISTS unavailable_pvs_top5 DOUBLE DEFAULT 0",
    "ALTER TABLE team_round_value ADD COLUMN IF NOT EXISTS unavailable_pvs_vfl_only DOUBLE DEFAULT 0",
    "ALTER TABLE team_round_value ADD COLUMN IF NOT EXISTS unavailable_pvs_games_missed DOUBLE DEFAULT 0",
    "ALTER TABLE player_value ADD COLUMN IF NOT EXISTS established_pvs DOUBLE",
    "ALTER TABLE player_value ADD COLUMN IF NOT EXISTS injury_weight_pvs DOUBLE",
    "ALTER TABLE vfl_games ADD COLUMN IF NOT EXISTS competition VARCHAR DEFAULT 'vfl'",
    "ALTER TABLE vfl_games ADD COLUMN IF NOT EXISTS game_date DATE",
    "ALTER TABLE availability ADD COLUMN IF NOT EXISTS absence_reason VARCHAR",
    "ALTER TABLE availability ADD COLUMN IF NOT EXISTS injury_type VARCHAR",
    "ALTER TABLE availability ADD COLUMN IF NOT EXISTS injury_category VARCHAR",
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
