import json
import re
import requests

url = "https://wafl.com.au/match/league-peel-thunder-v-south-fremantle-round-1-2024"
r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
print("status", r.status_code)

m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', r.text, re.S)
if m:
    data = json.loads(m.group(1))
    print("next data keys", data.keys())
    print(json.dumps(data, indent=2)[:4000])
else:
    # nuxt / other
    for pat in [
        r"window\.__NUXT__=.*?;</script>",
        r"application/ld\+json\">(.+?)</script>",
        r"\"players\":\s*\[",
    ]:
        if re.search(pat, r.text, re.S):
            print("found pattern", pat[:40])

# search for json blobs with player names
for script in re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.S):
    if "Peel" in script and "Thunder" in script and len(script) < 50000:
        if "player" in script.lower():
            print("script with peel", script[:500])

# try 2024 peel match from fixturedownload + construct slug
import requests as rq
fx = rq.get("https://fixturedownload.com/feed/json/wafl-2024", timeout=30).json()
peel = [x for x in fx if "Peel" in x["HomeTeam"] or "Peel" in x["AwayTeam"]][:3]
print("peel fixtures", peel)
