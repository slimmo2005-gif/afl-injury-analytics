import json
import re
import requests
from bs4 import BeautifulSoup

r = requests.get(
    "https://sanfl.com.au/league/matches/",
    timeout=30,
    headers={"User-Agent": "Mozilla/5.0"},
)
soup = BeautifulSoup(r.text, "html.parser")

# scripts with json/config
for script in soup.find_all("script"):
    txt = script.string or ""
    if "match" in txt.lower() and len(txt) > 200:
        print("script snippet", txt[:300].replace("\n", " "))

# data attributes / api urls in page
urls = set(re.findall(r"https?://[^\s\"']+", r.text))
api_urls = [u for u in urls if any(x in u.lower() for x in ("api", "stats", "fixture", "match", "json"))]
print("api-like urls", api_urls[:20])

# wordpress rest api
for endpoint in [
    "https://sanfl.com.au/wp-json/wp/v2/posts?search=stats",
    "https://sanfl.com.au/wp-json/",
]:
    rr = requests.get(endpoint, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    print(endpoint, rr.status_code, rr.text[:200])

# fixturedownload sanfl 2024
fd = requests.get(
    "https://fixturedownload.com/feed/json/sanfl-2024",
    timeout=30,
)
print("fixturedownload", fd.status_code, len(fd.content))
if fd.ok:
    fixtures = fd.json()
    print("fixtures", len(fixtures), fixtures[0])
