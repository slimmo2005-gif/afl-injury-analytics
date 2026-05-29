import json
import requests

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.afl.com.au/",
    }
)
home = session.get("https://www.afl.com.au/", timeout=30)
print("home", home.status_code, session.cookies.get_dict())

for path in [
    "/cfs/afl/competitions",
    "/cfs/afl/seasons?competitionCode=VFL",
    "/cfs/afl/fixtures?competitionCode=VFL&seasonYear=2024",
    "/cfs/afl/wcm/competitions",
]:
    url = "https://api.afl.com.au" + path
    r = session.get(url, timeout=30)
    print(path, r.status_code)
    if r.status_code == 200:
        try:
            data = r.json()
            print(json.dumps(data)[:500])
        except Exception:
            print(r.text[:300])
