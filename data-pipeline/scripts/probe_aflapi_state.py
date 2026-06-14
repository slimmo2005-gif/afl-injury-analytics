import json
import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
base = "https://aflapi.afl.com.au/afl/v2"

for comp_id, name in [(14, "SANFL"), (12, "WAFL")]:
    for params in [
        {"competitionId": comp_id, "year": 2024},
        {"competitionIds": comp_id, "seasonYear": 2024},
        {"competition.id": comp_id, "season.year": 2024},
    ]:
        r = requests.get(f"{base}/matches", headers=H, params=params, timeout=20)
        print(name, params, r.status_code, r.text[:250])

# comp seasons
r = requests.get(f"{base}/compseasons", headers=H, params={"competitionId": 14}, timeout=20)
print("compseasons SANFL", r.status_code, r.text[:500])

r2 = requests.get(f"{base}/compseasons", headers=H, params={"competitionId": 12}, timeout=20)
print("compseasons WAFL", r2.status_code, r2.text[:500])
