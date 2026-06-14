import json
import re
import requests

# WAFL match page
url = "https://wafl.com.au/match/league-west-coast-v-peel-thunder-round-8-2026"
r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
print("match page", r.status_code, len(r.text))
for pat in [r"api\.sportix\.cloud[^\s\"']*", r"/public/[^\s\"']*", r"player[^\s\"']*"]:
    hits = set(re.findall(pat, r.text, re.I))
    if hits:
        print("hits", list(hits)[:10])

# find sportix api calls in wafl homepage
r2 = requests.get("https://wafl.com.au/", timeout=30, headers={"User-Agent": "Mozilla/5.0"})
apis = set(re.findall(r"https://api\.sportix\.cloud/public[^\"']+", r2.text))
print("sportix urls", apis)

for api in list(apis)[:5]:
    rr = requests.get(api, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    print(api, rr.status_code, rr.text[:300])

# try sportix endpoints
for ep in [
    "https://api.sportix.cloud/public/wafl/matches/2024",
    "https://api.sportix.cloud/public/wafl/fixtures/2024",
    "https://api.sportix.cloud/public/competitions",
    "https://api.sportix.cloud/public/matches?competition=wafl&season=2024",
]:
    rr = requests.get(ep, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    print(ep, rr.status_code, rr.text[:200])
