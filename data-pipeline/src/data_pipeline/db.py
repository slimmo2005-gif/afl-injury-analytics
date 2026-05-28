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
    won BOOLEAN,
    PRIMARY KEY (team, season, round)
);
"""


def connect(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    for stmt in SCHEMA_SQL.strip().split(";"):
        s = stmt.strip()
        if s:
            con.execute(s)
    return con
