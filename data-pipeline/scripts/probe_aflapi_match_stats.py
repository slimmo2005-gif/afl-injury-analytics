import json
import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
base = "https://aflapi.afl.com.au/afl/v2"

# paginate SANFL 2024 matches
matches = []
for page in range(50):
    r = requests.get(
        f"{base}/matches",
        headers=H,
        params={"competitionId": 14, "year": 2024, "page": page},
        timeout=30,
    )
    r.raise_for_status()
    batch = r.json().get("matches", [])
    if not batch:
        break
    for m in batch:
        cs = m.get("compSeason", {})
        if "2024" in cs.get("name", ""):
            matches.append(m)
print("SANFL 2024 matches", len(matches))
if matches:
    m = matches[0]
    print("sample", m["id"], m.get("compSeason", {}).get("name"), m.get("homeTeam", {}).get("name"), "v", m.get("awayTeam", {}).get("name"))
    mid = m["id"]
    for ep in [
        f"/matches/{mid}/stats/players",
        f"/matches/{mid}/playerStats",
        f"/matches/{mid}/statistics/players",
        f"/matches/{mid}/players",
        f"/matches/{mid}/stats",
    ]:
        rr = requests.get(base + ep, headers=H, timeout=20)
        print(ep, rr.status_code, rr.text[:200])
