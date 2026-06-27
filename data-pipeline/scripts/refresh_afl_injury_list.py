"""Re-scrape the official AFL injury list and load all 18 clubs into the DB."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from data_pipeline.db import connect
from data_pipeline.ingest.injury_list import (
    fetch_injury_list,
    link_injury_list_players,
    load_injury_list_entries,
)

con = connect()
df = fetch_injury_list()
df["source"] = "afl_injury_list"
linked = link_injury_list_players(df, con)
load_injury_list_entries(con, linked)

print("\n=== afl_injury_list coverage after refresh ===")
rows = con.execute(
    """
    SELECT team, COUNT(*) n, SUM(CASE WHEN is_injury THEN 1 ELSE 0 END) inj
    FROM injury_list_entries
    WHERE source = 'afl_injury_list'
      AND list_date = (SELECT MAX(list_date) FROM injury_list_entries WHERE source='afl_injury_list')
    GROUP BY team ORDER BY team
    """
).fetchall()
for t, n, inj in rows:
    print(f"  {t:24s} {n:3d} entries  {inj:3d} injuries")
print("clubs:", len(rows))
