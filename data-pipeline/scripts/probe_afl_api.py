import requests

BASE = "https://api.afl.com.au/cfs/afl"
paths = [
    "/competitions",
    "/seasons",
    "/matches?competitionCode=VFL&seasonId=2024",
    "/stats/v2/competitions",
    "/wcm/competitions",
]
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.afl.com.au/",
}
for p in paths:
    url = BASE + p
    try:
        r = requests.get(url, headers=headers, timeout=15)
        print(p, r.status_code, r.text[:200].replace("\n", " "))
    except Exception as e:
        print(p, e)
