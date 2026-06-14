import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
base = "https://aflapi.afl.com.au/afl/v2/matches/6205"
paths = [
    "", "/scoreboard", "/lineups", "/squad", "/squads", "/teamStats", "/playerStats",
    "/scoreInvolvements", "/extendedStats", "/full", "/details", "/participants",
    "/home/players", "/away/players", "/stats/player", "/statistics",
]
for p in paths:
    r = requests.get(base + p, headers=H, timeout=15)
    if r.status_code == 200 and len(r.content) > 200:
        print(p or "/", r.status_code, r.text[:180])
    else:
        print(p or "/", r.status_code)

# champion data public?
for u in [
    "https://api.afl.com.au/cfs/afl/sanfl/matchStats/6205",
    "https://api.afl.com.au/cfs/afl/matchCentre/6205",
]:
    r = requests.get(u, headers=H, timeout=15)
    print(u, r.status_code, r.text[:150])
