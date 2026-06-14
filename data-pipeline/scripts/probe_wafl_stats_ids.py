import json
import re
import requests

# get peel r1 2024 page
url = "https://wafl.com.au/match/league-peel-thunder-v-east-fremantle-round-1-2024"
html = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text

# nuxt payload sometimes in script
for pat in [
    r'\\"id\\":\\"([0-9a-f-]{36})\\"',
    r'"match":\{[^}]*"id":"([0-9a-f-]{36})"',
    r'matchId[^"]*"([0-9a-f-]{36})"',
]:
    hits = re.findall(pat, html)
    if hits:
        print("pattern", pat[:40], hits[:5])

# brute: try all uuids for stats with players
uuids = set(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", html))
found = []
for uid in uuids:
    r = requests.get(
        f"https://sportix-storage.syd1.digitaloceanspaces.com/statistics/{uid}.json",
        timeout=15,
    )
    if r.status_code != 200:
        continue
    st = r.json()
    hp = (st.get("home") or {}).get("players") or []
    if hp:
        found.append((uid, hp[0].get("player"), len(hp)))

print("stats hits", found[:10])

# fixtures-and-results page may list match ids
fx = requests.get("https://wafl.com.au/fixtures-and-results", timeout=30, headers={"User-Agent": "Mozilla/5.0"})
print("fixtures page", fx.status_code, len(fx.text))
match_slugs = re.findall(r"/match/league-[^\"']+", fx.text)
print("match slugs", len(set(match_slugs)), list(set(match_slugs))[:5])
