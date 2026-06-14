import json
import re
import requests

for site in ("https://sanfl.com.au/", "https://sanfl.com.au/league/matches/"):
    r = requests.get(site, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    print(site, r.status_code)
    if "sportix" in r.text.lower():
        print("  has sportix")
        m = re.search(r'apiKey:"([^"]+)"', r.text)
        t = re.search(r'tenantId:"([^"]+)"', r.text)
        print("  key", m.group(1)[:20] if m else None, "tenant", t.group(1) if t else None)

# try SANFL match URL pattern
for slug in [
    "league-adelaide-v-west-adelaide-round-1-2024",
    "sanfl-adelaide-v-west-adelaide-round-1-2024",
]:
    r = requests.get(f"https://sanfl.com.au/match/{slug}", timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    print("sanfl match", slug, r.status_code, len(r.text))
