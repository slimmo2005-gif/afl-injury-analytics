import json
import re
import requests

r = requests.get(
    "https://sanfl.com.au/league/matches/",
    timeout=30,
    headers={"User-Agent": "Mozilla/5.0"},
)
m = re.search(r"var themeVars = (\{.*?\});", r.text, re.S)
if m:
    tv = json.loads(m.group(1))
    print("themeVars keys", list(tv.keys()))
    for k, v in tv.items():
        if k not in ("clubsInfo",):
            print(k, v)
    print("clubs sample", tv.get("clubsInfo", [])[:2])

# search for stats endpoint patterns
for pat in [r"stats[A-Za-z]*Url[^\n]{0,80}", r"api[A-Za-z]*[^\n]{0,80}", r"championdata[^\n]{0,80}"]:
    hits = re.findall(pat, r.text, re.I)
    if hits:
        print("hits", hits[:5])

# try SANFL stats API patterns from other AFL state leagues
candidates = [
    "https://sanfl.com.au/wp-json/sanfl/v1/matches",
    "https://sanfl.com.au/wp-json/sanfl/v1/fixture/2024",
    "https://stats.sanfl.com.au/",
    "https://api.sanfl.com.au/",
]
for u in candidates:
    try:
        rr = requests.get(u, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        print(u, rr.status_code, rr.text[:150])
    except Exception as e:
        print(u, e)
