import re
import requests
from bs4 import BeautifulSoup

# SANFL stats resources
r = requests.get(
    "https://sanfl.com.au/inside-sanfl/resources/?s=stats",
    timeout=30,
    headers={"User-Agent": "Mozilla/5.0"},
)
print("sanfl resources", r.status_code)
soup = BeautifulSoup(r.text, "html.parser")
for a in soup.find_all("a", href=True):
    t = (a.get_text(" ", strip=True) + " " + a["href"]).lower()
    if any(x in t for x in ("stats", "2024", "hostplus", "report")):
        print(a.get_text(" ", strip=True)[:80], "->", a["href"][:100])

# WAFL homepage scripts
r2 = requests.get("https://wafl.com.au/", timeout=30, headers={"User-Agent": "Mozilla/5.0"})
print("\nwafl home", r2.status_code)
for pat in [r"api\.[^\s\"']+", r"fixture[^\s\"']*json", r"stats[^\s\"']*"]:
    hits = set(re.findall(pat, r2.text, re.I))
    if hits:
        print("pat", pat, list(hits)[:8])

links = re.findall(r'href="([^"]+)"', r2.text)
stats_links = [l for l in links if "stat" in l.lower() or "match" in l.lower()][:15]
print("wafl stats links", stats_links)
