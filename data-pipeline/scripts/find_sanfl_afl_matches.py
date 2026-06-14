import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
matches = []
for page in range(50):
    r = requests.get(
        "https://aflapi.afl.com.au/afl/v2/matches",
        headers=H,
        params={"competitionId": 14, "year": 2024, "page": page},
        timeout=30,
    ).json()
    batch = r.get("matches", [])
    if not batch:
        break
    for m in batch:
        if "2024 SANFL" not in m.get("compSeason", {}).get("name", ""):
            continue
        h = m.get("home", {}).get("team", {}).get("name", "")
        a = m.get("away", {}).get("team", {}).get("name", "")
        if h in ("Adelaide", "Port Adelaide") or a in ("Adelaide", "Port Adelaide"):
            matches.append((m["id"], m["round"]["roundNumber"], h, a))

print("adelaide/port sanfl matches", len(matches))
for x in matches[:15]:
    print(x)
