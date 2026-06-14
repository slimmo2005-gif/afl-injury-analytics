import json
import requests

KEY = "290|yQfFH5WycjbEb8eUtVtTCXZt2aWOxFpDjUYEdxgQ9326de46"
TEN = "3b47430d-e8a4-4f13-bc22-1b622d4e9bda"
H = {"Authorization": f"Bearer {KEY}", "Accept": "application/json", "tenant-id": TEN}
API = "https://api.sportix.cloud/public"

seasons = requests.get(f"{API}/seasons", headers=H, timeout=30).json()
print("seasons", seasons[:3] if isinstance(seasons, list) else seasons)

r = requests.get(
    f"{API}/matches",
    headers=H,
    params={"season_slug": "2024", "round_slug": "all"},
    timeout=30,
)
print("matches season_slug", r.status_code, r.text[:500])

r2 = requests.get(
    f"{API}/matches",
    headers=H,
    params={
        "competition": "59d10030-4bd7-11e9-ac6b-6d7005a09517",
        "season": "a89365f2-a2af-4d9b-962a-22c09c15ee77",
        "round": "all",
    },
    timeout=30,
)
print("matches full", r2.status_code)
if r2.ok:
    d = r2.json()
    comps = d.get("competitions", [])
    if comps:
        matches = comps[0].get("matches", [])
        print("match count", len(matches))
        print("sample slug", matches[0].get("slug") if matches else None)
