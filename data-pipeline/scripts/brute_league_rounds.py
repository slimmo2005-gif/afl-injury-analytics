import json
import requests

BASE = "https://www.wheeloratings.com/src/match_stats/table_data"
found = []
for league in (12, 16, 120, 160):
    for season in (2024, 24):
        for rnd in range(0, 25):
            for fmt in [
                f"{league}{season}{rnd:02d}",
                f"{league}{season}{rnd}",
                f"{season}{league}{rnd:02d}",
            ]:
                r = requests.get(f"{BASE}/{fmt}.json", timeout=8)
                if r.status_code == 200 and len(r.content) > 5000:
                    d = r.json()
                    s = d.get("Summary", [{}])[0]
                    teams = d.get("Matches", [{}])[0].get("HomeTeam", [])
                    found.append((fmt, s, teams[:2]))

print("found", len(found))
for x in found[:15]:
    print(x)
