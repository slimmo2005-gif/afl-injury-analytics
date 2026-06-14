import json
import requests

KEY = "290|yQfFH5WycjbEb8eUtVtTCXZt2aWOxFpDjUYEdxgQ9326de46"
TENANT = "3b47430d-e8a4-4f13-bc22-1b622d4e9bda"
H = {
    "Authorization": f"Bearer {KEY}",
    "Accept": "application/json",
    "tenant-id": TENANT,
}
API = "https://api.sportix.cloud/public"

for ep, params in [
    ("/matches", {"season": 2024, "competition": "league"}),
    ("/matches", {"season": "2024", "competition": "league"}),
    ("/matches", {"season": 2024, "competition": "League"}),
    ("/fixtures", {"season": 2024}),
    ("/fixtures-and-results", {"season": 2024}),
    ("/competitions/league/matches", {"season": 2024}),
]:
    r = requests.get(API + ep, headers=H, params=params, timeout=20)
    print(ep, params, r.status_code, r.text[:400])

# try season matches via competition id from match
comp_id = "59d10030-4bd7-11e9-ac6b-6d7005a09517"
season_id = "a89365f2-a2af-4d9b-962a-22c09c15ee77"
for ep in [
    f"/competitions/{comp_id}/matches?season={season_id}",
    f"/competitions/{comp_id}/seasons/{season_id}/matches",
    f"/seasons/{season_id}/competitions/{comp_id}/matches",
]:
    r = requests.get(API + ep, headers=H, timeout=20)
    print(ep, r.status_code, r.text[:400])
