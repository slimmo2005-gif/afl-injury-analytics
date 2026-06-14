import re
import requests

r = requests.get(
    "https://sanfl.com.au/match-centre/",
    timeout=20,
    headers={"User-Agent": "Mozilla/5.0"},
)
print("status", r.status_code, "len", len(r.text))
links = set(re.findall(r'href="([^"]+)"', r.text))
mc = sorted(l for l in links if "match" in l.lower())[:20]
print("match links", mc)
