"""Compare Watson AFL rounds: Fryzigg vs expected from afltables pattern."""

from data_pipeline.db import connect

# AFL Tables 2024 game order (from web): debut R1,2,3 then gap then R9 WB sub, etc.
# Footyinfo: 18 GM, VFL 2 (BHH)
con = connect()
pid = "13103"

pg = set(
    con.execute(
        "SELECT round FROM player_games WHERE player_id=? AND season=2024", [pid]
    ).df()["round"]
)
sched = set(
    con.execute(
        """
        SELECT DISTINCT round FROM matches
        WHERE season=2024 AND (home_team='Hawthorn' OR away_team='Hawthorn')
          AND round > 0 AND round <= 24
        """
    ).df()["round"]
)
# finals block excluded via round<=24 and home-away filter in availability build uses >4 games

print("Fryzigg AFL rounds:", sorted(pg))
print("Missing from Fryzigg:", sorted(sched - pg))
print("Scheduled count:", len(sched), "Fryzigg count:", len(pg))

av = con.execute(
    "SELECT round, status, afl_played, vfl_played FROM availability WHERE player_id=? AND season=2024 ORDER BY round",
    [pid],
).df()
print("\nAvailability non-played:")
print(av[~av.afl_played])

import pandas as pd
raw = pd.read_parquet("c:/temp/Temp/shared/data/state_league_2024_raw.parquet")
nw = raw[(raw.competition == "vfl") & (raw.player_name_norm == "nick watson")]
print("\nRaw VFL:", nw[["state_round", "game_slug"]].to_string())

print("\nDB vfl_games:")
print(
    con.execute(
        "SELECT round, game_slug, player_id FROM vfl_games WHERE season=2024 AND LOWER(player_name) LIKE '%nick watson%'"
    ).df()
)
