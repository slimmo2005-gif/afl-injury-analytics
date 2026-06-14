import json
import requests

BASE = "https://www.wheeloratings.com/src"
paths = [
    "match_stats/table_data/202401.json",
    "match_stats/sanfl/2024.json",
    "match_stats/sanfl/table_data/2024.json",
    "match_stats/wafl/table_data/2024.json",
    "sanfl_match_stats/table_data/2024.json",
    "wafl_match_stats/table_data/2024.json",
    "afl_stats/player_match_stats/sanfl/2024.json",
]
for p in paths:
    r = requests.get(f"{BASE}/{p}", timeout=20)
    print(p, r.status_code, len(r.content))
    if r.ok and r.headers.get("content-type", "").startswith("application/json"):
        d = r.json()
        print("  keys", list(d.keys())[:15])
        if "Player" in d:
            print("  players", len(d["Player"]), "teams", set(d.get("Team", [])) & {"Adelaide", "Port Adelaide", "Peel Thunder"})

# fetch one AFL round for reference
r = requests.get(f"{BASE}/match_stats/table_data/202401.json", timeout=30)
d = r.json()
print("\nAFL round 1 keys", list(d.keys()))
matches = d.get("Matches", [{}])[0]
print("match teams sample", matches.get("HomeTeam", [])[:2], matches.get("AwayTeam", [])[:2])
players = d.get("PlayerStats", d.get("Players", [{}]))
if isinstance(players, list) and players:
    print("player stats keys", list(players[0].keys())[:10])
elif isinstance(d.get("Player"), list):
    print("Player count", len(d["Player"]), "sample", d["Player"][:3])
