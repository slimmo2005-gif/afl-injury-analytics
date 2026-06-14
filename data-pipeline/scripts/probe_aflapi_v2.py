import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
base = "https://aflapi.afl.com.au/afl/v2"

for ep in [
    "/competitions",
    "/competitions?sport=sanfl",
    "/matches?competitionId=sanfl&season=2024",
    "/matches?compSeasonId=2024&teamId=adelaide",
    "/teams?competition=sanfl",
]:
    r = requests.get(base + ep, headers=H, timeout=20)
    print(ep, r.status_code, r.text[:350])
