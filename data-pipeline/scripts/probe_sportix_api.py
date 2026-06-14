import json
import requests

API = "https://api.sportix.cloud/public"
KEY = "290|yQfFH5WycjbEb8eUtVtTCXZt2aWOxFpDjUYEdxgQ9326de46"
TENANT = "3b47430d-e8a4-4f13-bc22-1b622d4e9bda"
HEADERS = {
    "User-Agent": "afl-injury-analytics/0.3",
    "Authorization": f"Bearer {KEY}",
    "X-Tenant-Id": TENANT,
    "Accept": "application/json",
}

endpoints = [
    "/",
    "/competitions",
    "/seasons",
    "/fixtures",
    "/matches",
    "/teams",
    "/players",
    "/statistics",
    "/match-stats",
    "/wafl/fixtures",
    "/wafl/matches",
    f"/tenants/{TENANT}/competitions",
    f"/tenants/{TENANT}/fixtures",
    f"/tenants/{TENANT}/matches",
]

for ep in endpoints:
    r = requests.get(API + ep, headers=HEADERS, timeout=20)
    print(ep, r.status_code, r.text[:180].replace("\n", " "))

# try with api key as query param
r = requests.get(API + "/competitions", params={"api_key": KEY}, timeout=20)
print("query key", r.status_code, r.text[:200])
