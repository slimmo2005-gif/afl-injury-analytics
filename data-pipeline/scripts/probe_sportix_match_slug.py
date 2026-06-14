import re
import requests

for chunk in ["DplOWySu.js", "BNDGuO_r.js", "Cpj98o6Y.js", "DfJL1DE_.js", "f5f-uFW3.js"]:
    t = requests.get(f"https://wafl.com.au/_nuxt/{chunk}", timeout=30).text
    if "matches/" in t or "match/" in t:
        print("\n===", chunk, "===")
        for m in re.finditer(r'.{0,30}matches[^"\']{0,60}.{0,30}', t):
            print(m.group(0)[:120])

KEY = "290|yQfFH5WycjbEb8eUtVtTCXZt2aWOxFpDjUYEdxgQ9326de46"
H = {"Authorization": f"Bearer {KEY}", "Accept": "application/json"}
API = "https://api.sportix.cloud/public"

slug = "league-peel-thunder-v-east-fremantle-round-1-2024"
for ep in [
    f"/matches/{slug}",
    f"/match/{slug}",
    f"/matches?slug={slug}",
    f"/matches?filters[slug]={slug}",
]:
    r = requests.get(API + ep, headers=H, timeout=20)
    print(ep, r.status_code, r.text[:300])

# recent 2026 match
slug2 = "league-west-coast-v-peel-thunder-round-8-2026"
r2 = requests.get(f"{API}/matches/{slug2}", headers=H, timeout=20)
print("2026", r2.status_code, r2.text[:500])
