import json
import requests

KEY = "290|yQfFH5WycjbEb8eUtVtTCXZt2aWOxFpDjUYEdxgQ9326de46"
TENANT = "3b47430d-e8a4-4f13-bc22-1b622d4e9bda"
H = {
    "Authorization": f"Bearer {KEY}",
    "Accept": "application/json",
    "X-Tenant-Id": TENANT,
}
API = "https://api.sportix.cloud/public"

r = requests.get(f"{API}/matches", headers=H, params={"season": 2024}, timeout=30)
print("matches 2024", r.status_code)
d = r.json()
print(json.dumps(d, indent=2)[:2000])

season_id = d.get("season", {}).get("id")
for ep, params in [
    ("/matches", {"season": season_id}),
    ("/matches", {"season": "2024", "competition": "league"}),
    (f"/seasons/{season_id}/matches", None),
    (f"/seasons/2024/matches", None),
    ("/competitions", {"season": 2024}),
]:
    rr = requests.get(API + ep, headers=H, params=params, timeout=20)
    print(ep, params, rr.status_code, rr.text[:300])

# try fetch a known match slug from wafl page - extract match id from HTML payload
r2 = requests.get(
    "https://wafl.com.au/match/league-peel-thunder-v-east-fremantle-round-1-2024",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30,
)
import re

# look for uuid in page
uuids = set(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", r2.text))
print("uuids in page", uuids)

# try statistics json with each uuid
for uid in list(uuids)[:5]:
    sr = requests.get(
        f"https://sportix-storage.syd1.digitaloceanspaces.com/statistics/{uid}.json",
        timeout=20,
    )
    if sr.status_code == 200:
        st = sr.json()
        hp = st.get("home", {}).get("players", [])
        print("stats", uid, "home players", len(hp), hp[:2] if hp else None)
