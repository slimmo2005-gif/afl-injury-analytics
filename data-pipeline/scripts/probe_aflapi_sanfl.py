import requests

bases = [
    "https://aflapi.afl.com.au/afl/v2/matches/100",
    "https://aflapi.afl.com.au/afl/v2/matches/100/stats",
    "https://aflapi.afl.com.au/afl/v2/matches/100/players",
    "https://api.afl.com.au/cfs/afl/matchItems/100",
    "https://api.afl.com.au/cfs/afl/matchStats/100",
    "https://api.afl.com.au/statspro/match/100",
    "https://api.afl.com.au/statspro/matches/100/playerStats",
]
H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
for u in bases:
    r = requests.get(u, headers=H, timeout=20)
    print(u.split(".au")[1], r.status_code, r.text[:200].replace("\n", " "))
