import json
import requests

BASE = "https://www.wheeloratings.com/src/afl_stats/player_stats"
for comp in ("sanfl", "wafl", "vfl"):
    url = f"{BASE}/{comp}/2024.json"
    r = requests.get(url, timeout=60, headers={"User-Agent": "afl-injury-analytics/0.3"})
    print(comp, r.status_code, len(r.content))
    if r.status_code != 200:
        continue
    data = r.json()
    if "Data" in data:
        d = data["Data"]
        meta = data.get("Metadata", {})
        if isinstance(meta, dict):
            print("  metadata keys", list(meta.keys()))
        elif meta:
            print("  metadata", meta[:2] if isinstance(meta, list) else meta)
    else:
        d = data
    print("  data keys", list(d.keys())[:30])
    for k in ("Player", "PlayerId", "Team", "Games", "AFLListed", "MatchId", "Round"):
        if k in d:
            sample = d[k][:3] if isinstance(d[k], list) else d[k]
            print(f"  {k} sample:", sample)
    if "Player" in d:
        print("  rows", len(d["Player"]))
