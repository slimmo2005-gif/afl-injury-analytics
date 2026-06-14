import json
import requests

BASE = "https://www.wheeloratings.com/src/afl_stats/player_stats"
for comp in ("sanfl", "wafl"):
    d = requests.get(f"{BASE}/{comp}/2024.json", timeout=60).json()["Data"]
    print("\n===", comp, "===")
    match_keys = [k for k in d.keys() if "match" in k.lower() or "round" in k.lower() or "game" in k.lower()]
    print("match-ish keys", match_keys)
    if "IsAFLListedPlayer" in d:
        listed = sum(1 for x in d["IsAFLListedPlayer"] if x)
        print("AFL listed players", listed)
        # sample adelaide/port/peel teams
        teams = {"Adelaide", "Port Adelaide", "Peel Thunder", "Peel", "West Coast"}
        for i, (p, t, afl) in enumerate(zip(d["Player"], d["Team"], d["IsAFLListedPlayer"])):
            if afl and t in teams:
                print(" ", p, t, "matches", d.get("Matches", [None])[i])
