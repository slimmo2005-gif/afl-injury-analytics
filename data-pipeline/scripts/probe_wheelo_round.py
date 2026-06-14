import json
import requests

r = requests.get(
    "https://www.wheeloratings.com/src/match_stats/table_data/202401.json",
    timeout=60,
)
d = r.json()
data = d["Data"]
print("Data type", type(data))
if isinstance(data, dict):
    print("Data keys", list(data.keys())[:20])
    for k in ("Player", "Team", "IsAFLListedPlayer", "MatchId"):
        if k in data:
            print(k, "len", len(data[k]), "sample", data[k][:3])
elif isinstance(data, list):
    print("Data list len", len(data))
    if data:
        print("first keys", data[0].keys() if isinstance(data[0], dict) else data[0])

summary = d.get("Summary", [{}])
print("Summary", summary[0] if summary else None)

# Check if wheelo has VFL round ids - try 202401 with different prefix
for rid in ["202401", "VFL202401", "SANFL202401", "WAFL202401", "12202401"]:
    rr = requests.get(
        f"https://www.wheeloratings.com/src/match_stats/table_data/{rid}.json",
        timeout=15,
    )
    if rr.status_code == 200 and len(rr.content) > 5000:
        print("found", rid, len(rr.content))
