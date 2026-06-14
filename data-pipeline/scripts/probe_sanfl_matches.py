import re
import requests
from bs4 import BeautifulSoup

r = requests.get(
    "https://sanfl.com.au/league/matches/",
    timeout=30,
    headers={"User-Agent": "Mozilla/5.0"},
)
print("status", r.status_code)
soup = BeautifulSoup(r.text, "html.parser")
# find links to individual matches
links = []
for a in soup.find_all("a", href=True):
    h = a["href"]
    if "match" in h.lower() or "fixture" in h.lower() or "stats" in h.lower():
        links.append(h)
print("sample links", sorted(set(links))[:25])

# look for 2024 round content
text = r.text
for pat in [r"2024", r"round", r"stats", r"player"]:
    print(pat, len(re.findall(pat, text, re.I)))

# try wheelo match stats comps
for ds in ["match_stats", "afl_match_stats", "player_match_stats"]:
    url = f"https://www.wheeloratings.com/src/afl_stats/{ds}/comps.json"
    rr = requests.get(url, timeout=15)
    print(ds, rr.status_code, rr.text[:100] if rr.text else "")
