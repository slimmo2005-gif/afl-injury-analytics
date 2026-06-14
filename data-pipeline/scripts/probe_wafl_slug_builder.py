import re
import requests

def slugify(name: str) -> str:
    s = name.lower().replace(" fc", "").replace(" football club", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s

fx = requests.get("https://fixturedownload.com/feed/json/wafl-2024", timeout=30).json()
m = fx[0]
home = slugify(m["HomeTeam"])
away = slugify(m["AwayTeam"])
slug = f"league-{home}-v-{away}-round-{m['RoundNumber']}-2024"
print("constructed", slug)

KEY = "290|yQfFH5WycjbEb8eUtVtTCXZt2aWOxFpDjUYEdxgQ9326de46"
TEN = "3b47430d-e8a4-4f13-bc22-1b622d4e9bda"
H = {"Authorization": f"Bearer {KEY}", "Accept": "application/json", "tenant-id": TEN}

ok = 0
for m in fx:
    home = slugify(m["HomeTeam"])
    away = slugify(m["AwayTeam"])
    slug = f"league-{home}-v-{away}-round-{m['RoundNumber']}-2024"
    r = requests.get(f"https://api.sportix.cloud/public/matches/{slug}", headers=H, timeout=20)
    if r.status_code == 200:
        ok += 1
    else:
        print("fail", slug, r.status_code)
print("ok", ok, "/", len(fx))
