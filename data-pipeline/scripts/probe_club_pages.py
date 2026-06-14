import json
import re
import requests
from bs4 import BeautifulSoup

# Adelaide SANFL club page
for url in [
    "https://sanfl.com.au/league/clubs/adelaide/",
    "https://sanfl.com.au/league/clubs/adelaide/fixture/",
    "https://sanfl.com.au/league/clubs/adelaide/matches/",
]:
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    print(url, r.status_code)
    if r.ok:
        links = re.findall(r'href="(/[^"]*(?:match|stats|fixture)[^"]*)"', r.text, re.I)
        print(" links", links[:10])

# WAFL
for url in [
    "https://wafl.com.au/fixture-and-results/",
    "https://wafl.com.au/",
    "https://www.wafl.com.au/fixture-and-results/",
]:
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        print(url, r.status_code, len(r.text))
    except Exception as e:
        print(url, e)

# fixturedownload wafl
for comp in ("wafl-2024", "sanfl-2024"):
    r = requests.get(f"https://fixturedownload.com/feed/json/{comp}", timeout=30)
    print(comp, r.status_code, len(r.json()) if r.ok else 0)
