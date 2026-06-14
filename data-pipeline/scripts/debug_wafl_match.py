import json
import re
import requests

KEY = "290|yQfFH5WycjbEb8eUtVtTCXZt2aWOxFpDjUYEdxgQ9326de46"
TEN = "3b47430d-e8a4-4f13-bc22-1b622d4e9bda"
H = {"Authorization": f"Bearer {KEY}", "Accept": "application/json", "tenant-id": TEN}

r = requests.get(
    "https://api.sportix.cloud/public/matches/league-peel-thunder-v-east-fremantle-round-1-2024",
    headers=H,
    timeout=30,
)
m = r.json()
print("completed", m.get("completed"), "provider", m.get("provider"))
stats = m.get("statistics")
print("stats type", type(stats), "keys", stats.keys() if isinstance(stats, dict) else None)
if stats:
    home = stats.get("home")
    print("home type", type(home))
    if isinstance(home, list):
        print("home list len", len(home), home[:1])
    elif isinstance(home, dict):
        print("home dict keys", home.keys())
        print("players", len(home.get("players", [])), home.get("players", [])[:1])

# list endpoint match shape
r2 = requests.get(
    "https://api.sportix.cloud/public/matches",
    headers=H,
    params={"season_slug": "2024", "round_slug": "all"},
    timeout=30,
).json()
for comp in r2["competitions"]:
    if comp["slug"] == "league":
        sample = comp["matches"][0]
        print("list sample keys", sample.keys())
        print("list completed", sample.get("completed"))
        print("list stats", sample.get("statistics"))
