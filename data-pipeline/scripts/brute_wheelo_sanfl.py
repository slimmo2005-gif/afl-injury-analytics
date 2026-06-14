import requests

BASE = "https://www.wheeloratings.com/src/match_stats/table_data"
found = []
for prefix in [142024, 14024, 202414, 2414]:
    for rnd in range(0, 25):
        rid = f"{prefix}{rnd:02d}"
        r = requests.get(f"{BASE}/{rid}.json", timeout=8)
        if r.status_code == 200 and len(r.content) > 5000:
            d = r.json()
            s = d.get("Summary", [{}])[0]
            teams = d.get("Matches", [{}])[0].get("HomeTeam", [])
            found.append((rid, s, teams[:2]))

print("found", found)
