import re
import requests

# AFL.com.au SANFL match
for url in [
    "https://www.afl.com.au/sanfl",
    "https://www.afl.com.au/wafl",
    "https://www.afl.com.au/sanfl/matches",
]:
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    print(url, r.status_code, "sportix" in r.text.lower(), "sanfl" in r.text.lower())

# search sanfl site for champion or stats embed
r = requests.get("https://sanfl.com.au/", timeout=30, headers={"User-Agent": "Mozilla/5.0"})
for term in ["sportix", "champion", "statistics", "apiKey", "tenant"]:
    print(term, term.lower() in r.text.lower())

# try constructing SANFL slug on sportix with WAFL tenant (unlikely)
KEY = "290|yQfFH5WycjbEb8eUtVtTCXZt2aWOxFpDjUYEdxgQ9326de46"
TEN = "3b47430d-e8a4-4f13-bc22-1b622d4e9bda"
H = {"Authorization": f"Bearer {KEY}", "Accept": "application/json", "tenant-id": TEN}
slug = "league-adelaide-v-west-adelaide-round-1-2024"
r = requests.get(f"https://api.sportix.cloud/public/matches/{slug}", headers=H, timeout=20)
print("sportix sanfl slug on wafl tenant", r.status_code, r.text[:200])
