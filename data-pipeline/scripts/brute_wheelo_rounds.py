import requests

BASE = "https://www.wheeloratings.com/src/match_stats/table_data"
# brute force round id patterns around 2024 SANFL
candidates = []
for prefix in (2024, 20240, 2024000, 12024, 122024):
    for rnd in range(0, 25):
        candidates.append(f"{prefix}{rnd:02d}")
        candidates.append(f"{prefix}{rnd}")

found = []
for rid in candidates:
    r = requests.get(f"{BASE}/{rid}.json", timeout=10)
    if r.status_code == 200 and len(r.content) > 3000:
        import json

        d = r.json()
        summary = d.get("Summary", [{}])[0]
        teams = d.get("Matches", [{}])[0].get("HomeTeam", [])
        if teams and teams[0] not in (
            "Carlton",
            "Collingwood",
            "Richmond",
            "Sydney",
            "Adelaide",
            "Brisbane Lions",
        ):
            found.append((rid, summary, teams[:2]))
        elif any(t in ("Adelaide", "Port Adelaide", "Peel Thunder", "Glenelg") for t in teams):
            found.append((rid, summary, teams[:3]))

print("interesting", found[:20])
print("total checked", len(candidates))

# also try comp-specific season files
for p in [
    "sanfl_2024",
    "SANFL2024",
    "2024_sanfl",
    "2024SANFL",
    "wafl_2024",
]:
    r = requests.get(f"{BASE}/{p}.json", timeout=10)
    if r.status_code == 200:
        print("found season file", p, len(r.content))
