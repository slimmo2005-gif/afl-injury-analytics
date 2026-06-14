import json
import requests

BASE = "https://www.wheeloratings.com/src/afl_stats/player_stats/sanfl/2024.json"
d = requests.get(BASE, timeout=60).json()["Data"]
idx = d["Player"].index("Harry Schoenberg")
wid = d["WebsiteId"][idx]
pid = d["PlayerId"][idx]
print("Harry Schoenberg", wid, pid)

paths = [
    f"https://www.wheeloratings.com/src/afl_stats/player_profiles/{wid}.json",
    f"https://www.wheeloratings.com/src/afl_stats/player_profiles/{pid}.json",
    f"https://www.wheeloratings.com/src/player_profiles/{wid}.json",
    f"https://www.wheeloratings.com/src/afl_stats/player_match_log/sanfl/2024/{pid}.json",
    f"https://www.wheeloratings.com/src/afl_stats/player_stats/sanfl/2024/{pid}.json",
]
for p in paths:
    r = requests.get(p, timeout=15)
    print(p.split("wheeloratings.com")[1], r.status_code, len(r.content))
    if r.ok and "json" in r.headers.get("content-type", ""):
        print(" ", list(r.json().keys())[:15])

# player profile page
r = requests.get(
    f"https://www.wheeloratings.com/afl_player_profile.html?id={wid}",
    timeout=30,
)
import re

for pat in [r"src/afl_stats/[^\"']+\.json", r"fetch\(`[^`]+`"]:
    hits = re.findall(pat, r.text)
    if hits:
        print("page hits", hits[:10])
